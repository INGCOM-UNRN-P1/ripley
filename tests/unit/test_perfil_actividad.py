"""Perfil de satélites por actividad y sobre JSON con hallazgos comunes (revisión 07)."""

from pathlib import Path

from ripley.core.engine import AnalysisResult
from ripley.core.perfil_actividad import BASE, a_hallazgos, incluido, satelites_de_la_actividad


def test_perfil_por_tema(tmp_path: Path):
    (tmp_path / "ripley.toml").write_text('[actividad]\ntema = "punteros"\n', encoding="utf-8")
    perfil = satelites_de_la_actividad(tmp_path)
    assert perfil == set(BASE) | {"bishop", "tetsuo"}
    assert incluido("sanitizer_translator", "tetsuo", perfil) and not incluido("padding", "brett", perfil)


def test_perfil_explicito_y_ausente(tmp_path: Path):
    (tmp_path / "ripley.toml").write_text('[actividad]\nsatelites = ["gaff", "Motoko"]\n', encoding="utf-8")
    assert satelites_de_la_actividad(tmp_path) == {"gaff", "motoko"}
    otro = tmp_path / "otro"
    otro.mkdir()
    (otro / "ripley.toml").write_text('[general]\npistas = true\n', encoding="utf-8")
    assert satelites_de_la_actividad(otro) is None


def test_sobre_json_con_hallazgos():
    resultado = AnalysisResult(version="x", target="t", is_directory=False, ast_findings=[
        {"rule_code": "0x3001h", "severity": "ERROR", "file": "a.c", "line": 3, "message": "m", "source_plugin": "gaff"},
        {"rule_code": "KAN001", "severity": "CRITICO", "file": "a.c", "line": 4, "message": "gets", "source_plugin": "security"},
    ])
    hallazgos = resultado.to_dict()["hallazgos"]
    assert [h["id"] for h in hallazgos] == ["gaff:0x3001h", "security:KAN001"]
    assert hallazgos[0]["categoria"] == "memoria" and hallazgos[0]["enlace"].endswith("/x3001h")
    assert hallazgos[1]["categoria"] == "seguridad" and hallazgos[1]["severidad"] == "error"
    assert a_hallazgos([{"message": "sin código"}]) == []
