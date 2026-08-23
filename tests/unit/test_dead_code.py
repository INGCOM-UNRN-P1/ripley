"""Unit tests for dead code and unreachable function detection."""

from ripley.core.callgraph import CallGraphGenerator
from ripley.core.linters import DeadCodeLinter


def test_dead_code_linter_detects_unreachable_function():
    code = """
    #include <stdio.h>

    void funcion_utilizada(void) {
        printf("En uso\\n");
    }

    void funcion_olvidada(void) {
        printf("Nunca llamada\\n");
    }

    int main() {
        funcion_utilizada();
        return 0;
    }
    """
    linter = DeadCodeLinter()
    obs = linter.analyze(code, "test.c")

    assert len(obs) == 1
    assert "funcion_olvidada" in obs[0].message
