"""Pedagogical translator: GCC/ld diagnostics into plain Spanish explanations.

Convierte la salida cruda del compilador en diagnósticos didácticos
(título, explicación y sugerencia) manteniendo siempre el mensaje
original para trazabilidad.
"""

from dataclasses import dataclass, field
import re
from typing import List, Optional

# (patrón sobre el texto del diagnóstico, título, explicación, sugerencia)
_RULES: List[tuple] = [
    (
        r"expected .*?;.*? before",
        "Falta un punto y coma (;)",
        "El compilador esperaba un punto y coma antes de continuar: alguna sentencia previa no fue cerrada.",
        "Revisá la línea anterior al error: casi siempre falta `;` al final de una declaración o llamada.",
    ),
    (
        r"expected .*'\}'.*? at end of input|expected declaration",
        "Falta cerrar una llave (})",
        "El archivo terminó sin cerrar todas las llaves de funciones o bloques.",
        "Contá las llaves abiertas vs cerradas; indentá el código para verlas mejor.",
    ),
    (
        r"expected .*'\('.*? before|expected expression before",
        "Paréntesis o expresión incompleta",
        "Hay una estructura de control o llamada con paréntesis desbalanceados o una expresión vacía.",
        "Verificá que cada `if`, `while` o llamada tenga sus paréntesis completos.",
    ),
    (
        r"'(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)' undeclared \(first use in this function\)",
        "Identificador no declarado: `{name}`",
        "Se usó `{name}` pero nunca se declaró. Puede ser un error de tipeo o falta la declaración/prototipo.",
        "Declará `{name}` antes de usarlo o corregí su escritura (C distingue mayúsculas de minúsculas).",
    ),
    (
        r"implicit declaration of function '(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'",
        "Función usada sin prototipo: `{name}`",
        "Se llamó a `{name}` sin declararla antes: C89 lo permitía, C99+ es error y el tipo de retorno se asume `int` incorrectamente.",
        "Incluí la cabecera correspondiente (por ejemplo `<string.h>`) o agregá el prototipo arriba del archivo.",
    ),
    (
        r"conflicting types for '(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'",
        "Tipos contradictorios para `{name}`",
        "La firma de `{name}` difiere entre su prototipo y su definición (tipos o cantidad de parámetros).",
        "Compará ambas firmas carácter por carácter; recordá que `char *` no es lo mismo que `const char *`.",
    ),
    (
        r"lvalue required as (left )?operand of assignment",
        "Asignación inválida: lo de la izquierda no es asignable",
        "El lado izquierdo de `=` debe ser una variable modificable, no una constante, literal o expresión.",
        "Ejemplo típico: `if (x = 0)` cuando se quiso comparar, o asignar a un literal/arreglo completo.",
    ),
    (
        r"incompatible types when assigning to type (?P<dst>'[^']*') from type (?P<src>'[^']*')",
        "Asignación incompatible: {dst} ← {src}",
        "Los tipos no son directamente convertibles: {src} no puede asignarse a {dst} sin conversión explícita.",
        "Usá un cast si realmente corresponde (`({dst}) expr`) o revisá el diseño: suele indicar un error lógico.",
    ),
    (
        r"initialization of (?P<dst>'char \*') from (incompatible pointer type|integer makes pointer)",
        "Puntero inicializado con algo que no es puntero",
        "{dst} recibió un valor entero o de otro tipo: los literales de cadena y arreglos tienen tipos distintos.",
        "Para cadenas usá `char s[] = \"...\"` (copia) o `char *s = \"...\"` (literal); nunca mezcles con enteros.",
    ),
    (
        r"subscripted value is neither array nor pointer",
        "Indexado de algo que no es arreglo ni puntero",
        "Se aplicó `[i]` a una variable escalar (int, float...), que no tiene posiciones de memoria indexables.",
        "Revisá el tipo de la variable a la izquierda de `[i]`; quizá querías un arreglo o desreferenciar con `*`.",
    ),
    (
        r"request for member '(?P<member>[a-zA-Z_][a-zA-Z0-9_]*)' in something not a structure",
        "`.{member}` usado sobre algo que no es struct",
        "El operador `.` accede a campos de estructuras; la variable no lo es (o es un puntero a estructura).",
        "Si es puntero a struct usá flecha: `p->{member}`; si no, verificá el tipo de la variable.",
    ),
    (
        r"dereferencing pointer to incomplete type",
        "Desreferencia de tipo incompleto",
        "El compilador no conoce el layout del struct al que apunta: falta la definición completa.",
        "Incluí la cabecera que define la estructura antes de acceder a sus campos.",
    ),
    (
        r"too few arguments to function (?P<name>[a-zA-Z_][a-zA-Z0-9_]*)",
        "Faltan argumentos en la llamada a `{name}`",
        "La función `{name}` espera más parámetros de los recibidos.",
        "Revisá el prototipo de `{name}` y completá todos sus argumentos en orden.",
    ),
    (
        r"too many arguments to function (?P<name>[a-zA-Z_][a-zA-Z0-9_]*)",
        "Sobran argumentos en la llamada a `{name}`",
        "Se pasaron más parámetros de los que `{name}` acepta.",
        "Eliminá los argumentos extra o corregí la firma si la función necesita más parámetros.",
    ),
    (
        r"control reaches end of non-void function",
        "Función no-void sin return garantizado",
        "Hay caminos de ejecución que terminan sin devolver valor: comportamiento indefinido.",
        "Agregá `return` al final (y en cada rama de `if/else`) acorde al tipo de retorno.",
    ),
    (
        r"unused variable '(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'",
        "Variable sin uso: `{name}`",
        "Se declaró `{name}` pero nunca se leyó. Suele indicar lógica incompleta.",
        "Eliminá la declaración o completá la lógica que debía usarla.",
    ),
    (
        r"division by zero",
        "División por cero detectada en tiempo de compilación",
        "El divisor es la constante 0: el resultado es indefinido.",
        "Validá el divisor antes de dividir; si es literal, corregí la fórmula.",
    ),
    (
        r"array subscript .*? above array bounds|exceeds array bound",
        "Índice fuera de los límites del arreglo",
        "El compilador detectó un acceso más allá del tamaño declarado del arreglo.",
        "Recordá que los índices válidos van de 0 a N-1; verificá condiciones de bucle.",
    ),
    (
        r"format (?P<fmt>'%[a-z]*') expects argument of type (?P<want>[^,]+), but argument (?P<n>\d+) has type (?P<have>[^ ;]+)",
        "Formato {fmt} incompatible con el argumento {n}",
        "printf/scanf esperaba {want} para {fmt} pero recibe {have}: salida corrupta o crash seguro.",
        "Hacé coincidir especificador y tipo: %d↔int, %f↔double, %s↔char*, %zu↔size_t.",
    ),
    (
        r"undefined reference to '(?P<name>main)'",
        "Falta la función main",
        "El enlazador no encontró `main`: todo programa ejecutable necesita uno.",
        "Definí `int main(void)` o incluí el .c que la contiene en la compilación.",
    ),
    (
        r"undefined reference to '(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'",
        "Símbolo sin definir en el enlace: `{name}`",
        "La función `{name}` se usa pero su cuerpo no está en ninguno de los archivos compilados.",
        "Compilación modular: pasá TODOS los .c al gcc (`gcc main.c modulo.c -o app`) o implementá `{name}`.",
    ),
    (
        r"(?P<path>[^ :\n]+): No such file or directory",
        "Archivo inexistente: {path}",
        "Un #include local o fuente listada no existe en la ruta indicada.",
        "Verificá rutas relativas y nombres exactos; para includes propios usá comillas: #include \"modulo.h\".",
    ),
    (
        r"redefinition of '(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'",
        "Redefinición de `{name}`",
        "El símbolo se define dos veces: solo puede existir una definición por programa.",
        "Marcá cabeceras con include guards (#ifndef/#define/#endif) y definí funciones una sola vez.",
    ),
    (
        r"comparison of integer expressions of different signedness",
        "Comparación entre entero con signo y sin signo",
        "Mezclar int y size_t/unsigned en <, > o == produce resultados sorpresivos por promoción de tipos.",
        "Unificá tipos de la comparación o casteá explícitamente; preferí size_t para tamaños.",
    ),
    (
        r"warning: suggest parentheses around assignment used as truth value",
        "¿= dentro de una condición?",
        "`if (a = b)` asigna en vez de comparar: casi siempre se quería `==`.",
        "Usá `==` para comparar; envolvé asignaciones intencionales en paréntesis dobles para silenciar el aviso.",
    ),
]

