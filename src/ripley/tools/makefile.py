"""Student Makefile support: quality audit and modular builds via make."""

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Sequence

from ripley.models import LinterObservation


@dataclass
class MakeBuildResult:
    success: bool
    target: str = "all"
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    binary_path: Optional[Path] = None
    human_errors: str = ""
    message: str = ""


class MakefileAnalyzer:
    """Audita la calidad de un Makefile estudiantil y delega la compilación modular a make.

    Reglas didácticas:
      - objetivo `all` presente y primero
      - objetivo `clean` definido
      - `.PHONY` declarado para targets no-archivo
      - usa variables (CC/CFLAGS) en vez de hardcodear el compilador
    """

    TARGET_REGEX = re.compile(r"^([a-zA-Z0-9_./-]+)\s*:", re.MULTILINE)

    def analyze(self, makefile_text: str, filename: str = "Makefile") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        targets = [t for t in self.TARGET_REGEX.findall(makefile_text) if not t.startswith(".")]
        has_phony = ".PHONY" in makefile_text

        if "all" not in targets:
            observations.append(LinterObservation(
                linter_name="makefile_quality", filename=filename, line=1, severity="ADVERTENCIA",
                message="Falta el objetivo por defecto `all`.",
                suggestion="El primer objetivo es el que ejecuta `make` sin argumentos; declará `all` al inicio.",
            ))
        elif targets[0] != "all":
            observations.append(LinterObservation(
                linter_name="makefile_quality", filename=filename, line=1, severity="ADVERTENCIA",
                message=f"El primer objetivo es `{targets[0]}`, no `all`: `make` a secas no compila lo esperado.",
                suggestion="Reordená el Makefile para que `all` sea el primer objetivo.",
            ))

        if "clean" not in targets:
            observations.append(LinterObservation(
                linter_name="makefile_quality", filename=filename, line=1, severity="ESTILO",
                message="Falta el objetivo `clean` para borrar binarios y objetos.",
                suggestion='Agregá: clean:\n\trm -f *.o app',
            ))

        if targets and not has_phony:
            observations.append(LinterObservation(
                linter_name="makefile_quality", filename=filename, line=1, severity="ADVERTENCIA",
                message="`.PHONY` no está declarado para los objetivos no-archivo.",
                suggestion="Evitá colisiones con archivos del mismo nombre: .PHONY: all clean",
            ))

        if re.search(r"^\t\s*(gcc|cc)\b", makefile_text, re.MULTILINE) and "$(CC)" not in makefile_text:
            observations.append(LinterObservation(
                linter_name="makefile_quality", filename=filename, line=1, severity="ADVERTENCIA",
                message="Compilador hardcodeado en las recetas.",
                suggestion="Usá variables: CC = gcc ... $(CC) $(CFLAGS) -c fuente.c",
            ))

        # Receta que arranca con espacios donde make exige TAB ('missing separator').
        if re.search(r"^[ ]+(?:gcc|cc|g\+\+|clang|\$\([A-Za-z_]+\))\b", makefile_text, re.MULTILINE):
            observations.append(LinterObservation(
                linter_name="makefile_quality", filename=filename, line=1, severity="ERROR",
                message="Recetas con espacios en lugar de TAB: make fallará con 'missing separator'.",
                suggestion="Las recetas deben empezar con un TAB literal, nunca espacios.",
            ))

        return observations


def _executable_snapshot(directory: Path) -> set:
    result = set()
    for f in directory.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink() and f.stat().st_mode & 0o111:
                result.add((str(f), f.stat().st_mtime_ns))
        except OSError:
            continue
    return result


def make_build(
    directory: Path | str,
    executable: str = "make",
    target: str = "all",
    timeout_sec: int = 30,
    expected_binary: str = "",
) -> MakeBuildResult:
    """Ejecuta `make <target>` y descubre el binario producido.

    Descubrimiento del binario, en orden:
      1. ``expected_binary`` si fue indicado.
      2. Archivo ejecutable nuevo o modificado durante la compilación.
    """
    make_bin = shutil.which(executable)
    d = Path(directory)
    makefile = d / "Makefile"
    if makefile.exists() is False and (d / "makefile").exists():
        makefile = d / "makefile"
    if not makefile.exists():
        return MakeBuildResult(success=False, target=target,
                               message=f"Sin Makefile en {d}: compilación directa requerida.")
    if not make_bin:
        return MakeBuildResult(success=False, target=target,
                               message=f"'{executable}' no está disponible en el sistema.")

    before = _executable_snapshot(d)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [make_bin, "-C", str(d), target],
            capture_output=True, text=True, timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return MakeBuildResult(success=False, target=target,
                               message=f"Timeout ({timeout_sec}s) durante `make {target}`.")
    elapsed = time.monotonic() - start
    after = _executable_snapshot(d)

    result = MakeBuildResult(success=proc.returncode == 0, target=target,
                             returncode=proc.returncode,
                             stdout=proc.stdout[-4000:], stderr=proc.stderr[-4000:])

    from ripley.core.gcc_translator import summarize_for_humans, translate_stderr
    combined_err = proc.stderr or proc.stdout
    translated = translate_stderr(combined_err)
    if translated:
        result.human_errors = summarize_for_humans(translated)

    if result.success:
        nuevos_o_modificados = [Path(p) for p, _ in (after - before)]
        if expected_binary:
            exacta = d / expected_binary
            result.binary_path = exacta if exacta.exists() else None
        elif nuevos_o_modificados:
            result.binary_path = max(nuevos_o_modificados, key=lambda p: p.stat().st_mtime)
        if result.binary_path is None:
            # make exitoso pero sin binario detectado (p.ej. solo objetos).
            result.message = "`make` terminó OK pero no se detectó binario nuevo."
    else:
        result.message = f"`make {target}` falló en {elapsed:.1f}s."
    return result


