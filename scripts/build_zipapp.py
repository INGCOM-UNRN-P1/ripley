#!/usr/bin/env python3
"""Builds a self-contained ripley-check zipapp (.pyz) for zero-install student use.

Uso:
    python scripts/build_zipapp.py [-o dist/ripley_check.pyz]

El paquete resultante incluye los módulos de la zona estudiante
(models, core, tools, pipeline, cli sin teacher) y se ejecuta con:

    ./ripley_check.pyz doctor

Requisitos del entorno destino: solo Python >= 3.11. Las dependencias de
ejecución (typer, rich, jinja2, pyyaml…, fijadas por uv.lock) viajan dentro
del zipapp en su versión de Python puro: entorno descarga ripley.pyz y lo
ejecuta sin venv ni pip (N-RIPLEY-07). Las herramientas externas opcionales
(gcc, valgrind...) se detectan en tiempo de ejecución.

Se construye con el venv del proyecto sincronizado (`uv sync`): las
dependencias se copian de ahí, sin las extensiones compiladas (PyYAML y
MarkupSafe usan su implementación en Python si no las encuentran). Las que
solo existen en otra plataforma (colorama en Windows) se descargan con uv.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from importlib import metadata
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGE = SRC / "ripley"

STUDENT_ZONES = ["models", "core", "tools", "pipeline"]  # de cli/, solo lo del estudiante (abajo)
EXCLUDE_TEACHER_SHIMS = {
    # shims planos que re-exportan el flujo docente
    "ingest.py", "mapping.py", "db.py", "evaluate.py", "reporter.py",
    "templates.py", "exporter.py", "plagiarism.py", "practice.py",
}

BOOTSTRAP = """\
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ripley.cli.student import app  # noqa: E402

if __name__ == "__main__":
    app()
