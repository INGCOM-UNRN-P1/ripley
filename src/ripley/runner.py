"""Dynamic test runner, Valgrind memory auditor, Cppcheck static analyzer and rubric calculator."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Sequence, Tuple

from ripley.compiler import set_process_limits
from ripley.config import CppcheckConfig, LimitsConfig, RubricConfig, ValgrindConfig
from ripley.testcases import TestCaseInfo


@dataclass
class TestResultDetail:
    ejercicio: str
    nombre_caso: str
    argumentos_cli: str
    resultado: str  # "PASSED" | "FAILED" | "TIMEOUT" | "ERROR"
    tiempo_ms: float
    stdout: str = ""
    stderr: str = ""
    esperado: str = ""


@dataclass
class ValgrindResult:
    enabled: bool
    passed: bool
    summary: str
    full_output: str


@dataclass
class CppcheckResult:
    passed: bool
    violations_count: int
    summary: str
    full_output: str


@dataclass
class RubricScoreBreakdown:
    nota_compilacion: float  # 0 a 10
    nota_estilo: float  # 0 a 10
    nota_linter: float  # 0 a 10
    nota_pruebas: float  # 0 a 10
    nota_preliminar: float  # 0 a 10


def normalize_output_text(text: str) -> str:
    """Normaliza texto removiendo espacios finales por línea y saltos de línea al final."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    # Eliminar líneas vacías al final
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


class DynamicTestRunner:
    """Ejecuta los casos de prueba I/O contra el binario compilado."""

    def __init__(self, limits_cfg: LimitsConfig) -> None:
        self.limits_cfg = limits_cfg

    def run_case(
        self,
        binary_path: Path | str,
        test_case: TestCaseInfo,
    ) -> TestResultDetail:
        bin_path = Path(binary_path)
        if not bin_path.exists():
            return TestResultDetail(
                ejercicio=test_case.exercise,
                nombre_caso=test_case.case_name,
                argumentos_cli="",
                resultado="ERROR",
                tiempo_ms=0.0,
                stderr="Binario no encontrado.",
            )

        # Leer argumentos CLI si existe .argv
        cli_args: List[str] = []
        raw_args_str = ""
        if test_case.argv_file and test_case.argv_file.exists():
            raw_args_str = test_case.argv_file.read_text(encoding="utf-8").strip()
            if raw_args_str:
                cli_args = shlex.split(raw_args_str)

        # Leer entrada .in
        stdin_data = ""
        if test_case.in_file and test_case.in_file.exists():
            stdin_data = test_case.in_file.read_text(encoding="utf-8")

        # Leer salida esperada .out
        expected_out = ""
        if test_case.out_file and test_case.out_file.exists():
            expected_out = test_case.out_file.read_text(encoding="utf-8")

        cmd = [str(bin_path)] + cli_args
        start_time = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=self.limits_cfg.timeout_segundos,
                preexec_fn=lambda: set_process_limits(
                    self.limits_cfg.limite_memoria_mb,
                    self.limits_cfg.timeout_segundos,
                ),
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            norm_actual = normalize_output_text(proc.stdout)
            norm_expected = normalize_output_text(expected_out)

            if proc.returncode != 0:
                result_status = "ERROR"
            elif norm_actual == norm_expected:
                result_status = "PASSED"
            else:
                result_status = "FAILED"

            return TestResultDetail(
                ejercicio=test_case.exercise,
                nombre_caso=test_case.case_name,
                argumentos_cli=raw_args_str,
                resultado=result_status,
                tiempo_ms=elapsed_ms,
                stdout=proc.stdout,
                stderr=proc.stderr,
                esperado=expected_out,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return TestResultDetail(
                ejercicio=test_case.exercise,
                nombre_caso=test_case.case_name,
                argumentos_cli=raw_args_str,
                resultado="TIMEOUT",
                tiempo_ms=elapsed_ms,
                stderr=f"Timeout ({self.limits_cfg.timeout_segundos}s excedidos)",
                esperado=expected_out,
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return TestResultDetail(
                ejercicio=test_case.exercise,
                nombre_caso=test_case.case_name,
                argumentos_cli=raw_args_str,
                resultado="ERROR",
                tiempo_ms=elapsed_ms,
                stderr=str(e),
                esperado=expected_out,
            )


class ValgrindRunner:
    """Audita fugas de memoria y errores con Valgrind."""

    def __init__(self, valgrind_cfg: ValgrindConfig, limits_cfg: LimitsConfig) -> None:
        self.valgrind_cfg = valgrind_cfg
        self.limits_cfg = limits_cfg

    def audit(
        self,
        binary_path: Path | str,
        stdin_data: str = "",
        cli_args: Sequence[str] = (),
    ) -> ValgrindResult:
        if not self.valgrind_cfg.enabled:
            return ValgrindResult(
                enabled=False,
                passed=True,
                summary="Desactivado",
                full_output="",
            )

        if not shutil.which("valgrind"):
            return ValgrindResult(
                enabled=True,
                passed=True,
                summary="Valgrind no disponible",
                full_output="Valgrind no está instalado en el sistema.",
            )

        cmd = ["valgrind"] + self.valgrind_cfg.flags + [str(binary_path)] + list(cli_args)

        try:
            proc = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=self.limits_cfg.timeout_segundos * 3,
            )
            output = proc.stderr or proc.stdout

            has_errors = (
                proc.returncode != 0
                or "definitely lost:" in output
                and not "definitely lost: 0 bytes" in output
                or "ERROR SUMMARY:" in output
                and not "ERROR SUMMARY: 0 errors" in output
            )

            if not has_errors:
                summary = "Limpio (0 fugas / 0 errores)"
                passed = True
            else:
                summary = "Fugas o accesos inválidos detectados"
                passed = False

            return ValgrindResult(
                enabled=True,
                passed=passed,
                summary=summary,
                full_output=output,
            )
        except subprocess.TimeoutExpired:
            return ValgrindResult(
                enabled=True,
                passed=False,
                summary="Timeout en Valgrind",
                full_output="Ejecución de Valgrind abortada por timeout.",
            )
        except Exception as e:
            return ValgrindResult(
                enabled=True,
                passed=False,
                summary=f"Error en Valgrind: {e}",
                full_output=str(e),
            )


class CppcheckRunner:
    """Ejecuta análisis estático con cppcheck y addons/reglas personalizadas."""

    def __init__(self, cppcheck_cfg: CppcheckConfig) -> None:
        self.cppcheck_cfg = cppcheck_cfg

    def analyze(self, source_files: Sequence[str | Path]) -> CppcheckResult:
        sources = [str(Path(s)) for s in source_files]
        if not sources:
            return CppcheckResult(
                passed=True,
                violations_count=0,
                summary="Sin fuentes",
                full_output="",
            )

        exe = self.cppcheck_cfg.ejecutable
        if not shutil.which(exe) and not Path(exe).exists():
            return CppcheckResult(
                passed=True,
                violations_count=0,
                summary="Cppcheck no disponible",
                full_output=f"Ejecutable '{exe}' no encontrado.",
            )

        cmd = [exe] + self.cppcheck_cfg.parametros

        for rule in self.cppcheck_cfg.reglas_python:
            if rule.endswith(".py"):
                cmd.append(f"--addon={rule}")
            else:
                cmd.append(f"--rule-file={rule}")

        cmd += sources

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
            )
            output = proc.stderr or proc.stdout
            lines = [l for l in output.splitlines() if "[error]" in l.lower() or "[warning]" in l.lower() or "[style]" in l.lower()]
            count = len(lines)

            if count == 0:
                summary = "0 advertencias"
                passed = True
            else:
                summary = f"{count} advertencias"
                passed = False

            return CppcheckResult(
                passed=passed,
                violations_count=count,
                summary=summary,
                full_output=output,
            )
        except Exception as e:
            return CppcheckResult(
                passed=False,
                violations_count=1,
                summary=f"Error: {e}",
                full_output=str(e),
            )


