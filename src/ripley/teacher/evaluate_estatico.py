"""Análisis estático y diagramas por archivo fuente de la evaluación de un estudiante."""

from pathlib import Path
from typing import Any, Dict, List

import ripley.pipeline.checks  # noqa: F401  (registra el catálogo unificado)
from ripley.pipeline.registry import iter_uniform_static

from ripley.core.callgraph import CallGraphGenerator
from ripley.core.doxygen import DoxygenAuditor
from ripley.core.flowchart import FlowchartGenerator
from ripley.core.linters import DeadCodeLinter, MagicNumberLinter, NamingConventionLinter
from ripley.core.memory_visualizer import DynamicMemoryVisualizer
from ripley.core.property_testing import PropertyTestRunner
from ripley.core.pure_functions import PureFunctionAnalyzer
from ripley.core.restrictions import CodeRestrictionsValidator
from ripley.core.semantic_diff import extract_c_functions


def analizar_fuente(
    src: Path,
    act_cfg,
    style_analyzer,
    p1_checker,
    all_style_obs: List[Dict[str, Any]],
    compilation_logs: List[str],
) -> float:
    """Estilo, P1, linters, auditores, diagramas y property testing de un .c.

    Acumula observaciones y logs en las listas recibidas y devuelve la nota de
    estilo del archivo (10.0 si el análisis de estilo está desactivado).
    """
    # 3.2 Análisis de Estilo individual (si está habilitado)
    s_score = 10.0
    if act_cfg.style.enabled:
        s_res = style_analyzer.analyze_file(src)
        s_score = s_res.score
        for obs in s_res.observaciones:
            all_style_obs.append(
                {
                    "archivo": obs.archivo,
                    "linea": obs.linea,
                    "mensaje": obs.mensaje,
                }
            )

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
    return s_score
