"""Extracción y normalización de observaciones emitidas por los plugins satélites."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union



def extract_raw_observations(data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
    """Extrae la lista de observaciones/violaciones/antipatrones/vulnerabilidades de la salida de un plugin."""
    raw_obs: List[Dict[str, Any]] = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Soporte de salida de sebastian (funciones analizadas)
                if "riesgo_overflow" in item:
                    riesgo = str(item.get("riesgo_overflow", "BAJO")).upper()
                    if riesgo in ("ALTO", "CRITICO"):
                        raw_obs.append({
                            "rule_code": "STACK_OVERFLOW_RISK",
                            "severity": "ERROR" if riesgo == "CRITICO" else "ADVERTENCIA",
                            "message": f"Función '{item.get('funcion')}' presenta riesgo {riesgo} de stack overflow.",
                            "file": item.get("archivo", ""),
                            "line": int(item.get("linea_inicio", 1)),
                        })
                    for rec in item.get("recomendaciones", []):
                        raw_obs.append({
                            "rule_code": "RECURSION_RECOMMENDATION",
                            "severity": "SUGERENCIA",
                            "message": str(rec),
                            "file": item.get("archivo", ""),
                            "line": int(item.get("linea_inicio", 1)),
                        })
                elif any(k in item for k in ("rule_code", "codigo", "code", "message", "mensaje")):
                    raw_obs.append(item)
        return raw_obs

    if not isinstance(data, dict):
        return raw_obs

    keys = (
        "observaciones",
        "issues",
        "diagnosticos",
        "diagnostics",
        "diagnoses",
        "violations",
        "violaciones",
        "antipatrones",
        "vulnerabilidades",
        "hallazgos",
        "findings",
        "auditorias",
        "structs",
        "makefile_issues",
    )
    for k in keys:
        v = data.get(k)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    raw_obs.append(item)

    # drake: cada crash del fuzzing es un hallazgo; `ok: false` sin ellos dejaba al
    # alumno con un plugin fallido y ningún mensaje.
    if isinstance(data.get("crashes"), list):
        for crash in data["crashes"]:
            if isinstance(crash, dict):
                raw_obs.append({
                    "rule_code": "FUZZ_CRASH",
                    "rule_name": "Caída bajo fuzzing",
                    "severity": "ERROR",
                    "file": data.get("archivo", ""),
                    "message": (
                        f"El fuzzing provocó {crash.get('senal') or 'una terminación anormal'} "
                        f"con la entrada {str(crash.get('payload', '')).strip()!r}."
                    ),
                })

    # ferro: avisos de que el perfilado no es confiable (p. ej. el optimizador
    # eliminó el bucle medido).
    if isinstance(data.get("advertencias"), list):
        for aviso in data["advertencias"]:
            if isinstance(aviso, str):
                raw_obs.append({"rule_code": "PERF_WARNING", "severity": "ADVERTENCIA", "message": aviso})

    if "guard_issues" in data and isinstance(data["guard_issues"], list):
        for g in data["guard_issues"]:
            raw_obs.append({
                "rule_code": "GUARD_MISSING",
                "severity": "ADVERTENCIA",
                "message": str(g),
            })

    if "cycles" in data and isinstance(data["cycles"], list):
        for c in data["cycles"]:
            if isinstance(c, dict):
                raw_obs.append({
                    "rule_code": "CIRCULAR_DEPENDENCY",
                    "severity": "ERROR",
                    "message": c.get("description", "Dependencia circular detectada"),
                    "file": c.get("cycle", [""])[0] if c.get("cycle") else "",
                })

    if "archivos" in data and isinstance(data["archivos"], list):
        for arch in data["archivos"]:
            if isinstance(arch, dict):
                for subk in ("violaciones", "observaciones", "issues", "violations", "antipatrones", "vulnerabilidades", "diagnosticos", "diagnostics"):
                    subv = arch.get(subk)
                    if isinstance(subv, list):
                        for item in subv:
                            if isinstance(item, dict):
                                raw_obs.append(item)

    if "files" in data and isinstance(data["files"], list):
        for f in data["files"]:
            if isinstance(f, dict):
                for subk in ("violaciones", "observaciones", "issues", "violations", "antipatrones", "vulnerabilidades", "diagnosticos", "diagnostics"):
                    subv = f.get(subk)
                    if isinstance(subv, list):
                        for item in subv:
                            if isinstance(item, dict):
                                raw_obs.append(item)

    return raw_obs


def normalize_finding(raw_obs: Dict[str, Any], source_plugin: str) -> Dict[str, Any]:
    """Adapta cualquier observación devuelta por plugins (RAM o CLI) al esquema canónico de Ripley."""
    # Soporte para structs auditados por brett
    if "wasted_padding_bytes" in raw_obs:
        wasted = int(raw_obs.get("wasted_padding_bytes", 0))
        struct_name = str(raw_obs.get("name", "struct"))
        rule_code = "PADDING_INEFFICIENT" if wasted > 0 else "PADDING_OPTIMAL"
        rule_name = f"Alineación y Padding: {struct_name}"
        severity = "ADVERTENCIA" if wasted > 0 else "INFO"
        msg = str(raw_obs.get("message") or f"Estructura '{struct_name}' desperdicia {wasted} bytes de padding.")
        sug = str(raw_obs.get("suggestion") or (f"Reordenar campos para ahorrar {wasted} bytes." if wasted > 0 else ""))
        raw_file = str(raw_obs.get("file_path") or raw_obs.get("file") or raw_obs.get("archivo") or "")
        f_name = Path(raw_file).name if raw_file else ""
        line = int(raw_obs.get("line_number") or raw_obs.get("line") or raw_obs.get("linea") or 0)
        return {
            "rule_code": rule_code,
            "rule_name": rule_name,
            "severity": severity,
            "file": f_name,
            "line": line,
            "column": 0,
            "message": msg,
            "suggestion": sug,
            "source_plugin": source_plugin,
            "rule_id": rule_code,
            "codigo": rule_code,
            "titulo": rule_name,
            "severidad": severity,
            "archivo": f_name,
            "linea": line,
            "columna": 0,
            "mensaje": msg,
            "sugerencia": sug,
        }

    rule_code = str(
        raw_obs.get("rule_code")
        or raw_obs.get("codigo")
        or raw_obs.get("code")
        or raw_obs.get("rule_id")
        or raw_obs.get("alias")
        or source_plugin
    )
    rule_name = str(
        raw_obs.get("rule_name")
        or raw_obs.get("titulo")
        or raw_obs.get("title")
        or raw_obs.get("nombre")
        or (f"Violación de Encapsulamiento TDA: {raw_obs['tda']}" if "tda" in raw_obs else None)
        or (f"Violación de Encapsulamiento TDA: {raw_obs['tda_name']}" if "tda_name" in raw_obs else None)
        or raw_obs.get("symbol")
        or rule_code
    )

    raw_sev = str(raw_obs.get("severity") or raw_obs.get("severidad") or "ADVERTENCIA").upper()
    if raw_sev in ("WARN", "WARNING"):
        severity = "ADVERTENCIA"
    elif raw_sev in ("CRITICO", "ALTO", "ERROR", "FATAL"):
        severity = "ERROR"
    elif raw_sev in ("ESTILO", "STYLE"):
        severity = "ESTILO"
    elif raw_sev in ("INFO", "INFORMACION", "INFORMATIVO"):
        severity = "INFO"
    else:
        severity = raw_sev

    raw_file = str(
        raw_obs.get("file")
        or raw_obs.get("archivo")
        or raw_obs.get("location")
        or raw_obs.get("file_path")
        or ""
    )
    f_name = Path(raw_file).name if raw_file else ""
    line = int(raw_obs.get("line") or raw_obs.get("linea") or raw_obs.get("line_number") or 0)
    col = int(raw_obs.get("column") or raw_obs.get("columna") or raw_obs.get("col_offset") or 0)
    msg = str(raw_obs.get("message") or raw_obs.get("mensaje") or raw_obs.get("explicacion") or "")
    sug = str(raw_obs.get("suggestion") or raw_obs.get("sugerencia") or "")

    return {
        "rule_code": rule_code,
        "rule_name": rule_name,
        "severity": severity,
        "file": f_name,
        "line": line,
        "column": col,
        "message": msg,
        "suggestion": sug,
        "source_plugin": source_plugin,
        # Claves de compatibilidad institucional
        "rule_id": rule_code,
        "codigo": rule_code,
        "titulo": rule_name,
        "severidad": severity,
        "archivo": f_name,
        "linea": line,
        "columna": col,
        "mensaje": msg,
        "sugerencia": sug,
    }
