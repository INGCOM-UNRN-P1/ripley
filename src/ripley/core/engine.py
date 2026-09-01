"""Ripley Core Engine: Pure stateless C analysis and verification.

Executes AST linters, P1 rules, GCC sandboxed compilation, AddressSanitizer checks,
and testcases against a target source file or directory.
"""

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from ripley.core.ast_auditors import (
    ConstCorrectnessLinter,
    DanglingStackPointerLinter,
    DeepFreeLinter,
    FloatComparisonLinter,
    IWYULinter,
    ShortCircuitLinter,
    StringNullPointerLinter,
    VariableShadowingLinter,
)
from ripley.core.gcc_translator import translate_stderr, summarize_for_humans
from ripley.core.linters import (
    DeadCodeLinter,
    InternalCloneLinter,
    LinterObservation,
    MagicNumberLinter,
    NamingConventionLinter,
)
from ripley.core.p1_rules import P1RuleChecker


@dataclass
class CompilationResult:
    success: bool
    return_code: int
    raw_stderr: str
    translated_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    human_summary: str = ""
    binary_path: Optional[str] = None


@dataclass
class TestCaseResult:
    name: str
    passed: bool
    input_data: str
    expected_output: str
    actual_output: str
    timed_out: bool = False
    sanitizer_error: Optional[str] = None
    memory_leak: bool = False
    return_code: int = 0


@dataclass
class AnalysisResult:
    version: str = "2.0.0"
    target: str = ""
    is_directory: bool = False
    c_files: List[str] = field(default_factory=list)
    compilation: Dict[str, Any] = field(default_factory=dict)
    tests: Dict[str, Any] = field(default_factory=dict)
    ast_findings: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def find_c_sources(target: Path) -> List[Path]:
    """Encuentra todos los archivos .c en el destino omitiendo carpetas ocultas y temporales."""
    if target.is_file() and target.suffix == ".c":
        return [target]
    if target.is_dir():
        return sorted([
            p for p in target.glob("**/*.c")
            if not any(part.startswith(".") for part in p.parts)
            and "build" not in p.parts
            and "dist" not in p.parts
        ])
    return []


