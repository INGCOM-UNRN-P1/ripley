"""Coverage-guided fuzzing for C assignments using gcov instrumentation as feedback."""

from dataclasses import dataclass, field
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
from typing import List, Optional, Set

from ripley.compiler import Compiler
from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig

_INTERESTING_INTS = [0, 1, -1, 127, 128, 255, 256, 1024, 65535, 2147483647, -2147483648]


@dataclass
class CoverageFuzzFinding:
    input_data: str
    returncode: int
    stderr_excerpt: str


@dataclass
class CoverageFuzzReport:
    available: bool
    iterations: int = 0
    final_coverage_lines: int = 0
    corpus_size: int = 0
    crashes: List[CoverageFuzzFinding] = field(default_factory=list)
    message: str = ""

    def summary(self) -> str:
        if not self.available:
            return self.message
        crash_txt = f", {len(self.crashes)} crashes" if self.crashes else ""
        return (
            f"{self.iterations} iteraciones | líneas cubiertas: {self.final_coverage_lines} "
            f"| corpus: {self.corpus_size}{crash_txt}"
        )


class CoverageGuidedFuzzer:
    """Fuzzer guiado por cobertura: compila con ``--coverage`` (gcov), ejecuta
    mutaciones y prioriza las entradas que descubren líneas nuevas del código
    del alumno. No requiere AFL++ ni LibFuzzer."""

    def __init__(self, seed: int = 42, timeout_per_run_sec: float = 5.0) -> None:
        self.random = random.Random(seed)
        self.timeout_sec = timeout_per_run_sec
        self._compiler = Compiler(
            CompilerConfig(executable="gcc", flags=["-std=c11", "-Wall", "--coverage"]),
            LimitsConfig(timeout_segundos=10),
            SandboxConfig(),
        )

    # ------------------------------------------------------------------
    # Compilación instrumentada y medición de cobertura
    # ------------------------------------------------------------------
    def _compile_instrumented(self, source: Path, workdir: Path) -> Optional[Path]:
        comp = self._compiler.compile([source], workdir / "fuzz_target")
        if not comp.success:
            return None
        return workdir / "fuzz_target"

    def _covered_lines(self, source: Path, workdir: Path, binary: Path, stdin_data: str) -> Optional[Set[int]]:
        """Ejecuta el binario instrumentado y devuelve las líneas cubiertas de esa única corrida."""
        gcov_bin = shutil.which("gcov")
        if not gcov_bin:
            return None

        # Purga previa: sin esto las cuentas se acumulan en el .gcda y el
        # feedback deja de reflejar la corrida individual.
        for stale in workdir.glob("*.gcda"):
            stale.unlink(missing_ok=True)

        try:
            subprocess.run(
                [str(binary)],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                cwd=str(workdir),
            )
        except (subprocess.TimeoutExpired, OSError):
            return set()

        gcda_files = sorted(workdir.glob("*.gcda"))
        covered: Set[int] = set()

        # Formato texto vía stdout (-t): líneas `cuenta: línea:código`.
        for gcda in gcda_files:
            try:
                proc = subprocess.run(
                    [gcov_bin, "-t", str(gcda)],
                    capture_output=True,
                    text=True,
                    cwd=str(workdir),
                    timeout=15,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            for out_line in (proc.stdout or "").splitlines():
                m = re.match(r"^\s*(?P<count>\d+|-|\*+):\s*(?P<lineno>\d+):", out_line)
                if m and m.group("count").isdigit() and int(m.group("count")) > 0:
                    covered.add(int(m.group("lineno")))
        return covered

    # ------------------------------------------------------------------
    # Mutación guiada por feedback de cobertura
    # ------------------------------------------------------------------
    def _mutate(self, data: bytes) -> bytes:
        buf = bytearray(data)
        strategy = self.random.randrange(5)
        if not buf:
            buf.extend(str(self.random.choice(_INTERESTING_INTS)).encode() + b"\n")
            return bytes(buf)
        if strategy == 0:  # Bit flip
            idx = self.random.randrange(len(buf))
            buf[idx] ^= 1 << self.random.randrange(8)
        elif strategy == 1:  # Insertar entero interesante como texto
            token = f"{self.random.choice(_INTERESTING_INTS)} ".encode()
            pos = self.random.randrange(len(buf) + 1)
            buf[pos:pos] = token
        elif strategy == 2:  # Borrar byte
            idx = self.random.randrange(len(buf))
            del buf[idx]
        elif strategy == 3:  # Duplicar segmento
            start = self.random.randrange(len(buf))
            end = min(len(buf), start + max(1, len(buf) // 4))
            buf[end:end] = buf[start:end]
        else:  # Reemplazar byte con valor de borde
            idx = self.random.randrange(len(buf))
            buf[idx] = self.random.choice([0x00, 0xFF, 0x7F, 0x80, 0x0A])
        return bytes(buf)

    # ------------------------------------------------------------------
    # Ciclo principal de fuzzing
    # ------------------------------------------------------------------
    def fuzz(
        self,
        source_path: Path | str,
        seed_inputs: Optional[List[str]] = None,
        max_iterations: int = 200,
        stall_limit: int = 30,
    ) -> CoverageFuzzReport:
        src = Path(source_path)
        with tempfile.TemporaryDirectory(prefix="ripley_cfuzz_") as temp_dir:
            workdir = Path(temp_dir)
            binary = self._compile_instrumented(src, workdir)
            if binary is None:
                return CoverageFuzzReport(available=False, message="No se pudo compilar la fuente para instrumentar cobertura.")

            seeds = seed_inputs or ["0\n", "1\n", "abc\n"]
            corpus: List[bytes] = [s.encode() if isinstance(s, str) else s for s in seeds]
            covered_global: Set[int] = set()
            first_cov = self._covered_lines(src, workdir, binary, corpus[0].decode(errors="replace"))
            if first_cov is None:
                return CoverageFuzzReport(available=False, message="La herramienta `gcov` no está disponible en el sistema.")
            covered_global |= first_cov
            for extra_seed in corpus[1:]:
                extra_cov = self._covered_lines(src, workdir, binary, extra_seed.decode(errors="replace"))
                if extra_cov:
                    covered_global |= extra_cov

            crashes: List[CoverageFuzzFinding] = []
            stalled = 0
            iterations = 0

            while iterations < max_iterations and stalled < stall_limit:
                iterations += 1
                base = self.random.choice(corpus)
                candidate = self._mutate(base)

                run_result = subprocess.run(
                    [str(binary)],
                    input=candidate.decode(errors="replace"),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec + 5,
                )
                if run_result.returncode != 0:
                    crashes.append(
                        CoverageFuzzFinding(
                            input_data=candidate.decode(errors="replace"),
                            returncode=run_result.returncode,
                            stderr_excerpt=run_result.stderr.strip()[:400],
                        )
                    )

                new_cov = self._covered_lines(src, workdir, binary, candidate.decode(errors="replace")) or set()
                fresh = new_cov - covered_global
                if fresh:
                    covered_global |= fresh
                    corpus.append(candidate)
                    stalled = 0
                else:
                    stalled += 1

            return CoverageFuzzReport(
                available=True,
                iterations=iterations,
                final_coverage_lines=len(covered_global),
                corpus_size=len(corpus),
                crashes=crashes,
                message="Fuzzing guiado por cobertura finalizado.",
            )