# ============================================================================
# Verificación integral de proyectos con Makefile
# ============================================================================
@dataclass
class MakeVerificationReport:
    """Resultado del circuito completo de verificación de un proyecto."""

    directory: str
    estructura: List[LinterObservation] = field(default_factory=list)
    build_ok: bool = False
    binary_path: Optional[Path] = None
    human_errors: str = ""
    idempotent: Optional[bool] = None        # `make -q` tras el build: nada por hacer
    missing_header_deps: List[str] = field(default_factory=list)  # .h que NO disparan rebuild
    orphan_sources: List[str] = field(default_factory=list)       # .c jamás compilados
    clean_ok: Optional[bool] = None          # None = sin target clean
    test_ok: Optional[bool] = None           # None = sin target test
    message: str = ""

    @property
    def ok(self) -> bool:
        return (
            self.build_ok
            and self.idempotent is not False
            and not self.missing_header_deps
            and not self.orphan_sources
            and self.clean_ok is not False
            and self.test_ok is not False
            and not any(o.severity == "ERROR" for o in self.estructura)
        )


def _run_make(directory: Path, *args: str, executable: str = "make",
              timeout: int = 30) -> "subprocess.CompletedProcess":
    return subprocess.run(
        [executable, "-C", str(directory), *args],
        capture_output=True, text=True, timeout=timeout,
    )


def _dry_run_commands(directory: Path, unconditional: bool = False,
                      executable: str = "make", timeout: int = 30) -> List[str]:
    """Recetas que make ejecutaría (sin correrlas). Con unconditional=True (-B)
    devuelve el plan COMPLETO aunque los objetivos estén al día."""
    args = ["-n"] + (["-B"] if unconditional else [])
    try:
        proc = _run_make(directory, *args, executable=executable, timeout=timeout)
    except subprocess.TimeoutExpired:
        return []
    cmds = []
    for raw_line in proc.stdout.splitlines():
        # limpiar prefijos "make[1]: Entering..." y eco recursivo
        cleaned = re.sub(r"^make\[\d+\]:", "", raw_line).strip()
        if cleaned and not cleaned.startswith(("make", "echo")):
            cmds.append(cleaned)
    return cmds


def _project_sources(directory: Path) -> List[Path]:
    """Fuentes .c del proyecto como rutas RELATIVAS al directorio raíz."""
    d = Path(directory)
    return sorted(
        p.relative_to(d) for p in d.rglob("*.c")
        if not any(part.startswith(".") for part in p.parts)
    )


def _included_headers(directory: Path, sources: List[Path]) -> List[Path]:
    headers_by_name: Dict[str, Path] = {
        h.name: h for h in directory.rglob("*.h")
        if not any(part.startswith(".") for part in h.relative_to(directory).parts)
    }
    included: List[Path] = []
    seen_names: set = set()
    inc_regex = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)
    for s in sources:
        try:
            text = (directory / s).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name in inc_regex.findall(text):
            if name in headers_by_name and name not in seen_names:
                seen_names.add(name)
                included.append(headers_by_name[name])
    return included