class RubricCalculator:
    """Calcula la nota cuantitativa preliminar (0 a 10) según la rúbrica."""

    def __init__(self, rubric_cfg: RubricConfig) -> None:
        self.rubric_cfg = rubric_cfg

    def calculate(
        self,
        compiled: bool,
        style_score: float,  # 0 a 10
        linter_passed: bool,
        linter_violations: int,
        tests_passed_count: int,
        total_tests_count: int,
    ) -> RubricScoreBreakdown:
        # Nota compilación (10 si compila, 0 si no)
        nota_comp = 10.0 if compiled else 0.0

        # Si no compila, las pruebas no pueden correr
        if not compiled:
            nota_pruebas = 0.0
        elif total_tests_count > 0:
            nota_pruebas = round((tests_passed_count / total_tests_count) * 10.0, 2)
        else:
            nota_pruebas = 10.0

        # Nota linter (10 si limpio, restando 2 por cada advertencia)
        nota_linter = max(0.0, 10.0 - (linter_violations * 2.0)) if compiled else 0.0

        # Nota estilo (0 a 10)
        nota_estilo = style_score if compiled else 0.0

        # Ponderación
        preliminar = (
            (nota_comp * self.rubric_cfg.peso_compilacion)
            + (nota_linter * self.rubric_cfg.peso_linter)
            + (nota_estilo * self.rubric_cfg.peso_estilo)
            + (nota_pruebas * self.rubric_cfg.peso_pruebas)
        )

        return RubricScoreBreakdown(
            nota_compilacion=round(nota_comp, 2),
            nota_estilo=round(nota_estilo, 2),
            nota_linter=round(nota_linter, 2),
            nota_pruebas=round(nota_pruebas, 2),
            nota_preliminar=round(preliminar, 2),
        )
