"""AST and token-level code restrictions and requirements validator."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

from ripley.core.c_tokens import tokenize_c_code
from ripley.core.security import strip_c_comments_and_strings
from ripley.core.semantic_diff import extract_c_functions


@dataclass
class RestrictionViolation:
    violation_type: str  # "PROHIBIDO" o "REQUERIDO"
    construct: str
    message: str
    line_number: int = 1


class CodeRestrictionsValidator:
    """Valida restricciones y requisitos pedagógicos del enunciado sobre el código del estudiante."""

    def __init__(
        self,
        forbidden_constructs: Optional[List[str]] = None,
        required_constructs: Optional[List[str]] = None,
        forbidden_headers: Optional[List[str]] = None,
        forbidden_functions: Optional[List[str]] = None,
    ) -> None:
        self.forbidden_constructs = [c.lower() for c in (forbidden_constructs or [])]
        self.required_constructs = [c.lower() for c in (required_constructs or [])]
        self.forbidden_headers = [h.lower() for h in (forbidden_headers or [])]
        self.forbidden_functions = [f.lower() for f in (forbidden_functions or [])]

    def validate_file(self, file_path: Path | str) -> List[RestrictionViolation]:
        path = Path(file_path)
        if not path.exists():
            return []
        code = path.read_text(encoding="utf-8", errors="replace")
        return self.validate_code(code, filename=path.name)

    def validate_code(self, code: str, filename: str = "entrega.c") -> List[RestrictionViolation]:

        violations: List[RestrictionViolation] = []
        clean = strip_c_comments_and_strings(code)
        tokens = tokenize_c_code(code)
        functions = extract_c_functions(code)

        token_types = {t[0] for t in tokens}

        # 1. Validar Headers Prohibidos
        for forbidden_h in self.forbidden_headers:
            clean_h = forbidden_h.replace("<", "").replace(">", "").strip()
            pattern = re.compile(rf'#\s*include\s*[<"]{re.escape(clean_h)}[>"]', re.MULTILINE)
            for m in pattern.finditer(code):
                line = code[: m.start()].count("\n") + 1
                violations.append(
                    RestrictionViolation(
                        violation_type="PROHIBIDO",
                        construct=f"#{clean_h}",
                        message=f"Consigna violada en {filename}: Prohibido incluir la cabecera `<{clean_h}>`.",
                        line_number=line,
                    )
                )

        # 2. Validar Construcciones Prohibidas (for, while, goto, switch)
        for forb in self.forbidden_constructs:
            if forb in ("for", "while", "do", "goto", "switch"):
                token_target = f"K_{forb}"
                for tok, line_num in tokens:
                    if tok == token_target:
                        violations.append(
                            RestrictionViolation(
                                violation_type="PROHIBIDO",
                                construct=forb,
                                message=f"Consigna violada en {filename}: El enunciado prohíbe el uso de la estructura `{forb}`.",
                                line_number=line_num,
                            )
                        )
                        break

            elif forb == "recursion":
                # Validar si alguna función se llama a sí misma recursivamente
                for fname, fobj in functions.items():
                    # Buscar llamadas a fname dentro del cuerpo de fname
                    call_regex = re.compile(rf"\b{re.escape(fname)}\s*\(", re.MULTILINE)
                    if call_regex.search(fobj.raw_body):
                        violations.append(
                            RestrictionViolation(
                                violation_type="PROHIBIDO",
                                construct="recursion",
                                message=f"Consigna violada en {filename}: La función `{fname}` es recursiva, pero la consigna exige una solución estrictamente iterativa.",
                                line_number=fobj.start_line,
                            )
                        )

            elif forb == "pointers":
                # Detectar uso explícito de desreferencia o parámetros puntero
                if any(t[0].startswith("OP_*") or t[0].startswith("OP_&") for t in tokens):
                    violations.append(
                        RestrictionViolation(
                            violation_type="PROHIBIDO",
                            construct="pointers",
                            message=f"Consigna violada en {filename}: Se prohíbe el uso de punteros / operadores de dirección.",
                        )
                    )

        # 3. Validar Funciones Prohibidas (qsort, strlen, strcpy, malloc, etc.)
        for fn in self.forbidden_functions:
            fn_regex = re.compile(rf"\b{re.escape(fn)}\s*\(", re.MULTILINE)
            for m in fn_regex.finditer(clean):
                line = clean[: m.start()].count("\n") + 1
                violations.append(
                    RestrictionViolation(
                        violation_type="PROHIBIDO",
                        construct=fn,
                        message=f"Consigna violada en {filename}: Uso de función no autorizada `{fn}()`.",
                        line_number=line,
                    )
                )
                break

        # 4. Validar Requisitos Obligatorios
        for req in self.required_constructs:
            if req == "recursion":
                is_recursive = False
                for fname, fobj in functions.items():
                    if fname == "main":
                        continue
                    call_regex = re.compile(rf"\b{re.escape(fname)}\s*\(", re.MULTILINE)
                    if call_regex.search(fobj.raw_body):
                        is_recursive = True
                        break
                if not is_recursive:
                    violations.append(
                        RestrictionViolation(
                            violation_type="REQUERIDO",
                            construct="recursion",
                            message=f"Consigna incumplida en {filename}: El ejercicio exige una solución recursiva.",
                        )
                    )

            elif req in ("struct", "switch"):
                token_target = f"K_{req}"
                if not any(t[0] == token_target for t in tokens):
                    violations.append(
                        RestrictionViolation(
                            violation_type="REQUERIDO",
                            construct=req,
                            message=f"Consigna incumplida en {filename}: Se requiere el uso de `{req}`.",
                        )
                    )

            elif req == "malloc":
                if "malloc" not in clean and "calloc" not in clean and "realloc" not in clean:
                    violations.append(
                        RestrictionViolation(
                            violation_type="REQUERIDO",
                            construct="malloc",
                            message=f"Consigna incumplida en {filename}: Se requiere el uso de reserva dinámica de memoria (malloc/calloc).",
                        )
                    )

        return violations