def run_ast_linters(
    c_files: List[Path],
    target_path: Optional[Path] = None,
    include_plugins: bool = True,
) -> List[Dict[str, Any]]:
    """Aplica el catálogo de linters AST, reglas de cátedra P1 y plugins satélites sobre cada archivo .c."""
    findings: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, int, str]] = set()

    if target_path is not None:
        target_path = Path(target_path).resolve()
        is_single_file = target_path.is_file()
        workspace = target_path
    elif c_files and len(c_files) == 1:
        is_single_file = True
        workspace = c_files[0]
    else:
        is_single_file = False
        workspace = c_files[0].parent if c_files else Path.cwd()

    allowed_filenames = {f.name for f in c_files}
    has_style_plugin = False

    # 1. Ejecución de plugins satélites desacoplados (ripley.plugins)
    if include_plugins:
        try:
            from ripley.core.entrypoints import discover_entrypoint_plugins
            discovered = discover_entrypoint_plugins()
        except Exception:
            discovered = []

        static_plugins = {
            "style", "antipatterns", "security", "headers_audit",
            "portability", "abi_audit", "macro_security", "tda_encapsulation"
        }

        for p in discovered:
            if p.name not in static_plugins or not p.is_available:
                continue
            if p.name == "style":
                has_style_plugin = True

            try:
                res = p.execute(workspace, {})
                raw_obs = res.get("observaciones") or res.get("issues") or []
                for obs in raw_obs:
                    raw_f = str(obs.get("archivo") or obs.get("file") or obs.get("location") or "")
                    f_name = Path(raw_f).name if raw_f else (c_files[0].name if c_files else "")

                    # En modo archivo individual, filtrar observaciones de otros archivos
                    if is_single_file and allowed_filenames and f_name not in allowed_filenames:
                        continue

                    rule_code = str(obs.get("codigo") or obs.get("rule_code") or obs.get("code") or p.name)
                    rule_name = str(obs.get("rule_name") or obs.get("titulo") or obs.get("title") or obs.get("symbol") or rule_code)
                    raw_sev = str(obs.get("severidad") or obs.get("severity") or "ADVERTENCIA").upper()
                    if raw_sev in ("WARN", "WARNING", "ESTILO"):
                        severity = "ADVERTENCIA" if raw_sev != "ESTILO" else "ESTILO"
                    elif raw_sev in ("CRITICO", "ALTO", "ERROR"):
                        severity = "ERROR"
                    else:
                        severity = raw_sev

                    line = int(obs.get("linea") or obs.get("line") or 0)
                    col = int(obs.get("columna") or obs.get("column") or 0)
                    msg = str(obs.get("mensaje") or obs.get("message") or "")
                    sug = str(obs.get("sugerencia") or obs.get("suggestion") or "")

                    norm_code = rule_code.lower()
                    key = (f_name, line, norm_code)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    findings.append({
                        "rule_id": rule_code,
                        "rule_code": rule_code,
                        "codigo": rule_code,
                        "rule_name": rule_name,
                        "titulo": rule_name,
                        "severity": severity,
                        "severidad": severity,
                        "file": f_name,
                        "archivo": f_name,
                        "line": line,
                        "linea": line,
                        "column": col,
                        "columna": col,
                        "message": msg,
                        "mensaje": msg,
                        "suggestion": sug,
                        "sugerencia": sug,
                        "source_plugin": p.name,
                    })
            except Exception:
                pass

    # 2. Linters AST internos y reglas P1
    p1_checker = P1RuleChecker()
    linters = [
        FloatComparisonLinter(),
        ConstCorrectnessLinter(),
        DeepFreeLinter(),
        DanglingStackPointerLinter(),
        ShortCircuitLinter(),
        StringNullPointerLinter(),
        VariableShadowingLinter(),
        IWYULinter(),
        DeadCodeLinter(),
    ]
    if not has_style_plugin:
        linters.extend([
            MagicNumberLinter(),
            NamingConventionLinter(),
        ])

    for c_file in c_files:
        try:
            code = c_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            findings.append({
                "rule_id": "READ_ERROR",
                "rule_code": "READ_ERROR",
                "codigo": "READ_ERROR",
                "rule_name": "Error de Lectura",
                "titulo": "Error de Lectura",
                "severity": "ERROR",
                "severidad": "ERROR",
                "file": c_file.name,
                "archivo": c_file.name,
                "line": 0,
                "linea": 0,
                "column": 0,
                "columna": 0,
                "message": f"No se pudo leer el archivo: {e}",
                "mensaje": f"No se pudo leer el archivo: {e}",
                "suggestion": "",
                "sugerencia": "",
            })
            continue

        # Reglas P1 (0xXXXXh)
        for p in p1_checker.analyze(code, filename=c_file.name):
            norm_code = p.rule_code.lower()
            key = (c_file.name, p.line, norm_code)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            rule_title = getattr(p, "title", p.rule_code)
            findings.append({
                "rule_id": p.rule_code,
                "rule_code": p.rule_code,
                "codigo": p.rule_code,
                "rule_name": rule_title,
                "titulo": rule_title,
                "severity": p.severity,
                "severidad": p.severity,
                "file": c_file.name,
                "archivo": c_file.name,
                "line": p.line,
                "linea": p.line,
                "column": 0,
                "columna": 0,
                "message": f"{p.rule_code}: {p.message}",
                "mensaje": f"{p.rule_code}: {p.message}",
                "suggestion": p.suggestion,
                "sugerencia": p.suggestion,
            })

        # Linters de Calidad y AST
        for linter in linters:
            for obs in linter.analyze(code, filename=c_file.name):
                norm_code = obs.linter_name.lower()
                key = (c_file.name, obs.line, norm_code)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                findings.append({
                    "rule_id": obs.linter_name,
                    "rule_code": obs.linter_name,
                    "codigo": obs.linter_name,
                    "rule_name": obs.linter_name,
                    "titulo": obs.linter_name,
                    "severity": obs.severity,
                    "severidad": obs.severity,
                    "file": c_file.name,
                    "archivo": c_file.name,
                    "line": obs.line,
                    "linea": obs.line,
                    "column": 0,
                    "columna": 0,
                    "message": obs.message,
                    "mensaje": obs.message,
                    "suggestion": obs.suggestion or "",
                    "sugerencia": obs.suggestion or "",
                })

        # Detector de código duplicado
        for d in InternalCloneLinter().analyze(code, filename=c_file.name):
            key = (c_file.name, d.line_a, "copy_paste_clone")
            if key in seen_keys:
                continue
            seen_keys.add(key)

            findings.append({
                "rule_id": "COPY_PASTE_CLONE",
                "rule_code": "COPY_PASTE_CLONE",
                "codigo": "COPY_PASTE_CLONE",
                "rule_name": "Código Duplicado",
                "titulo": "Código Duplicado",
                "severity": "ADVERTENCIA",
                "severidad": "ADVERTENCIA",
                "file": c_file.name,
                "archivo": c_file.name,
                "line": d.line_a,
                "linea": d.line_a,
                "column": 0,
                "columna": 0,
                "message": d.description,
                "mensaje": d.description,
                "suggestion": "Extraé la lógica común en una función auxiliar.",
                "sugerencia": "Extraé la lógica común en una función auxiliar.",
            })

    return findings


