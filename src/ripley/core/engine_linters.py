"""Ejecución de linters AST y reglas P1 sobre las fuentes C."""


from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
from ripley.core.linters import (
    DeadCodeLinter,
    InternalCloneLinter,
    MagicNumberLinter,
    NamingConventionLinter,
)
from ripley.core.p1_rules import P1RuleChecker

from ripley.core.engine import normalize_rule_code


def run_ast_linters(
    c_files: List[Path],
    target_path: Optional[Path] = None,
    include_plugins: bool = True,
    strict: bool = False,
    plugins_dinamicos: bool = False,
) -> List[Dict[str, Any]]:
    """Aplica el catálogo de linters AST, reglas de cátedra P1 y plugins satélites sobre cada archivo .c.

    Los satélites de fase dinámica (fuzzing, mutación, inyección de fallos,
    perfilado) compilan y ejecutan el código del estudiante, así que quedan
    fuera del análisis estático salvo que se pidan con `plugins_dinamicos`.
    """
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

        # Se deriva del catálogo en vez de mantenerse a mano: la lista paralela
        # anterior omitía 15 de los 28 satélites catalogados (mocks, semantic_diff,
        # mcdc_coverage, binary_io, documentation, dataset_generator,
        # mutation_testing...), que quedaban declarados pero nunca ejecutados.
        from ripley.core.entrypoints import plugins_de_fase

        static_plugins = plugins_de_fase("estatico")
        if plugins_dinamicos:
            static_plugins |= plugins_de_fase("dinamico")

        for p in discovered:
            if p.name not in static_plugins or not p.is_available:
                continue
            if p.name in ("style", "gaff"):
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
