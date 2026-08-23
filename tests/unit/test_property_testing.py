"""Unit tests for Property-Based Testing framework in C."""

from pathlib import Path
from ripley.tools.property_testing import PropertyTestRunner


def test_property_testing_idempotence_and_commutativity(tmp_path):
    student_c = tmp_path / "operaciones.c"
    student_c.write_text(
        """
        #include <stdlib.h>

        int valor_absoluto(int x) {
            return abs(x);
        }

        int sumar(int a, int b) {
            return a + b;
        }

        int no_conmutativo(int a, int b) {
            return a - b;
        }
        """,
        encoding="utf-8",
    )

    runner = PropertyTestRunner()

    # 1. Idempotencia: abs(abs(x)) == abs(x) -> PASSED
    res_idem = runner.run_property_test(
        student_source=student_c,
        property_type="IDEMPOTENCE",
        target_function="valor_absoluto",
        iterations=50,
    )
    assert res_idem.passed is True
    assert res_idem.iterations_run == 50

    # 2. Conmutatividad: sumar(a, b) == sumar(b, a) -> PASSED
    res_comm = runner.run_property_test(
        student_source=student_c,
        property_type="COMMUTATIVITY",
        target_function="sumar",
        iterations=50,
    )
    assert res_comm.passed is True

    # 3. Violación: no_conmutativo(a, b) != no_conmutativo(b, a) -> FAILED
    res_fail = runner.run_property_test(
        student_source=student_c,
        property_type="COMMUTATIVITY",
        target_function="no_conmutativo",
        iterations=50,
    )
    assert res_fail.passed is False
    assert res_fail.counterexample_output is not None
