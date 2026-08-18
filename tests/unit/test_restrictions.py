"""Unit tests for code restrictions and requirement validator."""

from ripley.restrictions import CodeRestrictionsValidator


def test_restrictions_forbidden_constructs():
    validator = CodeRestrictionsValidator(
        forbidden_constructs=["for", "while", "goto"],
        forbidden_headers=["string.h"],
        forbidden_functions=["qsort"],
    )

    bad_code = """
    #include <stdio.h>
    #include <string.h>

    int main() {
        for (int i = 0; i < 10; i++) {
            printf("%d\\n", i);
        }
        qsort(NULL, 0, 0, NULL);
        return 0;
    }
    """

    violations = validator.validate_code(bad_code, "test.c")
    assert len(violations) >= 3
    constructs = [v.construct for v in violations]
    assert "#string.h" in constructs
    assert "for" in constructs
    assert "qsort" in constructs


def test_restrictions_required_constructs():
    validator = CodeRestrictionsValidator(
        required_constructs=["recursion", "malloc", "struct"],
    )

    non_recursive_code = """
    #include <stdio.h>
    int sumar(int a, int b) {
        return a + b;
    }
    int main() {
        return 0;
    }
    """
    violations = validator.validate_code(non_recursive_code, "test.c")
    assert any(v.construct == "recursion" and v.violation_type == "REQUERIDO" for v in violations)
    assert any(v.construct == "malloc" and v.violation_type == "REQUERIDO" for v in violations)
    assert any(v.construct == "struct" and v.violation_type == "REQUERIDO" for v in violations)

    recursive_code = """
    #include <stdlib.h>
    struct Nodo { int valor; };
    int factorial(int n) {
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    }
    int main() {
        struct Nodo *n = malloc(sizeof(struct Nodo));
        free(n);
        return 0;
    }
    """
    violations_clean = validator.validate_code(recursive_code, "test.c")
    assert len(violations_clean) == 0
