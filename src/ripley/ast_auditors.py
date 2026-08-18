"""Advanced AST and syntactic auditors for C source code."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from ripley.linters import LinterObservation
from ripley.security import strip_c_comments_and_strings
from ripley.semantic_diff import CFunctionAST, extract_c_functions


# ============================================================================
# 1. Comparaciones Peligrosas en Números de Punto Flotante
# ============================================================================
class FloatComparisonLinter:
    """Detecta comparaciones de igualdad directa (== o !=) entre variables float/double."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)

        # Detectar declaraciones de float/double
        float_vars: Set[str] = set()
        float_decl_regex = re.compile(r"\b(?:float|double)\s+(?P<vars>[a-zA-Z0-9_,\s=.\-]+);", re.MULTILINE)
        for m in float_decl_regex.finditer(clean):
            var_part = m.group("vars")
            for item in var_part.split(","):
                v = item.split("=")[0].strip()
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
                    float_vars.add(v)

        lines = clean.splitlines()
        cmp_regex = re.compile(r"\b(?P<lhs>[a-zA-Z0-9_]+)\s*(?P<op>==|!=)\s*(?P<rhs>[a-zA-Z0-9_.]+)")

        for line_idx, line in enumerate(lines):
            for match in cmp_regex.finditer(line):
                lhs = match.group("lhs")
                rhs = match.group("rhs")
                op = match.group("op")

                # Si involucra literal con punto decimal o variable float
                if (
                    lhs in float_vars
                    or rhs in float_vars
                    or "." in lhs
                    or "." in rhs
                    or "0.0" in line
                ):
                    observations.append(
                        LinterObservation(
                            linter_name="float_comparison",
                            filename=filename,
                            line=line_idx + 1,
                            severity="ADVERTENCIA",
                            message=f"Comparación de igualdad directa `{lhs} {op} {rhs}` sobre números de punto flotante.",
                            suggestion="Los números en coma flotante sufren imprecisiones de redondeo IEEE 754. Usá un margen de tolerancia: `fabs(a - b) < EPSILON`.",
                        )
                    )

        return observations


# ============================================================================
# 2. Detección de Inclusiones Innecesarias (Include What You Use - IWYU)
# ============================================================================
class IWYULinter:
    """Identifica directivas #include cuyas funciones o tipos no son utilizados."""

    HEADER_SYMBOLS = {
        "math.h": {"sin", "cos", "tan", "sqrt", "pow", "fabs", "ceil", "floor", "log", "exp", "M_PI"},
        "string.h": {"strlen", "strcpy", "strncpy", "strcmp", "strncmp", "strcat", "strchr", "strstr", "memcpy", "memset", "memcmp"},
        "ctype.h": {"isalpha", "isdigit", "isalnum", "isspace", "toupper", "tolower"},
        "time.h": {"time", "clock", "difftime", "time_t", "clock_t", "struct tm"},
        "stdbool.h": {"bool", "true", "false"},
    }

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        included_headers: List[Tuple[str, int]] = []
        include_regex = re.compile(r'^[ \t]*#\s*include\s*[<"](?P<header>[^>"]+)[>"]')

        for idx, line in enumerate(lines):
            m = include_regex.match(line)
            if m:
                included_headers.append((m.group("header"), idx + 1))

        # Comprobar símbolos usados
        for header, line_num in included_headers:
            if header in self.HEADER_SYMBOLS:
                expected_symbols = self.HEADER_SYMBOLS[header]
                # Buscar si alguno de los símbolos aparece en el código fuera de los includes
                found = any(re.search(rf"\b{re.escape(sym)}\b", clean) for sym in expected_symbols)
                if not found:
                    observations.append(
                        LinterObservation(
                            linter_name="iwyu_unused_include",
                            filename=filename,
                            line=line_num,
                            severity="ESTILO",
                            message=f"Inclusión innecesaria de `<{header}>`. Ninguno de sus símbolos es utilizado en el archivo.",
                            suggestion=f"Eliminá `#include <{header}>` para acelerar la compilación y evitar acoplamiento superfluo.",
                        )
                    )

        return observations


