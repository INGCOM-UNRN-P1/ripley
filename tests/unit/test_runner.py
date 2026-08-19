"""Unit tests for DynamicTestRunner, ValgrindRunner, CppcheckRunner and RubricCalculator."""

from pathlib import Path
import subprocess

from ripley.compiler import Compiler
from ripley.config import (
    CompilerConfig,
    CppcheckConfig,
    CustomToolConfig,
    LimitsConfig,
    RubricConfig,
    SandboxConfig,
    ValgrindConfig,
)
from ripley.runner import (
    CppcheckRunner,
    CustomToolRunner,
    DynamicTestRunner,
    RubricCalculator,
    ValgrindRunner,
    compare_outputs,
    normalize_output_text,
)
from ripley.testcases import TestCaseInfo



def test_normalize_output_text():
    raw = "line 1   \r\nline 2\t  \n\n\n"
    norm = normalize_output_text(raw)
    assert norm == "line 1\nline 2"


def test_compare_outputs_exact_regex_and_fuzzy():
    # 1. Exacto
    assert compare_outputs("Hola mundo\n", "Hola mundo")

    # 2. Regex
    expected_regex = "REGEX: ^Resultado: \\d+$"
    assert compare_outputs("Resultado: 42\n", expected_regex)
    assert not compare_outputs("Resultado: cuarenta\n", expected_regex)

    # 3. Fuzzy (casing, espacios, puntuación)
    actual = "El resultado es: 42!"
    expected_fuzzy = "el  resultado   es 42"
    assert compare_outputs(actual, expected_fuzzy, fuzzy=True)



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


def test_custom_tool_runner(tmp_path):
    runner = CustomToolRunner(LimitsConfig(timeout_segundos=3))
    dummy_c = tmp_path / "dummy.c"
    dummy_c.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    # 1. Herramienta estándar que devuelve éxito (ej. 'echo')
    tool_echo = CustomToolConfig(
        name="echo_test",
        command="echo Analizando archivo {filename}",
        enabled=True,
        stage="source",
    )
    res_echo = runner.run(tool_echo, source=dummy_c)
    assert res_echo.success is True
    assert "Analizando archivo dummy.c" in res_echo.output

    # 2. Herramienta inexistente en PATH
    tool_nonexistent = CustomToolConfig(
        name="fake_tool",
        command="non_existent_tool_12345 {source}",
        enabled=True,
    )
    res_nonexistent = runner.run(tool_nonexistent, source=dummy_c)
    assert res_nonexistent.success is False
    assert res_nonexistent.returncode == 127

