"""Comprehensive style and quality rule definitions following Programación I apunte."""

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any, Optional

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


@dataclass
class _Fuente:
    """Lo que necesitan las reglas de un archivo, calculado una sola vez por análisis."""

    code: str
    filename: str
    raw_lines: list[str]
    clean: str
    clean_lines: list[str]
    functions: dict[str, Any]

    @classmethod
    def de(cls, code: str, filename: str) -> "_Fuente":
        clean = strip_c_comments_and_strings(code)
        return cls(code, filename, code.splitlines(), clean, clean.splitlines(), extract_c_functions(code))

    def linea_de(self, offset: int) -> int:
        """Línea (desde 1) de una posición del código sin comentarios ni cadenas."""
        return self.clean[:offset].count("\n") + 1

    def observacion(self, regla: str, linea: int, message: str, suggestion: str,
                    severity: str | None = None) -> P1RuleObservation:
        """Una observación con el título (y, si no se indica, la severidad) del catálogo."""
        return P1RuleObservation(
            rule_code=regla,
            filename=self.filename,
            line=linea,
            severity=severity if severity is not None else P1_RULES_CATALOG[regla].severity,
            title=P1_RULES_CATALOG[regla].title,
            message=message,
            suggestion=suggestion,
        )


def _to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ------------------------------------------------------------------------------------------------
# Una función por regla, en el orden en que se informan. Cada una recibe el fuente ya preprocesado
# y devuelve sus observaciones (N-ECO-16: antes era un único `analyze` de 391 líneas).
# ------------------------------------------------------------------------------------------------

_DECLARACION = re.compile(
    r"\b(?:int|char|float|double|size_t|ssize_t|long|short|unsigned|signed|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|bool|FILE|struct\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+_t|t_[a-zA-Z0-9_]+)\s+(?P<decl>[^;{}()]+);",
    re.MULTILINE,
)


def _regla_0001h_nombres_cortos(f: _Fuente) -> list[P1RuleObservation]:
    """Variables cortas (< 5 letras: «A mejorar»; de 1 letra: «Revisión manual»)."""
    observations = []
    for m in _DECLARACION.finditer(f.clean):
        line_num = f.linea_de(m.start())
        for item in m.group("decl").split(","):
            item_clean = re.sub(r"=.*$", "", item).strip()
            item_clean = re.sub(r"\[.*\]", "", item_clean).strip()
            var_match = re.search(r"[*]*\s*([a-zA-Z_][a-zA-Z0-9_]*)$", item_clean)
            if not var_match:
                continue
            vname = var_match.group(1)
            if vname in ("main", "setUp", "tearDown") or len(vname) >= 5:
                continue
            if len(vname) > 1:
                observations.append(f.observacion(
                    "0x0001h", line_num,
                    f"Nombre de variable corto ({len(vname)} letras): `{vname}` (A mejorar).",
                    "Se recomienda utilizar identificadores más descriptivos y expresivos que expliciten el propósito de la variable (Regla 0x0001h).",
                    severity="ESTILO",
                ))
            elif vname.lower() in ("i", "j", "k"):
                observations.append(f.observacion(
                    "0x0001h", line_num,
                    f"Variable de 1 letra: `{vname}` (Aceptable para contadores `i`, `j`, `k`, pero requiere revisión manual de contexto).",
                    "Conservar únicamente como contador o índice local de bucle; no emplear para datos de dominio (Regla 0x0001h).",
                    severity="ESTILO",
                ))
            else:
                observations.append(f.observacion(
                    "0x0001h", line_num,
                    f"Variable de 1 letra no descriptiva: `{vname}` (Requiere revisión manual obligatoria).",
                    f"Renombrá la variable `{vname}` por un identificador representativo del dominio (Regla 0x0001h).",
                    severity="ADVERTENCIA",
                ))
    return observations


_DECLARACION_MULTIPLE = re.compile(
    r"^[ \t]*(?:int|char|float|double|size_t|long|short)\s+([a-zA-Z_][a-zA-Z0-9_]*\s*(?:=\s*[^,;]+)?\s*,\s*)+[a-zA-Z_][a-zA-Z0-9_]*",
    re.MULTILINE,
)


