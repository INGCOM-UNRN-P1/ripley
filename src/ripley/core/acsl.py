"""Pure ACSL contract parsing (no subprocess): extracts requires/ensures/assigns blocks."""

from dataclasses import dataclass, field
import re
from typing import List, Tuple

from ripley.core.security import strip_c_comments_and_strings


@dataclass
class ACSLContract:
    function_name: str = ""
    line: int = 0
    requires: List[str] = field(default_factory=list)
    ensures: List[str] = field(default_factory=list)
    assigns: str | None = None

    @property
    def is_complete(self) -> bool:
        return bool(self.requires) and bool(self.ensures)


@dataclass
class ContractInventory:
    contracts: List[ACSLContract] = field(default_factory=list)
    functions_without_contract: List[str] = field(default_factory=list)
    total_functions: int = 0


_ACSL_MARKER_START = "___ACSL___"
_ACSL_MARKER_END = "___END_ACSL___"
_BLOCK_REGEX = re.compile(
    rf"{_ACSL_MARKER_START}(?P<body>.*?){_ACSL_MARKER_END}", re.DOTALL
)
_FUNCTION_REGEX = re.compile(
    r"^[ \t]*(?P<ret>[a-zA-Z_][a-zA-Z0-9_ \t\*]*?)\s+\**(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)"
    r"\s*\([^;{)]*\)\s*\{",
    re.MULTILINE,
)


def _preprocess(code: str) -> str:
    """Marca los bloques /*@ ... */ para sobrevivir a la limpieza de comentarios."""
    return strip_c_comments_and_strings(
        code.replace("/*@", _ACSL_MARKER_START).replace("*/", _ACSL_MARKER_END)
    )


def extract_contracts(code: str) -> ContractInventory:
    """Inventario de contratos ACSL adjuntos a funciones de nivel superior."""
    clean = _preprocess(code)
    inventory = ContractInventory()

    contract_blocks: List[Tuple[ACSLContract, int]] = []
    for m in _BLOCK_REGEX.finditer(clean):
        body = m.group("body")
        if not re.search(r"\b(requires|ensures|assigns)\b", body):
            continue  # Comentario doxygen normal, no contrato ACSL.
        contract = ACSLContract(line=clean[: m.start()].count("\n") + 1)
        contract.requires = [s.strip() for s in re.findall(r"\brequires\b\s+([^;]+);", body)]
        contract.ensures = [s.strip() for s in re.findall(r"\bensures\b\s+([^;]+);", body)]
        assigns_m = re.search(r"\bassigns\b\s+([^;]+);", body)
        if assigns_m:
            contract.assigns = assigns_m.group(1).strip()
        contract_blocks.append((contract, m.end()))

    functions = list(_FUNCTION_REGEX.finditer(clean))
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


def audit_coverage(code: str) -> dict:
    """Resumen de cobertura de contratos para informes docentes y estudiantiles."""
    inventory = extract_contracts(code)
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
