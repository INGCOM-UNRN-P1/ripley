"""Peak stack usage auditor based on GCC -fstack-usage instrumentation (.su files)."""

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List


@dataclass
class StackUsageEntry:
    source_file: str
    line: int
    function: str
    size_bytes: int
    qualifier: str  # "static" | "dynamic" | "bounded"

    @property
    def is_dynamic(self) -> bool:
        return self.qualifier == "dynamic"


@dataclass
class StackUsageReport:
    available: bool
    compiler_available: bool = True
    entries: List[StackUsageEntry] = field(default_factory=list)
    threshold_bytes: int = 1024
    message: str = ""

    @property
    def offenders(self) -> List[StackUsageEntry]:
        return [e for e in self.entries if e.size_bytes > self.threshold_bytes]

    @property
    def dynamic_entries(self) -> List[StackUsageEntry]:
        return [e for e in self.entries if e.is_dynamic]


class StackUsageAuditor:
    """Compila con ``-fstack-usage`` y reporta las funciones que consumen más
    stack del umbral permitido, además de asignaciones dinámicas (VLA/alloca)."""

    _SU_REGEX = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):(?P<func>[^\t]+)\t(?P<size>\d+)\t(?P<qual>\w+)$"
    )

    def __init__(self, threshold_bytes: int = 1024, compiler_executable: str = "gcc") -> None:
        self.threshold_bytes = threshold_bytes
        self.compiler_executable = compiler_executable

    def audit(self, source_files: List[Path]) -> StackUsageReport:
        compiler_bin = shutil.which(self.compiler_executable)
        if not compiler_bin:
            return StackUsageReport(
                available=False,
                compiler_available=False,
                threshold_bytes=self.threshold_bytes,
                message=f"Compilador '{self.compiler_executable}' no disponible en el sistema.",
            )

        with tempfile.TemporaryDirectory(prefix="ripley_stack_") as temp_dir:
            out_dir = Path(temp_dir)
            cmd = [
                compiler_bin,
                "-fstack-usage",
                "-c",
                *[str(Path(s)) for s in source_files],
                "-o",
                str(out_dir / "audit.o"),
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired:
                return StackUsageReport(
                    available=False,
                    threshold_bytes=self.threshold_bytes,
                    message="Timeout durante la compilación con -fstack-usage.",
                )
            except OSError as e:
                return StackUsageReport(
                    available=False,
                    threshold_bytes=self.threshold_bytes,
                    message=f"Error ejecutando el compilador: {e}",
                )

            entries: List[StackUsageEntry] = []
            su_files = sorted(out_dir.glob("*.su"))
            if not su_files and proc.returncode != 0:
                return StackUsageReport(
                    available=False,
                    threshold_bytes=self.threshold_bytes,
                    message=f"Compilación fallida: {proc.stderr.strip()[:300]}",
                )

            for su_file in su_files:
                for raw_line in su_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = self._SU_REGEX.match(raw_line.strip())
                    if not m:
                        continue
                    entries.append(
                        StackUsageEntry(
                            source_file=Path(m.group("file")).name,
                            line=int(m.group("line")),
                            function=m.group("func").strip(),
                            size_bytes=int(m.group("size")),
                            qualifier=m.group("qual"),
                        )
                    )

            entries.sort(key=lambda e: e.size_bytes, reverse=True)
            return StackUsageReport(
                available=True,
                entries=entries,
                threshold_bytes=self.threshold_bytes,
                message="Análisis de consumo de stack completado.",
            )
