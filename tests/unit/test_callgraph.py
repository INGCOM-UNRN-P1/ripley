"""Unit tests for Call Graph generator."""

from pathlib import Path
from ripley.callgraph import CallGraphGenerator


def test_callgraph_extracts_calls_and_recursion():
    code = """
    #include <stdio.h>

    int factorial(int n) {
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    }

    void imprimir_resultado(int val) {
        printf("Resultado: %d\\n", val);
    }

    int main() {
        int res = factorial(5);
        imprimir_resultado(res);
        return 0;
    }
    """
    gen = CallGraphGenerator()
    cg = gen.build_callgraph(code)

    assert "main" in cg.defined_functions
    assert "factorial" in cg.defined_functions
    assert "imprimir_resultado" in cg.defined_functions

    # Llamadas detectadas
    assert ("main", "factorial") in cg.calls
    assert ("main", "imprimir_resultado") in cg.calls
    assert ("factorial", "factorial") in cg.calls
    assert "factorial" in cg.recursive_functions

    # Mermaid
    mermaid = gen.to_mermaid(cg)
    assert "fn_main --> fn_factorial" in mermaid
    assert "fn_factorial --> fn_factorial" in mermaid
    assert "Recursiva" in mermaid
