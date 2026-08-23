"""Unit tests for PureFunctionAnalyzer."""

from pathlib import Path
from ripley.tools.pure_functions import PureFunctionAnalyzer


def test_pure_function_static_analysis():
    code = """
    #include <stdio.h>

    int funcion_pura(int a, int b) {
        return a + b;
    }

    int funcion_impura(int a) {
        printf("Efecto colateral: %d\\n", a);
        return a * 2;
    }
    """
    analyzer = PureFunctionAnalyzer()
    obs = analyzer.analyze_static(code)

    assert len(obs) == 2
    by_name = {o.function_name: o for o in obs}

    assert by_name["funcion_pura"].is_pure is True
    assert by_name["funcion_pura"].is_const is True
    assert by_name["funcion_pura"].suggested_attribute == "__attribute__((const))"

    assert by_name["funcion_impura"].is_pure is False
    assert len(by_name["funcion_impura"].violations) > 0


def test_pure_function_injection_and_compiler_verification(tmp_path):
    c_file = tmp_path / "suma.c"
    c_file.write_text(
        """
        int duplicar(int x) {
            return x * 2;
        }

        int main() {
            return duplicar(21) == 42 ? 0 : 1;
        }
        """,
        encoding="utf-8",
    )

    analyzer = PureFunctionAnalyzer()
    injected = analyzer.inject_pure_attributes(c_file.read_text(encoding="utf-8"), mode="const")
    assert "__attribute__((const))" in injected

    ok, msg = analyzer.verify_with_compiler(c_file, mode="const")
    assert ok is True
    assert "cumplen estrictamente" in msg
