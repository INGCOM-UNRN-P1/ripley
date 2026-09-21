"""Comprehensive style and quality rule definitions following Programación I apunte."""

from dataclasses import dataclass
import re
from typing import List

from ripley.core.security import strip_c_comments_and_strings
from ripley.core.semantic_diff import extract_c_functions

@dataclass
class P1RuleObservation:
    rule_code: str
    filename: str
    line: int
    severity: str
    title: str
    message: str
    suggestion: str


class P1RuleChecker:
    """Evaluador exhaustivo de las reglas de estilo y buenas prácticas de Programación I."""

    def __init__(self) -> None:
        try:
            from ripley.core.entrypoints import get_satellite_plugin
            self.satellite = get_satellite_plugin("style")
        except Exception:
            self.satellite = None

    def analyze(self, code: str, filename: str = "archivo.c") -> List[P1RuleObservation]:
        observations: List[P1RuleObservation] = []
        raw_lines = code.splitlines()
        clean = strip_c_comments_and_strings(code)
        clean_lines = clean.splitlines()
        functions = extract_c_functions(code)

        # --------------------------------------------------------------------
        # 0. 0x0001h: Variables cortas (< 5 letras: "A mejorar" / 1 letra: "Revisión manual")
        # --------------------------------------------------------------------
        var_decl_pattern = re.compile(
            r"\b(?:int|char|float|double|size_t|ssize_t|long|short|unsigned|signed|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|bool|FILE|struct\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+_t|t_[a-zA-Z0-9_]+)\s+(?P<decl>[^;{}()]+);",
            re.MULTILINE,
        )
        for m in var_decl_pattern.finditer(clean):
            decl_str = m.group("decl")
            line_num = clean[: m.start()].count("\n") + 1
            items = decl_str.split(",")
            for item in items:
                item_clean = re.sub(r"=.*$", "", item).strip()
                item_clean = re.sub(r"\[.*\]", "", item_clean).strip()
                var_match = re.search(r"[*]*\s*([a-zA-Z_][a-zA-Z0-9_]*)$", item_clean)
                if var_match:
                    vname = var_match.group(1)
                    if vname in ("main", "setUp", "tearDown"):
                        continue
                    if len(vname) < 5:
                        if len(vname) == 1:
                            if vname.lower() in ("i", "j", "k"):
                                observations.append(
                                    P1RuleObservation(
                                        rule_code="0x0001h",
                                        filename=filename,
                                        line=line_num,
                                        severity="ESTILO",
                                        title=P1_RULES_CATALOG["0x0001h"].title,
                                        message=f"Variable de 1 letra: `{vname}` (Aceptable para contadores `i`, `j`, `k`, pero requiere revisión manual de contexto).",
                                        suggestion="Conservar únicamente como contador o índice local de bucle; no emplear para datos de dominio (Regla 0x0001h).",
                                    )
                                )
                            else:
                                observations.append(
                                    P1RuleObservation(
                                        rule_code="0x0001h",
                                        filename=filename,
                                        line=line_num,
                                        severity="ADVERTENCIA",
                                        title=P1_RULES_CATALOG["0x0001h"].title,
                                        message=f"Variable de 1 letra no descriptiva: `{vname}` (Requiere revisión manual obligatoria).",
                                        suggestion=f"Renombrá la variable `{vname}` por un identificador representativo del dominio (Regla 0x0001h).",
                                    )
                                )
                        else:
                            observations.append(
                                P1RuleObservation(
                                    rule_code="0x0001h",
                                    filename=filename,
                                    line=line_num,
                                    severity="ESTILO",
                                    title=P1_RULES_CATALOG["0x0001h"].title,
                                    message=f"Nombre de variable corto ({len(vname)} letras): `{vname}` (A mejorar).",
                                    suggestion=f"Se recomienda utilizar identificadores más descriptivos y expresivos que expliciten el propósito de la variable (Regla 0x0001h).",
                                )
                            )

        # --------------------------------------------------------------------
        # 1. 0x0002h: Una declaración de variable por línea
        # --------------------------------------------------------------------

        multi_decl_regex = re.compile(
            r"^[ \t]*(?:int|char|float|double|size_t|long|short)\s+([a-zA-Z_][a-zA-Z0-9_]*\s*(?:=\s*[^,;]+)?\s*,\s*)+[a-zA-Z_][a-zA-Z0-9_]*",
            re.MULTILINE,
        )
        for m in multi_decl_regex.finditer(clean):
            line_num = clean[: m.start()].count("\n") + 1
            observations.append(
                P1RuleObservation(
                    rule_code="0x0002h",
                    filename=filename,
                    line=line_num,
                    severity=P1_RULES_CATALOG["0x0002h"].severity,
                    title=P1_RULES_CATALOG["0x0002h"].title,
                    message="Múltiples declaraciones de variables en la misma línea.",
                    suggestion="Declarar cada variable en su propia línea (ej. `int a;\\nint b;`).",
                )
            )

        # --------------------------------------------------------------------
        # 2. 0x0004h: Espacio antes y después de operadores binarios
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            for op in ("==", "!=", "<=", ">=", "&&", r"\|\|"):
                clean_op = op.replace("\\", "")
                if re.search(rf"[a-zA-Z0-9_]{op}[a-zA-Z0-9_]", line):
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x0004h",
                            filename=filename,
                            line=idx,
                            severity=P1_RULES_CATALOG["0x0004h"].severity,
                            title=P1_RULES_CATALOG["0x0004h"].title,
                            message=f"Falta espacio alrededor del operador binario `{clean_op}`.",
                            suggestion=f"Colocá un espacio antes y después: `x {clean_op} y`.",
                        )
                    )

        # --------------------------------------------------------------------
        # 3. 0x0006h: Asterisco de punteros junto al identificador (int *p vs int* p)
        # --------------------------------------------------------------------
        star_type_regex = re.compile(r"\b(?:int|char|float|double|void|size_t)\*\s+[a-zA-Z_][a-zA-Z0-9_]*\b")
        for idx, line in enumerate(clean_lines, start=1):
            if star_type_regex.search(line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x0006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x0006h"].severity,
                        title=P1_RULES_CATALOG["0x0006h"].title,
                        message="El asterisco de puntero está pegado al tipo (`tipo* ptr`) en lugar del identificador.",
                        suggestion="Escribí `tipo *ptr` para mantener la convención estándar de la cátedra.",
                    )
                )

        # --------------------------------------------------------------------
        # 4. 0x0007h / 0x0008h: Nomenclatura camelCase en variables vs MAYUSCULAS en constantes
        # --------------------------------------------------------------------
        camel_var_regex = re.compile(r"\b(?:int|char|float|double|size_t)\s+(?P<v>[a-z]+[A-Z][a-zA-Z0-9]*)\b")
        for idx, line in enumerate(clean_lines, start=1):
            m = camel_var_regex.search(line)
            if m:
                vname = m.group("v")
                observations.append(
                    P1RuleObservation(
                        rule_code="0x0007h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x0007h"].severity,
                        title=P1_RULES_CATALOG["0x0007h"].title,
                        message=f"La variable `{vname}` usa camelCase en lugar de snake_case.",
                        suggestion=f"Renombrala en minúsculas separadas por guión bajo (ej. `{self._to_snake(vname)}`).",
                    )
                )

        # --------------------------------------------------------------------
        # 5. 0x0009h: Longitud de línea > 79 caracteres
        # --------------------------------------------------------------------
        for idx, line in enumerate(raw_lines, start=1):
            if len(line) > 79:
                observations.append(
                    P1RuleObservation(
                        rule_code="0x0009h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x0009h"].severity,
                        title=P1_RULES_CATALOG["0x0009h"].title,
                        message=f"La línea excede los 79 caracteres ({len(line)} columnas).",
                        suggestion="Dividí la instrucción o cadena en múltiples líneas para respetar el estándar de 80 columnas.",
                    )
                )

        # --------------------------------------------------------------------
        # 6. 0x1001h: Todas las estructuras de control deben utilizar llaves
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            s_line = line.strip()
            for kw in ("if", "for", "while"):
                match = re.search(rf"\b{kw}\s*\([^\)]*\)\s*([^{{;]+);", s_line)
                if match and not s_line.endswith("{") and not match.group(1).startswith("//"):
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x1001h",
                            filename=filename,
                            line=idx,
                            severity=P1_RULES_CATALOG["0x1001h"].severity,
                            title=P1_RULES_CATALOG["0x1001h"].title,
                            message=f"Estructura de control `{kw}` en una sola línea sin llaves {{}}.",
                            suggestion="Envolvé siempre el cuerpo de la estructura con llaves `{ ... }` en líneas propias.",
                        )
                    )

        # --------------------------------------------------------------------
        # 7. 0x1002h: Prohibición de continue
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if re.search(r"\bcontinue\s*;", line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1002h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x1002h"].severity,
                        title=P1_RULES_CATALOG["0x1002h"].title,
                        message="Uso prohibido de la sentencia `continue`.",
                        suggestion="Reestructurá el lazo utilizando una condición lógica o bandera booleana.",
                    )
                )

        # --------------------------------------------------------------------
        # 8. 0x1006h: Prohibición de goto
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if re.search(r"\bgoto\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;", line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x1006h"].severity,
                        title=P1_RULES_CATALOG["0x1006h"].title,
                        message="Uso prohibido de la instrucción `goto`.",
                        suggestion="Reemplazá `goto` por estructuras de control estructuradas estándar (`while`, `for`, `if`).",
                    )
                )

        # --------------------------------------------------------------------
        # 9. 0x1007h: Prohibición del operador ternario ?:
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if "?" in line and ":" in line and not line.strip().startswith("//") and not line.strip().startswith("case "):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1007h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x1007h"].severity,
                        title=P1_RULES_CATALOG["0x1007h"].title,
                        message="Uso desaconsejado del operador condicional ternario `?:`.",
                        suggestion="Reemplazá el operador ternario por un bloque estructurado `if / else`.",
                    )
                )

        # --------------------------------------------------------------------
        # 10. 0x1008h: Switch debe incluir default
        # --------------------------------------------------------------------
        switch_matches = re.finditer(r"\bswitch\s*\([^\)]*\)\s*\{(?P<body>[^}]*)\}", clean)
        for sm in switch_matches:
            s_body = sm.group("body")
            if "default:" not in s_body:
                line_num = clean[: sm.start()].count("\n") + 1
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1008h",
                        filename=filename,
                        line=line_num,
                        severity=P1_RULES_CATALOG["0x1008h"].severity,
                        title=P1_RULES_CATALOG["0x1008h"].title,
                        message="Bloque `switch` sin cláusula `default:` obligatoria.",
                        suggestion="Agregá `default:` al final del `switch` para manejar estados imprevistos.",
                    )
                )

        # --------------------------------------------------------------------
        # 11. 0x2004h: Prohibición de variables globales mutables
        # --------------------------------------------------------------------
        global_var_regex = re.compile(
            r"^[ \t]*(?!const\b)(?:int|char|float|double|size_t)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=\s*[^;]+)?;",
            re.MULTILINE,
        )
        # Extraer variables que están fuera de funciones y fuera de structs/unions/enums
        in_fn_ranges = [(f.start_line, f.start_line + f.raw_body.count("\n")) for f in functions.values()]
        struct_ranges = [
            (clean[: sm.start()].count("\n") + 1, clean[: sm.end()].count("\n") + 1)
            for sm in re.finditer(r"\b(?:struct|union|enum)\b[^{};]*\{[^}]*\}", clean, re.DOTALL)
        ]
        for m in global_var_regex.finditer(clean):
            line_num = clean[: m.start()].count("\n") + 1
            inside_any_fn = any(start <= line_num <= end for start, end in in_fn_ranges)
            inside_any_struct = any(start <= line_num <= end for start, end in struct_ranges)
            if not inside_any_fn and not inside_any_struct:
                observations.append(
                    P1RuleObservation(
                        rule_code="0x2004h",
                        filename=filename,
                        line=line_num,
                        severity=P1_RULES_CATALOG["0x2004h"].severity,
                        title=P1_RULES_CATALOG["0x2004h"].title,
                        message="Declaración de variable global mutable.",
                        suggestion="Eliminá la variable global; pasá el estado explícitamente mediante parámetros de función.",
                    )
                )

        # --------------------------------------------------------------------
        # 12. 0x3001h: Verificación obligatoria de retorno de malloc/calloc
        # --------------------------------------------------------------------
        for fname, fobj in functions.items():
            alloc_calls = re.findall(r"(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc|realloc)\s*\(", fobj.raw_body)
            for v in alloc_calls:
                # Comprobar si en el cuerpo se valida if (v == NULL) o if (!v)
                if not re.search(rf"\bif\s*\(\s*(?:{v}\s*==\s*NULL|!{v}|NULL\s*==\s*{v})\b", fobj.raw_body):
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x3001h",
                            filename=filename,
                            line=fobj.start_line,
                            severity=P1_RULES_CATALOG["0x3001h"].severity,
                            title=P1_RULES_CATALOG["0x3001h"].title,
                            message=f"Asignación dinámica de `{v}` sin verificación inmediata contra `NULL`.",
                            suggestion=f"Agregá `if ({v} == NULL) {{ /* manejo de error */ }}` antes de usar el puntero.",
                        )
                    )

        # --------------------------------------------------------------------
        # 13. 0x3003h: No mezclar asignación y comparación en if
        # --------------------------------------------------------------------
        assign_in_cond = re.compile(r"\bif\s*\(\s*\([a-zA-Z0-9_* ]+\s*=\s*(?:malloc|calloc|realloc|fopen)\s*\(")
        for idx, line in enumerate(clean_lines, start=1):
            if assign_in_cond.search(line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x3003h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x3003h"].severity,
                        title=P1_RULES_CATALOG["0x3003h"].title,
                        message="Asignación y comparación combinadas en una sola línea dentro del `if`.",
                        suggestion="Separá la asignación en la línea anterior y evaluá la condición en una sentencia limpia.",
                    )
                )

        # --------------------------------------------------------------------
        # 14. 0x3004h: Structs con typedef y sufijo _t / prefijo t_
        # --------------------------------------------------------------------
        bare_struct_regex = re.compile(r"^[ \t]*struct\s+(?P<sname>[a-zA-Z0-9_]+)\s*\{", re.MULTILINE)
        for m in bare_struct_regex.finditer(clean):
            sname = m.group("sname")
            line_num = clean[: m.start()].count("\n") + 1
            if not sname.endswith("_t") and not sname.startswith("t_"):
                # Comprobar si está dentro de un typedef
                typedef_check = clean[max(0, m.start() - 15) : m.start()]
                if "typedef" not in typedef_check:
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x3004h",
                            filename=filename,
                            line=line_num,
                            severity=P1_RULES_CATALOG["0x3004h"].severity,
                            title=P1_RULES_CATALOG["0x3004h"].title,
                            message=f"Estructura `{sname}` declarada sin `typedef` ni sufijo `_t` / prefijo `t_`.",
                            suggestion=f"Definila como `typedef struct {{ ... }} {sname}_t;`.",
                        )
                    )

        # --------------------------------------------------------------------
        # 15. 0x5001h: Prohibición de VLAs (Arreglos de longitud variable)
        # --------------------------------------------------------------------
        vla_regex = re.compile(r"\b(?:int|char|float|double)\s+[a-zA-Z_][a-zA-Z0-9_]*\[\s*(?![0-9A-Z_]+\s*\])[a-z_][a-zA-Z0-9_]*\s*\]\s*;")
        for idx, line in enumerate(clean_lines, start=1):
            if vla_regex.search(line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x5001h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x5001h"].severity,
                        title=P1_RULES_CATALOG["0x5001h"].title,
                        message="Uso de Arreglo de Longitud Variable (VLA).",
                        suggestion="Los VLAs están prohibidos. Utilizá una constante `#define TAM 100` o asignación dinámica con `malloc`.",
                    )
                )

        # --------------------------------------------------------------------
        # 16. 0x5006h: Preferir fgets sobre gets y scanf("%s")
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if re.search(r"\bgets\s*\(", line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x5006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x5006h"].severity,
                        title=P1_RULES_CATALOG["0x5006h"].title,
                        message="Uso de la función obsoleta e insegura `gets()`.",
                        suggestion="Reemplazá `gets()` por `fgets(buffer, sizeof(buffer), stdin)`.",
                    )
                )
            elif re.search(r'\bscanf\s*\(\s*"%s"', line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x5006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x5006h"].severity,
                        title=P1_RULES_CATALOG["0x5006h"].title,
                        message="Uso de `scanf(\"%s\")` desprotegido contra desbordamiento de búfer.",
                        suggestion="Utilizá `fgets` o especificá un ancho máximo como `scanf(\"%99s\", buffer)`.",
                    )
                )

        return filter_suppressed_observations(observations, code)

    def _to_snake(self, name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# Registro de comandos y re-exports (deben ir tras definir los objetos compartidos)
from ripley.core.p1_catalog import P1Rule, P1_RULES_CATALOG  # noqa: E402,F401
from ripley.core.p1_suppressions import extract_suppressions, filter_suppressed_observations  # noqa: E402,F401
