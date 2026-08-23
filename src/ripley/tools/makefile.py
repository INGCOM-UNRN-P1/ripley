"""Student Makefile support: quality audit and modular builds via make."""

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import List, Optional

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
