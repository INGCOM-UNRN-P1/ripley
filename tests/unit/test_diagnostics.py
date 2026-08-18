"""Unit tests for specialized diagnostics (Stack Overflow, Stdin Deadlock, Dangling Pointers)."""

from ripley.diagnostics import (
    DiagnosisType,
    detect_static_dangling_pointers,
    diagnose_runtime_crash,
)


def test_diagnose_stack_overflow():
    res = diagnose_runtime_crash(
        returncode=-11,
        stdout="",
        stderr="AddressSanitizer:DEADLYSIGNAL\n==1234==ERROR: AddressSanitizer: stack-overflow on address 0x7ffe",
        timeout=False,
        input_data="10\n",
    )
    assert res.diagnosis == DiagnosisType.STACK_OVERFLOW
    assert "recursivas" in res.pedagogical_hint


def test_diagnose_use_after_free_and_double_free():
    res_uaf = diagnose_runtime_crash(
        returncode=-11,
        stdout="",
        stderr="ERROR: AddressSanitizer: heap-use-after-free on address 0x602000000010",
        timeout=False,
        input_data="",
    )
    assert res_uaf.diagnosis == DiagnosisType.USE_AFTER_FREE
    assert "free()" in res_uaf.pedagogical_hint

    res_df = diagnose_runtime_crash(
        returncode=-6,
        stdout="",
        stderr="free(): double free detected in tcache 2",
        timeout=False,
        input_data="",
    )
    assert res_df.diagnosis == DiagnosisType.DOUBLE_FREE


def test_diagnose_stdin_deadlock():
    # Timeout con entrada corta agotada por el programa
    res = diagnose_runtime_crash(
        returncode=0,
        stdout="",
        stderr="",
        timeout=True,
        input_data="10\n",
    )
    assert res.diagnosis == DiagnosisType.STDIN_DEADLOCK
    assert "scanf" in res.pedagogical_hint


def test_detect_static_dangling_pointers():
    code = """
    #include <stdlib.h>
    void test() {
        int *ptr = malloc(sizeof(int));
        *ptr = 10;
        free(ptr);
        *ptr = 20; // Dangling pointer!
    }
    """
    violations = detect_static_dangling_pointers(code)
    assert len(violations) >= 1
    line, var, msg = violations[0]
    assert var == "ptr"
    assert "Dangling Pointer" in msg
