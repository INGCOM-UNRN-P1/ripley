"""c-antipatterns — Detectores de vicios y malas prácticas específicas de C.

Cada linter implementa la misma interfaz que el resto de la suite:
``analyze(code, filename) -> List[LinterObservation]``.

Reglas (nuevas.md §1.5):
1. ``MallocCastLinter``      — cast innecesario del retorno de malloc/calloc/realloc.
2. ``StrlenAllocationLinter``— malloc(strlen(s)) sin el byte nulo (+ 1).
3. ``LoopControlMutationLinter`` — variable de control mutada fuera del encabezado.
4. ``GodFunctionLinter``     — funciones monolíticas que violan la cohesión.
"""

import re
from typing import List

from ripley.models import LinterObservation
from ripley.core.security import strip_c_comments_and_strings
from ripley.core.semantic_diff import extract_c_functions


def _obs(linter: str, filename: str, line: int, mensaje: str, sugerencia: str,
         severidad: str = "ADVERTENCIA") -> LinterObservation:
    return LinterObservation(
        linter_name=linter,
        filename=filename,
        line=line,
        severity=severidad,
        message=mensaje,
        suggestion=sugerencia,
    )


def _linea_de(clean: str, offset: int) -> int:
    return clean.count("\n", 0, offset) + 1


class MallocCastLinter:
    """Detecta casts del retorno de malloc/calloc/realloc, innecesarios en C99.

    En C89 era obligatorio porque `void *` no se convertía implícitamente; en
    C99+ el cast sólo esconde un `<stdlib.h>` faltante y se repite en cada
    cambio de tipo.
    """

    PATRON = re.compile(
        r"\(\s*[A-Za-z_]\w*\s*(?:\*+\s*)?\)\s*(malloc|calloc|realloc)\s*\(",
        re.DOTALL,
    )

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        clean = strip_c_comments_and_strings(code)
        observaciones: List[LinterObservation] = []
        for m in self.PATRON.finditer(clean):
            observaciones.append(_obs(
                "antipattern.malloc_cast", filename, _linea_de(clean, m.start()),
                "Cast innecesario sobre el retorno de "
                f"{m.group(1)}(): en C99 `void *` se convierte implícitamente.",
                "Eliminá el cast; si el compilador exige uno, te está avisando "
                "de que falta #include <stdlib.h>.",
            ))
        return observaciones


class StrlenAllocationLinter:
    """Detecta reservas de memoria para cadenas sin el terminador nulo.

    ``malloc(strlen(s))`` reserva un byte de menos para '\\0'; lo idiomático es
    ``malloc(strlen(s) + 1)`` (o mejor, sizeof tras declarar con tamaño).
    """

    PATRON = re.compile(
        r"(malloc|calloc|realloc)\s*\(\s*strlen\s*\(\s*([A-Za-z_]\w*)\s*\)\s*\)",
        re.DOTALL,
    )

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        clean = strip_c_comments_and_strings(code)
        observaciones: List[LinterObservation] = []
        for m in self.PATRON.finditer(clean):
            if m.group(1) == "calloc":
                continue  # calloc(n, size): la aritmética es distinta
            observaciones.append(_obs(
                "antipattern.strlen_sin_nulo", filename, _linea_de(clean, m.start()),
                f"Reserva para cadena sin lugar para el terminador: "
                f"{m.group(0)} omite el byte '\\0'.",
                f"Usá {m.group(1)}(strlen({m.group(2)}) + 1) o duplicá la cadena "
                "con strdup() si tu cátedra lo permite.",
                severidad="ERROR",
            ))
        return observaciones


