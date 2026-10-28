"""Conversor de hallazgos de Ripley a formato SARIF (Static Analysis Results Interchange Format 2.1.0).

Pensado para GitHub Code Scanning (sulaco `evaluar.yml`, Ola 25): cada resultado lleva la ruta
relativa a la raíz del repositorio (`%SRCROOT%`), que es lo que GitHub necesita para poner la
anotación sobre la línea del archivo. Antes salía sólo el nombre (`main.c`), y en un proyecto
con `src/main.c` la anotación no encontraba el archivo. Las rutas salen del sobre común de
hallazgos (`yutani.hallazgos`), que también aporta el enlace al apunte de cada regla.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ripley import __version__

_NIVELES = {"error": "error", "advertencia": "warning"}  # estilo, info y el resto: note


def _nivel(severidad: Any) -> str:
    return _NIVELES.get(str(severidad or "").strip().lower(), "note")


def _ubicacion(archivo: Optional[str], linea: Any, columna: Any = None) -> Dict[str, Any]:
    region: Dict[str, Any] = {"startLine": max(1, int(linea or 1))}
    if isinstance(columna, int) and columna > 0:
        region["startColumn"] = columna
    return {"physicalLocation": {
        "artifactLocation": {"uri": Path(archivo or "desconocido.c").as_posix(), "uriBaseId": "%SRCROOT%"},
        "region": region,
    }}


def _diagnosticos_de_compilacion(analisis_resultado: Any) -> List[Dict[str, Any]]:
    """Los errores del compilador, con la misma ruta relativa que el resto de los hallazgos."""
    from ripley.core.perfil_actividad import resolver_archivo

    comp = getattr(analisis_resultado, "compilation", {}) or {}
    base = _base(analisis_resultado)
    resultados = []
    for d in comp.get("translated_diagnostics", []) or []:
        archivo = resolver_archivo(d.get("file"), base, getattr(analisis_resultado, "c_files", []))
        if not archivo:
            continue
        resultados.append({
            "ruleId": "compilacion",
            "level": "error" if str(d.get("severity", "error")).lower() == "error" else "warning",
            "message": {"text": str(d.get("translated_message") or d.get("message") or "Error de compilación")
                        + (f" Sugerencia: {d['suggestion']}" if d.get("suggestion") else "")},
            "locations": [_ubicacion(archivo, d.get("line"), d.get("column"))],
        })
    return resultados


def _base(analisis_resultado: Any) -> Optional[Path]:
    target = getattr(analisis_resultado, "target", "")
    if not target:
        return None
    return Path(target) if getattr(analisis_resultado, "is_directory", False) else Path(target).parent


def _hallazgos(analisis_resultado: Any) -> List[Dict[str, Any]]:
    """Una entrada por observación: la del sobre común si la regla tiene código; si no, la observación
    tal cual (el sobre descarta las que no tienen `rule_code`, y en el SARIF no se puede perder ninguna)."""
    from ripley.core.perfil_actividad import a_hallazgos, resolver_archivo

    base, fuentes = _base(analisis_resultado), getattr(analisis_resultado, "c_files", []) or []
    resultado = []
    for f in getattr(analisis_resultado, "ast_findings", []) or []:
        sobre = a_hallazgos([f], base, fuentes)
        if sobre:
            resultado.append(sobre[0])
            continue
        resultado.append({
            "codigo": f.get("rule_id") or "RIPLEY000",
            "severidad": {"WARN": "advertencia"}.get(str(f.get("severity", "")).upper(), str(f.get("severity", "")).lower()),
            "mensaje": f.get("message", ""),
            "sugerencia": f.get("suggestion"),
            "archivo": resolver_archivo(f.get("file"), base, fuentes) or f.get("file"),
            "linea": f.get("line"),
            "columna": f.get("column"),
        })
    return resultado


def exportar_sarif(analisis_resultado: Any) -> Dict[str, Any]:
    """Convierte el objeto AnalysisResult de Ripley a un diccionario compatible con SARIF v2.1.0."""
    hallazgos = _hallazgos(analisis_resultado)

    rules_map: Dict[str, Dict[str, Any]] = {}
    results_list: List[Dict[str, Any]] = []

    for h in hallazgos:
        rule_id = str(h.get("codigo") or "RIPLEY000")
        if rule_id not in rules_map:
            regla: Dict[str, Any] = {
                "id": rule_id,
                "name": rule_id,
                "shortDescription": {"text": str(h.get("mensaje") or rule_id)},
                "fullDescription": {"text": str(h.get("sugerencia") or h.get("mensaje") or rule_id)},
                "defaultConfiguration": {"level": _nivel(h.get("severidad"))},
                "properties": {"tags": [str(h.get("categoria") or "estilo")]},
            }
            if h.get("enlace"):
                regla["helpUri"] = h["enlace"]
            rules_map[rule_id] = regla

        texto = str(h.get("mensaje") or "")
        if h.get("sugerencia"):
            texto += f" Sugerencia: {h['sugerencia']}"
        results_list.append({
            "ruleId": rule_id,
            "level": _nivel(h.get("severidad")),
            "message": {"text": texto},
            "locations": [_ubicacion(h.get("archivo"), h.get("linea"), h.get("columna"))],
        })

    compilacion = _diagnosticos_de_compilacion(analisis_resultado)
    if compilacion:
        rules_map["compilacion"] = {
            "id": "compilacion",
            "name": "compilacion",
            "shortDescription": {"text": "El programa no compila"},
            "defaultConfiguration": {"level": "error"},
        }
        results_list = compilacion + results_list

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Ripley",
                        "version": __version__,
                        "informationUri": "https://github.com/INGCOM-UNRN-P1/ripley",
                        "rules": list(rules_map.values()),
                    }
                },
                "originalUriBaseIds": {"%SRCROOT%": {"description": {"text": "Raíz del repositorio"}}},
                "results": results_list,
            }
        ],
    }
