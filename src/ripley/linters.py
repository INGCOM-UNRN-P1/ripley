"""Specialized linters for magic numbers, internal code duplication, and naming conventions."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from ripley.plagiarism import tokenize_c_code
from ripley.security import strip_c_comments_and_strings
from ripley.semantic_diff import extract_c_functions


@dataclass
class LinterObservation:
    linter_name: str
    filename: str
    line: int
    severity: str  # "ADVERTENCIA" | "ESTILO" | "ERROR"
    message: str
    suggestion: str = ""


# ============================================================================
# 1. Detector de Números Mágicos (Magic Numbers)
# ============================================================================
class MagicNumberLinter:
    """Detecta el uso de literales numéricos sin nombre en lugar de constantes o enumeradores."""

    def __init__(self, allowed_numbers: Optional[Set[str]] = None) -> None:
        self.allowed_numbers = allowed_numbers or {"0", "1", "2", "-1"}

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        tokens = tokenize_c_code(code)

        # Detectar líneas de #define para ignorar sus constantes
        defined_lines = {
            idx + 1
            for idx, line in enumerate(clean.splitlines())
            if line.strip().startswith("#define") or line.strip().startswith("enum")
        }

        for tok, line_num in tokens:
            if tok == "NUM" and line_num not in defined_lines:
                # Extraer el valor literal en la línea
                line_text = clean.splitlines()[line_num - 1] if line_num <= len(clean.splitlines()) else ""
                # Buscar números en la línea
                for match in re.finditer(r"\b(?P<val>\d+)\b", line_text):
                    val = match.group("val")
                    if val not in self.allowed_numbers:
                        observations.append(
                            LinterObservation(
                                linter_name="magic_numbers",
                                filename=filename,
                                line=line_num,
                                severity="ESTILO",
                                message=f"Uso de número mágico `{val}` sin nombre.",
                                suggestion=f"Definí una constante `#define NOMBRE {val}` o usá un `enum` con significado claro.",
                            )
                        )
                        break

        return observations


# ============================================================================
# 2. Detector de Duplicación Interna de Código (Copy-Paste Detector)
# ============================================================================
@dataclass
class InternalCloneMatch:
    function_a: str
    function_b: str
    shared_tokens: int
    line_a: int
    line_b: int
    description: str


class InternalCloneLinter:
    """Detecta bloques duplicados o copiados y pegados dentro del mismo código del estudiante."""

    def __init__(self, min_token_length: int = 12) -> None:
        self.min_token_length = min_token_length

    def analyze(self, code: str, filename: str = "archivo.c") -> List[InternalCloneMatch]:
        functions = extract_c_functions(code)
        func_list = list(functions.values())
        clones: List[InternalCloneMatch] = []

        for i in range(len(func_list)):
            for j in range(i + 1, len(func_list)):
                f_a = func_list[i]
                f_b = func_list[j]

                tokens_a = f_a.normalized_tokens
                tokens_b = f_b.normalized_tokens

                # Buscar la subsecuencia contigua común más larga
                longest_seq = 0
                for start_a in range(len(tokens_a) - self.min_token_length + 1):
                    for start_b in range(len(tokens_b) - self.min_token_length + 1):
                        match_len = 0
                        while (
                            start_a + match_len < len(tokens_a)
                            and start_b + match_len < len(tokens_b)
                            and tokens_a[start_a + match_len] == tokens_b[start_b + match_len]
                        ):
                            match_len += 1

                        if match_len > longest_seq:
                            longest_seq = match_len

                if longest_seq >= self.min_token_length:
                    clones.append(
                        InternalCloneMatch(
                            function_a=f_a.name,
                            function_b=f_b.name,
                            shared_tokens=longest_seq,
                            line_a=f_a.start_line,
                            line_b=f_b.start_line,
                            description=(
                                f"Bloque duplicado de {longest_seq} tokens entre `{f_a.name}()` (línea {f_a.start_line}) "
                                f"y `{f_b.name}()` (línea {f_b.start_line}). Fomentá la reutilización de código extrayendo una función auxiliar."
                            ),
                        )
                    )

        return clones


# ============================================================================
# 3. Linter de Convenciones de Nombres Configurable
# ============================================================================
@dataclass
class NamingConfig:
    variable_style: str = "snake_case"  # "snake_case" | "camelCase"
    function_style: str = "snake_case"  # "snake_case" | "camelCase"
    constant_style: str = "UPPER_CASE"  # "UPPER_CASE"
    type_prefix: Optional[str] = "t_"  # ej. "t_" o None


class NamingConventionLinter:
    """Valida convenciones de nombres en variables, funciones, tipos y constantes."""

    def __init__(self, config: Optional[NamingConfig] = None) -> None:
        self.config = config or NamingConfig()

    def is_snake_case(self, name: str) -> bool:
        return bool(re.match(r"^[a-z][a-z0-9_]*$", name))

    def is_camel_case(self, name: str) -> bool:
        return bool(re.match(r"^[a-z][a-zA-Z0-9]*$", name))

    def is_upper_case(self, name: str) -> bool:
        return bool(re.match(r"^[A-Z][A-Z0-9_]*$", name))

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)

        # 1. Validar Nombres de Funciones
        functions = extract_c_functions(code)
        for fname, fobj in functions.items():
            if fname in ("main", "setUp", "tearDown"):
                continue

            if self.config.function_style == "snake_case" and not self.is_snake_case(fname):
                observations.append(
                    LinterObservation(
                        linter_name="naming_conventions",
                        filename=filename,
                        line=fobj.start_line,
                        severity="ESTILO",
                        message=f"La función `{fname}` no respeta la convención `snake_case`.",
                        suggestion=f"Renombrala a `{self._to_snake(fname)}`.",
                    )
                )

        # 2. Validar Constantes de #define (permitiendo indentación)
        define_regex = re.compile(r"^[ \t]*#\s*define\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s+(?P<val>.+)$", re.MULTILINE)
        for m in define_regex.finditer(clean):
            cname = m.group("name")
            line = clean[: m.start()].count("\n") + 1
            if not self.is_upper_case(cname):
                observations.append(
                    LinterObservation(
                        linter_name="naming_conventions",
                        filename=filename,
                        line=line,
                        severity="ESTILO",
                        message=f"La constante `#define {cname}` no respeta la convención `UPPER_CASE`.",
                        suggestion=f"Usá mayúsculas como `{cname.upper()}`.",
                    )
                )

        # 3. Validar Tipos typedef / struct (permitiendo indentación)
        typedef_regex = re.compile(r"^[ \t]*typedef\s+struct[^{;]*\{[^}]*\}\s*(?P<tname>[a-zA-Z0-9_]+)\s*;", re.MULTILINE)

        for m in typedef_regex.finditer(clean):
            tname = m.group("tname")
            line = clean[: m.start()].count("\n") + 1
            if self.config.type_prefix and not tname.startswith(self.config.type_prefix):
                observations.append(
                    LinterObservation(
                        linter_name="naming_conventions",
                        filename=filename,
                        line=line,
                        severity="ESTILO",
                        message=f"El tipo `{tname}` no incluye el prefijo obligatorio `{self.config.type_prefix}`.",
                        suggestion=f"Renombralo con prefijo como `{self.config.type_prefix}{tname}`.",
                    )
                )

        return observations

    def _to_snake(self, name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
