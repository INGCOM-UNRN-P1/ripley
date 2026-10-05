"""Caracterización de Evaluator.evaluate_student (revisión 07: partir la función).

golden_evaluacion.json se generó antes de partirla (caracterizacion/generar_golden_evaluacion.py).
"""

import importlib.util
import json
import os
from pathlib import Path

DIRECTORIO = Path(__file__).parent / "caracterizacion"
_spec = importlib.util.spec_from_file_location("generar_golden_evaluacion", DIRECTORIO / "generar_golden_evaluacion.py")
_generador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_generador)


def test_misma_evaluacion_que_antes_del_refactor():
    """El informe completo depende de qué herramientas hay instaladas (cppcheck, valgrind, gaff…),
    así que se compara entero solo en el entorno donde se generó (RIPLEY_CARACTERIZACION=1); en el
    CI, lo que no depende del entorno."""
    esperado = json.loads((DIRECTORIO / "golden_evaluacion.json").read_text(encoding="utf-8"))
    actual = _generador.evaluar()
    if os.environ.get("RIPLEY_CARACTERIZACION") == "1":
        assert actual == esperado
    else:
        for clave in ("compilo", "pruebas", "version"):
            assert actual[clave] == esperado[clave], clave
        assert actual["informe"][0] == esperado["informe"][0]
