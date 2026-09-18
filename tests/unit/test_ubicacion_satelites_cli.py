"""Regresión de CROWE-D0901 y MOTOKO-D0901: la ubicación se perdía al pasar por la CLI.

El JSON de crowe usa `issues[].file_path/line_number` y el de motoko
`violations[].file_path/line_number`; el adaptador entregaba `archivo: ''` y
`linea: 0`, con lo que el alumno veía el diagnóstico sin poder ir a la línea.
Los payloads reproducen la salida real de `crowe check --json` y
`motoko check --json`.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ripley.core.entrypoints import SatellitePluginAdapter

SALIDA_CROWE = {
    "schema_version": "1.0.0",
    "files_analyzed": ["proy/p.c"],
    "issues": [
        {
            "code": "CRW001", "category": "POINTER_SIZE", "severity": "ERROR",
            "file_path": "proy/p.c", "line_number": 3, "line_content": "int x = (int)ptr;",
            "message": "Casteo directo de puntero a 'int'.", "suggestion": "Usá uintptr_t.",
        },
        {
            "code": "CRW002", "category": "CHAR_SIGN", "severity": "WARNING",
            "file_path": "proy/p.c", "line_number": 4, "line_content": "char c = -1;",
            "message": "Uso de 'char' con signo.", "suggestion": "Usá signed char.",
        },
    ],
    "architectures": [],
    "passed": False,
}

SALIDA_MOTOKO = {
    "schema_version": "1.0.0",
    "tdas_analyzed": [{"name": "t_lista", "is_opaque": False, "header_path": "proy/lista.h", "line_number": 1}],
    "violations": [
        {
            "code": "MOT001", "severity": "WARNING", "tda_name": "t_lista",
            "file_path": "proy/lista.h", "line_number": 1, "line_content": "typedef struct { ... } t_lista;",
            "message": "El TDA 't_lista' expone sus campos internos.", "suggestion": "Hacelo opaco.",
        },
        {
            "code": "MOT002", "severity": "ERROR", "tda_name": "t_lista",
            "file_path": "proy/main.c", "line_number": 3, "line_content": "l->cantidad",
            "message": "Acceso directo al campo 'cantidad'.", "suggestion": "Usá las primitivas.",
        },
    ],
    "passed": False,
}


def _ejecutar(monkeypatch, tmp_path, nombre, herramienta, salida):
    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, capture_output=True, text=True, timeout=20: subprocess.CompletedProcess(
            args, 1, stdout=json.dumps(salida), stderr=""
        ),
    )
    adaptador = SatellitePluginAdapter(
        name=nombre, tool_name=herramienta, cli_command=herramienta, entry_point=None, instance=None
    )
    return adaptador.execute(tmp_path)


@pytest.mark.parametrize(
    "nombre, herramienta, salida, esperadas",
    [
        ("portability", "crowe", SALIDA_CROWE, [("CRW001", "p.c", 3), ("CRW002", "p.c", 4)]),
        ("tda_encapsulation", "motoko", SALIDA_MOTOKO, [("MOT001", "lista.h", 1), ("MOT002", "main.c", 3)]),
    ],
)
def test_la_ubicacion_de_cada_hallazgo_llega_al_reporte(
    monkeypatch, tmp_path, nombre, herramienta, salida, esperadas
):
    res = _ejecutar(monkeypatch, tmp_path, nombre, herramienta, salida)
    obtenidas = [(o["rule_code"], o["file"], o["line"]) for o in res["observaciones"]]
    assert obtenidas == esperadas
    # Los dos juegos de nombres que consumen los reportes deben coincidir.
    for o in res["observaciones"]:
        assert (o["archivo"], o["linea"]) == (o["file"], o["line"])
        assert o["message"]


@pytest.mark.parametrize(
    "nombre, herramienta, salida",
    [("portability", "crowe", SALIDA_CROWE), ("tda_encapsulation", "motoko", SALIDA_MOTOKO)],
)
def test_el_veredicto_negativo_se_propaga(monkeypatch, tmp_path, nombre, herramienta, salida):
    res = _ejecutar(monkeypatch, tmp_path, nombre, herramienta, salida)
    assert res["ok"] is False
    assert res["passed"] is False


@pytest.mark.skipif(
    not (shutil.which("crowe") and shutil.which("motoko")), reason="requiere crowe y motoko instalados"
)
def test_con_las_herramientas_reales(tmp_path: Path):
    (tmp_path / "p.c").write_text("void t(void *ptr) { int x = (int)ptr; }\n", encoding="utf-8")
    (tmp_path / "lista.h").write_text("typedef struct { int cantidad; void *primero; } t_lista;\n", encoding="utf-8")
    (tmp_path / "main.c").write_text('#include "lista.h"\nvoid f(t_lista *l) { int c = l->cantidad; }\n', encoding="utf-8")

    for nombre, herramienta, codigo in (("portability", "crowe", "CRW001"), ("tda_encapsulation", "motoko", "MOT002")):
        adaptador = SatellitePluginAdapter(
            name=nombre, tool_name=herramienta, cli_command=herramienta, entry_point=None, instance=None
        )
        res = adaptador.execute(tmp_path)
        hallazgo = next(o for o in res["observaciones"] if o["rule_code"] == codigo)
        assert hallazgo["file"] and hallazgo["line"] > 0, hallazgo