def _regla_0002h_una_declaracion_por_linea(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x0002h", f.linea_de(m.start()),
                      "Múltiples declaraciones de variables en la misma línea.",
                      "Declarar cada variable en su propia línea (ej. `int a;\\nint b;`).")
        for m in _DECLARACION_MULTIPLE.finditer(f.clean)
    ]


def _regla_0004h_espacios_en_operadores(f: _Fuente) -> list[P1RuleObservation]:
    observations = []
    for idx, line in enumerate(f.clean_lines, start=1):
        for op in ("==", "!=", "<=", ">=", "&&", r"\|\|"):
            clean_op = op.replace("\\", "")
            if re.search(rf"[a-zA-Z0-9_]{op}[a-zA-Z0-9_]", line):
                observations.append(f.observacion(
                    "0x0004h", idx,
                    f"Falta espacio alrededor del operador binario `{clean_op}`.",
                    f"Colocá un espacio antes y después: `x {clean_op} y`.",
                ))
    return observations


_ASTERISCO_PEGADO_AL_TIPO = re.compile(r"\b(?:int|char|float|double|void|size_t)\*\s+[a-zA-Z_][a-zA-Z0-9_]*\b")


def _regla_0006h_asterisco_junto_al_nombre(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x0006h", idx,
                      "El asterisco de puntero está pegado al tipo (`tipo* ptr`) en lugar del identificador.",
                      "Escribí `tipo *ptr` para mantener la convención estándar de la cátedra.")
        for idx, line in enumerate(f.clean_lines, start=1)
        if _ASTERISCO_PEGADO_AL_TIPO.search(line)
    ]


_VARIABLE_CAMEL_CASE = re.compile(r"\b(?:int|char|float|double|size_t)\s+(?P<v>[a-z]+[A-Z][a-zA-Z0-9]*)\b")


def _regla_0007h_snake_case(f: _Fuente) -> list[P1RuleObservation]:
    observations = []
    for idx, line in enumerate(f.clean_lines, start=1):
        m = _VARIABLE_CAMEL_CASE.search(line)
        if m:
            vname = m.group("v")
            observations.append(f.observacion(
                "0x0007h", idx,
                f"La variable `{vname}` usa camelCase en lugar de snake_case.",
                f"Renombrala en minúsculas separadas por guión bajo (ej. `{_to_snake(vname)}`).",
            ))
    return observations


def _regla_0009h_largo_de_linea(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x0009h", idx,
                      f"La línea excede los 79 caracteres ({len(line)} columnas).",
                      "Dividí la instrucción o cadena en múltiples líneas para respetar el estándar de 80 columnas.")
        for idx, line in enumerate(f.raw_lines, start=1)
        if len(line) > 79
    ]


def _regla_1001h_llaves_en_estructuras(f: _Fuente) -> list[P1RuleObservation]:
    observations = []
    for idx, line in enumerate(f.clean_lines, start=1):
        s_line = line.strip()
        for kw in ("if", "for", "while"):
            match = re.search(rf"\b{kw}\s*\([^\)]*\)\s*([^{{;]+);", s_line)
            if match and not s_line.endswith("{") and not match.group(1).startswith("//"):
                observations.append(f.observacion(
                    "0x1001h", idx,
                    f"Estructura de control `{kw}` en una sola línea sin llaves {{}}.",
                    "Envolvé siempre el cuerpo de la estructura con llaves `{ ... }` en líneas propias.",
                ))
    return observations


def _regla_1002h_sin_continue(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x1002h", idx,
                      "Uso prohibido de la sentencia `continue`.",
                      "Reestructurá el lazo utilizando una condición lógica o bandera booleana.")
        for idx, line in enumerate(f.clean_lines, start=1)
        if re.search(r"\bcontinue\s*;", line)
    ]


def _regla_1006h_sin_goto(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x1006h", idx,
                      "Uso prohibido de la instrucción `goto`.",
                      "Reemplazá `goto` por estructuras de control estructuradas estándar (`while`, `for`, `if`).")
        for idx, line in enumerate(f.clean_lines, start=1)
        if re.search(r"\bgoto\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;", line)
    ]