# ============================================================================
# 3. Auditoría de Calificación const en Parámetros (Const-Correctness)
# ============================================================================
class ConstCorrectnessLinter:
    """Valida que los parámetros puntero de solo lectura estén calificados con const."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        functions = extract_c_functions(code)

        for fname, fobj in functions.items():
            if fname in ("main", "setUp", "tearDown") or not fobj.params:
                continue

            params = [p.strip() for p in fobj.params.split(",") if p.strip() and p.strip() != "void"]
            for p in params:
                # Si es un puntero o arreglo pero no tiene const
                if ("*" in p or "[]" in p) and not re.search(r"\bconst\b", p):
                    # Extraer el nombre del parámetro
                    m = re.search(r"(?P<pname>[a-zA-Z_][a-zA-Z0-9_]*)(?:\[\])?$", p)
                    if m:
                        pname = m.group("pname")
                        body = fobj.raw_body
                        # Verificar si se escribe en el contenido del puntero: *pname = ..., pname[...] = ..., strcpy(pname, ...)
                        is_written = (
                            bool(re.search(rf"\*\s*{pname}\s*=[^=]", body))
                            or bool(re.search(rf"{pname}\s*\[[^\]]+\]\s*=[^=]", body))
                            or bool(re.search(rf"\b(strcpy|strcat|sprintf|memcpy|memset)\s*\(\s*{pname}\b", body))
                        )
                        if not is_written:
                            observations.append(
                                LinterObservation(
                                    linter_name="const_correctness",
                                    filename=filename,
                                    line=fobj.start_line,
                                    severity="ESTILO",
                                    message=f"El parámetro puntero `{pname}` en `{fname}()` es solo de lectura pero carece del calificador `const`.",
                                    suggestion=f"Declaralo como `const {p}` para garantizar inmutabilidad y seguridad de tipos.",
                                )
                            )

        return observations


# ============================================================================
# 4. Detección de Cortocircuitos Peligrosos con Efectos Colaterales
# ============================================================================
class ShortCircuitLinter:
    """Detecta operaciones con efectos colaterales dentro de expresiones booleanas (&&, ||)."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        cond_regex = re.compile(r"\b(?:if|while)\s*\((?P<cond>[^\)]+)\)")
        side_effect_regex = re.compile(r"(\+\+|\-\-|[^=!<>]=[^=])")

        for idx, line in enumerate(lines):
            for m in cond_regex.finditer(line):
                cond = m.group("cond")
                if "&&" in cond or "||" in cond:
                    if side_effect_regex.search(cond):
                        observations.append(
                            LinterObservation(
                                linter_name="short_circuit_side_effect",
                                filename=filename,
                                line=idx + 1,
                                severity="ADVERTENCIA",
                                message=f"Efecto colateral peligroso dentro de evaluación de cortocircuito booleano: `({cond.strip()})`.",
                                suggestion="El operador `&&` o `||` puede no evaluar la segunda parte de la expresión, omitiendo el incremento o asignación. Realizá la operación antes del condicional.",
                            )
                        )

        return observations