# Pre-compilar: (regex_compilada, plantilla_titulo, explicacion, sugerencia)
_COMPILED = [(re.compile(p, re.IGNORECASE), t, e, s) for p, t, e, s in _RULES]

_DIAG_LINE = re.compile(
    r"^(?P<file>[^:\n]+):(?P<line>\d+):(?:(?P<col>\d+):)?\s*(?P<level>error|warning|note|fatal error):\s*(?P<body>.+)$"
)


@dataclass
class TranslatedDiagnostic:
    original: str
    file: str = ""
    line: int = 0
    col: int = 0
    level: str = ""
    title: str = ""
    explanation: str = ""
    suggestion: str = ""
    matched_rule: bool = False

    @property
    def translated(self) -> bool:
        return self.matched_rule


def _format(template: str, match: re.Match) -> str:
    """Rellena plantillas con grupos nombrados del patrón."""
    if not template:
        return ""
    try:
        return template.format(**match.groupdict())
    except (KeyError, IndexError):
        return template


def translate_diagnostic_line(line: str) -> Optional[TranslatedDiagnostic]:
    """Traduce una sola línea de diagnóstico GCC (devuelve None si no es diagnóstico)."""
    m = _DIAG_LINE.match(line.strip())
    if not m:
        return None

    diag = TranslatedDiagnostic(
        original=line.rstrip("\n"),
        file=m.group("file"),
        line=int(m.group("line")),
        col=int(m.group("col") or 0),
        level=m.group("level"),
    )

    # GCC 12+ usa comillas tipográficas ('x'); normalizar para las reglas.
    body_norm = m.group("body").replace("\u2018", "'").replace("\u2019", "'")
    for regex, title_tpl, expl_tpl, sug_tpl in _COMPILED:
        rm = regex.search(body_norm)
        if rm:
            diag.title = _format(title_tpl, rm)
            diag.explanation = _format(expl_tpl, rm)
            diag.suggestion = _format(sug_tpl, rm)
            diag.matched_rule = True
            break

    if not diag.translated:
        diag.title = "Error de compilación"
        diag.explanation = m.group("body").strip()
        diag.suggestion = "Leé el identificador mencionado: indica qué construcción sintáctica falló."
    return diag


def translate_stderr(stderr: str) -> List[TranslatedDiagnostic]:
    """Traduce toda la salida de un gcc fallido; conserva también líneas de contexto."""
    results: List[TranslatedDiagnostic] = []
    for raw in stderr.splitlines():
        if not raw.strip():
            continue
        diag = translate_diagnostic_line(raw)
        if diag is None:
            continue
        results.append(diag)
    return results


def summarize_for_humans(diagnostics: List[TranslatedDiagnostic], max_items: int = 5) -> str:
    """Bloque de texto listo para informes: top-N diagnósticos traducidos."""
    errors = [d for d in diagnostics if d.level == "error"] or diagnostics
    lines = []
    for d in errors[:max_items]:
        loc = f"{d.file}:{d.line}" if d.file else f"línea {d.line}"
        lines.append(f"→ {loc} · {d.title}")
        if d.explanation and d.explanation != d.title:
            lines.append(f"  {d.explanation}")
        if d.suggestion:
            lines.append(f"  Sugerencia: {d.suggestion}")
    remaining = len(errors) - min(len(errors), max_items)
    if remaining > 0:
        lines.append(f"(… y {remaining} diagnósticos más)")
    return "\n".join(lines)
