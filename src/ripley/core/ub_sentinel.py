"""ub-sentinel — Auditor consolidado de Comportamiento Indefinido (nuevas.md).

Pipeline por niveles (todos con degradación elegante si falta la herramienta):

- Nivel 1: compilación instrumentada (``-fsanitize=undefined,address,leak``,
  ``-fno-sanitize-recover=all``, ``-ftrapv``) y ejecución contra los testcases
  de la convención ``tests/caso_*.in``; los stderr se clasifican con el
  parser pedagógico existente (:class:`SanitizerAnalyzer`).
- Nivel 2: análisis estático ``clang --analyze`` (si clang está instalado).
- Nivel 3: verificación formal ligera Frama-C WP (reutiliza
  :class:`FormalContractAnalyzer`; sólo si frama-c está instalado).
- Nivel 4: ThreadSanitizer (``-fsanitize=thread``) para ejercicios con hilos.

Salida: lista de :class:`HallazgoUB` con traducción pedagógica, lista de
herramientas omitidas y veredicto (hay errores / no hay / inconcluso).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from ripley.core.engine import compile_sources
from ripley.core.security import strip_c_comments_and_strings
from ripley.tools.formal_contracts import FormalContractAnalyzer
from ripley.tools.sanitizers import SanitizerAnalyzer

FLAGS_UB_N1 = ["-fsanitize=undefined,address,leak", "-fno-sanitize-recover=all", "-ftrapv"]
FLAGS_TSAN = ["-fsanitize=thread"]


@dataclass
class HallazgoUB:
    nivel: int
    categoria: str          # p.ej. INTEGER_OVERFLOW, CLANG_ANALYZER, FRAMA_C, TSAN
    archivo: str
    linea: Optional[int]
    mensaje: str
    sugerencia: str = ""
    severidad: str = "ERROR"  # ERROR | ADVERTENCIA


@dataclass
class ReporteUB:
    hallazgos: List[HallazgoUB] = field(default_factory=list)
    omitidos: List[str] = field(default_factory=list)
    niveles_ejecutados: List[int] = field(default_factory=list)

    @property
    def errores(self) -> List[HallazgoUB]:
        return [h for h in self.hallazgos if h.severidad == "ERROR"]

    @property
    def hay_errores(self) -> bool:
        return bool(self.errores)

    def resumen(self) -> str:
        niveles = ", ".join(str(n) for n in self.niveles_ejecutados) or "-"
        partes = [f"niveles ejecutados: {niveles}", f"{len(self.hallazgos)} hallazgo(s)"]
        if self.omitidos:
            partes.append(f"omitidos por faltar herramientas: {', '.join(self.omitidos)}")
        return "; ".join(partes)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _testcases(test_dir: Path) -> List[Path]:
    if not test_dir.is_dir():
        return []
    return sorted(test_dir.glob("caso_*.in"))


def _usa_hilos(fuentes: Sequence[Path]) -> bool:
    for f in fuentes:
        try:
            if re.search(r"#\s*include\s*<pthread\.h>|pthread_create", strip_c_comments_and_strings(f.read_text(encoding="utf-8", errors="replace"))):
                return True
        except OSError:
            continue
    return False


def _correr_binario(binario: Path, entrada: bytes, timeout: int):
    try:
        return subprocess.run([str(binario)], input=entrada, capture_output=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


# ---------------------------------------------------------------------------
# Niveles
# ---------------------------------------------------------------------------

def _nivel1_sanitizers(fuentes: Sequence[Path], tests: Sequence[Path],
                       reporte: ReporteUB, timeout: int,
                       workdir: Path, flags_extra: List[str],
                       categoria_prefix: str = "UBSAN") -> None:
    analizador = SanitizerAnalyzer()
    binario = workdir / "ub_sentinel.bin"
    comp = compile_sources(list(fuentes), binario, enable_asan=False,
                           extra_flags=FLAGS_UB_N1 + flags_extra)
    if not comp.success and _falta_runtime_sanitizers(comp.raw_stderr):
        # Host sin los runtimes de sanitizers (p.ej. libasan.so rota): el
        # pipeline se degrada; clang-analyzer/Frama-C siguen cubriendo.
        reporte.omitidos.append(
            "sanitizers de nivel 1 (el host no tiene libasan/libubsan instaladas)")
        return
    if not comp.success:
        # Con -Werror fuera: aquí compilamos sin -Werror; un fallo real es info útil.
        reporte.hallazgos.append(HallazgoUB(
            nivel=1, categoria=f"{categoria_prefix}.COMPILE",
            archivo=str(fuentes[0]) if fuentes else "?", linea=None,
            mensaje="La compilación instrumentada falló: " + (comp.raw_stderr[:300] or "sin detalle"),
            sugerencia="Revisá los errores reportados; suelen anticipar UB real.",
            severidad="ADVERTENCIA",
        ))
        return

    entradas = [(t.read_bytes(), t.name) for t in tests] or [(b"", "(stdin vacío)")]
    for datos, nombre in entradas:
        proc = _correr_binario(binario, datos, timeout)
        stderr = (proc.stderr or "") if proc is not None else ""
        if proc is None:
            reporte.hallazgos.append(HallazgoUB(
                nivel=1, categoria=f"{categoria_prefix}.TIMEOUT",
                archivo=nombre, linea=None,
                mensaje=f"El binario instrumentado excedió {timeout}s con el testcase {nombre}.",
                sugerencia="Un ciclo sin progreso o una espera infinita también es comportamiento a corregir.",
                severidad="ERROR",
            ))
            continue
        for f in analizador.parse_ubsan_runtime_errors(stderr):
            reporte.hallazgos.append(HallazgoUB(
                nivel=1, categoria=f"{categoria_prefix}.{f.category}",
                archivo=f.filename, linea=f.line,
                mensaje=f.message, sugerencia=f.pedagogical_hint,
            ))
        asan_error = re.search(
            r"==\d+==ERROR: AddressSanitizer: ([^\n]+)", stderr)
        if asan_error:
            ubic = re.search(r"#[0-9]+ 0x\S+ \S+ ([^\s:]+):(\d+)", stderr)
            reporte.hallazgos.append(HallazgoUB(
                nivel=1, categoria=f"{categoria_prefix}.ASAN",
                archivo=ubic.group(1) if ubic else nombre,
                linea=int(ubic.group(2)) if ubic else None,
                mensaje=f"AddressSanitizer: {asan_error.group(1).strip()}",
                sugerencia="Leé la traza completa del reporte: marca la operación inválida y dónde fue reservada/liberada la memoria.",
            ))


def _falta_runtime_sanitizers(stderr: str) -> bool:
    """True si el fallo de enlace es por runtimes de sanitizers ausentes."""
    return bool(re.search(r"cannot find[\s:.-]*(?:/usr/lib\S*/)?(?:lib|-l)?(asan|ubsan|tsan|lsan)",
                          stderr, re.IGNORECASE))


def _nivel2_clang_analyze(fuentes: Sequence[Path], reporte: ReporteUB) -> None:
    clang = shutil.which("clang")
    if clang is None:
        reporte.omitidos.append("clang (nivel 2)")
        return
    for fuente in fuentes:
        try:
            proc = subprocess.run(
                [clang, "--analyze", "-Xanalyzer", "-analyzer-output=text", str(fuente)],
                capture_output=True, text=True, timeout=60,
            )
        except subprocess.TimeoutExpired:
            reporte.omitidos.append("clang --analyze (timeout)")
            continue
        patron = re.compile(
            r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s*warning:\s*(?P<msg>[^\n]+)",
            re.MULTILINE,
        )
        for m in patron.finditer(proc.stdout + proc.stderr):
            msg = m.group("msg").strip()
            if msg.startswith(("division by zero", "Dereference of null pointer",
                               "Out of bound", "Use of zero-allocated memory",
                               "Assigned value is garbage")):
                severidad = "ERROR"
            else:
                severidad = "ADVERTENCIA"
            reporte.hallazgos.append(HallazgoUB(
                nivel=2, categoria="CLANG_ANALYZER",
                archivo=m.group("file"), linea=int(m.group("line")),
                mensaje=msg, sugerencia="El analizador estático modela todos los caminos posibles: si lo marca, el caso existe aunque tus pruebas no lo hayan disparado.",
                severidad=severidad,
            ))


def _nivel3_frama(fuentes: Sequence[Path], reporte: ReporteUB, timeout: int) -> None:
    frama = shutil.which("frama-c")
    if frama is None:
        reporte.omitidos.append("frama-c (nivel 3)")
        return
    analizador = FormalContractAnalyzer()
    for fuente in fuentes:
        resultado = analizador.run_frama_c(fuente, timeout_sec=timeout)
        if not resultado.available:
            reporte.omitidos.append("frama-c WP (no verificable)")
            continue
        if resultado.unproved_goals:
            reporte.hallazgos.append(HallazgoUB(
                nivel=3, categoria="FRAMA_C",
                archivo=str(fuente), linea=None,
                mensaje=f"Frama-C WP: {resultado.unproved_goals} objetivo(s) sin probar "
                        f"({resultado.proved_goals} probados).",
                sugerencia="Anotá contratos ACSL (@requires/@ensures) en el header para que la prueba formal pueda cerrar.",
                severidad="ADVERTENCIA",
            ))


def _nivel4_tsan(fuentes: Sequence[Path], tests: Sequence[Path],
                 reporte: ReporteUB, timeout: int, workdir: Path) -> None:
    if not _usa_hilos(fuentes):
        return  # nivel 4 sólo aplica a ejercicios con hilos
    binario = workdir / "ub_sentinel_tsan.bin"
    comp = compile_sources(list(fuentes), binario, enable_asan=False,
                           extra_flags=FLAGS_TSAN + ["-g"])
    if not comp.success:
        reporte.omitidos.append("tsan (compilación falló)")
        return
    for datos, nombre in ([(t.read_bytes(), t.name) for t in tests] or [(b"", "(vacío)")]):
        proc = _correr_binario(binario, datos, timeout * 2)
        stderr = (proc.stderr or "") if proc is not None else ""
        if "WARNING: ThreadSanitizer" in stderr or "data race" in stderr:
            primera = re.search(r"WARNING: ThreadSanitizer: ([^\n]+)", stderr)
            reporte.hallazgos.append(HallazgoUB(
                nivel=4, categoria="TSAN",
                archivo=nombre, linea=None,
                mensaje=f"ThreadSanitizer: {(primera.group(1) if primera else 'carrera de datos detectada').strip()}",
                sugerencia="Protegé las secciones críticas con mutex o reducí el estado compartido entre hilos.",
            ))


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------

def normalizar_nivel(nivel: int) -> int:
    """Acota el nivel al rango 1..4."""
    return max(1, min(4, int(nivel)))

# ---------------------------------------------------------------------------

def auditar_ub(fuentes: Sequence[Path], testcases: Sequence[Path],
               nivel_maximo: int = 4, timeout: int = 30) -> ReporteUB:
    """Ejecuta el pipeline ub-sentinel hasta ``nivel_maximo`` (1..4)."""
    nivel_maximo = normalizar_nivel(nivel_maximo)
    reporte = ReporteUB()

    with tempfile.TemporaryDirectory(prefix="ripley_ub_") as td:
        workdir = Path(td)
        tests = list(testcases)

        if nivel_maximo >= 1:
            reporte.niveles_ejecutados.append(1)
            _nivel1_sanitizers(fuentes, tests, reporte, timeout, workdir, flags_extra=[])

        if nivel_maximo >= 2:
            reporte.niveles_ejecutados.append(2)
            _nivel2_clang_analyze(fuentes, reporte)

        if nivel_maximo >= 3:
            reporte.niveles_ejecutados.append(3)
            _nivel3_frama(fuentes, reporte, timeout)

        if nivel_maximo >= 4:
            reporte.niveles_ejecutados.append(4)
            _nivel4_tsan(fuentes, tests, reporte, timeout, workdir)

    # dedupe estable
    vistos = set()
    únicos: List[HallazgoUB] = []
    for h in reporte.hallazgos:
        clave = (h.categoria, h.archivo, h.linea, h.mensaje)
        if clave not in vistos:
            vistos.add(clave)
            únicos.append(h)
    reporte.hallazgos = únicos
    return reporte
