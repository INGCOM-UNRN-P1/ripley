"""Unit tests for Programación I official rules checker (0xXXXXh)."""

from ripley.p1_rules import P1RuleChecker


def test_p1_rules_syntax_and_nomenclature():
    checker = P1RuleChecker()

    # 1. 0x0002h: Multiple declarations per line
    code_multi_decl = """
    int main() {
        int a, b, c;
        return 0;
    }
    """
    obs = checker.analyze(code_multi_decl)
    assert any(o.rule_code == "0x0002h" for o in obs)

    # 2. 0x0004h: Binary operators spacing
    code_spacing = """
    int main() {
        int x = 10;
        if (x==10) return 0;
        return 1;
    }
    """
    obs_spacing = checker.analyze(code_spacing)
    assert any(o.rule_code == "0x0004h" for o in obs_spacing)

    # 3. 0x0006h: Asterisk on type instead of identifier
    code_star = """
    int main() {
        int* ptr = NULL;
        return 0;
    }
    """
    obs_star = checker.analyze(code_star)
    assert any(o.rule_code == "0x0006h" for o in obs_star)

    # 4. 0x0007h: camelCase in variable name
    code_camel = """
    int main() {
        int miContador = 0;
        return miContador;
    }
    """
    obs_camel = checker.analyze(code_camel)
    assert any(o.rule_code == "0x0007h" for o in obs_camel)


def test_p1_rules_control_structures():
    checker = P1RuleChecker()

    # 1. 0x1001h: Single-line if without braces
    code_no_braces = """
    int main() {
        int x = 5;
        if (x > 0) x++;
        return x;
    }
    """
    obs = checker.analyze(code_no_braces)
    assert any(o.rule_code == "0x1001h" for o in obs)

    # 2. 0x1002h: continue
    code_continue = """
    int main() {
        for (int i = 0; i < 5; i++) {
            continue;
        }
        return 0;
    }
    """
    obs_cont = checker.analyze(code_continue)
    assert any(o.rule_code == "0x1002h" for o in obs_cont)

    # 3. 0x1006h: goto
    code_goto = """
    int main() {
        goto salida;
    salida:
        return 0;
    }
    """
    obs_goto = checker.analyze(code_goto)
    assert any(o.rule_code == "0x1006h" for o in obs_goto)

    # 4. 0x1007h: Ternary operator
    code_ternary = """
    int main() {
        int x = (5 > 2) ? 1 : 0;
        return x;
    }
    """
    obs_ternary = checker.analyze(code_ternary)
    assert any(o.rule_code == "0x1007h" for o in obs_ternary)

    # 5. 0x1008h: switch without default
    code_switch = """
    int main() {
        int x = 1;
        switch (x) {
            case 1: break;
        }
        return 0;
    }
    """
    obs_switch = checker.analyze(code_switch)
    assert any(o.rule_code == "0x1008h" for o in obs_switch)


def test_p1_rules_pointers_and_memory():
    checker = P1RuleChecker()

    # 1. 0x3001h: malloc without NULL check
    code_malloc = """
    #include <stdlib.h>
    void procesar() {
        int *p = malloc(sizeof(int) * 10);
        p[0] = 42;
    }
    """
    obs_malloc = checker.analyze(code_malloc)
    assert any(o.rule_code == "0x3001h" for o in obs_malloc)

    # 2. 0x3003h: Assignment inside if condition
    code_assign_if = """
    #include <stdlib.h>
    int main() {
        int *p;
        if ((p = malloc(10)) == NULL) {
            return 1;
        }
        return 0;
    }
    """
    obs_assign_if = checker.analyze(code_assign_if)
    assert any(o.rule_code == "0x3003h" for o in obs_assign_if)

    # 3. 0x3004h: Struct without typedef
    code_struct = """
    struct Persona {
        int edad;
    };
    """
    obs_struct = checker.analyze(code_struct)
    assert any(o.rule_code == "0x3004h" for o in obs_struct)


def test_p1_rules_good_practices_and_functions():
    checker = P1RuleChecker()

    # 1. 0x2004h: Global variable
    code_global = """
    int contador_global = 0;
    int main() {
        return contador_global;
    }
    """
    obs_global = checker.analyze(code_global)
    assert any(o.rule_code == "0x2004h" for o in obs_global)

    # 2. 0x5001h: VLA
    code_vla = """
    int main() {
        int n = 10;
        int arreglo[n];
        return 0;
    }
    """
    obs_vla = checker.analyze(code_vla)
    assert any(o.rule_code == "0x5001h" for o in obs_vla)

    # 3. 0x5006h: gets()
    code_gets = """
    int main() {
        char buf[10];
        gets(buf);
        return 0;
    }
    """
    obs_gets = checker.analyze(code_gets)
    assert any(o.rule_code == "0x5006h" for o in obs_gets)
