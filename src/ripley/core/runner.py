"""Dynamic test runner, Valgrind memory auditor, Cppcheck static analyzer and rubric calculator."""

from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
from typing import List, Optional

from ripley.core.compiler import set_process_limits
from ripley.config import CustomToolConfig, LimitsConfig
from ripley.core.diagnostics import DiagnosisType, diagnose_runtime_crash
from ripley.core.testcases import TestCaseInfo


def _try_import_nostromo():
    try:
        from nostromo.core.sandbox import ejecutar_aislado
        return ejecutar_aislado
    except ImportError:
        import sys
        sibling = Path(__file__).resolve().parents[4] / "nostromo" / "src"
        if sibling.is_dir() and str(sibling) not in sys.path:
            sys.path.insert(0, str(sibling))
            try:
                from nostromo.core.sandbox import ejecutar_aislado
                return ejecutar_aislado
            except ImportError:
                return None
        return None


@dataclass
class CustomToolResult:
    name: str
    command: str
    success: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def output(self) -> str:
        out = (self.stdout + "\n" + self.stderr).strip()
        return out or "Ejecución finalizada sin mensajes."



@dataclass
class TestResultDetail:
    ejercicio: str
    nombre_caso: str
    argumentos_cli: str
    resultado: str  # "PASSED" | "FAILED" | "TIMEOUT" | "ERROR" | "STACK_OVERFLOW" | "STDIN_DEADLOCK" | ...
    tiempo_ms: float
    stdout: str = ""
    stderr: str = ""
    esperado: str = ""
    pedagogical_hint: str = ""