class LoopControlMutationLinter:
    """Detecta bucles cuya variable de control cambia fuera del encabezado.

    Mutar `i` dentro del cuerpo (o saltarlo con asignaciones mágicas) rompe la
    lectura del invariante del bucle y suele esconder un off-by-one.
    """

    FOR_HEADER = re.compile(
        r"\bfor\s*\(\s*(?:(?:register\s+)?(?:const\s+)?"
        r"(?:int|long|short|char|size_t|unsigned)(?:\s+int)?\s+)?"
        r"([A-Za-z_]\w*)\s*=\s*[^;]+;[^;]*;[^)]*\)",
        re.DOTALL,
    )

    @staticmethod
    def _bloque(code: str, apertura_llave: int) -> tuple[str, int]:
        profundidad = 0
        for j in range(apertura_llave, len(code)):
            if code[j] == "{":
                profundidad += 1
            elif code[j] == "}":
                profundidad -= 1
                if profundidad == 0:
                    return code[apertura_llave:j + 1], j + 1
        return code[apertura_llave:], len(code)

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        clean = strip_c_comments_and_strings(code)
        observaciones: List[LinterObservation] = []
        patrones_mutacion = [
            r"\b{v}\s*(?:\+\+|--)",
            r"(?:\+\+|--)\s*\b{v}\b",
            r"\b{v}\s*(?:\+=|-=|\*=|/=|%=)",
        ]
        for m in self.FOR_HEADER.finditer(clean):
            var = m.group(1)
            cuerpo, _fin = self._bloque(clean, m.end() - 1)
            # quitar el encabezado del propio for para no auto-detectarse
            cuerpo_interno = cuerpo[cuerpo.find("{") + 1:] if "{" in cuerpo else cuerpo
            for patron in patrones_mutacion:
                mm = re.search(patron.format(v=var), cuerpo_interno)
                if mm:
                    offset = clean.find(cuerpo_interno, m.end()) + mm.start()
                    observaciones.append(_obs(
                        "antipattern.loop_control_mutation", filename,
                        _linea_de(clean, max(offset, m.end())),
                        f"La variable de control '{var}' se modifica dentro del cuerpo "
                        "del for además de en el encabezado.",
                        f"Dejá que sólo el encabezado del for mueva '{var}'; usá otra "
                        "variable auxiliar si necesitás saltos extra.",
                    ))
                    break
        return observaciones


class GodFunctionLinter:
    """Detecta funciones monolíticas ('god functions') que violan cohesión.

    Heurística pedagógica: una función que supera `max_lineas` líneas efectivas
    o declara más de `max_variables_locales` variables probablemente mezcla
    varias responsabilidades y conviene descomponerla.
    """

    def __init__(self, max_lineas: int = 40, max_variables_locales: int = 10) -> None:
        self.max_lineas = max_lineas
        self.max_variables_locales = max_variables_locales

    @staticmethod
    def _cuerpo_balanceado(code: str, apertura_llave: int) -> str:
        profundidad = 0
        for j in range(apertura_llave, len(code)):
            if code[j] == "{":
                profundidad += 1
            elif code[j] == "}":
                profundidad -= 1
                if profundidad == 0:
                    return code[apertura_llave:j + 1]
        return code[apertura_llave:]

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        clean = strip_c_comments_and_strings(code)
        observaciones: List[LinterObservation] = []

        for funcion in extract_c_functions(code).values():
            nombre = funcion.name
            m = re.search(rf"\b{re.escape(nombre)}\s*\([^)]*\)[^{{;]*{{",
                          clean, re.DOTALL)
            if not m:
                continue
            cuerpo = self._cuerpo_balanceado(clean, m.end() - 1)
            lineas_efectivas = sum(
                1 for linea in cuerpo.splitlines() if linea.strip()
            )
            variables = set(re.findall(r"^\s*(?:const\s+)?(?:unsigned\s+)?"
                                       r"[A-Za-z_]\w*(?:\s*\*)*\s+([A-Za-z_]\w*)"
                                       r"\s*(?:=[^=]|;)",
                                       cuerpo, re.MULTILINE))
            if lineas_efectivas > self.max_lineas or len(variables) > self.max_variables_locales:
                motivos = []
                if lineas_efectivas > self.max_lineas:
                    motivos.append(f"{lineas_efectivas} líneas (>{self.max_lineas})")
                if len(variables) > self.max_variables_locales:
                    motivos.append(f"{len(variables)} locales (>{self.max_variables_locales})")
                observaciones.append(_obs(
                    "antipattern.god_function", filename,
                    _linea_de(clean, m.start()),
                    f"'{nombre}()' parece una god function: {', '.join(motivos)}.",
                    "Partila en funciones con una sola responsabilidad cada una: "
                    "leer entrada, procesar y mostrar son pasos distintos.",
                ))
        return observaciones


TODOS_ANTIPATRONES = (
    MallocCastLinter(),
    StrlenAllocationLinter(),
    LoopControlMutationLinter(),
    GodFunctionLinter(),
)


def analizar_antipatterns(code: str, filename: str = "archivo.c") -> List[LinterObservation]:
    """Ejecuta todos los detectores de antipatrones sobre un archivo."""
    observaciones: List[LinterObservation] = []
    for detector in TODOS_ANTIPATRONES:
        observaciones.extend(detector.analyze(code, filename))
    return observaciones
