"""Modo pista de las evaluaciones (revisión 05 §3), del lado de ripley.

daedalus, tetsuo y hal tienen un modo pista: dicen qué tipo de error hay y en qué función, sin la línea
ni la corrección. Lo activan con `--pista` o con la variable `P1_PISTA=1`. ripley la exporta a los
satélites que invoca cuando la práctica lo pide (`[general] pistas = true` en ripley.toml, que viaja en
el manifiesto del .ripkg) o con `ripley-check check --pista`.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

VARIABLE_PISTA = "P1_PISTA"


def pista_activa(bandera: bool = False) -> bool:
    return bandera or os.environ.get(VARIABLE_PISTA, "").strip().lower() in ("1", "true", "si", "sí", "yes")


@contextmanager
def con_pista(activa: bool) -> Iterator[None]:
    """Exporta P1_PISTA=1 a los satélites mientras dura el bloque, y después deja el entorno como estaba.

    Restaurar importa en el lado docente, que evalúa varias prácticas (con y sin pistas) en un proceso.
    """
    if not activa:
        yield
        return
    anterior = os.environ.get(VARIABLE_PISTA)
    os.environ[VARIABLE_PISTA] = "1"
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop(VARIABLE_PISTA, None)
        else:
            os.environ[VARIABLE_PISTA] = anterior
