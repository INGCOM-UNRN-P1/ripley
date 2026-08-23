"""Unit tests for AST semantic diffing module."""

from pathlib import Path
from ripley.core.semantic_diff import SemanticDiffer, extract_c_functions


def test_extract_c_functions():
    code = """
    #include <stdio.h>

    int sumar(int a, int b) {
        return a + b;
    }

    void imprimir_saludo(void) {
        printf("Hola\\n");
    }
    """
    funcs = extract_c_functions(code)
    assert "sumar" in funcs
    assert "imprimir_saludo" in funcs
    assert funcs["sumar"].return_type == "int"
    assert "int a, int b" in funcs["sumar"].params


def test_semantic_diff_identifies_logical_vs_cosmetic_changes():
    old_code = """
    int procesar(int a) {
        int x = a * 2;
        return x + 1;
    }
    """

    # Cambio puramente cosmético: renombrado de x a resultado y espacios
    cosmetic_code = """
    int procesar(int a)
    {
        int resultado = a * 2;
        return resultado + 1;
    }
    """

    # Cambio lógico: condición cambiada
    logic_code = """
    int procesar(int a) {
        int x = a * 3; // Lógica cambiada
        if (x > 10) return x;
        return x + 1;
    }
    """

    differ = SemanticDiffer()

    # 1. Comparación con cambio cosmético
    diff_cosmetic = differ.compare_c_codes("tp.c", old_code, cosmetic_code)
    assert not diff_cosmetic.has_semantic_changes
    assert any(c.category == "COSMETICO" for c in diff_cosmetic.changes)

    # 2. Comparación con cambio lógico
    diff_logic = differ.compare_c_codes("tp.c", old_code, logic_code)
    assert diff_logic.has_semantic_changes
    assert any(c.category == "MODIFICADO_LOGICA" for c in diff_logic.changes)