def _regla_1007h_sin_ternario(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x1007h", idx,
                      "Uso desaconsejado del operador condicional ternario `?:`.",
                      "Reemplazá el operador ternario por un bloque estructurado `if / else`.")
        for idx, line in enumerate(f.clean_lines, start=1)
        if "?" in line and ":" in line and not line.strip().startswith("//") and not line.strip().startswith("case ")
    ]


def _regla_1008h_switch_con_default(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x1008h", f.linea_de(sm.start()),
                      "Bloque `switch` sin cláusula `default:` obligatoria.",
                      "Agregá `default:` al final del `switch` para manejar estados imprevistos.")
        for sm in re.finditer(r"\bswitch\s*\([^\)]*\)\s*\{(?P<body>[^}]*)\}", f.clean)
        if "default:" not in sm.group("body")
    ]


_VARIABLE_GLOBAL = re.compile(
    r"^[ \t]*(?!const\b)(?:int|char|float|double|size_t)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=\s*[^;]+)?;",
    re.MULTILINE,
)


def _regla_2004h_sin_globales_mutables(f: _Fuente) -> list[P1RuleObservation]:
    # Las variables fuera de las funciones y de los struct/union/enum.
    in_fn_ranges = [(fn.start_line, fn.start_line + fn.raw_body.count("\n")) for fn in f.functions.values()]
    struct_ranges = [
        (f.linea_de(sm.start()), f.linea_de(sm.end()))
        for sm in re.finditer(r"\b(?:struct|union|enum)\b[^{};]*\{[^}]*\}", f.clean, re.DOTALL)
    ]
    observations = []
    for m in _VARIABLE_GLOBAL.finditer(f.clean):
        line_num = f.linea_de(m.start())
        inside_any_fn = any(start <= line_num <= end for start, end in in_fn_ranges)
        inside_any_struct = any(start <= line_num <= end for start, end in struct_ranges)
        if not inside_any_fn and not inside_any_struct:
            observations.append(f.observacion(
                "0x2004h", line_num,
                "Declaración de variable global mutable.",
                "Eliminá la variable global; pasá el estado explícitamente mediante parámetros de función.",
            ))
    return observations


def _regla_3001h_verificar_malloc(f: _Fuente) -> list[P1RuleObservation]:
    observations = []
    for fobj in f.functions.values():
        alloc_calls = re.findall(r"(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc|realloc)\s*\(", fobj.raw_body)
        for v in alloc_calls:
            # ¿Se valida en el cuerpo con if (v == NULL) o if (!v)?
            if not re.search(rf"\bif\s*\(\s*(?:{v}\s*==\s*NULL|!{v}|NULL\s*==\s*{v})\b", fobj.raw_body):
                observations.append(f.observacion(
                    "0x3001h", fobj.start_line,
                    f"Asignación dinámica de `{v}` sin verificación inmediata contra `NULL`.",
                    f"Agregá `if ({v} == NULL) {{ /* manejo de error */ }}` antes de usar el puntero.",
                ))
    return observations


_ASIGNACION_EN_CONDICION = re.compile(r"\bif\s*\(\s*\([a-zA-Z0-9_* ]+\s*=\s*(?:malloc|calloc|realloc|fopen)\s*\(")


def _regla_3003h_asignacion_fuera_del_if(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x3003h", idx,
                      "Asignación y comparación combinadas en una sola línea dentro del `if`.",
                      "Separá la asignación en la línea anterior y evaluá la condición en una sentencia limpia.")
        for idx, line in enumerate(f.clean_lines, start=1)
        if _ASIGNACION_EN_CONDICION.search(line)
    ]


_STRUCT_SIN_TYPEDEF = re.compile(r"^[ \t]*struct\s+(?P<sname>[a-zA-Z0-9_]+)\s*\{", re.MULTILINE)


