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
from ripley.core.entrypoints import (
    discover_entrypoint_plugins,
    get_satellite_plugin,
    SatellitePluginAdapter,
    SATELLITE_CATALOG,
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
    return_code: int = 0
    raw_stderr: str = ""
    translated_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    human_summary: str = ""
    binary_path: Optional[str] = None


@dataclass
class TestCaseResult:
    name: str
    passed: bool
    input_data: str = ""
    expected_output: str = ""
    actual_output: str = ""
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
    passed: bool = True

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


def normalize_rule_code(code: str) -> str:
    """Normaliza identificadores de reglas para desduplicación jerárquica entre analizadores."""
    c = str(code).strip().lower()
    mapping = {
        "0x300ah": "0x300ah",
        "cast_malloc": "0x300ah",
        "spk_malloc_cast": "0x300ah",
        "0x300dh": "0x300dh",
        "gets_prohibited": "0x300dh",
        "kan001": "0x300dh",
        "0x000bh": "0x000bh",
        "brace_style": "0x000bh",
        "0x1001h": "0x1001h",
        "require_braces": "0x1001h",
    }
    return mapping.get(c, c)


def run_ast_linters(
    c_files: List[Path],
    target_path: Optional[Path] = None,
    include_plugins: bool = True,
    strict: bool = False,
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

    # 1. Ejecución de plugins satélites desacoplados (ripley.plugins y catálogo)
    if include_plugins:
        try:
            from ripley.core.entrypoints import discover_entrypoint_plugins
            discovered = discover_entrypoint_plugins()
        except Exception:
            discovered = []

        static_plugins = {
            "style", "antipatterns", "security", "headers_audit",
            "macro_security", "padding", "tda_encapsulation",
            "portability", "callgraph", "formal_contracts", "abi_audit"
        }

        for p in discovered:
            if p.name not in static_plugins or not p.is_available:
                continue
            if p.name == "style":
                has_style_plugin = True

            try:
                res = p.execute(workspace, {}, strict=strict)
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

                    norm_code = normalize_rule_code(rule_code)
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

    # 2. Linters AST internos y reglas P1 (con desduplicación jerárquica)
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
            norm_code = normalize_rule_code(p.rule_code)
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
                norm_code = normalize_rule_code(obs.linter_name)
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


def _fill_metrics(result: AnalysisResult, c_files: List[Path], ast_findings: List[Dict[str, Any]]) -> None:
    """Calcula y asigna las métricas del análisis estático."""
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


def analyze_target(target_path: str | Path, strict: bool = False) -> AnalysisResult:
    """Ejecuta el pipeline completo de análisis estático, compilación y pruebas delegando en plugins satélites."""
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
        result.passed = False
        return result

    # 1. Auditoría Estática (Plugins satélites + reglas P1 + desduplicación)
    ast_findings = run_ast_linters(c_files, target_path=path, strict=strict)
    result.ast_findings = ast_findings

    # 2. Compilación: delegada exclusivamente en el plugin compiler (daedalus)
    compiler_plugin = get_satellite_plugin("compiler")
    if not compiler_plugin.is_available:
        missing_res = compiler_plugin.execute(path, strict=strict)
        missing_obs = missing_res.get("observaciones", [])
        result.compilation = {
            "success": False,
            "return_code": 127,
            "human_summary": "Plugin de compilación 'daedalus' no disponible.",
            "translated_diagnostics": missing_obs,
            "raw_stderr": "Plugin 'daedalus' no disponible en el entorno ni en PATH.",
        }
        result.ast_findings.extend(missing_obs)
        result.passed = False
        _fill_metrics(result, c_files, result.ast_findings)
        return result

    with tempfile.TemporaryDirectory(prefix="ripley_engine_") as td:
        tmp_bin = Path(td) / "app.bin"
        comp_exec = compiler_plugin.execute(
            path,
            manifest_config={
                "c_files": c_files,
                "output_bin": tmp_bin,
                "timeout": 20.0,
            },
            strict=strict,
        )
        comp_ok = bool(comp_exec.get("success", comp_exec.get("ok", False)))
        bin_path = comp_exec.get("binary_path") or (tmp_bin if tmp_bin.exists() else None)
        raw_stderr = comp_exec.get("raw_stderr", "")
        diags = comp_exec.get("translated_diagnostics", [])

        # Detección de múltiples archivos con main()
        files_with_main = []
        for f in c_files:
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
                if re.search(r'\b(?:int|void)\s+main\s*\(', txt):
                    files_with_main.append(f)
            except Exception:
                pass

        active_bins: List[Path] = []
        if len(files_with_main) > 1 or (not comp_ok and ("multiple definition of `main'" in raw_stderr or "multiple definition of 'main'" in raw_stderr)):
            file_compilations = {}
            all_diags = []
            all_stderrs = []
            all_ok = True

            for idx, c_f in enumerate(c_files):
                sub_bin = Path(td) / f"bin_{idx}"
                sub_exec = compiler_plugin.execute(
                    c_f,
                    manifest_config={
                        "c_files": [c_f],
                        "output_bin": sub_bin,
                        "timeout": 20.0,
                    },
                    strict=strict,
                )
                sub_ok = bool(sub_exec.get("success", sub_exec.get("ok", False)))
                sub_bin_path = sub_exec.get("binary_path") or (sub_bin if sub_bin.exists() else None)
                sub_stderr = sub_exec.get("raw_stderr", "")
                sub_diags = sub_exec.get("translated_diagnostics", [])

                file_compilations[c_f.name] = {
                    "success": sub_ok,
                    "return_code": sub_exec.get("return_code", 0 if sub_ok else 1),
                    "raw_stderr": sub_stderr,
                    "translated_diagnostics": sub_diags,
                }
                if not sub_ok:
                    all_ok = False
                    all_stderrs.append(f"[{c_f.name}]:\n{sub_stderr}")
                all_diags.extend(sub_diags)
                if sub_ok and sub_bin_path and Path(sub_bin_path).exists():
                    active_bins.append(Path(sub_bin_path))

            result.compilation = {
                "success": all_ok,
                "return_code": 0 if all_ok else 1,
                "human_summary": "Compilación aislada de múltiples ejercicios completada." if all_ok else "Errores en compilación aislada.",
                "translated_diagnostics": all_diags,
                "raw_stderr": "\n\n".join(all_stderrs),
                "files": file_compilations,
            }
        else:
            result.compilation = {
                "success": comp_ok,
                "return_code": comp_exec.get("return_code", 0 if comp_ok else 1),
                "human_summary": comp_exec.get("human_summary", "Compilación exitosa." if comp_ok else "Falló la compilación."),
                "translated_diagnostics": diags,
                "raw_stderr": raw_stderr,
                "binary_path": str(bin_path) if bin_path else None,
            }
            if comp_ok and bin_path and Path(bin_path).exists():
                active_bins.append(Path(bin_path))

        # 3. Sandbox y Pruebas: delegadas exclusivamente en el plugin sandbox (nostromo)
        test_dir = path / "tests" if path.is_dir() else path.parent / "tests"
        in_files = []
        if test_dir.is_dir():
            in_files = sorted(test_dir.glob("caso_*.in")) + sorted(test_dir.glob("*.in"))
            in_files = list(dict.fromkeys(in_files))

        all_test_cases = []
        if in_files:
            sandbox_plugin = get_satellite_plugin("sandbox")
            if not sandbox_plugin.is_available:
                missing_sb = sandbox_plugin.execute(path, strict=strict)
                obs_sb = missing_sb.get("observaciones", [])
                result.tests = {
                    "total": len(in_files),
                    "passed": 0,
                    "failed": 0,
                    "omitted": len(in_files),
                    "skipped": len(in_files),
                    "cases": [],
                    "warning": "Plugin de sandbox 'nostromo' no disponible. Pruebas omitidas.",
                }
                result.ast_findings.extend(obs_sb)
                if strict:
                    result.passed = False
            elif active_bins:
                for b_path in active_bins:
                    sb_res = sandbox_plugin.execute(
                        path,
                        manifest_config={
                            "binary_path": str(b_path),
                            "test_dir": str(test_dir),
                            "timeout": 3.0,
                        },
                        strict=strict,
                    )
                    raw_cases = sb_res.get("cases") or sb_res.get("casos") or sb_res.get("resultados") or []
                    for c in raw_cases:
                        all_test_cases.append({
                            "name": c.get("name") or c.get("nombre") or "caso",
                            "passed": bool(c.get("passed", c.get("paso", False))),
                            "input_data": str(c.get("input_data", c.get("stdout_esperado", ""))),
                            "expected_output": str(c.get("expected_output", c.get("stdout_esperado", ""))),
                            "actual_output": str(c.get("actual_output", c.get("stdout_obtenido", ""))),
                            "timed_out": bool(c.get("timed_out", c.get("error_tipo") == "TIMEOUT")),
                            "sanitizer_error": c.get("sanitizer_error", c.get("stderr_obtenido") if not c.get("paso", True) else None),
                            "memory_leak": bool(c.get("memory_leak", "leak" in str(c.get("stderr_obtenido", "")).lower())),
                            "return_code": int(c.get("return_code", c.get("codigo_retorno", 0))),
                        })
                p_count = sum(1 for tc in all_test_cases if tc["passed"])
                f_count = len(all_test_cases) - p_count
                result.tests = {
                    "total": len(all_test_cases),
                    "passed": p_count,
                    "failed": f_count,
                    "cases": all_test_cases,
                }
        else:
            result.tests = {"total": 0, "passed": 0, "failed": 0, "cases": []}

    # 4. Métricas y estado global
    _fill_metrics(result, c_files, result.ast_findings)

    comp_ok_final = result.compilation.get("success", False)
    tests_failed = result.tests.get("failed", 0)
    has_blocking_errors = any(f.get("severity") == "ERROR" for f in result.ast_findings)
    if not comp_ok_final or tests_failed > 0 or has_blocking_errors:
        result.passed = False

    if strict:
        has_missing = any(f.get("rule_code", "").startswith("MISSING_TOOL_") for f in result.ast_findings)
        has_plugin_err = any(f.get("rule_code", "").startswith("PLUGIN_ERROR_") for f in result.ast_findings)
        if has_missing or has_plugin_err:
            result.passed = False

    return result
