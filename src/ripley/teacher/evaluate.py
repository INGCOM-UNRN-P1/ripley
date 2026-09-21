"""Evaluation orchestrator: compilation, security, style, linters, tests, diffing and reporting."""

import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import tempfile
from typing import Any, Callable, Dict, List, Optional


import ripley.pipeline.checks  # noqa: F401  (registra el catálogo unificado)

from ripley.core.compiler import CompilationResult, Compiler
from ripley.config import RipleyConfig, load_config
from ripley.teacher.db import DatabaseManager
from ripley.core.diffing import generate_unified_diff
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

from ripley.core.p1_rules import P1RuleChecker
from ripley.teacher.reporter import MarkdownReporter, StudentReportContext, VersionReportContext
from ripley.core.runner import (
    CppcheckResult,
    CppcheckRunner,
    CustomToolRunner,
    DynamicTestRunner,
    RubricCalculator,
    ValgrindResult,
    ValgrindRunner,
)
from ripley.core.security import SecurityScanner
from ripley.core.style import StyleAnalyzer
from ripley.core.testcases import discover_testcases
from ripley.teacher.evaluate_estatico import analizar_fuente
from ripley.teacher.evaluate_pruebas import ejecutar_casos_de_prueba


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

                    s_score = analizar_fuente(
                        src, act_cfg, style_analyzer, p1_checker, all_style_obs, compilation_logs
                    )
                    total_style_sum += s_score



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
                test_results, tests_passed_count, total_tests_count = ejecutar_casos_de_prueba(
                    compiled, compiled_binaries, testcases_by_exercise, test_runner
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