def _regla_3004h_struct_con_typedef(f: _Fuente) -> list[P1RuleObservation]:
    observations = []
    for m in _STRUCT_SIN_TYPEDEF.finditer(f.clean):
        sname = m.group("sname")
        if sname.endswith("_t") or sname.startswith("t_"):
            continue
        if "typedef" not in f.clean[max(0, m.start() - 15) : m.start()]:
            observations.append(f.observacion(
                "0x3004h", f.linea_de(m.start()),
                f"Estructura `{sname}` declarada sin `typedef` ni sufijo `_t` / prefijo `t_`.",
                f"Definila como `typedef struct {{ ... }} {sname}_t;`.",
            ))
    return observations


_VLA = re.compile(r"\b(?:int|char|float|double)\s+[a-zA-Z_][a-zA-Z0-9_]*\[\s*(?![0-9A-Z_]+\s*\])[a-z_][a-zA-Z0-9_]*\s*\]\s*;")


def _regla_5001h_sin_vla(f: _Fuente) -> list[P1RuleObservation]:
    return [
        f.observacion("0x5001h", idx,
                      "Uso de Arreglo de Longitud Variable (VLA).",
                      "Los VLAs están prohibidos. Utilizá una constante `#define TAM 100` o asignación dinámica con `malloc`.")
        for idx, line in enumerate(f.clean_lines, start=1)
        if _VLA.search(line)
    ]


def _regla_5006h_lectura_segura(f: _Fuente) -> list[P1RuleObservation]:
    """Preferir fgets sobre gets y scanf("%s")."""
    observations = []
    for idx, line in enumerate(f.clean_lines, start=1):
        if re.search(r"\bgets\s*\(", line):
            observations.append(f.observacion(
                "0x5006h", idx,
                "Uso de la función obsoleta e insegura `gets()`.",
                "Reemplazá `gets()` por `fgets(buffer, sizeof(buffer), stdin)`.",
            ))
        elif re.search(r'\bscanf\s*\(\s*"%s"', line):
            observations.append(f.observacion(
                "0x5006h", idx,
                "Uso de `scanf(\"%s\")` desprotegido contra desbordamiento de búfer.",
                "Utilizá `fgets` o especificá un ancho máximo como `scanf(\"%99s\", buffer)`.",
            ))
    return observations


REGLAS: tuple[Callable[[_Fuente], list[P1RuleObservation]], ...] = (
    _regla_0001h_nombres_cortos,
    _regla_0002h_una_declaracion_por_linea,
    _regla_0004h_espacios_en_operadores,
    _regla_0006h_asterisco_junto_al_nombre,
    _regla_0007h_snake_case,
    _regla_0009h_largo_de_linea,
    _regla_1001h_llaves_en_estructuras,
    _regla_1002h_sin_continue,
    _regla_1006h_sin_goto,
    _regla_1007h_sin_ternario,
    _regla_1008h_switch_con_default,
    _regla_2004h_sin_globales_mutables,
    _regla_3001h_verificar_malloc,
    _regla_3003h_asignacion_fuera_del_if,
    _regla_3004h_struct_con_typedef,
    _regla_5001h_sin_vla,
    _regla_5006h_lectura_segura,
)


class P1RuleChecker:
    """Evaluador exhaustivo de las reglas de estilo y buenas prácticas de Programación I."""

    def __init__(self) -> None:
        try:
            from ripley.core.entrypoints import get_satellite_plugin
            self.satellite: Optional[Any] = get_satellite_plugin("style")
        except Exception:
            self.satellite = None

    def analyze(self, code: str, filename: str = "archivo.c") -> list[P1RuleObservation]:
        fuente = _Fuente.de(code, filename)
        observations = [obs for regla in REGLAS for obs in regla(fuente)]
        return filter_suppressed_observations(observations, code)

    def _to_snake(self, name: str) -> str:
        return _to_snake(name)


# Registro de comandos y re-exports (deben ir tras definir los objetos compartidos)
from ripley.core.p1_catalog import P1Rule, P1_RULES_CATALOG  # noqa: E402,F401
from ripley.core.p1_suppressions import extract_suppressions, filter_suppressed_observations  # noqa: E402,F401