"""


def collect_modules() -> dict[str, bytes]:
    files: dict[str, bytes] = {}

    def add(path: Path, arcname: str) -> None:
        if path.is_file():
            files[arcname] = path.read_bytes()
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if "__pycache__" in child.parts or child.is_dir():
                    continue
                rel = child.relative_to(path)
                files[f"{arcname}/{'/'.join(rel.parts)}"] = child.read_bytes()

    for zone in STUDENT_ZONES:
        add(PACKAGE / zone, f"ripley/{zone}")

    # Módulos planos: todos salvo los shims del flujo docente. Antes entraban solo los que citaban
    # ripley.core/ripley.tools, y config_modelos.py (salido de partir config.py) quedaba afuera:
    # `ripley check` terminaba en ModuleNotFoundError aunque --help y doctor anduvieran.
    for flat in sorted(PACKAGE.glob("*.py")):
        if flat.name in EXCLUDE_TEACHER_SHIMS or flat.name in ("cli.py", "__main__.py"):
            continue
        files[f"ripley/{flat.name}"] = flat.read_bytes()

    # __init__.py raíz y cli/__init__ reducido para no arrastrar teacher
    root_init = PACKAGE / "__init__.py"
    if root_init.exists():
        files["ripley/__init__.py"] = root_init.read_bytes()

    # cli/: el __init__ reducido, _common y los módulos del CLI estudiantil (student*.py); los del
    # docente (teacher*.py) dependen de ripley.teacher, que no viaja en el zipapp.
    files["ripley/cli/__init__.py"] = b'"""CLI estudiantil autocontenido (zipapp)."""\nfrom ripley.cli.student import app\n'
    for p in sorted((PACKAGE / "cli").glob("*.py")):
        if p.name == "_common.py" or p.name.startswith("student"):
            files[f"ripley/cli/{p.name}"] = p.read_bytes()

    return files


COMPILADOS = (".so", ".pyd", ".dll", ".dylib", ".pyc")


def dependencias_fijadas() -> list[tuple[str, str]]:
    """Dependencias de ejecución (sin grupos de desarrollo) con la versión de uv.lock.

    Las que vienen de git (yutani: no está en PyPI) llevan su referencia `git+…@commit` en
    lugar de la versión: sin esto quedaban fuera del zipapp.
    """
    salida = subprocess.run(
        ["uv", "export", "--no-dev", "--no-emit-project", "--no-hashes", "--frozen"],
        cwd=SRC.parent, capture_output=True, text=True, check=True,
    ).stdout
    return (re.findall(r"(?m)^([A-Za-z0-9._-]+)==([^\s;]+)", salida)
            + re.findall(r"(?m)^([A-Za-z0-9._-]+) @ (git\+[^\s;]+)", salida))


def _commit_instalado(dist: metadata.Distribution) -> str:
    """Commit desde el que se instaló una dependencia de git (direct_url.json), o ""."""
    try:
        datos = json.loads(dist.read_text("direct_url.json") or "{}")
    except ValueError:
        return ""
    return str(datos.get("vcs_info", {}).get("commit_id", ""))


def _archivos_de(dist: metadata.Distribution) -> dict[str, bytes]:
    archivos = {}
    for relativo in dist.files or []:
        nombre = str(relativo).replace("\\", "/")
        if nombre.startswith("..") or "__pycache__" in nombre or nombre.endswith(COMPILADOS):
            continue
        ruta = Path(dist.locate_file(relativo))
        if ruta.is_file():
            archivos[nombre] = ruta.read_bytes()
    return archivos


def collect_dependencies() -> dict[str, bytes]:
    """Archivos de Python puro de cada dependencia fijada, listos para la raíz del zipapp."""
    archivos: dict[str, bytes] = {}
    faltantes = []
    for nombre, version in dependencias_fijadas():
        try:
            dist = metadata.distribution(nombre)
        except metadata.PackageNotFoundError:
            faltantes.append((nombre, version))
            continue
        if version.startswith("git+"):
            if not version.endswith("@" + _commit_instalado(dist)):
                sys.exit(f"ERROR: {nombre} instalado no es el commit que pide uv.lock ({version}): corré `uv sync`.")
        elif dist.version != version:
            sys.exit(f"ERROR: {nombre} {dist.version} instalado y uv.lock pide {version}: corré `uv sync`.")
        archivos.update(_archivos_de(dist))
    for nombre, version in faltantes:
        # Solo existen en otra plataforma (p. ej. colorama en Windows): se bajan sin instalar.
        with tempfile.TemporaryDirectory() as tmp:
            requisito = f"{nombre} @ {version}" if version.startswith("git+") else f"{nombre}=={version}"
            proc = subprocess.run(["uv", "pip", "install", "--quiet", "--no-deps", "--target", tmp,
                                   requisito], capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"AVISO: no se pudo incluir {nombre}=={version} ({proc.stderr.strip()[:120]})")
                continue
            for ruta in Path(tmp).rglob("*"):
                rel = ruta.relative_to(tmp).as_posix()
                if ruta.is_file() and "__pycache__" not in rel and not rel.endswith(COMPILADOS) \
                        and not rel.startswith("bin/"):
                    archivos[rel] = ruta.read_bytes()
    return archivos


def build(output: Path, con_dependencias: bool = True) -> Path:
    if not (PACKAGE / "cli" / "student.py").exists():
        sys.exit("ERROR: no se encontró ripley/cli/student.py; ¿ejecutaste desde la raíz del repo?")

    files = collect_modules()
    if con_dependencias:
        dependencias = collect_dependencies()
        repetidos = set(dependencias) & set(files)
        if repetidos:
            sys.exit(f"ERROR: archivos de dependencias que pisan a ripley: {sorted(repetidos)[:5]}")
        files.update(dependencias)
    output.parent.mkdir(parents=True, exist_ok=True)

    # 1. Escribir archivo zipapp con shebang ejecutable
    with open(output, "wb") as f:
        f.write(b"#!/usr/bin/env python3\n")
        with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("__main__.py", BOOTSTRAP)
            for arcname in sorted(files):
                zf.writestr(arcname, files[arcname])

    output.chmod(0o755)

    # 2. Generar alias/copia ripley_check.pyz si el target principal es ripley.pyz
    if output.name == "ripley.pyz":
        check_alias = output.parent / "ripley_check.pyz"
        shutil.copyfile(output, check_alias)
        check_alias.chmod(0o755)
    elif output.name == "ripley_check.pyz":
        main_alias = output.parent / "ripley.pyz"
        shutil.copyfile(output, main_alias)
        main_alias.chmod(0o755)

    size_kb = output.stat().st_size / 1024
    print(f"Zipapp generado: {output} ({size_kb:.0f} KB, {len(files)} módulos)")
    return output


def smoke_test(app_path: Path, autocontenido: bool = True) -> bool:
    """Verifica que el zipapp responde --help.

    Con `autocontenido`, se ejecuta con `python -S` (sin site-packages): así se
    comprueba que no depende de nada instalado, como en la máquina del estudiante.
    """
    opciones = ["-S"] if autocontenido else []
    proc = subprocess.run([sys.executable, *opciones, str(app_path), "--help"], capture_output=True, text=True)
    ok = proc.returncode == 0 and ("Verificación temprana" in proc.stdout or "ripley" in proc.stdout)
    if not ok:
        print(proc.stdout, proc.stderr)
        return False
    # --help y doctor no importan todo: un módulo que falta recién aparece al usar `check`. Se
    # importan todos los módulos de ripley que viajan en el zipapp.
    modulos = sorted(n[:-3].replace("/", ".").removesuffix(".__init__") for n in zipfile.ZipFile(app_path).namelist()
                     if n.startswith("ripley/") and n.endswith(".py"))
    programa = ("import importlib, sys\n"
                f"sys.path.insert(0, {str(app_path)!r})\n"
                "fallas = []\n"
                f"for m in {modulos!r}:\n"
                "    try:\n"
                "        importlib.import_module(m)\n"
                "    except Exception as e:\n"
                "        fallas.append(f'{m}: {e!r}')\n"
                "print('\\n'.join(fallas))\n")
    proc = subprocess.run([sys.executable, *opciones, "-c", programa], capture_output=True, text=True)
    if proc.returncode != 0 or proc.stdout.strip():
        print("Módulos del zipapp que no importan:", proc.stdout, proc.stderr, sep="\n")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default="dist/ripley.pyz")
    parser.add_argument("--sin-dependencias", action="store_true",
                        help="no incluir typer/rich/…: el destino tiene que tenerlas instaladas")
    args = parser.parse_args()
    out = build(Path(args.output), con_dependencias=not args.sin_dependencias)
    if not smoke_test(out, autocontenido=not args.sin_dependencias):
        sys.exit("ERROR: el smoke test del zipapp falló.")
    print("Smoke test OK: el zipapp responde correctamente como ripley.")


if __name__ == "__main__":
    main()

