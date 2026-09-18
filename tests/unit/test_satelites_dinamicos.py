"""Regresión de FERRO-D0901, TETSUO-D0901, DRAKE-D0902 y ESPER-D0903.

Los satélites dinámicos estaban catalogados pero ripley los invocaba con el
directorio del proyecto, que no aceptan: drake y esper daban un error de uso,
tetsuo y ferro salían sin observaciones. Los payloads reproducen la salida real
de cada CLI.
"""

import json
import subprocess
from pathlib import Path

import pytest

from ripley.core.entrypoints import (
    SATELLITE_CATALOG,
    SatellitePluginAdapter,
    _define_main,
    extract_raw_observations,
)


def _adaptador(clave):
    info = SATELLITE_CATALOG[clave]
    return SatellitePluginAdapter(
        name=clave, tool_name=info["tool"], cli_command=info["cli_cmd"], entry_point=None, instance=None
    )


@pytest.fixture
def proyecto(tmp_path):
    (tmp_path / "main.c").write_text("#include <stdio.h>\nint main(void) { return 0; }\n", encoding="utf-8")
    (tmp_path / "util.c").write_text("int suma(int a, int b) { return a + b; }\n", encoding="utf-8")
    return tmp_path


def _simular(monkeypatch, salidas):
    """Reemplaza subprocess.run: devuelve `salidas[herramienta]` y registra los argumentos."""
    llamadas = []

    def falso_run(args, capture_output=True, text=True, timeout=20):
        llamadas.append(list(args))
        cuerpo = salidas.get(args[0], {})
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(cuerpo), stderr="")

    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr("subprocess.run", falso_run)
    return llamadas


@pytest.mark.parametrize("clave", ["fuzzing", "sanitizer_translator"])
def test_solo_se_invocan_los_programas_completos_uno_por_uno(proyecto, monkeypatch, clave):
    llamadas = _simular(monkeypatch, {})
    _adaptador(clave)._execute_cli(proyecto, {})
    herramienta = SATELLITE_CATALOG[clave]["cli_cmd"]
    assert llamadas == [[herramienta, "check", str(proyecto / "main.c"), "--json"]]


def test_un_modulo_sin_main_no_se_invoca(proyecto, monkeypatch):
    (proyecto / "main.c").unlink()
    llamadas = _simular(monkeypatch, {})
    res = _adaptador("fuzzing")._execute_cli(proyecto, {})
    assert llamadas == [] and res["ok"] is True


def test_define_main_reconoce_las_formas_habituales(tmp_path):
    for i, texto in enumerate(["int main(void){}", "int main( int argc, char **argv ){}", "int  main (void){}"]):
        f = tmp_path / f"{i}.c"
        f.write_text(texto, encoding="utf-8")
        assert _define_main(f), texto
    g = tmp_path / "sin.c"
    g.write_text("int domain(void){return 0;} /* remain (void) */\n", encoding="utf-8")
    assert not _define_main(g)


def test_ferro_solo_corre_si_el_manifiesto_indica_el_objetivo(proyecto, monkeypatch):
    llamadas = _simular(monkeypatch, {})
    res = _adaptador("hardware_profiler")._execute_cli(proyecto, {})
    assert res["omitido"] is True and llamadas == []

    objetivo = str(proyecto / "main.c")
    llamadas = _simular(monkeypatch, {"ferro": {"passed": True, "advertencias": []}})
    _adaptador("hardware_profiler")._execute_cli(proyecto, {"target": objetivo})
    assert llamadas == [["ferro", "check", objetivo, "--json"]]


def test_esper_invoca_compile_sobre_el_archivo_y_no_el_catalogo(proyecto, monkeypatch):
    llamadas = _simular(monkeypatch, {"esper": {"passed": True, "diagnostics": []}})
    _adaptador("gcc_explainer")._execute_cli(proyecto, {})
    assert llamadas
    for llamada in llamadas:
        assert llamada[:2] == ["esper", "compile"]
        assert "catalog" not in llamada
        assert llamada[-3:] == ["-o", "/dev/null", "--json"]


DRAKE = {
    "ok": False,
    "archivo": "main.c",
    "crashes": [{"id": 5, "payload": "2147483647\n", "codigo_retorno": 124, "senal": "TIMEOUT"}],
}
FERRO = {
    "passed": True,
    "advertencias": ["Las instrucciones ejecutadas casi no crecen con N (171,856 para N=100 y 171,904 para N=1,600)."],
}
TETSUO = {
    "passed": False,
    "instrumented": True,
    "diagnoses": [{
        "sanitizer_type": "AddressSanitizer", "error_tag": "heap-buffer-overflow",
        "title_es": "Desbordamiento de heap", "explanation_es": "Se leyó fuera del bloque.",
        "file_path": "main.c", "line_number": 10, "suggestion_es": "Revisá los índices.",
    }],
}


def test_los_crashes_del_fuzzing_llegan_como_hallazgos():
    obs = extract_raw_observations(DRAKE)
    assert [o["rule_code"] for o in obs] == ["FUZZ_CRASH"]
    assert "TIMEOUT" in obs[0]["message"] and "2147483647" in obs[0]["message"]


def test_los_avisos_de_ferro_llegan_como_hallazgos():
    obs = extract_raw_observations(FERRO)
    assert [o["rule_code"] for o in obs] == ["PERF_WARNING"]


def test_los_diagnosticos_de_tetsuo_llegan_como_hallazgos():
    assert len(extract_raw_observations(TETSUO)) == 1


def test_el_veredicto_negativo_de_tetsuo_se_propaga_por_archivo(proyecto, monkeypatch):
    _simular(monkeypatch, {"tetsuo": TETSUO})
    res = _adaptador("sanitizer_translator")._execute_cli(proyecto, {})
    assert res["ok"] is False
    assert len(res["observaciones"]) == 1


def test_sin_poder_instrumentar_no_hay_hallazgo_ni_falla(proyecto, monkeypatch):
    """Falta libasan: no se verificó nada, y eso no es un defecto del código del alumno."""
    _simular(monkeypatch, {"tetsuo": {"passed": False, "instrumented": False, "diagnoses": [], "raw_output": "ld: no libasan"}})
    res = _adaptador("sanitizer_translator")._execute_cli(proyecto, {})
    assert res["ok"] is True and res["observaciones"] == []
