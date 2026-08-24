"""Evaluation orchestrator: compilation, security, style, linters, tests, diffing and reporting."""

import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Dict, List, Optional


from ripley.pipeline.checks import *  # noqa: F401,F403  (registra el catálogo)
from ripley.pipeline.registry import iter_uniform_static

from ripley.core.callgraph import CallGraphGenerator
from ripley.tools.compiler import CompilationResult, Compiler
from ripley.config import RipleyConfig, load_config
from ripley.teacher.db import DatabaseManager
from ripley.core.diffing import generate_unified_diff
from ripley.core.doxygen import DoxygenAuditor
from ripley.core.flowchart import FlowchartGenerator
from ripley.core.linters import (
    DeadCodeLinter,
    InternalCloneLinter,
    MagicNumberLinter,
    NamingConventionLinter,
)
SPECIAL_AUXILIARY = "[AUXILIAR]"
SPECIAL_IGNORE = "[IGNORAR]"


class MappingStore:
    def __init__(self, workspace_dir: str | Path, activity_slug: str) -> None:
        self.mapping_file = Path(workspace_dir) / activity_slug / "mappings.json"
        self.mappings: Dict[str, Any] = {}
        if self.mapping_file.exists():
            try:
                self.mappings = json.loads(self.mapping_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    def get_effective_mapping(self, student_slug: str, filename: str, available_exercises: List[str]) -> Optional[str]:
        student_m = self.mappings.get("student_mappings", {}).get(student_slug, {})
        if filename in student_m:
            return student_m[filename]
        global_m = self.mappings.get("global_mappings", {})
        if filename in global_m:
            return global_m[filename]
        stem = Path(filename).stem.lower()
        for ex in available_exercises:
            if stem == ex.lower():
                return ex
        if len(available_exercises) == 1 and stem in ("main", "tp", "tarea", "entrega"):
            return available_exercises[0]
        return None

from ripley.core.memory_visualizer import DynamicMemoryVisualizer
from ripley.core.p1_rules import P1RuleChecker
from ripley.tools.property_testing import PropertyTestRunner
from ripley.tools.pure_functions import PureFunctionAnalyzer
from ripley.teacher.reporter import MarkdownReporter, StudentReportContext, VersionReportContext
from ripley.core.restrictions import CodeRestrictionsValidator
from ripley.tools.runner import (
    CppcheckResult,
    CppcheckRunner,
    CustomToolResult,
    CustomToolRunner,
    DynamicTestRunner,
    RubricCalculator,
    ValgrindResult,
    ValgrindRunner,
)
from ripley.core.security import SecurityScanner
from ripley.core.semantic_diff import extract_c_functions
from ripley.core.style import StyleCheckResult, StyleAnalyzer
from ripley.tools.testcases import discover_testcases


@dataclass
class StudentEvaluationSummary:
    student_slug: str
    student_name: str
    version_evaluated: int
    compiled: bool
    style_score: float
    tests_passed: int
    total_tests: int
    preliminary_grade: float
    report_file: Path


class Evaluator:
    """Orquesta la evaluación integral de los estudiantes para una actividad."""

    def __init__(
        self,
        config: RipleyConfig,
        workspace_dir: str | Path = ".",
    ) -> None:
        self.config = config
        self.workspace_dir = Path(workspace_dir)

    def get_activity_config(self, activity_slug: str) -> RipleyConfig:
        """Obtiene la configuración específica de la práctica si existe en practicas/<slug>/ripley.toml, o fallback a la global."""
        clean_slug = Path(activity_slug).name or activity_slug.strip("/\\")
        practice_toml = self.workspace_dir / "practicas" / clean_slug / "ripley.toml"
        if practice_toml.exists():
            return load_config(practice_toml)
        root_toml = self.workspace_dir / "ripley.toml"
        if root_toml.exists():
            return load_config(root_toml)
        return self.config

    def evaluate_student(
        self,
        activity_slug: str,
        student_dir: Path,
    ) -> Optional[StudentEvaluationSummary]:
        clean_act_slug = Path(activity_slug).name or activity_slug.strip("/\\")
        db_path = student_dir / ".metadata.db"
        if not db_path.exists():
            return None

        db = DatabaseManager(db_path)
        student_slug = student_dir.name
        revisions = db.get_all_revisions(student_slug)
        if not revisions:
            return None

        # Cargar configuración específica de la actividad y sus herramientas activas
        act_cfg = self.get_activity_config(clean_act_slug)

        compiler = Compiler(act_cfg.compiler, act_cfg.limits, act_cfg.sandbox)
        security_scanner = SecurityScanner(act_cfg.security)
        style_analyzer = StyleAnalyzer(act_cfg.style)
        p1_checker = P1RuleChecker() if act_cfg.p1_rules.enabled else None
        valgrind_runner = ValgrindRunner(act_cfg.valgrind, act_cfg.limits)
        cppcheck_runner = CppcheckRunner(act_cfg.cppcheck)
        test_runner = DynamicTestRunner(act_cfg.limits)
        custom_tool_runner = CustomToolRunner(act_cfg.limits)
        rubric_calc = RubricCalculator(act_cfg.rubric)
        reporter = MarkdownReporter(act_cfg.templates.ruta_plantillas)


        # Descubrir casos de prueba para la actividad
        testcases_by_exercise = discover_testcases(self.workspace_dir, activity_slug)

        version_contexts: List[VersionReportContext] = []
        latest_summary: Optional[StudentEvaluationSummary] = None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            for i, rev in enumerate(revisions):
                v_num = rev["version_num"]
                rev_folder = student_dir / f"r{v_num}"
                prev_rev_folder = student_dir / f"r{v_num - 1}" if v_num > 1 else None

                if not rev_folder.exists():
                    continue

                c_sources = sorted(rev_folder.glob("*.c"))
                h_sources = sorted(rev_folder.glob("*.h"))
                all_sources = sorted(c_sources + h_sources)

                # 1. Diff unificado contra la versión previa
                unified_diff = generate_unified_diff(
                    old_folder=prev_rev_folder,
                    new_folder=rev_folder,
                )

                # 2. Escaneo de seguridad preventivo (si está habilitado)
                if act_cfg.security.enabled:
                    security_violations = security_scanner.scan_files(all_sources)
                else:
                    security_violations = []

                # 3. Compilación, Estilo, Cppcheck y Valgrind Estrictamente Archivo por Archivo
                mapping_store = MappingStore(self.workspace_dir, activity_slug)
                available_ex_names = list(testcases_by_exercise.keys())

                compiled_binaries: Dict[str, Optional[Path]] = {}
                compilation_results_table: List[Dict[str, str]] = []
                all_style_obs: List[Dict[str, Any]] = []
                compilation_logs: List[str] = []
                file_compilation_status: Dict[str, bool] = {}

                total_style_sum = 0.0
                total_cppcheck_violations = 0
                all_compiled = True

                if security_violations:
                    all_compiled = False
                    comp_log = "Violaciones de seguridad detectadas:\n" + "\n".join(
                        f"- [{v.filename}:{v.line}] {v.message}" for v in security_violations
                    )
                    compilation_logs.append(comp_log)

                for src in c_sources:
                    target = mapping_store.get_effective_mapping(student_slug, src.name, available_ex_names)
                    if target == SPECIAL_IGNORE:
                        continue

                    # 3.1 Compilación individual (si está habilitada)
                    bin_out = temp_path / f"bin_v{v_num}_{src.stem}"
                    if act_cfg.compiler.enabled:
                        comp_res = compiler.compile([src], bin_out)
                        file_compilation_status[src.name] = comp_res.success

                        if comp_res.success:
                            compiled_binaries[src.name] = bin_out
                            compiled_binaries[src.stem] = bin_out
                            if target and target != SPECIAL_AUXILIARY:
                                compiled_binaries[target] = bin_out
                        else:
                            all_compiled = False

                        # Salida de compilación individual
                        compiler_raw = (comp_res.stdout + "\n" + comp_res.stderr).strip()
                        display_target = f" -> {target}" if target else ""
                        if compiler_raw:
                            compilation_logs.append(
                                f"=== Salida del Compilador ({src.name}{display_target}) ===\n{compiler_raw}\n"
                            )
                        else:
                            compilation_logs.append(
                                f"=== Salida del Compilador ({src.name}{display_target}) ===\nCompilación limpia sin errores ni advertencias.\n"
                            )
                    else:
                        comp_res = CompilationResult(success=True, binary_path=None, stdout="", stderr="", returncode=0)
                        file_compilation_status[src.name] = True
                        compilation_logs.append(f"=== Compilador ({src.name}) ===\nCompilación desactivada en configuración.\n")

                    # 3.2 Análisis de Estilo individual (si está habilitado)
                    s_score = 10.0
                    if act_cfg.style.enabled:
                        s_res = style_analyzer.analyze_file(src)
                        s_score = s_res.score
                        total_style_sum += s_res.score
                        for obs in s_res.observaciones:
                            all_style_obs.append(
                                {
                                    "archivo": obs.archivo,
                                    "linea": obs.linea,
                                    "mensaje": obs.mensaje,
                                }
                            )
                    else:
                        total_style_sum += 10.0

                    # 3.2.1 Reglas oficiales de Programación I (P1 Rules)
                    if p1_checker is not None:
                        src_content = src.read_text(encoding="utf-8", errors="replace")
                        p1_obs = p1_checker.analyze(src_content, src.name)
                        for obs in p1_obs:
                            all_style_obs.append(
                                {
                                    "archivo": obs.filename,
                                    "linea": obs.line,
                                    "mensaje": f"[{obs.rule_code}] {obs.title}: {obs.message}",
                                }
                            )

                    # 3.2.2 Linters especializados (si están habilitados)
                    if act_cfg.linters.enabled:
                        src_content = src.read_text(encoding="utf-8", errors="replace")
                        if act_cfg.linters.dead_code:
                            for obs in DeadCodeLinter().analyze(src_content, src.name):
                                all_style_obs.append({"archivo": obs.filename, "linea": obs.line, "mensaje": f"[DeadCode] {obs.message}"})
                        if act_cfg.linters.magic_numbers:
                            for obs in MagicNumberLinter().analyze(src_content, src.name):
                                all_style_obs.append({"archivo": obs.filename, "linea": obs.line, "mensaje": f"[MagicNumber] {obs.message}"})
                        if act_cfg.linters.naming:
                            for obs in NamingConventionLinter().analyze(src_content, src.name):
                                all_style_obs.append({"archivo": obs.filename, "linea": obs.line, "mensaje": f"[Naming] {obs.message}"})

                    # 3.2.3 Auditores AST Profundos + padding, vía registro unificado.
                    # El catálogo (pipeline.checks) replica 1:1 los toggles de ripley.toml,
                    # de modo que el estudiante ejecute exactamente las mismas reglas.
                    src_content = src.read_text(encoding="utf-8", errors="replace")
                    for spec in iter_uniform_static():
                        section = getattr(act_cfg, spec.config_section, None)
                        if section is None or not getattr(section, "enabled", True):
                            continue  # Sección sin master enabled (p. ej. padding off).
                        if spec.config_section == "ast_auditors" and not act_cfg.ast_auditors.enabled:
                            continue
                        if not getattr(section, spec.toggle, False):
                            continue
                        for obs in spec.runner(src_content, src.name):
                            all_style_obs.append({
                                "archivo": obs.filename,
                                "linea": obs.line,
                                "mensaje": f"{spec.prefix} {obs.message}",
                            })

                    # 3.2.4 Validación de Restricciones (si está habilitada)
                    if act_cfg.restrictions.enabled:
                        rest_val = CodeRestrictionsValidator(
                            forbidden_constructs=act_cfg.restrictions.forbidden_constructs,
                            required_constructs=act_cfg.restrictions.required_constructs,
                        )
                        violations = rest_val.validate_file(src)
                        for viol in violations:
                            all_style_obs.append({"archivo": src.name, "linea": viol.line_number, "mensaje": f"[Restricción:{viol.violation_type}] {viol.message}"})


                    # 3.2.5 Auditoría de Documentación Doxygen (si está habilitada)
                    if act_cfg.doxygen.enabled:
                        dox_auditor = DoxygenAuditor(
                            require_brief=act_cfg.doxygen.require_brief,
                            require_params=act_cfg.doxygen.require_params,
                            require_return=act_cfg.doxygen.require_return,
                        )
                        d_obs = dox_auditor.audit_file(src)
                        for obs in d_obs:
                            all_style_obs.append({"archivo": obs.filename, "linea": obs.line, "mensaje": f"[Doxygen] {obs.message}"})

                    # 3.2.6 Análisis de Funciones Puras (si está habilitado)
                    if act_cfg.pure_functions.enabled:
                        pure_analyzer = PureFunctionAnalyzer(target_functions=act_cfg.pure_functions.functions)
                        p_obs = pure_analyzer.analyze_file(src)
                        for obs in p_obs:
                            if not obs.is_pure:
                                all_style_obs.append({"archivo": src.name, "linea": obs.line, "mensaje": f"[FunciónPura] `{obs.function_name}()` no es pura: {', '.join(obs.violations)}"})


                    # 3.2.7 Generación de Diagramas de Flujo (si está habilitado)
                    if act_cfg.flowchart.enabled:
                        fc_gen = FlowchartGenerator()
                        try:
                            fc_diagrams = fc_gen.generate_for_file(src, output_format=act_cfg.flowchart.format)
                            for fn_name, d_code in fc_diagrams.items():
                                compilation_logs.append(
                                    f"=== Diagrama de Flujo: `{fn_name}()` ({src.name}) ===\n```{act_cfg.flowchart.format}\n{d_code}\n```\n"
                                )
                        except Exception as e:
                            compilation_logs.append(f"[Flowchart] Error generando diagrama para {src.name}: {e}\n")

                    # 3.2.8 Visualizador de Memoria y Estructuras (si está habilitado)
                    if act_cfg.memory_visualizer.enabled:
                        mem_vis = DynamicMemoryVisualizer()
                        try:
                            mem_diag = mem_vis.generate_diagram(src, output_format=act_cfg.memory_visualizer.format)
                            compilation_logs.append(
                                f"=== Diagrama de Topología de Memoria ({src.name}) ===\n```{act_cfg.memory_visualizer.format}\n{mem_diag}\n```\n"
                            )
                        except Exception as e:
                            compilation_logs.append(f"[MemoryVisualizer] Error generando diagrama para {src.name}: {e}\n")


                    # 3.2.9 Grafo de Llamadas y Recursión (si está habilitado)
                    if act_cfg.callgraph.enabled:
                        cg_gen = CallGraphGenerator()
                        try:
                            cg_diag = cg_gen.generate_for_file(
                                src,
                                output_format=act_cfg.callgraph.format,
                                include_stdlib=act_cfg.callgraph.include_stdlib,
                            )
                            compilation_logs.append(
                                f"=== Grafo de Invocación / Call Graph ({src.name}) ===\n```{act_cfg.callgraph.format}\n{cg_diag}\n```\n"
                            )
                        except Exception as e:
                            compilation_logs.append(f"[CallGraph] Error generando grafo para {src.name}: {e}\n")

                    # 3.2.10 Property-Based Testing (si está habilitado y el archivo compila)
                    if act_cfg.property_testing.enabled:
                        prop_runner = PropertyTestRunner()
                        try:
                            fns = extract_c_functions(src.read_text(encoding="utf-8", errors="replace"))
                            for fn_name in fns.keys():
                                if fn_name in ("main", "setUp", "tearDown"):
                                    continue
                                for prop in act_cfg.property_testing.properties:
                                    p_res = prop_runner.run_property_test(
                                        student_source=src,
                                        property_type=prop,
                                        target_function=fn_name,
                                        iterations=50,
                                    )
                                    status_str = "PASSED" if p_res.passed else "FAILED"
                                    compilation_logs.append(
                                        f"=== Property Test [{prop.upper()}] (`{fn_name}()` en {src.name}) ===\nResultado: {status_str} ({p_res.iterations_run} iters)\n{p_res.message}\n"
                                    )
                        except Exception as e:
                            compilation_logs.append(f"[PropertyTesting] Error evaluando {src.name}: {e}\n")


                    # 3.3 Análisis Estático Cppcheck individual (si está habilitado)
                    if act_cfg.cppcheck.enabled:
                        cpp_res = cppcheck_runner.analyze([src])
                        total_cppcheck_violations += cpp_res.violations_count
                        if cpp_res.full_output:
                            compilation_logs.append(
                                f"--- Logs Cppcheck ({src.name}) ---\n{cpp_res.full_output}\n"
                            )
                    else:
                        cpp_res = CppcheckResult(passed=True, violations_count=0, summary="Desactivado", full_output="")

                    # 3.4 Auditoría de Memoria Valgrind individual (si está habilitado)
                    if act_cfg.valgrind.enabled and act_cfg.compiler.enabled and comp_res.success:
                        valg_res = valgrind_runner.audit(bin_out)
                    else:
                        valg_res = ValgrindResult(
                            enabled=act_cfg.valgrind.enabled,
                            passed=True,
                            summary="Desactivado" if not act_cfg.valgrind.enabled else "-",
                            full_output="",
                        )
                    if valg_res.full_output:
                        compilation_logs.append(
                            f"--- Logs Valgrind ({src.name}) ---\n{valg_res.full_output}\n"
                        )

                    # 3.4.1 Herramientas CLI personalizadas por archivo fuente (stage = "source")
                    for tool in act_cfg.custom_tools:
                        if tool.enabled and tool.stage in ("source", "file"):
                            t_res = custom_tool_runner.run(tool, source=src, folder=rev_folder)
                            compilation_logs.append(
                                f"--- Herramienta Personalizada [{tool.name}] ({src.name}) ---\n{t_res.output}\n"
                            )
                            if tool.fail_on_error and not t_res.success:
                                all_compiled = False

                    # 3.4.2 Herramientas CLI personalizadas por binario (stage = "binary")
                    if comp_res.success and bin_out.exists():
                        for tool in act_cfg.custom_tools:
                            if tool.enabled and tool.stage == "binary":
                                t_res = custom_tool_runner.run(tool, source=src, binary=bin_out, folder=rev_folder)
                                compilation_logs.append(
                                    f"--- Herramienta Personalizada [{tool.name}] ({src.name}) ---\n{t_res.output}\n"
                                )
                                if tool.fail_on_error and not t_res.success:
                                    all_compiled = False

                    # 3.5 Fila de resultados por archivo
                    compilation_results_table.append(
                        {
                            "nombre_archivo": src.name,
                            "estado": "✓ Compilación OK" if comp_res.success else ("Desactivada" if not act_cfg.compiler.enabled else "✗ Falló Compilación"),
                            "estado_estilo": f"{s_score}/10" if act_cfg.style.enabled else "Desactivado",
                            "estado_valgrind": valg_res.summary if (comp_res.success and act_cfg.valgrind.enabled) else ("Desactivado" if not act_cfg.valgrind.enabled else "-"),
                            "estado_cppcheck": cpp_res.summary if act_cfg.cppcheck.enabled else "Desactivado",
                        }
                    )

                # 3.6 Herramientas CLI personalizadas por carpeta de revisión (stage = "folder")
                for tool in act_cfg.custom_tools:
                    if tool.enabled and tool.stage in ("folder", "revision"):
                        t_res = custom_tool_runner.run(tool, folder=rev_folder)
                        compilation_logs.append(
                            f"--- Herramienta Personalizada [{tool.name}] (Revisión r{v_num}) ---\n{t_res.output}\n"
                        )
                        if tool.fail_on_error and not t_res.success:
                            all_compiled = False


                avg_style_score = round(total_style_sum / len(c_sources), 2) if c_sources else 10.0
                compiled = len(compiled_binaries) > 0 and (all_compiled or any(file_compilation_status.values()))

                # 4. Ejecución Dinámica de Casos de Prueba
                test_results: List[Dict[str, Any]] = []
                tests_passed_count = 0
                total_tests_count = 0

                if compiled:
                    for ex_name, cases in testcases_by_exercise.items():
                        # Obtener el binario correspondiente al ejercicio
                        bin_for_ex = compiled_binaries.get(ex_name)
                        if not bin_for_ex:
                            # Fallback si un binario coincide en dígitos
                            for k, b in compiled_binaries.items():
                                if re.findall(r"\d+", k) == re.findall(r"\d+", ex_name):
                                    bin_for_ex = b
                                    break

                        if not bin_for_ex:
                            for tc in cases:
                                total_tests_count += 1
                                test_results.append(
                                    {
                                        "ejercicio": tc.exercise,
                                        "nombre_caso": tc.case_name,
                                        "argumentos_cli": "-",
                                        "resultado": "NO_SOURCE",
                                        "tiempo_ms": 0.0,
                                    }
                                )
                            continue

                        for tc in cases:
                            total_tests_count += 1
                            r_detail = test_runner.run_case(bin_for_ex, tc)
                            if r_detail.resultado == "PASSED":
                                tests_passed_count += 1
                            test_results.append(
                                {
                                    "ejercicio": r_detail.ejercicio,
                                    "nombre_caso": r_detail.nombre_caso,
                                    "argumentos_cli": r_detail.argumentos_cli or "-",
                                    "resultado": r_detail.resultado,
                                    "tiempo_ms": r_detail.tiempo_ms,
                                }
                            )

                # 5. Cálculo de Rúbrica
                breakdown = rubric_calc.calculate(
                    compiled=compiled,
                    style_score=avg_style_score,
                    linter_passed=total_cppcheck_violations == 0,
                    linter_violations=total_cppcheck_violations,
                    tests_passed_count=tests_passed_count,
                    total_tests_count=total_tests_count,
                )

                # 9. Guardar evaluación en BD
                db.save_evaluation(
                    revision_id=rev["id"],
                    compilation_status="OK" if compiled else "FAILED",
                    preliminary_grade=breakdown.nota_preliminar,
                    grade_compilation=breakdown.nota_compilacion,
                    grade_style=breakdown.nota_estilo,
                    grade_linter=breakdown.nota_linter,
                    grade_tests=breakdown.nota_pruebas,
                    unified_diff=unified_diff,
                    compilation_logs="\n".join(compilation_logs),
                    test_results=test_results,
                )

                # Contexto de versión para Markdown
                v_ctx = VersionReportContext(
                    numero_version=v_num,
                    fecha_hora=rev["created_at"] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    archivos_nuevos=str(len(c_sources) + len(h_sources)),
                    archivos_modificados="0" if v_num == 1 else str(len(c_sources)),
                    archivos_sin_cambios="0",
                    archivos_ignorados="0",
                    diff_unificado=unified_diff,
                    resultados_compilacion=compilation_results_table,
                    observaciones_estilo=all_style_obs,
                    logs_detallados_compilacion="\n".join(compilation_logs) or "Sin logs adicionales.",
                    resultados_pruebas=test_results,
                    nota_preliminar=breakdown.nota_preliminar,
                    nota_compilacion=breakdown.nota_compilacion,
                    nota_estilo=breakdown.nota_estilo,
                    nota_linter=breakdown.nota_linter,
                    nota_pruebas=breakdown.nota_pruebas,
                )
                version_contexts.append(v_ctx)

                latest_summary = StudentEvaluationSummary(
                    student_slug=student_slug,
                    student_name=student_slug,
                    version_evaluated=v_num,
                    compiled=compiled,
                    style_score=avg_style_score,
                    tests_passed=tests_passed_count,
                    total_tests=total_tests_count,
                    preliminary_grade=breakdown.nota_preliminar,
                    report_file=student_dir / f"{student_slug}_{clean_act_slug}.md",
                )

        if not version_contexts or not latest_summary:
            return None

        # Renderizar informe Markdown acumulativo
        student_report_ctx = StudentReportContext(
            estudiante_nombre=student_slug,
            estudiante_id=student_slug.split("_")[-1] if "_" in student_slug else "0",
            actividad_nombre=clean_act_slug,
            actividad_id=clean_act_slug.split("_")[-1] if "_" in clean_act_slug else "0",
            revision_actual=f"r{len(version_contexts)}",
            fecha_generacion=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            origen_configuracion=act_cfg.origen_configuracion,
            versiones=version_contexts,
            nota_final_preliminar=latest_summary.preliminary_grade,
        )


        reporter.write_student_report(
            output_file=latest_summary.report_file,
            ctx=student_report_ctx,
        )


        return latest_summary

    def evaluate_activity(
        self,
        activity_slug: str,
        parallel: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[StudentEvaluationSummary]:
        activity_dir = self.workspace_dir / activity_slug
        if not activity_dir.exists():
            raise FileNotFoundError(f"Directorio de actividad no encontrado: {activity_dir}")

        student_dirs = [d for d in sorted(activity_dir.iterdir()) if d.is_dir() and not d.name.startswith(".")]
        results: List[StudentEvaluationSummary] = []

        if parallel and len(student_dirs) > 1:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self.evaluate_student, activity_slug, s_dir): s_dir
                    for s_dir in student_dirs
                }
                for fut in concurrent.futures.as_completed(futures):
                    s_dir = futures[fut]
                    try:
                        res = fut.result()
                        if res:
                            results.append(res)
                            if progress_callback:
                                progress_callback(res.student_name)
                    except Exception as e:
                        if progress_callback:
                            progress_callback(f"Error evaluando {s_dir.name}: {e}")
        else:
            for s_dir in student_dirs:
                res = self.evaluate_student(activity_slug, s_dir)
                if res:
                    results.append(res)
                    if progress_callback:
                        progress_callback(res.student_name)

        return results
