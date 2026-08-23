"""Unit tests for specialized linters (magic numbers, clones, and naming conventions)."""

from ripley.core.linters import (
    InternalCloneLinter,
    MagicNumberLinter,
    NamingConfig,
    NamingConventionLinter,
)


def test_magic_number_linter():
    code = """
    #define MAX_ITEMS 100
    int procesar(int a) {
        int x = a * 42; // 42 es un número mágico
        int y = a + 1;  // 1 está permitido
        return x + y;
    }
    """
    linter = MagicNumberLinter(allowed_numbers={"0", "1", "2", "-1"})
    obs = linter.analyze(code, "test.c")

    assert len(obs) == 1
    assert "42" in obs[0].message
    assert obs[0].line == 4


def test_internal_clone_linter():
    code = """
    int funcion_a(int x) {
        int r = 0;
        for (int i = 0; i < x; i++) {
            r += i * 2 + 10;
        }
        return r;
    }

    int funcion_b(int y) {
        int r = 0;
        for (int i = 0; i < y; i++) {
            r += i * 2 + 10;
        }
        return r;
    }
    """
    linter = InternalCloneLinter(min_token_length=10)
    clones = linter.analyze(code, "test.c")

    assert len(clones) >= 1
    match = clones[0]
    assert match.function_a == "funcion_a"
    assert match.function_b == "funcion_b"


def test_naming_convention_linter():
    code = """
    #define max_size 50
    typedef struct { int x; } MiNodo;

    void ProcesarDatos(int x) {
        int i = 0;
        int z = 10;
        int num = 20;
        (void)x;
        (void)i;
        (void)z;
        (void)num;
    }
    """
    config = NamingConfig(
        function_style="snake_case",
        constant_style="UPPER_CASE",
        type_prefix="t_",
    )
    linter = NamingConventionLinter(config)
    obs = linter.analyze(code, "test.c")

    assert any("ProcesarDatos" in o.message and "snake_case" in o.message for o in obs)
    assert any("max_size" in o.message and "UPPER_CASE" in o.message for o in obs)
    assert any("MiNodo" in o.message and "t_" in o.message for o in obs)
    assert any("Variable de 1 letra: `i`" in o.message for o in obs)
    assert any("Variable de 1 letra no descriptiva: `z`" in o.message for o in obs)
    assert any("Nombre de variable corto (3 letras): `num`" in o.message for o in obs)

