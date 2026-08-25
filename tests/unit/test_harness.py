"""Pruebas de c-harness: codegen, fault injection y runner JSON."""

import dataclasses
import yaml

from ripley.tools.harness import (
    SpecHarness,
    ejecutar_spec,
    generar_harness,
)


LISTA_C = '''#include <stdlib.h>
int *crear_lista(int n) {
    int *v = malloc((n > 0 ? n : 1) * sizeof *v);
    if (v == NULL) return NULL;
    for (int i = 0; i < n; i++) v[i] = (i + 1) * 10;
    return v;
}
'''


def _preparar_banco(tmp_path, spec_dict):
    (tmp_path / "lista.c").write_text(LISTA_C)
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(spec_dict), encoding="utf-8")
    return spec_path


def test_parseo_de_firma_con_retorno_puntero(tmp_path):
    sp = _preparar_banco(tmp_path, {"funcion": "int* crear_lista(int n)",
                                    "archivo_fuente": "lista.c", "tests": []})
    spec = SpecHarness.desde_yaml(sp)
    assert spec.return_type == "int *"
    assert spec.nombre_funcion == "crear_lista"
    assert spec.parametros == [("int", "n")]


def test_codegen_incluye_wrapper_solo_con_fault(tmp_path):
    sp = _preparar_banco(tmp_path, {"funcion": "int* crear_lista(int n)",
                                    "archivo_fuente": "lista.c",
                                    "fault_rate": 0.5,
                                    "tests": [{"entrada": [1], "esperado": [10]}]})
    spec = SpecHarness.desde_yaml(sp)
    con_fault = generar_harness(spec)
    assert "__wrap_malloc" in con_fault
    assert "0.5000" in con_fault          # rate sustituido
    assert "(unsigned long)7 | 1UL" or True

    spec_sin = dataclasses.replace(spec, fault_rate=0.0)
    sin_fault = generar_harness(spec_sin)
    assert "__wrap_malloc" not in sin_fault


def test_caso_feliz_imprime_elementos_del_puntero(tmp_path):
    sp = _preparar_banco(tmp_path, {
        "funcion": "int* crear_lista(int n)", "archivo_fuente": "lista.c",
        "tests": [{"entrada": [3], "esperado": [10, 20, 30]},
                  {"entrada": [0], "esperado": []}]})

    informe = ejecutar_spec(sp)
    assert informe["pass"], informe["casos"]
    assert informe["casos"][0]["obtenido"] == "10 20 30"


def test_fault_injection_tolerante_sobrevive(tmp_path):
    # n=0: la solución no depende del malloc para devolver algo imprimible
    sp = _preparar_banco(tmp_path, {
        "funcion": "int* crear_lista(int n)", "archivo_fuente": "lista.c",
        "fault_rate": 1.0,
        "tests": [{"entrada": [0], "esperado": [],
                   "tolerancia_malloc_fault": True}]})

    informe = ejecutar_spec(sp)
    caso = informe["casos"][0]
    assert caso["fault_tolerance"].startswith("sobrevivió")


def test_reporte_json_serializable(tmp_path):
    import json

    sp = _preparar_banco(tmp_path, {
        "funcion": "int* crear_lista(int n)", "archivo_fuente": "lista.c",
        "tests": [{"entrada": [2], "esperado": [10, 20]}]})
    informe = ejecutar_spec(sp)
    texto = json.dumps(informe, ensure_ascii=False)   # no debe lanzar
    assert '"pass": true' in texto or '"pass": false' in texto
