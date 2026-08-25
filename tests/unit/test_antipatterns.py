"""Pruebas de c-antipatterns: los cuatro detectores de vicios en C."""

from ripley.core.antipatterns import (
    GodFunctionLinter,
    LoopControlMutationLinter,
    MallocCastLinter,
    StrlenAllocationLinter,
    analizar_antipatterns,
)

BANCO_CON_VICIOS = '''#include <stdlib.h>
#include <string.h>

char *copiar_malo(const char *s) {
    char *copia = (char *)malloc(strlen(s));
    if (copia == NULL) return NULL;
    strcpy(copia, s);
    return copia;
}

int procesar(int n) {
    int total = 0;
    for (int i = 0; i < n; i++) {
        if (i % 2 == 0) { i++; }
        total += i;
    }
    return total;
}
'''


def _reglas(hallazgos):
    return {h.linter_name for h in hallazgos}


def test_cast_de_malloc_se_detecta():
    hallazgos = MallocCastLinter().analyze(BANCO_CON_VICIOS, "x.c")
    assert len(hallazgos) == 1
    assert hallazgos[0].line == 5
    assert "C99" in hallazgos[0].message


def test_strlen_sin_byte_nulo_es_error():
    hallazgos = StrlenAllocationLinter().analyze(BANCO_CON_VICIOS, "x.c")
    assert len(hallazgos) == 1
    assert hallazgos[0].severity == "ERROR"
    assert "+ 1" in hallazgos[0].suggestion


def test_mutacion_de_variable_de_control():
    hallazgos = LoopControlMutationLinter().analyze(BANCO_CON_VICIOS, "x.c")
    assert len(hallazgos) == 1
    assert "'i'" in hallazgos[0].message


def test_for_limpio_no_genera_falsos_positivos():
    limpio = "int f(int n) {\n    int t = 0;\n    for (int i = 0; i < n; i++) {\n        t += i;\n    }\n    return t;\n}\n"
    assert LoopControlMutationLinter().analyze(limpio, "ok.c") == []


def test_god_function_por_longitud():
    larga = ("int larga(int x) {\n"
             + "\n".join(f"    x += {i};" for i in range(45))
             + "\n    return x;\n}\n")
    hallazgos = GodFunctionLinter().analyze(larga, "larga.c")
    assert len(hallazgos) == 1
    assert "god function" in hallazgos[0].message
    assert "líneas" in hallazgos[0].message


def test_god_function_por_cantidad_de_locales():
    muchas = ("int mucha(int x) {\n"
              + "\n".join(f"    int v{i} = {i};" for i in range(12))
              + "\n    return x + v0 + v11;\n}\n")
    hallazgos = GodFunctionLinter().analyze(muchas, "mucha.c")
    assert any("locales" in h.message for h in hallazgos)


def test_codigo_limpio_sin_hallazgos():
    limpio = '''#include <stdlib.h>

char *copiar_bien(size_t n) {
    char *copia = malloc(n + 1);
    if (copia == NULL) {
        return NULL;
    }
    copia[n] = '\\0';
    return copia;
}
'''
    assert analizar_antipatterns(limpio, "bien.c") == []


def test_agregador_ejecuta_todos_los_detectores():
    reglas = _reglas(analizar_antipatterns(BANCO_CON_VICIOS, "x.c"))
    assert {
        "antipattern.malloc_cast",
        "antipattern.strlen_sin_nulo",
        "antipattern.loop_control_mutation",
    } <= reglas
