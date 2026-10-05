"""Reglas que la actividad no evalúa: [reglas] ignorar y .ripleyignore (QoL #808)."""

from pathlib import Path

from ripley.config import load_config
from ripley.core.engine import run_ast_linters
from ripley.core.reglas_ignoradas import filtrar_ignoradas, patrones_de_la_actividad

HALLAZGOS = [
    {"rule_code": "0x1001h", "source_plugin": "gaff"},
    {"rule_code": "0x4003h", "source_plugin": "gaff"},
    {"rule_code": "0x0101h", "source_plugin": "gaff"},
    {"rule_code": "MAGIC_NUMBER", "source_plugin": "ripley"},
]


def _codigos(hallazgos):
    return [h["rule_code"] for h in hallazgos]


def test_codigo_comodin_y_herramienta():
    assert _codigos(filtrar_ignoradas(HALLAZGOS, ["0x40*h"])) == ["0x1001h", "0x0101h", "MAGIC_NUMBER"]
    assert _codigos(filtrar_ignoradas(HALLAZGOS, ["gaff:0x0101H", "magic_number"])) == ["0x1001h", "0x4003h"]
    assert filtrar_ignoradas(HALLAZGOS, []) == HALLAZGOS


def test_patrones_del_toml_y_del_ripleyignore(tmp_path: Path):
    (tmp_path / "ripley.toml").write_text('[reglas]\nignorar = ["0x40*h"]\n', encoding="utf-8")
    (tmp_path / ".ripleyignore").write_text("# TP1: sin reglas de nombres\n0x0101h  # nombres cortos\n\n", encoding="utf-8")
    assert patrones_de_la_actividad(tmp_path) == ["0x40*h", "0x0101h"]
    assert load_config(tmp_path / "ripley.toml").reglas.ignorar == ["0x40*h"]


def test_run_ast_linters_aplica_la_configuracion_de_la_actividad(tmp_path: Path):
    fuente = tmp_path / "main.c"
    fuente.write_text("int main(void)\n{\n    int v[50];\n    v[0] = 7;\n    return v[0];\n}\n", encoding="utf-8")
    todos = run_ast_linters([fuente], target_path=tmp_path, include_plugins=False)
    assert todos, "el ejemplo tiene que producir algún hallazgo"
    codigo = todos[0]["rule_code"]
    (tmp_path / ".ripleyignore").write_text(f"{codigo}\n", encoding="utf-8")
    filtrados = run_ast_linters([fuente], target_path=tmp_path, include_plugins=False)
    assert codigo not in _codigos(filtrados) and len(filtrados) < len(todos)
