"""Conversor de hallazgos de Ripley a formato SARIF (Static Analysis Results Interchange Format 2.1.0)."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def exportar_sarif(analisis_resultado: Any) -> Dict[str, Any]:
    """Convierte el objeto AnalysisResult de Ripley a un diccionario compatible con SARIF v2.1.0."""
    findings = getattr(analisis_resultado, "ast_findings", []) or []
    
    rules_map: Dict[str, Dict[str, Any]] = {}
    results_list: List[Dict[str, Any]] = []
    
    for f in findings:
        rule_id = f.get("rule_id", "RIPLEY000")
        if rule_id not in rules_map:
            rules_map[rule_id] = {
                "id": rule_id,
                "name": f.get("title", rule_id),
                "shortDescription": {"text": f.get("message", "Regla de análisis estático Ripley")},
                "fullDescription": {"text": f.get("suggestion") or f.get("message") or rule_id},
                "defaultConfiguration": {
                    "level": "error" if f.get("severity") == "ERROR" else "warning"
                },
            }
            
        file_path = f.get("file", "unknown.c")
        line_num = int(f.get("line", 1) or 1)
        col_num = int(f.get("column", 1) or 1)
        
        result_item = {
            "ruleId": rule_id,
            "level": "error" if f.get("severity") == "ERROR" else "warning",
            "message": {"text": f.get("message", "")},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": file_path},
                        "region": {
                            "startLine": line_num,
                            "startColumn": col_num,
                        },
                    }
                }
            ],
        }
        results_list.append(result_item)
        
    sarif_doc = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Ripley",
                        "version": "2.0.0",
                        "informationUri": "https://github.com/catedra-p1/ripley",
                        "rules": list(rules_map.values()),
                    }
                },
                "results": results_list,
            }
        ],
    }
    return sarif_doc