def compile_sources(
    c_files: List[Path],
    output_bin: Path,
    include_dirs: Optional[List[Path]] = None,
    extra_flags: Optional[List[str]] = None,
    enable_asan: bool = True,
) -> CompilationResult:
    """Compila las fuentes C con GCC, instrumentando AddressSanitizer y capturando stderr."""
    gcc = shutil.which("gcc")
    if not gcc:
        return CompilationResult(
            success=False,
            return_code=127,
            raw_stderr="GCC no está instalado o no se encuentra en el PATH.",
            human_summary="GCC no disponible en el sistema.",
        )

    cmd = [
        gcc,
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-std=c11",
        "-g3",
        "-O0",
    ]
    if enable_asan:
        cmd.extend(["-fsanitize=address,undefined", "-fno-omit-frame-pointer"])

    if include_dirs:
        for inc in include_dirs:
            cmd.extend(["-I", str(inc)])

    if extra_flags:
        cmd.extend(extra_flags)

    cmd.extend([str(f) for f in c_files])
    cmd.extend(["-o", str(output_bin), "-lm"])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        raw_stderr = proc.stderr or ""
        success = proc.returncode == 0 and output_bin.exists()

        # Si falló por falta de runtime de libasan, reintentar sin ASan
        if not success and enable_asan and ("cannot find" in raw_stderr and "asan" in raw_stderr.lower()):
            return compile_sources(
                c_files,
                output_bin,
                include_dirs=include_dirs,
                extra_flags=extra_flags,
                enable_asan=False,
            )

        translated = translate_stderr(raw_stderr) if raw_stderr else []
        summary = summarize_for_humans(translated) if translated else ""

        translated_dicts = [
            {
                "file": d.file or "",
                "line": d.line or 0,
                "column": d.col or 0,
                "severity": d.level or "error",
                "title": d.title or "",
                "raw_message": d.original,
                "translated_message": d.explanation or d.title or "",
                "suggestion": d.suggestion or "",
            }
            for d in translated
        ]

        return CompilationResult(
            success=success,
            return_code=proc.returncode,
            raw_stderr=raw_stderr,
            translated_diagnostics=translated_dicts,
            human_summary=summary,
            binary_path=str(output_bin) if success else None,
        )
    except subprocess.TimeoutExpired:
        return CompilationResult(
            success=False,
            return_code=124,
            raw_stderr="Tiempo de compilación excedido (20s).",
            human_summary="La compilación tardó demasiado tiempo y fue abortada.",
        )
    except Exception as e:
        return CompilationResult(
            success=False,
            return_code=1,
            raw_stderr=str(e),
            human_summary=f"Error al ejecutar GCC: {e}",
        )


