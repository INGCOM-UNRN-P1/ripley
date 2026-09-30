"""Los reportes de sebastian no generan hallazgos vacíos (N-RIPLEY-09).

sebastian devuelve una lista con un reporte por función. El adaptador de CLI de ripley la envuelve en
`observaciones` antes de extraer, y así cada función analizada, aun sin recursión ni riesgo, aparecía
como una ADVERTENCIA de «sebastian» sin mensaje en `ripley check`.
"""

from ripley.core.entrypoints_contrato import extract_raw_observations

SIN_RIESGO = {"schema_version": "1.0.0", "funcion": "main", "archivo": "main.c", "es_recursiva": False,
              "linea_inicio": 2, "riesgo_overflow": "BAJO", "recomendaciones": []}
CON_RIESGO = {"schema_version": "1.0.0", "funcion": "factorial", "archivo": "rec.c", "es_recursiva": True,
              "linea_inicio": 5, "riesgo_overflow": "ALTO", "recomendaciones": ["Agregá un caso base."]}


def test_sin_riesgo_no_hay_hallazgos_ni_en_lista_ni_envuelto():
    assert extract_raw_observations([SIN_RIESGO]) == []
    assert extract_raw_observations({"ok": True, "observaciones": [SIN_RIESGO]}) == []


def test_con_riesgo_el_hallazgo_tiene_regla_y_mensaje():
    for datos in ([CON_RIESGO], {"ok": True, "observaciones": [CON_RIESGO]}):
        obs = extract_raw_observations(datos)
        assert [o["rule_code"] for o in obs] == ["STACK_OVERFLOW_RISK", "RECURSION_RECOMMENDATION"]
        assert all(o["message"] for o in obs)
