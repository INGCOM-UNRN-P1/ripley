"""Los diagnósticos de gcc con rutas de Windows se reconocen (N-ECO-22).

MinGW (MSYS2 UCRT64) informa la ruta con la letra de unidad: «C:\\Users\\…\\main.c:5:12: error: …».
Las expresiones tomaban el archivo como «todo hasta el primer ':'»: el traductor (anclado al
principio de la línea) no reconocía nada y los sanitizers perdían la unidad en el nombre.
"""

from ripley.core.gcc_translator import translate_diagnostic_line
from ripley.core.sanitizers import SanitizerAnalyzer

RUTA = "C:\\Users\\runneradmin\\AppData\\Local\\Temp\\tp\\main.c"


def test_el_traductor_reconoce_rutas_con_unidad():
    d = translate_diagnostic_line(f"{RUTA}:5:12: error: expected ';' before 'return'")
    assert d is not None and d.translated
    assert (d.file, d.line, d.col) == (RUTA, 5, 12)


def test_los_sanitizers_conservan_la_unidad():
    (hallazgo,) = SanitizerAnalyzer().parse_compiler_uninitialized_warnings(
        f"{RUTA}:7:9: warning: 'total' is used uninitialized [-Wuninitialized]")
    assert hallazgo.filename == RUTA and hallazgo.line == 7
