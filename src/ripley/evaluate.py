"""Evaluation orchestrator: compilation, security, style, linters, tests, diffing and reporting."""

import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Dict, List, Optional


from ripley.compiler import Compiler
from ripley.config import RipleyConfig
from ripley.db import DatabaseManager
from ripley.diffing import generate_unified_diff
from ripley.mapping import MappingStore, SPECIAL_AUXILIARY, SPECIAL_IGNORE
from ripley.reporter import MarkdownReporter, StudentReportContext, VersionReportContext

from ripley.runner import (
    CppcheckRunner,
    DynamicTestRunner,
    RubricCalculator,
    ValgrindRunner,
)
from ripley.security import SecurityScanner
from ripley.style import StyleAnalyzer
from ripley.testcases import discover_testcases


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
        self.compiler = Compiler(config.compiler, config.limits, config.sandbox)
        self.security_scanner = SecurityScanner(config.security)
        self.style_analyzer = StyleAnalyzer(config.style)
        self.valgrind_runner = ValgrindRunner(config.valgrind, config.limits)
        self.cppcheck_runner = CppcheckRunner(config.cppcheck)
        self.test_runner = DynamicTestRunner(config.limits)
        self.rubric_calc = RubricCalculator(config.rubric)
        self.reporter = MarkdownReporter(config.templates.ruta_plantillas)

    def evaluate_student(
        self,
        activity_slug: str,
        student_dir: Path,
    ) -> Optional[StudentEvaluationSummary]:
        db_path = student_dir / ".metadata.db"
        if not db_path.exists():
            return None

        db = DatabaseManager(db_path)
        student_slug = student_dir.name
        revisions = db.get_all_revisions(student_slug)
        if not revisions:
            return None

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

                # 2. Escaneo de seguridad preventivo
                security_violations = self.security_scanner.scan_files(all_sources)

                # 3. Mapeo y Compilación por Ejercicio
                mapping_store = MappingStore(self.workspace_dir, activity_slug)
                available_ex_names = list(testcases_by_exercise.keys())

                exercise_groups: Dict[str, List[Path]] = {}
                aux_sources: List[Path] = []
                ignored_sources: List[Path] = []

                for src in c_sources:
                    target = mapping_store.get_effective_mapping(student_slug, src.name, available_ex_names)
                    if target == SPECIAL_IGNORE:
                        ignored_sources.append(src)
                    elif target == SPECIAL_AUXILIARY:
                        aux_sources.append(src)
                    elif target:
                        if target not in exercise_groups:
                            exercise_groups[target] = []
                        exercise_groups[target].append(src)
                    else:
                        # Cada archivo C no mapeado es un ejercicio independiente
                        unmapped_key = f"unmapped_{src.stem}"
                        exercise_groups[unmapped_key] = [src]

                compiled_binaries: Dict[str, Optional[Path]] = {}
                compilation_results_table: List[Dict[str, str]] = []
                all_style_obs: List[Dict[str, Any]] = []
                compilation_logs: List[str] = []
                file_compilation_status: Dict[str, bool] = {}
                all_compiled = True

                if security_violations:
                    all_compiled = False
                    comp_log = "Violaciones de seguridad detectadas:\n" + "\n".join(
                        f"- [{v.filename}:{v.line}] {v.message}" for v in security_violations
                    )
                    compilation_logs.append(comp_log)
                else:
                    for ex_name, ex_srcs in exercise_groups.items():
                        bin_out = temp_path / f"bin_v{v_num}_{ex_name}"
                        comp_res = self.compiler.compile(ex_srcs + aux_sources, bin_out)

                        for src_f in ex_srcs:
                            file_compilation_status[src_f.name] = comp_res.success

                        if comp_res.success:
                            compiled_binaries[ex_name] = bin_out
                        else:
                            all_compiled = False

                        # Registrar salida completa del compilador (stdout + stderr)
                        compiler_raw = (comp_res.stdout + "\n" + comp_res.stderr).strip()
                        display_name = ex_name.replace("unmapped_", "")
                        src_names = ", ".join(f.name for f in ex_srcs)

                        if compiler_raw:
                            compilation_logs.append(
                                f"=== Salida del Compilador ({src_names} -> {display_name}) ===\n{compiler_raw}\n"
                            )
                        else:
                            compilation_logs.append(
                                f"=== Salida del Compilador ({src_names} -> {display_name}) ===\nCompilación limpia sin errores ni advertencias.\n"
                            )

                compiled = len(compiled_binaries) > 0 and (all_compiled or any(file_compilation_status.values()))

                # 4. Análisis de Estilo
                total_style_score = 0.0
                if c_sources:
                    for src in c_sources:
                        s_res = self.style_analyzer.analyze_file(src)
                        total_style_score += s_res.score
                        for obs in s_res.observaciones:
                            all_style_obs.append(
                                {
                                    "archivo": obs.archivo,
                                    "linea": obs.linea,
                                    "mensaje": obs.mensaje,
                                }
                            )
                    avg_style_score = round(total_style_score / len(c_sources), 2)
                else:
                    avg_style_score = 10.0

                # 5. Análisis Estático (Cppcheck)
                cppcheck_res = self.cppcheck_runner.analyze(all_sources)
                if cppcheck_res.full_output:
                    compilation_logs.append(f"\n--- Logs Cppcheck ---\n{cppcheck_res.full_output}")

                # 6. Auditoría de Memoria (Valgrind)
                valgrind_sample_bin = next(iter(compiled_binaries.values()), None) if compiled else None
                valgrind_res = self.valgrind_runner.audit(
                    valgrind_sample_bin if valgrind_sample_bin else "none"
                )
                if valgrind_res.full_output:
                    compilation_logs.append(f"\n--- Logs Valgrind ---\n{valgrind_res.full_output}")

                for src in c_sources:
                    src_ok = file_compilation_status.get(src.name, False)
                    compilation_results_table.append(
                        {
                            "nombre_archivo": src.name,
                            "estado": "✓ Compilación OK" if src_ok else "✗ Falló Compilación",
                            "estado_estilo": f"{avg_style_score}/10" if src_ok else "-",
                            "estado_valgrind": valgrind_res.summary if src_ok else "-",
                            "estado_cppcheck": cppcheck_res.summary,
                        }
                    )

                # 7. Ejecución Dinámica de Casos de Prueba
                test_results: List[Dict[str, Any]] = []
                tests_passed_count = 0
                total_tests_count = 0

                if compiled:
                    for ex_name, cases in testcases_by_exercise.items():
                        # Obtener el binario correspondiente al ejercicio
                        bin_for_ex = compiled_binaries.get(ex_name)
                        if not bin_for_ex:
                            # Fallback si un binario no mapeado coincide en dígitos
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
                            r_detail = self.test_runner.run_case(bin_for_ex, tc)
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



                # 8. Cálculo de Rúbrica
                breakdown = self.rubric_calc.calculate(
                    compiled=compiled,
                    style_score=avg_style_score,
                    linter_passed=cppcheck_res.passed,
                    linter_violations=cppcheck_res.violations_count,
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
                    report_file=student_dir / f"{student_slug}_{activity_slug}.md",
                )

        if not version_contexts or not latest_summary:
            return None

        # Renderizar informe Markdown acumulativo
        student_report_ctx = StudentReportContext(
            estudiante_nombre=student_slug,
            estudiante_id=student_slug.split("_")[-1] if "_" in student_slug else "0",
            actividad_nombre=activity_slug,
            actividad_id=activity_slug.split("_")[-1] if "_" in activity_slug else "0",
            revision_actual=f"r{len(version_contexts)}",
            fecha_generacion=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            origen_configuracion=self.config.origen_configuracion,
            versiones=version_contexts,
            nota_final_preliminar=latest_summary.preliminary_grade,
        )


        self.reporter.write_student_report(
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