def verify_project(
    directory: Path | str,
    executable: str = "make",
    target: str = "all",
    expected_binary: str = "",
    timeout: int = 60,
    run_test_target: bool = True,
) -> MakeVerificationReport:
    """Circuito completo sobre un proyecto con Makefile:

    1. Auditoría estructural (objetivos, .PHONY, TABs…)
    2. Build real con descubrimiento de binario
    3. Idempotencia: `make -q` debe indicar que no hay nada por hacer
    4. Dependencias de headers: tocar cada .h incluido DEBE disparar rebuild
    5. Fuentes huérfanas: todo .c del proyecto debe aparecer en `make -nB`
    6. Target `test` (si existe) ejecutado y evaluado por código de salida
    7. Target `clean`: los artefactos deben desaparecer
    """
    d = Path(directory)
    report = MakeVerificationReport(directory=str(d))

    makefile = d / "Makefile"
    if not makefile.exists():
        makefile = d / "makefile"
    if not makefile.exists():
        report.message = f"Sin Makefile en {d}."
        return report

    # 0. Targets disponibles (una sola lectura)
    mk_text = makefile.read_text(encoding="utf-8", errors="replace")
    targets = MakefileAnalyzer.TARGET_REGEX.findall(mk_text)

    # 1. Estructura
    report.estructura = MakefileAnalyzer().analyze(mk_text, makefile.name)

    make_bin = shutil.which(executable)
    if not make_bin:
        report.message = f"'{executable}' no disponible."
        return report

    # 2. Build
    build = make_build(d, executable=executable, target=target,
                       expected_binary=expected_binary, timeout_sec=timeout)
    report.build_ok = build.success
    report.binary_path = build.binary_path
    report.human_errors = build.human_errors
    if not build.success:
        report.message = "El proyecto no compila vía make."
        return report

    sources = _project_sources(d)

    # 3. Idempotencia: -q sale 0 si está al día, 1 si habría trabajo, 2 = error
    q = _run_make(d, "-q", executable=executable, timeout=timeout)
    report.idempotent = (q.returncode == 0)

    # 4. Headers: tocar cada .h incluido debe hacer que make quiera reconstruir
    for header in _included_headers(d, sources)[:8]:
        saved = header.stat().st_mtime_ns
        bumped = saved + 1_000_000_000  # +1s
        try:
            os.utime(header, ns=(bumped, bumped))
            qh = _run_make(d, "-q", executable=executable, timeout=timeout)
            if qh.returncode != 1:
                report.missing_header_deps.append(header.name)
        finally:
            os.utime(header, ns=(saved, saved))

    # 5. Huérfanos: plan completo (-nB) debe mencionar cada fuente del proyecto
    plan_cmds = _dry_run_commands(d, unconditional=True, executable=executable, timeout=timeout)
    plan_text = "\n".join(plan_cmds)
    referenced = {s.name for s in sources if s.name in plan_text}
    report.orphan_sources = sorted(s.as_posix() for s in sources if s.name not in referenced)

    # 6. Target test (convención didáctica opcional)
    if run_test_target and "test" in targets:
        tproc = _run_make(d, "test", executable=executable, timeout=timeout)
        report.test_ok = (tproc.returncode == 0)

    # 7. Clean al final: deja el workspace prístino y valida limpieza
    if "clean" in targets:
        artefactos_antes = {
            p for p in d.rglob("*")
            if p.is_file() and p.suffix in (".o", ".out") or (p.is_file() and os.access(p, os.X_OK) and p.suffix == "")
        }
        _run_make(d, "clean", executable=executable, timeout=timeout)
        restantes = {p for p in artefactos_antes if p.exists()}
        report.clean_ok = (len(restantes) == 0)

    partes = []
    partes.append("build OK" if report.build_ok else "build FALLÓ")
    if report.idempotent is False:
        partes.append("re-build innecesario detectado (deps redundantes)")
    if report.missing_header_deps:
        partes.append(f"headers sin dependencia: {', '.join(report.missing_header_deps)}")
    if report.orphan_sources:
        partes.append(f"fuentes huérfanas: {', '.join(report.orphan_sources)}")
    report.message = " · ".join(partes)
    return report


# ============================================================================
# Integración inversa: Ripley como parte del Makefile (ripley.mk)
# ============================================================================
def suggest_sources(directory: Path | str) -> List[str]:
    """Fuentes .c sugeridas para variables de make (orden estable, rutas relativas)."""
    d = Path(directory)
    return sorted(p.as_posix() for p in _project_sources(d))


def render_ripley_mk(
    sources: Sequence[str],
    practica: str = "",
    ripley_bin: str = "$(RIPLEY)",
) -> str:
    """Genera un `ripley.mk` listo para `include` al final del Makefile del alumno."""
    src_list = " ".join(sources) if sources else "*.c"
    prac_flag = f"--practica {practica}" if practica else ""
    watch_flag = f" --practica {practica}" if practica else ""
    return f"""# ripley.mk — generado por Ripley ({datetime.now():%Y-%m-%d})
# Uso: agregar al FINAL de tu Makefile:   include ripley.mk
# Requiere ripley-check en PATH (pipx install ripley)

RIPLEY ?= {ripley_bin}
SOURCES ?= {src_list}
PRACTICA ?= {practica}

.PHONY: ripley ripley-verify ripley-lint ripley-watch ripley-explain help

## Verificación completa temprana (misma que usará el docente)
ripley-verify:
{chr(9)}{ripley_bin} run {prac_flag} $(SOURCES)

## Linter rápido del archivo principal
ripley-lint:
{chr(9)}{ripley_bin} lint -f $(firstword $(SOURCES))

## Live TDD: re-verifica al guardar (Ctrl+C para salir)
ripley-watch:
{chr(9)}{ripley_bin} watch{watch_flag} .

## Traducir el último log de compilación a lenguaje natural
ripley-explain: ;@{ripley_bin} explain build.log 2>/dev/null || echo "Generá build.log: make 2> build.log"

help: ## lista los objetivos de ripley
{chr(9)}@grep -E '^## ' $(lastword $(MAKEFILE_LIST)) | sed 's/^## //'
"""
