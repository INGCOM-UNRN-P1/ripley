"""Unit tests for fuzzing module."""

from pathlib import Path
from ripley.fuzzing import Fuzzer


def test_fuzzer_generates_edge_cases():
    fuzzer = Fuzzer()
    num_cases = fuzzer.generate_numeric_edge_cases()
    assert any("2147483647" in c for c in num_cases)
    assert any("0" in c for c in num_cases)

    str_cases = fuzzer.generate_string_edge_cases()
    assert any(len(c) >= 256 for c in str_cases)


def test_fuzzer_generates_testcases_with_reference_solution(tmp_path):
    # Crear solución modelo de referencia en C
    ref_sol = tmp_path / "solucion.c"
    ref_sol.write_text(
        """
        #include <stdio.h>
        int main() {
            int a = 0, b = 0;
            if (scanf("%d %d", &a, &b) == 2) {
                printf("Suma: %d\\n", a + b);
            } else {
                printf("Entrada invalida\\n");
            }
            return 0;
        }
        """,
        encoding="utf-8",
    )

    tests_out_dir = tmp_path / "tests" / "ejercicio1"
    fuzzer = Fuzzer(seed=123)

    pairs = fuzzer.generate_testcases(
        target_dir=tests_out_dir,
        cases_count=3,
        reference_source_or_binary=ref_sol,
        start_index=1,
    )

    assert len(pairs) == 3
    for in_f, out_f in pairs:
        assert in_f.exists()
        assert out_f.exists()
        assert len(out_f.read_text(encoding="utf-8")) > 0
