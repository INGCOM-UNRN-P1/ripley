"""Unit tests for DynamicTestRunner, ValgrindRunner, CppcheckRunner and RubricCalculator."""

from pathlib import Path
import subprocess

from ripley.compiler import Compiler
from ripley.config import (
    CompilerConfig,
    CppcheckConfig,
    LimitsConfig,
    RubricConfig,
    SandboxConfig,
    ValgrindConfig,
)
from ripley.runner import (
    CppcheckRunner,
    DynamicTestRunner,
    RubricCalculator,
    ValgrindRunner,
    normalize_output_text,
)
from ripley.testcases import TestCaseInfo


def test_normalize_output_text():
    raw = "line 1   \r\nline 2\t  \n\n\n"
    norm = normalize_output_text(raw)
    assert norm == "line 1\nline 2"


def test_dynamic_test_runner_with_argv_and_stdin(tmp_path):
    # Compilar un programa en C que lee argv y stdin
    src_file = tmp_path / "echo_app.c"
    src_file.write_text(
        """
        #include <stdio.h>
        int main(int argc, char *argv[]) {
            int val = 0;
            scanf("%d", &val);
            printf("Arg: %s, Stdin: %d\\n", argc > 1 ? argv[1] : "none", val * 2);
            return 0;
        }
        """,
        encoding="utf-8",
    )
    bin_file = tmp_path / "echo_app.out"

    compiler = Compiler(
        CompilerConfig(executable="gcc", flags=["-std=c11"]),
        LimitsConfig(timeout_segundos=5),
        SandboxConfig(),
    )
    comp_res = compiler.compile([src_file], bin_file)
    assert comp_res.success is True

    # Crear caso de prueba
    in_file = tmp_path / "caso1.in"
    in_file.write_text("21\n", encoding="utf-8")
    out_file = tmp_path / "caso1.out"
    out_file.write_text("Arg: foo, Stdin: 42\n", encoding="utf-8")
    argv_file = tmp_path / "caso1.argv"
    argv_file.write_text("foo\n", encoding="utf-8")

    tc = TestCaseInfo(
        exercise="echo",
        case_name="caso1",
        in_file=in_file,
        out_file=out_file,
        argv_file=argv_file,
    )

    runner = DynamicTestRunner(LimitsConfig(timeout_segundos=5))
    res = runner.run_case(bin_file, tc)
    assert res.resultado == "PASSED"
    assert res.tiempo_ms > 0


def test_dynamic_test_runner_detects_mismatch(tmp_path):
    src_file = tmp_path / "fail_app.c"
    src_file.write_text(
        """
        #include <stdio.h>
        int main() {
            printf("wrong answer\\n");
            return 0;
        }
        """,
        encoding="utf-8",
    )
    bin_file = tmp_path / "fail_app.out"

    compiler = Compiler(CompilerConfig(), LimitsConfig(), SandboxConfig())
    compiler.compile([src_file], bin_file)

    in_file = tmp_path / "caso1.in"
    in_file.write_text("", encoding="utf-8")
    out_file = tmp_path / "caso1.out"
    out_file.write_text("correct answer\n", encoding="utf-8")

    tc = TestCaseInfo(
        exercise="fail",
        case_name="caso1",
        in_file=in_file,
        out_file=out_file,
        argv_file=None,
    )

    runner = DynamicTestRunner(LimitsConfig(timeout_segundos=5))
    res = runner.run_case(bin_file, tc)
    assert res.resultado == "FAILED"


def test_rubric_calculator():
    calc = RubricCalculator(
        RubricConfig(
            peso_compilacion=0.25,
            peso_linter=0.25,
            peso_estilo=0.15,
            peso_pruebas=0.35,
        )
    )

    # Caso perfecto: compila, estilo 10, 0 linter errors, 2/2 tests
    breakdown = calc.calculate(
        compiled=True,
        style_score=10.0,
        linter_passed=True,
        linter_violations=0,
        tests_passed_count=2,
        total_tests_count=2,
    )
    assert breakdown.nota_compilacion == 10.0
    assert breakdown.nota_estilo == 10.0
    assert breakdown.nota_linter == 10.0
    assert breakdown.nota_pruebas == 10.0
    assert breakdown.nota_preliminar == 10.0

    # Caso parcial: compila (10), estilo 8.0, 1 advertencia linter (8.0), 1/2 tests (5.0)
    # Preliminar = 10*0.25 + 8*0.25 + 8*0.15 + 5*0.35 = 2.5 + 2.0 + 1.2 + 1.75 = 7.45
    breakdown_part = calc.calculate(
        compiled=True,
        style_score=8.0,
        linter_passed=False,
        linter_violations=1,
        tests_passed_count=1,
        total_tests_count=2,
    )
    assert breakdown_part.nota_preliminar == 7.45

    # Si no compila: todo 0
    breakdown_fail = calc.calculate(
        compiled=False,
        style_score=10.0,
        linter_passed=True,
        linter_violations=0,
        tests_passed_count=0,
        total_tests_count=2,
    )
    assert breakdown_fail.nota_preliminar == 0.0
