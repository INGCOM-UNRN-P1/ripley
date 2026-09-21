"""Linters AST de orden de evaluación y escritura sobre literales."""

import re
from typing import Dict, List

from ripley.core.linters import LinterObservation
from ripley.core.security import strip_c_comments_and_strings



# ============================================================================
# 10. Detector de Dependencia de Orden de Evaluación de Argumentos
# ============================================================================
class EvaluationOrderLinter:
    """Detecta llamadas a funciones con argumentos cuyo orden de evaluación es indefinido (unspecified behavior).

    Cubre dos formas:
      a) una variable mutada (i++, =) y leída en múltiples argumentos: f(i++, i);
      b) múltiples argumentos que son llamadas a funciones potencialmente con
         efectos secundarios: f(g(), h()) — el estándar no define el orden.
    """

    # Funciones matemáticas/transformacionales reconocidas como puras: exentas de (b).
    KNOWN_PURE_CALLS = {
        "abs", "labs", "llabs", "fabs", "sqrt", "pow", "floor", "ceil", "round",
        "fmin", "fmax", "fmod", "atan2", "sin", "cos", "tan", "exp", "log", "log10",
        "isalpha", "isdigit", "isalnum", "isspace", "isupper", "islower",
        "toupper", "tolower", "strlen", "strcmp", "memcmp",
    }

    _CALL_IN_ARG = re.compile(r"\b(?P<callee>[a-zA-Z_][a-zA-Z0-9_]*)\s*\(")

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        def _balanced_paren(start: int) -> str:
            depth = 0
            for i in range(start, len(clean)):
                if clean[i] == "(":
                    depth += 1
                elif clean[i] == ")":
                    depth -= 1
                    if depth == 0:
                        return clean[start + 1 : i]
            return ""

        def _split_top_level(args_text: str) -> List[str]:
            parts, current, depth = [], [], 0
            for ch in args_text:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                if ch == "," and depth == 0:
                    parts.append("".join(current).strip())
                    current = []
                else:
                    current.append(ch)
            parts.append("".join(current).strip())
            return [p for p in parts if p != ""]

        # Captura con paréntesis balanceados para soportar llamadas anidadas: suma(g(), h())
        call_open = re.compile(r"\b(?P<fn>[a-zA-Z_][a-zA-Z0-9_]*)\s*\(")

        for line_idx, line in enumerate(lines):
            offset_line_start = sum(len(l) + 1 for l in lines[:line_idx])
            for m in call_open.finditer(line):
                fn = m.group("fn")
                if fn in ("if", "while", "for", "switch", "sizeof"):
                    continue
                abs_start = offset_line_start + m.end() - 1
                args_str_full = _balanced_paren(abs_start)
                if "," not in args_str_full:
                    continue
                args = _split_top_level(args_str_full)
                if len(args) < 2:
                    continue

                # Extraer variables con mutación (++, --, =)
                mutated_vars = set()
                all_vars_per_arg = []

                for a in args:
                    m_mut = re.findall(r"(?:\+\+|--)\s*([a-zA-Z_][a-zA-Z0-9_]*)|([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\+\+|--)", a)
                    for mm in m_mut:
                        var = mm[0] or mm[1]
                        mutated_vars.add(var)
                    vars_in_a = set(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", a))
                    all_vars_per_arg.append(vars_in_a)

                # (a) Si alguna variable mutada aparece en más de un argumento
                mutation_found = False
                for mvar in mutated_vars:
                    count_args = sum(1 for vset in all_vars_per_arg if mvar in vset)
                    if count_args >= 2:
                        observations.append(
                            LinterObservation(
                                linter_name="evaluation_order_dependency",
                                filename=filename,
                                line=line_idx + 1,
                                severity="ADVERTENCIA",
                                message=f"Dependencia del orden de evaluación de argumentos en `{fn}(...)`: La variable `{mvar}` se modifica y se lee en múltiples argumentos.",
                                suggestion="En C, el orden de evaluación de los parámetros de una función no está definido en el estándar. Extraé las operaciones previas a la llamada en sentencias separadas.",
                            )
                        )
                        mutation_found = True
                        break

                if mutation_found:
                    continue

                # (b) Dos o más argumentos son llamadas a funciones no reconocidas como puras.
                called = [
                    mm.group("callee")
                    for a in args
                    if (mm := self._CALL_IN_ARG.search(a)) is not None
                ]
                impuras = [c for c in called if c not in self.KNOWN_PURE_CALLS and c not in ("if", "while", "for", "switch", "sizeof")]
                if len(impuras) >= 2:
                    observations.append(
                        LinterObservation(
                            linter_name="evaluation_order_dependency",
                            filename=filename,
                            line=line_idx + 1,
                            severity="ADVERTENCIA",
                            message=f"Posible dependencia del orden de evaluación en `{fn}(...)`: los argumentos invocan a {', '.join(f'{c}()' for c in impuras)} y el estándar no fija qué llamada se ejecuta primero.",
                            suggestion="Si esas funciones tienen efectos secundarios o comparten estado, guardá sus resultados en variables temporales antes de la llamada.",
                        )
                    )

        return observations


# ============================================================================
# 11. Auditoría de Modificación de Cadenas Literales en .rodata
# ============================================================================
class StringLiteralWriteLinter:
    """Detecta intentos de escritura en literales de cadena almacenados en memoria de solo lectura (.rodata).

    Cubre escrituras directas (`s[0] = 'H'`, `*s = 'H'`), la familia de
    funciones strcpy/strncpy/strcat/strncat/sprintf/snprintf/memcpy/memset
    y **alias** del puntero literal (`char *a = s; a[0] = 'x';`).
    En ejecución nativa (y bajo ASan) estas escrituras truenan al tocar la
    página de solo lectura; este auditor las atrapa antes de compilar.
    """

    WRITE_FAMILY = "strcpy|strncpy|strcat|strncat|sprintf|snprintf|memcpy|memset"

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        # 1. Identificar punteros asignados directamente a literales de cadena: char *p = "texto";
        literal_ptrs: Dict[str, int] = {}
        ptr_literal_regex = re.compile(
            r"\bchar\s*\*\s*(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\"[^\"]*\"\s*;",
            re.MULTILINE,
        )

        for m in ptr_literal_regex.finditer(code):
            var_name = m.group("var")
            line = code[: m.start()].count("\n") + 1
            literal_ptrs[var_name] = line

        # 1bis. Alias: `char *a = p;` donde p ya apunta a un literal.
        aliases: Dict[str, tuple] = {}  # alias -> (raíz, línea_decl_alias)
        alias_regex = re.compile(
            r"\bchar\s*\*\s*(?P<alias>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?P<root>[a-zA-Z_][a-zA-Z0-9_]*)\s*;",
            re.MULTILINE,
        )
        for m in alias_regex.finditer(code):
            alias, root = m.group("alias"), m.group("root")
            if root in literal_ptrs and alias not in literal_ptrs:
                decl_line = code[: m.start()].count("\n") + 1
                aliases[alias] = (root, decl_line)

        def _write_targets(var_name: str, line: str) -> bool:
            return bool(
                re.search(rf"\b{var_name}\s*\[[^\]]+\]\s*=[^=]", line)
                or re.search(rf"\*\s*{var_name}\s*=[^=]", line)
                or re.search(rf"\b(?:{self.WRITE_FAMILY})\s*\(\s*{var_name}\b", line)
            )

        # 2. Escrituras sobre los punteros literales y sobre sus alias.
        targets: Dict[str, tuple] = {v: ("literal", d) for v, d in literal_ptrs.items()}
        for alias, (root, decl_line) in aliases.items():
            targets[alias] = (root, decl_line)

        for var_name, (root_kind_or_root, decl_line) in targets.items():
            via = (
                f"el puntero `{var_name}`"
                if root_kind_or_root == "literal"
                else f"el alias `{var_name}` (apunta al literal declarado con `{root_kind_or_root}`)"
            )
            for line_idx, line in enumerate(lines):
                line_num = line_idx + 1
                if line_num == decl_line or line.strip().startswith("char "):
                    continue
                if _write_targets(var_name, line):
                    observations.append(
                        LinterObservation(
                            linter_name="rodata_string_write",
                            filename=filename,
                            line=line_num,
                            severity="ERROR",
                            message=f"Intento de modificación de cadena literal en `.rodata` a través de {via}.",
                            suggestion=(
                                'Las cadenas literales `"..."` residen en páginas de solo lectura y su '
                                "escritura aborta en tiempo de ejecución. Para cadenas mutables usá un "
                                f"arreglo `char buffer[] = \"...\";` o asigná memoria con `malloc`. "
                                "El flag `-Wwrite-strings` vuelve estos casos errores de compilación."
                            ),
                        )
                    )

        return observations
