"""Modo pista de las evaluaciones (revisión 05 §3): ripley lo activa para daedalus, tetsuo y hal."""

import os
import shutil
import warnings

import pytest

import ripley.core.engine as engine
from ripley.config import load_config
from ripley.core.gcc_translator import summarize_for_humans, translate_stderr
from ripley.core.pista import VARIABLE_PISTA, con_pista
from ripley.pipeline import bundle as bundle_mod
from ripley.pipeline.student_runner import run_bundle
from ripley.teacher.pack import pack_practice


def test_seccion_general_de_ripley_toml(tmp_path):
    toml = tmp_path / "ripley.toml"
    toml.write_text("[general]\npistas = true\n", encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # [general] y pistas son conocidas: sin avisos
        assert load_config(toml).general.pistas is True
    assert load_config(tmp_path / "no-existe.toml").general.pistas is False


def test_con_pista_exporta_y_restaura(monkeypatch):
    monkeypatch.delenv(VARIABLE_PISTA, raising=False)
    with con_pista(True):
        assert os.environ[VARIABLE_PISTA] == "1"
    assert VARIABLE_PISTA not in os.environ
    with con_pista(False):
        assert VARIABLE_PISTA not in os.environ


def test_analyze_target_corre_los_satelites_en_modo_pista(monkeypatch, tmp_path):
    monkeypatch.delenv(VARIABLE_PISTA, raising=False)
    vistos = []
    monkeypatch.setattr(engine, "_analyze_target", lambda *a, **k: vistos.append(os.environ.get(VARIABLE_PISTA)))
    engine.analyze_target(tmp_path, pista=True)
    engine.analyze_target(tmp_path)
    assert vistos == ["1", None] and VARIABLE_PISTA not in os.environ


def test_resumen_de_errores_sin_linea_ni_sugerencia():
    traducidos = translate_stderr("main.c:7:5: error: expected ';' before 'return'\n")
    completo = summarize_for_humans(traducidos)
    pista = summarize_for_humans(traducidos, pista=True)
    assert "main.c:7" in completo and "main.c:7" not in pista and "main.c" in pista
    assert "Sugerencia" not in pista


def test_el_manifiesto_lleva_el_modo_pista():
    assert bundle_mod.build_manifest("t", [], "gcc", [], {}, pistas=True)["general"] == {"pistas": True}
    assert "general" not in bundle_mod.build_manifest("t", [], "gcc", [], {})


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc no disponible")
def test_run_bundle_en_modo_pista_no_muestra_la_salida_cruda(tmp_path):
    pdir = tmp_path / "practicas" / "demo"
    (pdir / "testcases").mkdir(parents=True)
    (pdir / "ripley.toml").write_text('[general]\npistas = true\n\n[compiler]\nflags = ["-std=c11"]\n',
                                      encoding="utf-8")
    paquete = pack_practice(pdir).output_path
    roto = tmp_path / "roto.c"
    roto.write_text("int main(void)\n{\n    int x = 1\n    return x;\n}\n", encoding="utf-8")
    reporte = run_bundle(paquete, [roto])
    assert reporte.pista and not reporte.compiled_ok
    assert reporte.compile_errors == "" and reporte.human_diagnostics
    assert "roto.c:" not in reporte.human_diagnostics
