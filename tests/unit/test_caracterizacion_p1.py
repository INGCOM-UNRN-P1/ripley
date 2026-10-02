"""Caracterización de P1RuleChecker sobre fuentes que disparan cada regla (N-ECO-16).

golden.json se generó antes de partir `analyze` (391 líneas) en una función por regla: si este test
falla, el refactor cambió alguna observación o su orden. Ver tests/caracterizacion/generar_golden.py.
"""

import importlib.util
import json
from pathlib import Path

import pytest

DIRECTORIO = Path(__file__).parents[1] / "caracterizacion"
_spec = importlib.util.spec_from_file_location("generar_golden_p1", DIRECTORIO / "generar_golden.py")
_generador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_generador)

GOLDEN = json.loads((DIRECTORIO / "golden.json").read_text(encoding="utf-8"))


def test_el_golden_cubre_todos_los_fuentes_y_todas_las_reglas():
    # as_posix: en Windows relative_to usa la barra invertida y el golden se generó con «/».
    assert set(GOLDEN) == {r.relative_to(_generador.RAIZ).as_posix() for r in _generador.fuentes()}
    from ripley.core.p1_rules import REGLAS

    codigos = {obs[0] for observaciones in GOLDEN.values() for obs in observaciones}
    assert {"0x" + regla.__name__.split("_")[2] for regla in REGLAS} == codigos


@pytest.mark.parametrize("fuente", sorted(GOLDEN))
def test_mismas_observaciones_que_antes_del_refactor(fuente):
    assert _generador.observaciones(_generador.RAIZ / fuente) == GOLDEN[fuente]