def normalize_output_text(text: str) -> str:
    """Normaliza texto removiendo espacios finales por línea y saltos de línea al final."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    # Eliminar líneas vacías al final
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def normalize_fuzzy_text(text: str) -> str:
    """Normalización fuzzy: ignora mayúsculas, signos de puntuación y espacios repetidos."""
    lower = text.lower()
    # Eliminar signos de puntuación comunes excepto números y letras
    no_punct = re.sub(r"[^\w\s\d]", " ", lower)
    # Colapsar espacios múltiples
    return re.sub(r"\s+", " ", no_punct).strip()


def compare_outputs(
    actual: str,
    expected: str,
    fuzzy: bool = False,
) -> bool:
    """Compara la salida real contra la esperada admitiendo regex, igualdad exacta y normalización fuzzy."""
    norm_actual = normalize_output_text(actual)
    norm_expected = normalize_output_text(expected)

    # 1. Comparación exacta directa
    if norm_actual == norm_expected:
        return True

    # 2. Modo Expresión Regular si la salida esperada tiene directiva REGEX:
    if norm_expected.startswith("REGEX:"):
        regex_pattern = norm_expected[len("REGEX:") :].strip()
        try:
            return bool(re.search(regex_pattern, norm_actual, re.DOTALL | re.MULTILINE))
        except re.error:
            pass

    # 3. Normalización Fuzzy (si está activada o como fallback)
    if fuzzy:
        if normalize_fuzzy_text(actual) == normalize_fuzzy_text(expected):
            return True

    return False



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

        ejecutar_aislado = _try_import_nostromo()
        if ejecutar_aislado is not None:
            try:
                res = ejecutar_aislado(
                    binario=bin_path,
                    args=cli_args,
                    stdin_texto=stdin_data,
                    timeout_segundos=float(self.limits_cfg.timeout_segundos),
                    memoria_mb=self.limits_cfg.limite_memoria_mb,
                    usar_bwrap=False,
                )
                if res.error_tipo == "TIMEOUT":
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    diag = diagnose_runtime_crash(
                        returncode=0,
                        stdout="",
                        stderr="",
                        timeout=True,
                        input_data=stdin_data,
                    )
                    return TestResultDetail(
                        ejercicio=test_case.exercise,
                        nombre_caso=test_case.case_name,
                        argumentos_cli=raw_args_str,
                        resultado=diag.diagnosis.value,
                        tiempo_ms=elapsed_ms,
                        stderr=f"Timeout ({self.limits_cfg.timeout_segundos}s excedidos). {diag.message}",
                        esperado=expected_out,
                        pedagogical_hint=diag.pedagogical_hint,
                    )

                elapsed_ms = res.tiempo_ms
                is_match = compare_outputs(res.stdout, expected_out, fuzzy=True)

                if res.codigo_retorno != 0:
                    diag = diagnose_runtime_crash(
                        returncode=res.codigo_retorno,
                        stdout=res.stdout,
                        stderr=res.stderr,
                        timeout=False,
                        input_data=stdin_data,
                    )
                    result_status = diag.diagnosis.value if diag.diagnosis != DiagnosisType.CLEAN else "ERROR"
                    pedagogical_hint = diag.pedagogical_hint
                elif is_match:
                    result_status = "PASSED"
                    pedagogical_hint = ""
                else:
                    result_status = "FAILED"
                    pedagogical_hint = "La salida generada difiere de la esperada por el caso de prueba."

                return TestResultDetail(
                    ejercicio=test_case.exercise,
                    nombre_caso=test_case.case_name,
                    argumentos_cli=raw_args_str,
                    resultado=result_status,
                    tiempo_ms=elapsed_ms,
                    stdout=res.stdout,
                    stderr=res.stderr,
                    esperado=expected_out,
                    pedagogical_hint=pedagogical_hint,
                )
            except Exception:
                pass  # Fallback a ejecución local directa

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

            is_match = compare_outputs(proc.stdout, expected_out, fuzzy=True)

            if proc.returncode != 0:
                diag = diagnose_runtime_crash(
                    returncode=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    timeout=False,
                    input_data=stdin_data,
                )
                result_status = diag.diagnosis.value if diag.diagnosis != DiagnosisType.CLEAN else "ERROR"
                pedagogical_hint = diag.pedagogical_hint
            elif is_match:
                result_status = "PASSED"
                pedagogical_hint = ""
            else:
                result_status = "FAILED"
                pedagogical_hint = "La salida generada difiere de la esperada por el caso de prueba."

            return TestResultDetail(
                ejercicio=test_case.exercise,
                nombre_caso=test_case.case_name,
                argumentos_cli=raw_args_str,
                resultado=result_status,
                tiempo_ms=elapsed_ms,
                stdout=proc.stdout,
                stderr=proc.stderr,
                esperado=expected_out,
                pedagogical_hint=pedagogical_hint,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            diag = diagnose_runtime_crash(
                returncode=0,
                stdout="",
                stderr="",
                timeout=True,
                input_data=stdin_data,
            )
            return TestResultDetail(
                ejercicio=test_case.exercise,
                nombre_caso=test_case.case_name,
                argumentos_cli=raw_args_str,
                resultado=diag.diagnosis.value,
                tiempo_ms=elapsed_ms,
                stderr=f"Timeout ({self.limits_cfg.timeout_segundos}s excedidos). {diag.message}",
                esperado=expected_out,
                pedagogical_hint=diag.pedagogical_hint,
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



class CustomToolRunner:
    """Ejecutor de herramientas CLI externas arbitrarias configuradas en ripley.toml."""

    def __init__(self, limits: Optional[LimitsConfig] = None) -> None:
        self.limits = limits or LimitsConfig()

    def run(
        self,
        tool: CustomToolConfig,
        source: Optional[Path] = None,
        binary: Optional[Path] = None,
        folder: Optional[Path] = None,
    ) -> CustomToolResult:
        timeout = tool.timeout_segundos or self.limits.timeout_segundos
        cmd_str = tool.command

        # Interpolación de variables contextuales
        replacements = {
            "{source}": str(source.resolve()) if source else "",
            "{binary}": str(binary.resolve()) if binary else "",
            "{folder}": str(folder.resolve()) if folder else "",
            "{filename}": source.name if source else "",
            "{stem}": source.stem if source else (binary.stem if binary else ""),
        }
        for placeholder, val in replacements.items():
            cmd_str = cmd_str.replace(placeholder, val)

        try:
            args = shlex.split(cmd_str)
            if not args:
                return CustomToolResult(
                    name=tool.name,
                    command=tool.command,
                    success=False,
                    returncode=1,
                    stdout="",
                    stderr="Comando vacío o no interpretable.",
                )

            if not shutil.which(args[0]):
                return CustomToolResult(
                    name=tool.name,
                    command=cmd_str,
                    success=False,
                    returncode=127,
                    stdout="",
                    stderr=f"Herramienta no encontrada en el PATH del sistema: '{args[0]}'",
                )

            res = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=lambda: set_process_limits(self.limits.limite_memoria_mb, timeout),
            )

            success = (res.returncode == 0)
            return CustomToolResult(
                name=tool.name,
                command=cmd_str,
                success=success,
                returncode=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout_str = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            return CustomToolResult(
                name=tool.name,
                command=cmd_str,
                success=False,
                returncode=-1,
                stdout=stdout_str,
                stderr=f"Tiempo de ejecución agotado ({timeout}s)",
                timed_out=True,
            )
        except Exception as exc:
            return CustomToolResult(
                name=tool.name,
                command=cmd_str,
                success=False,
                returncode=1,
                stdout="",
                stderr=f"Error al ejecutar herramienta: {exc}",
            )


# Registro de comandos y re-exports (deben ir tras definir los objetos compartidos)
from ripley.core.runner_herramientas import ValgrindResult, CppcheckResult, RubricScoreBreakdown, ValgrindRunner, CppcheckRunner, RubricCalculator  # noqa: E402,F401
