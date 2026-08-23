"""Lightweight formal verification via Frama-C/ACSL contracts: static parsing + prover wrapper."""

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess
from typing import Dict, List, Optional

from ripley.core.security import strip_c_comments_and_strings


@dataclass
class ACSLContract:
    function_name: str
    line: int
    requires: List[str] = field(default_factory=list)
    ensures: List[str] = field(default_factory=list)
    assigns: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        return bool(self.requires) and bool(self.ensures)


@dataclass
class ContractInventory:
    contracts: List[ACSLContract] = field(default_factory=list)
    functions_without_contract: List[str] = field(default_factory=list)
    total_functions: int = 0


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
    """Inventario de contratos ACSL (`/*@ requires ... ensures ... */`) y
    ejecución opcional del demostrador WP de Frama-C cuando está instalado."""

    _CONTRACT_REGEX = re.compile(r"/\*@\s*(?P<body>.*?)\*/", re.DOTALL)
    _FUNCTION_REGEX = re.compile(
        r"^[ \t]*(?P<ret>[a-zA-Z_][a-zA-Z0-9_ \t\*]*?)\s+\**(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)"
        r"\s*\([^;{)]*\)\s*\{",
        re.MULTILINE,
    )

    # ------------------------------------------------------------------
    # Capa 1: parseo estático de contratos ACSL
    # ------------------------------------------------------------------
    def extract_contracts(self, code: str, filename: str = "archivo.c") -> ContractInventory:
        clean = strip_c_comments_and_strings(code.replace("/*@", "___ACSL___").replace("*/", "___END_ACSL___"))
        inventory = ContractInventory()

        contract_blocks: List[tuple] = []
        for m in re.finditer(r"___ACSL___(?P<body>.*?)___END_ACSL___", clean, re.DOTALL):
            body = m.group("body")
            if not re.search(r"\b(requires|ensures|assigns)\b", body):
                continue  # Comentario doxygen normal, no contrato ACSL.
            contract = ACSLContract(function_name="", line=clean[: m.start()].count("\n") + 1)
            contract.requires = [s.strip() for s in re.findall(r"\brequires\b\s+([^;]+);", body)]
            contract.ensures = [s.strip() for s in re.findall(r"\bensures\b\s+([^;]+);", body)]
            assigns_m = re.search(r"\bassigns\b\s+([^;]+);", body)
            if assigns_m:
                contract.assigns = assigns_m.group(1).strip()
            contract_blocks.append((contract, m.end()))

        functions = list(self._FUNCTION_REGEX.finditer(clean))
        inventory.total_functions = len(functions)

        for fn_match in functions:
            fn_start = fn_match.start()
            fn_name = fn_match.group("name")
            attached = None
            for contract, block_end in contract_blocks:
                if block_end > fn_start:
                    continue
                between = clean[block_end:fn_start].strip()
                if not between or re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_ \t\*&\n]*", between):
                    attached = contract
                    break
            if attached is not None:
                attached.function_name = fn_name
                inventory.contracts.append(attached)
            else:
                inventory.functions_without_contract.append(fn_name)

        return inventory

    def audit_contract_coverage(self, code: str, filename: str = "archivo.c") -> Dict[str, object]:
        """Resumen de cobertura de contratos para el informe docente."""
        inventory = self.extract_contracts(code, filename)
        incomplete = [c.function_name for c in inventory.contracts if not c.is_complete]
        covered = len(inventory.contracts)
        coverage_pct = (covered / inventory.total_functions * 100) if inventory.total_functions else 100.0
        return {
            "total_functions": inventory.total_functions,
            "documented": covered,
            "coverage_pct": round(coverage_pct, 1),
            "incomplete_contracts": incomplete,
            "undocumented_functions": inventory.functions_without_contract,
        }

    # ------------------------------------------------------------------
    # Capa 2: demostrador WP de Frama-C (si está instalado)
    # ------------------------------------------------------------------
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
