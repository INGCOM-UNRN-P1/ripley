"""Unit tests for AST auditors and C linters."""

from ripley.core.ast_auditors import (
    BackwardGotoLinter,
    ConstCorrectnessLinter,
    DanglingStackPointerLinter,
    DeepFreeLinter,
    DeprecatedAPILinter,
    EnumBitmaskLinter,
    EvaluationOrderLinter,
    FloatComparisonLinter,
    IWYULinter,
    LoopTerminationLinter,
    OverengineeringLinter,
    ShortCircuitLinter,
    StringLiteralWriteLinter,
    StringNullPointerLinter,
    VariableShadowingLinter,
)



def test_float_comparison_linter():
    code = """
    int main() {
        float a = 1.0f;
        float b = 2.0f;
        if (a == b) {
            return 1;
        }
        return 0;
    }
    """
    obs = FloatComparisonLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "float_comparison" in obs[0].linter_name


def test_iwyu_unused_include():
    code = """
    #include <math.h>
    #include <stdio.h>

    int main() {
        printf("Hola mundo\\n");
        return 0;
    }
    """
    obs = IWYULinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "math.h" in obs[0].message


def test_const_correctness_linter():
    code = """
    int calcular_largo(char *cadena) {
        int l = 0;
        while (cadena[l] != '\\0') l++;
        return l;
    }
    """
    obs = ConstCorrectnessLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "cadena" in obs[0].message
    assert "const" in obs[0].suggestion


def test_short_circuit_side_effect():
    code = """
    int evaluar(int x, int i) {
        if (x > 0 && i++) {
            return 1;
        }
        return 0;
    }
    """
    obs = ShortCircuitLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "short_circuit_side_effect" in obs[0].linter_name


def test_deep_free_linter():
    code = """
    #include <stdlib.h>
    struct Nodo {
        char *nombre;
        int edad;
    };

    void destruir(struct Nodo *n) {
        free(n);
    }
    """
    obs = DeepFreeLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "deep_free_verifier" in obs[0].linter_name
    assert "nombre" in obs[0].message


def test_string_null_pointer_linter():
    code = """
    #include <string.h>
    int proceso(char *str) {
        return strlen(str);
    }
    """
    obs = StringNullPointerLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "string_null_pointer" in obs[0].linter_name


def test_variable_shadowing_linter():
    code = """
    void procesar(int contador) {
        int contador = 10;
        (void)contador;
    }
    """
    obs = VariableShadowingLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "variable_shadowing" in obs[0].linter_name
    assert "contador" in obs[0].message


def test_dangling_stack_pointer_linter():
    code = """
    int* obtener_puntero() {
        int x = 42;
        return &x;
    }
    """
    obs = DanglingStackPointerLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert obs[0].severity == "ERROR"
    assert "dangling_stack_pointer" in obs[0].linter_name


def test_overengineering_linter():
    code = """
    void swap(int a, int b) {
        a ^= b; b ^= a; a ^= b;
    }
    """
    obs = OverengineeringLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "overengineering" in obs[0].linter_name


def test_evaluation_order_linter():
    code = """
    int sumar(int a, int b) { return a + b; }
    int main() {
        int i = 0;
        int res = sumar(i++, i++);
        return res;
    }
    """
    obs = EvaluationOrderLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "evaluation_order_dependency" in obs[0].linter_name
    assert "i" in obs[0].message


def test_string_literal_write_linter():
    code = """
    int main() {
        char *mensaje = "hola mundo";
        mensaje[0] = 'H';
        return 0;
    }
    """
    obs = StringLiteralWriteLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert obs[0].severity == "ERROR"
    assert "rodata_string_write" in obs[0].linter_name


def test_backward_goto_linter():
    code = """
    int main() {
        int i = 0;
    bucle_inicio:
        i++;
        if (i < 10) {
            goto bucle_inicio;
        }
        return i;
    }
    """
    obs = BackwardGotoLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "backward_goto" in obs[0].linter_name
    assert "bucle_inicio" in obs[0].message


def test_deprecated_api_linter():
    code = """
    #include <stdio.h>
    int main() {
        char nombre[64];
        char copia[128];
        gets(nombre);
        strcpy(copia, nombre);
        sprintf(copia, "valor: %s", nombre);
        return 0;
    }
    """
    obs = DeprecatedAPILinter().analyze(code, "test.c")
    assert len(obs) == 3
    assert all("deprecated_api" in o.linter_name for o in obs)
    funciones = [o.message for o in obs]
    assert any("gets" in m for m in funciones)
    assert any("strcpy" in m for m in funciones)
    assert any("sprintf" in m for m in funciones)


def test_deprecated_api_linter_clean_code():
    code = """
    #include <stdio.h>
    int main() {
        char nombre[64];
        fgets(nombre, sizeof(nombre), stdin);
        snprintf(nombre, sizeof(nombre), "ok");
        return 0;
    }
    """
    obs = DeprecatedAPILinter().analyze(code, "test.c")
    assert len(obs) == 0


def test_enum_bitmask_valid_flags():
    code = """
    enum permisos {
        LECTURA = 1,
        ESCRITURA = 2,
        EJECUCION = 4
    };
    int main() {
        int p = LECTURA | ESCRITURA;
        if (p & LECTURA) { return 1; }
        return 0;
    }
    """
    obs = EnumBitmaskLinter().analyze(code, "test.c")
    assert len(obs) == 0


def test_enum_bitmask_invalid_flags():
    code = """
    enum estado {
        INACTIVO = 0,
        ACTIVO = 1,
        PAUSADO = 2,
        ERROR = 3
    };
    int main() {
        int s = ACTIVO | PAUSADO;
        return s & ERROR;
    }
    """
    obs = EnumBitmaskLinter().analyze(code, "test.c")
    assert len(obs) >= 1
    assert "enum_bitmask" in obs[0].linter_name


def test_loop_termination_detects_infinite_while():
    code = """
    int main() {
        int i = 0;
        while (i < 10) {
            printf("%d\\n", i);
        }
        return 0;
    }
    """
    obs = LoopTerminationLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "loop_termination" in obs[0].linter_name


def test_loop_termination_accepts_mutated_counter():
    code = """
    int main() {
        int i = 0;
        while (i < 10) {
            printf("%d\\n", i);
            i++;
        }
        return 0;
    }
    """
    obs = LoopTerminationLinter().analyze(code, "test.c")
    assert len(obs) == 0


def test_loop_termination_accepts_sentinela_con_lectura():
    code = """
    int main() {
        int valor = 0;
        while (valor != -1) {
            scanf("%d", &valor);
        }
        return 0;
    }
    """
    obs = LoopTerminationLinter().analyze(code, "test.c")
    assert len(obs) == 0


def test_loop_termination_detects_do_while_infinito():
    code = """
    int main() {
        int x = 5;
        do {
            printf("%d\\n", x);
        } while (x > 0);
        return 0;
    }
    """
    obs = LoopTerminationLinter().analyze(code, "test.c")
    assert len(obs) == 1
    assert "do-while" in obs[0].message

