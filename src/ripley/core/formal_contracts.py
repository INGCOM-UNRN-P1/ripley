"""Lightweight formal verification: Frama-C/ACSL prover wrapper (parsing lives in core.acsl)."""

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess

from ripley.core.acsl import ContractInventory, audit_coverage, extract_contracts


@dataclass
class FramaCResult:
    available: bool
    proved_goals: int = 0
    unproved_goals: int = 0
    raw_output: str = ""
    message: str = ""

    @property
    def all_proved(self) -> bool:
        return self.available and self.proved_goals > 0 and self.unproved_goals == 0


class FormalContractAnalyzer:
    """Ejecución del demostrador WP de Frama-C cuando está instalado.
    El inventario de contratos se delega a ``ripley.core.acsl``."""

    def extract_contracts(self, code: str, filename: str = "archivo.c") -> ContractInventory:
        return extract_contracts(code)

    def audit_contract_coverage(self, code: str, filename: str = "archivo.c") -> dict:
        return audit_coverage(code)

    def run_frama_c(self, source_path: Path | str, timeout_sec: int = 60) -> FramaCResult:
        frama_c_bin = shutil.which("frama-c")
        if not frama_c_bin:
            return FramaCResult(
                available=False,
                message="Frama-C no está instalado en el sistema; se omite la demostración automática.",
            )
        try:
            proc = subprocess.run(
                [frama_c_bin, "-wp", "-wp-rte", "-wp-print", str(Path(source_path))],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return FramaCResult(available=True, message="Timeout del demostrador WP.")
        except OSError as e:
            return FramaCResult(available=True, message=f"Error ejecutando Frama-C: {e}")

        output = proc.stdout + "\n" + proc.stderr
        proved = len(re.findall(r"^Proved goal", output, re.MULTILINE)) or len(
            re.findall(r"\[wp\].*?Proved", output)
        )
        unproved = len(re.findall(r"^Unknown goal|^Timeout goal|^Unproved goal", output, re.MULTILINE))

        return FramaCResult(
            available=True,
            proved_goals=proved,
            unproved_goals=unproved,
            raw_output=output[:4000],
            message="Demostración WP finalizada.",
        )