def execute_testcases(
    binary_path: Path,
    test_dir: Path,
    timeout_seconds: float = 3.0,
) -> List[TestCaseResult]:
    """Ejecuta los pares tests/caso_*.in contra el binario compilado."""
    results = []
    if not test_dir.is_dir() or not binary_path.exists():
        return results

    in_files = sorted(test_dir.glob("caso_*.in")) + sorted(test_dir.glob("*.in"))
    in_files = list(dict.fromkeys(in_files))  # De-duplicate

    for in_file in in_files:
        base_name = in_file.stem
        out_file = in_file.with_suffix(".out")
        expected_output = out_file.read_text(encoding="utf-8", errors="replace") if out_file.exists() else ""

        input_data = in_file.read_text(encoding="utf-8", errors="replace")
        try:
            proc = subprocess.run(
                [str(binary_path)],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            actual_output = proc.stdout
            stderr = proc.stderr or ""
            norm_actual = actual_output.strip()
            norm_expected = expected_output.strip()
            if not out_file.exists():
                passed = (proc.returncode == 0)
            elif norm_actual == norm_expected:
                passed = True
            elif norm_expected.startswith("REGEX:"):
                pat = norm_expected[len("REGEX:"):].strip()
                try:
                    passed = bool(re.search(pat, actual_output, re.DOTALL | re.MULTILINE))
                except re.error:
                    passed = False
            elif norm_expected.startswith("regex:"):
                pat = norm_expected[len("regex:"):].strip()
                try:
                    passed = bool(re.search(pat, actual_output, re.DOTALL | re.MULTILINE))
                except re.error:
                    passed = False
            else:
                passed = False

            sanitizer_error = None
            memory_leak = False
            if "AddressSanitizer" in stderr or "LeakSanitizer" in stderr or "runtime error:" in stderr:
                sanitizer_error = stderr
                if "detected memory leaks" in stderr:
                    memory_leak = True
                passed = False

            results.append(
                TestCaseResult(
                    name=base_name,
                    passed=passed,
                    input_data=input_data,
                    expected_output=expected_output,
                    actual_output=actual_output,
                    timed_out=False,
                    sanitizer_error=sanitizer_error,
                    memory_leak=memory_leak,
                    return_code=proc.returncode,
                )
            )
        except subprocess.TimeoutExpired:
            results.append(
                TestCaseResult(
                    name=base_name,
                    passed=False,
                    input_data=input_data,
                    expected_output=expected_output,
                    actual_output="",
                    timed_out=True,
                    sanitizer_error="Tiempo de ejecución excedido (bucle infinito o I/O bloqueante)",
                    memory_leak=False,
                    return_code=124,
                )
            )
        except Exception as e:
            results.append(
                TestCaseResult(
                    name=base_name,
                    passed=False,
                    input_data=input_data,
                    expected_output=expected_output,
                    actual_output="",
                    timed_out=False,
                    sanitizer_error=str(e),
                    memory_leak=False,
                    return_code=1,
                )
            )

    return results


def analyze_target(target_path: str | Path) -> AnalysisResult:
    """Ejecuta el pipeline completo de análisis estático, compilación y pruebas sobre el objetivo."""
    path = Path(target_path).resolve()
    result = AnalysisResult(
        target=str(path),
        is_directory=path.is_dir(),
    )

    c_files = find_c_sources(path)
    result.c_files = [str(f.relative_to(path) if path.is_dir() else f.name) for f in c_files]

    if not c_files:
        result.compilation = {
            "success": False,
            "error": "No se encontraron archivos fuentes C (.c) para analizar.",
            "translated_diagnostics": [],
        }
        return result

    # 1. Análisis Estático y AST Linters
    ast_findings = run_ast_linters(c_files, target_path=path)
    result.ast_findings = ast_findings

    # 2. Compilación en sandbox temporal con AddressSanitizer
    with tempfile.TemporaryDirectory(prefix="ripley_engine_") as td:
        tmp_bin = Path(td) / "app.bin"
        include_dirs = [path, path / "include", path / "src"] if path.is_dir() else [path.parent]
        comp_res = compile_sources(c_files, tmp_bin, include_dirs=include_dirs, enable_asan=True)

        # Si falló la compilación conjunta por colisión de main() o hay múltiples archivos con main()
        files_with_main = []
        for f in c_files:
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
                if re.search(r'\b(?:int|void)\s+main\s*\(', txt):
                    files_with_main.append(f)
            except Exception:
                pass

        if len(files_with_main) > 1 or (not comp_res.success and ("multiple definition of `main'" in comp_res.raw_stderr or "multiple definition of 'main'" in comp_res.raw_stderr)):
            file_compilations = {}
            all_diags = []
            all_stderrs = []
            all_ok = True
            all_test_results = []

            for idx, c_f in enumerate(c_files):
                sub_bin = Path(td) / f"bin_{idx}"
                sub_res = compile_sources([c_f], sub_bin, include_dirs=include_dirs, enable_asan=True)
                file_compilations[c_f.name] = {
                    "success": sub_res.success,
                    "return_code": sub_res.return_code,
                    "raw_stderr": sub_res.raw_stderr,
                    "translated_diagnostics": sub_res.translated_diagnostics,
                }
                if not sub_res.success:
                    all_ok = False
                    all_stderrs.append(f"[{c_f.name}]:\n{sub_res.raw_stderr}")
                all_diags.extend(sub_res.translated_diagnostics)

                if sub_res.success:
                    test_dir = path / "tests" if path.is_dir() else path.parent / "tests"
                    all_test_results.extend(execute_testcases(sub_bin, test_dir))

            result.compilation = {
                "success": all_ok,
                "return_code": 0 if all_ok else 1,
                "human_summary": "Compilación aislada de múltiples ejercicios completada." if all_ok else "Errores en compilación aislada.",
                "translated_diagnostics": all_diags,
                "raw_stderr": "\n\n".join(all_stderrs),
                "files": file_compilations,
            }
            test_results = all_test_results
        else:
            result.compilation = {
                "success": comp_res.success,
                "return_code": comp_res.return_code,
                "human_summary": comp_res.human_summary,
                "translated_diagnostics": comp_res.translated_diagnostics,
                "raw_stderr": comp_res.raw_stderr,
            }

            # 3. Testcases (si compila exitosamente)
            test_dir = path / "tests" if path.is_dir() else path.parent / "tests"
            test_results = []
            if comp_res.success:
                test_results = execute_testcases(tmp_bin, test_dir)

        passed_count = sum(1 for t in test_results if t.passed)
        failed_count = len(test_results) - passed_count
        result.tests = {
            "total": len(test_results),
            "passed": passed_count,
            "failed": failed_count,
            "cases": [asdict(t) for t in test_results],
        }

    # 4. Métricas básicas
    total_lines = 0
    for f in c_files:
        try:
            total_lines += len(f.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            pass

    result.metrics = {
        "c_files_count": len(c_files),
        "total_lines_of_code": total_lines,
        "ast_findings_count": len(ast_findings),
        "ast_errors_count": sum(1 for f in ast_findings if f.get("severity") == "ERROR"),
        "ast_warnings_count": sum(1 for f in ast_findings if f.get("severity") in ("ADVERTENCIA", "WARN", "WARNING")),
    }

    return result