# ============================================================================
# 5. Verificación de Liberación de Estructuras Anidadas (Deep Free)
# ============================================================================
class DeepFreeLinter:
    """Audita que funciones que liberan estructuras con punteros internos liberen sus miembros."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)

        # Buscar definiciones de struct con campos puntero
        struct_regex = re.compile(r"struct\s+(?P<sname>[a-zA-Z0-9_]+)\s*\{(?P<body>[^}]+)\}", re.MULTILINE)
        structs_with_pointers: Dict[str, List[str]] = {}

        for m in struct_regex.finditer(clean):
            sname = m.group("sname")
            sbody = m.group("body")
            pointer_fields = [
                f.strip().split()[-1].replace("*", "")
                for f in sbody.split(";")
                if "*" in f and f.strip()
            ]
            if pointer_fields:
                structs_with_pointers[sname] = pointer_fields

        # Buscar llamadas a free(x) donde x es un struct con campos puntero
        functions = extract_c_functions(code)
        for fname, fobj in functions.items():
            free_calls = re.findall(r"free\s*\(\s*(?P<var>[a-zA-Z0-9_]+)\s*\)", fobj.raw_body)
            for v in free_calls:
                # Comprobar si v es del tipo struct con punteros
                for sname, pfields in structs_with_pointers.items():
                    # Si el parámetro o cuerpo menciona el struct y la variable v
                    is_struct_var = (
                        f"struct {sname}" in fobj.params and v in fobj.params
                        or f"{sname}" in fobj.params and v in fobj.params
                        or f"{v}->" in fobj.raw_body
                    )
                    if is_struct_var:
                        for fld in pfields:
                            arrow_free = f"free({v}->{fld})"
                            if arrow_free not in fobj.raw_body.replace(" ", ""):
                                observations.append(
                                    LinterObservation(
                                        linter_name="deep_free_verifier",
                                        filename=filename,
                                        line=fobj.start_line,
                                        severity="ADVERTENCIA",
                                        message=f"Posible fuga en estructura anidada: Se liberó `free({v})` sin liberar el puntero miembro `{v}->{fld}`.",
                                        suggestion=f"Hacé una liberación en profundidad (*deep free*): `free({v}->{fld});` antes de `free({v});`.",
                                    )
                                )


        return observations


# ============================================================================
# 6. Auditoría de Punteros Nulos en Funciones de Cadenas (<string.h>)
# ============================================================================
class StringNullPointerLinter:
    """Audita llamadas a funciones de <string.h> con punteros que pueden ser NULL."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        str_func_regex = re.compile(r"\b(?P<fn>strlen|strcpy|strcmp|strcat)\s*\(\s*(?P<arg1>[a-zA-Z0-9_]+)")

        for idx, line in enumerate(lines):
            for m in str_func_regex.finditer(line):
                fn = m.group("fn")
                arg1 = m.group("arg1")
                # Si en la misma función no hay una guarda if (arg1 == NULL) o if (!arg1)
                context = "\n".join(lines[max(0, idx - 10) : idx])
                if not re.search(rf"\bif\s*\(\s*(?:!{arg1}|{arg1}\s*==\s*NULL|{arg1}\s*!=\s*NULL)\b", context):
                    if arg1 not in ('""', "NULL") and not arg1.startswith('"'):
                        observations.append(
                            LinterObservation(
                                linter_name="string_null_pointer",
                                filename=filename,
                                line=idx + 1,
                                severity="ESTILO",
                                message=f"Invocación de `{fn}({arg1})` sin validación previa contra `NULL`.",
                                suggestion=f"Asegurate de validar `if ({arg1} != NULL)` antes de invocar funciones de `<string.h>` para evitar Segmentation Faults.",
                            )
                        )

        return observations


# ============================================================================
# 7. Detección de Sombras de Variables (Variable Shadowing)
# ============================================================================
class VariableShadowingLinter:
    """Detecta cuando una variable en un ámbito interno oculta a otra variable con el mismo nombre."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        functions = extract_c_functions(code)

        for fname, fobj in functions.items():
            if not fobj.params:
                continue

            param_names = [
                p.strip().split()[-1].replace("*", "")
                for p in fobj.params.split(",")
                if p.strip() and p.strip() != "void"
            ]

            # Buscar declaraciones locales dentro del cuerpo con el mismo nombre
            body = fobj.raw_body
            decl_regex = re.compile(
                r"\b(?:int|char|float|double|size_t|long|short|void\*)\s+(?P<vname>[a-zA-Z_][a-zA-Z0-9_]*)\s*[=;]",
                re.MULTILINE,
            )
            for m in decl_regex.finditer(body):
                vname = m.group("vname")
                if vname in param_names:
                    line = fobj.start_line + body[: m.start()].count("\n")
                    observations.append(
                        LinterObservation(
                            linter_name="variable_shadowing",
                            filename=filename,
                            line=line,
                            severity="ADVERTENCIA",
                            message=f"La variable local `{vname}` oculta (*shadowing*) al parámetro del mismo nombre en `{fname}()`.",
                            suggestion=f"Renombrá la variable local `{vname}` para evitar ambigüedades de ámbito y sobrescritura accidental.",
                        )
                    )

        return observations


# ============================================================================
# 8. Retorno de Direcciones de Variables del Stack (Punteros Salvajes)
# ============================================================================
class DanglingStackPointerLinter:
    """Detecta retornos de direcciones de memoria de variables locales del stack."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        functions = extract_c_functions(code)

        for fname, fobj in functions.items():
            # Extraer variables locales declaradas
            body = fobj.raw_body
            decl_regex = re.compile(
                r"\b(?:int|char|float|double|struct\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+_t)\s+(?P<vname>[a-zA-Z_][a-zA-Z0-9_]*)(?:\[[^\]]*\])?\s*[=;]",
                re.MULTILINE,
            )
            local_vars = {m.group("vname") for m in decl_regex.finditer(body)}

            # Buscar return &var_local
            ret_regex = re.compile(r"return\s+&\s*(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*;", re.MULTILINE)
            for m in ret_regex.finditer(body):
                var = m.group("var")
                if var in local_vars:
                    line = fobj.start_line + body[: m.start()].count("\n")
                    observations.append(
                        LinterObservation(
                            linter_name="dangling_stack_pointer",
                            filename=filename,
                            line=line,
                            severity="ERROR",
                            message=f"Retorno de dirección de variable local del stack `&{var}` en `{fname}()`.",
                            suggestion=(
                                f"La variable `{var}` vive en el marco de pila y es destruida al salir de `{fname}()`. "
                                "Asigná memoria dinámica en el Heap (`malloc`) o pedí el buffer como parámetro."
                            ),
                        )
                    )

        return observations


# ============================================================================
# 9. Detector de Sobre-Ingeniería y Optimizaciones Prematuras Ilegibles
# ============================================================================
class OverengineeringLinter:
    """Detecta trucos crípticos (XOR swap, ternarios triplemente anidados, operaciones de bits innecesarias)."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        # 1. Truco de intercambio con XOR (^=)
        xor_swap_regex = re.compile(r"(?P<a>[a-zA-Z0-9_]+)\s*\^=\s*(?P<b>[a-zA-Z0-9_]+);\s*(?P=b)\s*\^=\s*(?P=a);\s*(?P=a)\s*\^=\s*(?P=b);")
        for idx, line in enumerate(lines):
            if xor_swap_regex.search(line):
                observations.append(
                    LinterObservation(
                        linter_name="overengineering",
                        filename=filename,
                        line=idx + 1,
                        severity="ESTILO",
                        message="Uso de truco críptico de intercambio XOR (`a ^= b; b ^= a; a ^= b;`).",
                        suggestion="Priorizá la legibilidad con una variable temporal auxiliar `int temp = a; a = b; b = temp;`.",
                    )
                )

        # 2. Operadores ternarios anidados (más de 2 ?)
        for idx, line in enumerate(lines):
            if line.count("?") >= 2 and line.count(":") >= 2:
                observations.append(
                    LinterObservation(
                        linter_name="overengineering",
                        filename=filename,
                        line=idx + 1,
                        severity="ESTILO",
                        message="Operadores condicionales ternarios anidados con alta carga cognitiva.",
                        suggestion="Reemplazá los ternarios anidados por estructuras `if / else if / else` claras y legibles.",
                    )
                )

        return observations


# ============================================================================
# 10. Detector de Dependencia de Orden de Evaluación de Argumentos
# ============================================================================
class EvaluationOrderLinter:
    """Detecta llamadas a funciones con argumentos cuyo orden de evaluación es indefinido (unspecified behavior)."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        # Regex para capturar llamadas a función con múltiples argumentos separados por coma
        call_regex = re.compile(r"\b(?P<fn>[a-zA-Z_][a-zA-Z0-9_]*)\s*\((?P<args>[^()]+,[^()]+)\)")

        for line_idx, line in enumerate(lines):
            for match in call_regex.finditer(line):
                fn = match.group("fn")
                if fn in ("if", "while", "for", "switch", "sizeof"):
                    continue
                args_str = match.group("args")
                args = [a.strip() for a in args_str.split(",")]

                # Extraer variables con mutación (++, --, =)
                mutated_vars = set()
                all_vars_per_arg = []

                for a in args:
                    m_mut = re.findall(r"(?:\+\+|--)\s*([a-zA-Z_][a-zA-Z0-9_]*)|([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\+\+|--)", a)
                    for m in m_mut:
                        var = m[0] or m[1]
                        mutated_vars.add(var)
                    vars_in_a = set(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", a))
                    all_vars_per_arg.append(vars_in_a)

                # Si alguna variable mutada aparece en más de un argumento
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
                        break

        return observations


# ============================================================================
# 11. Auditoría de Modificación de Cadenas Literales en .rodata
# ============================================================================
class StringLiteralWriteLinter:
    """Detecta intentos de escritura en literales de cadena almacenados en memoria de solo lectura (.rodata)."""

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

        # 2. Buscar escrituras sobre esos punteros: p[0] = 'a' o *p = 'a' o strcpy(p, ...)
        for var_name, decl_line in literal_ptrs.items():
            for line_idx, line in enumerate(lines):
                line_num = line_idx + 1
                if line_num == decl_line or line.strip().startswith("char "):
                    continue
                is_write = (
                    re.search(rf"\b{var_name}\s*\[[^\]]+\]\s*=[^=]", line)
                    or re.search(rf"\*\s*{var_name}\s*=[^=]", line)
                    or re.search(rf"\b(strcpy|strncpy|strcat|sprintf)\s*\(\s*{var_name}\b", line)
                )
                if is_write:
                    observations.append(
                        LinterObservation(
                            linter_name="rodata_string_write",
                            filename=filename,
                            line=line_num,
                            severity="ERROR",
                            message=f"Intento de modificación de cadena literal en `.rodata` a través del puntero `{var_name}` (declarado en línea {decl_line}).",
                            suggestion=f"Las cadenas literales `\"...\"` residen en páginas de solo lectura. Para cadenas mutables, usá un arreglo `char {var_name}[] = \"...\";` o asigná memoria con `malloc`.",
                        )
                    )


        return observations


# ============================================================================
# 12. Control de Saltos Hacia Atrás con goto
# ============================================================================
class BackwardGotoLinter:
    """Detecta saltos hacia atrás con goto que emulan bucles desestructurados (spaghetti code)."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        # 1. Registrar etiquetas y sus líneas
        labels: Dict[str, int] = {}
        label_regex = re.compile(r"^[ \t]*(?P<label>[a-zA-Z_][a-zA-Z0-9_]*)\s*:", re.MULTILINE)

        for m in label_regex.finditer(clean):
            lbl = m.group("label")
            if lbl not in ("case", "default"):
                line = clean[: m.start()].count("\n") + 1
                labels[lbl] = line

        # 2. Registrar instrucciones goto y comprobar si la etiqueta está antes en el código
        goto_regex = re.compile(r"\bgoto\s+(?P<label>[a-zA-Z_][a-zA-Z0-9_]*)\s*;", re.MULTILINE)

        for m in goto_regex.finditer(clean):
            lbl = m.group("label")
            goto_line = clean[: m.start()].count("\n") + 1
            if lbl in labels:
                target_line = labels[lbl]
                if target_line < goto_line:
                    observations.append(
                        LinterObservation(
                            linter_name="backward_goto",
                            filename=filename,
                            line=goto_line,
                            severity="ADVERTENCIA",
                            message=f"Salto hacia atrás con `goto {lbl};` hacia la línea {target_line} (bucle desestructurado).",
                            suggestion="Los saltos hacia atrás generan código espagueti. Reemplazá el `goto` por estructuras de control estructuradas estándar (`while`, `for`, `do-while`).",
                        )
                    )

        return observations

