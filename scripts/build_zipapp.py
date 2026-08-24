#!/usr/bin/env python3
"""Builds a self-contained ripley-check zipapp (.pyz) for zero-install student use.

Uso:
    python scripts/build_zipapp.py [-o dist/ripley_check.pyz]

El paquete resultante incluye los módulos de la zona estudiante
(models, core, tools, pipeline, cli sin teacher) y se ejecuta con:

    ./ripley_check.pyz doctor

Requisitos del entorno destino: Python >= 3.11 con typer y rich
instalados (pip install typer rich). Las herramientas externas opcionales
(gcc, valgrind...) se detectan en tiempo de ejecución.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGE = SRC / "ripley"

STUDENT_ZONES = ["models", "core", "tools", "pipeline", "cli"]
STUDENT_CLI_MODULES = {"__init__.py", "_common.py", "student.py"}
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

    # Módulos planos compartidos: schema de config y shims estudiantiles
    for flat in sorted(PACKAGE.glob("*.py")):
        name = flat.name
        if name in EXCLUDE_TEACHER_SHIMS or name == "cli.py":
            continue
        text = flat.read_text(encoding="utf-8")
        if name == "config.py":
            files[f"ripley/{name}"] = text.encode("utf-8")
            continue
        target_zone = next((z for z in ("core", "tools") if f"ripley.{z}." in text), None)
        if target_zone:
            files[f"ripley/{name}"] = text.encode("utf-8")

    # __init__.py raíz y cli/__init__ reducido para no arrastrar teacher
    root_init = PACKAGE / "__init__.py"
    if root_init.exists():
        files["ripley/__init__.py"] = root_init.read_bytes()

    cli_pkg = PACKAGE / "cli"
    for mod in STUDENT_CLI_MODULES:
        p = cli_pkg / mod
        if mod == "__init__.py":
            content = '"""CLI estudiantil autocontenido (zipapp)."""\nfrom ripley.cli.student import app\n'
            files["ripley/cli/__init__.py"] = content.encode("utf-8")
        elif p.exists():
            files[f"ripley/cli/{mod}"] = p.read_bytes()

    return files


def build(output: Path) -> Path:
    if not (PACKAGE / "cli" / "student.py").exists():
        sys.exit("ERROR: no se encontró ripley/cli/student.py; ¿ejecutaste desde la raíz del repo?")

    files = collect_modules()
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


def smoke_test(app_path: Path) -> bool:
    """Verifica que el zipapp responde --help con el intérprete actual.

    Requiere typer/rich instalados en ese entorno (requisito documentado
    del paquete estudiantil).
    """
    import subprocess

    proc = subprocess.run([sys.executable, str(app_path), "--help"], capture_output=True, text=True)
    ok = proc.returncode == 0 and ("Verificación temprana" in proc.stdout or "ripley" in proc.stdout)
    if not ok:
        print(proc.stdout, proc.stderr)
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default="dist/ripley.pyz")
    args = parser.parse_args()
    out = build(Path(args.output))
    if not smoke_test(out):
        sys.exit("ERROR: el smoke test del zipapp falló.")
    print("Smoke test OK: el zipapp responde correctamente como ripley.")


if __name__ == "__main__":
    main()

