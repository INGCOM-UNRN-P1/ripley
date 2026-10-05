"""Caracterización de Evaluator.evaluate_student (revisión 07: partir la función).

golden_evaluacion.json se generó antes de partirla (caracterizacion/generar_golden_evaluacion.py).
"""

import importlib.util
import json
from pathlib import Path

DIRECTORIO = Path(__file__).parent / "caracterizacion"
_spec = importlib.util.spec_from_file_location("generar_golden_evaluacion", DIRECTORIO / "generar_golden_evaluacion.py")
_generador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_generador)


def test_misma_evaluacion_que_antes_del_refactor():
    esperado = json.loads((DIRECTORIO / "golden_evaluacion.json").read_text(encoding="utf-8"))
    assert _generador.evaluar() == esperado
