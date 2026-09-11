"""Motor de ejecución paralela asíncrona de plugins satélites para Ripley (QoL 1)."""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ResultadoTareaAsync:
    nombre_tarea: str
    archivo: Path
    exito: bool
    tiempo_ms: float
    resultado: Any
    error: Optional[str] = None


def ejecutar_tareas_paralelo(
    tareas: List[tuple[str, Path, Callable[[Path], Any]]],
    max_workers: Optional[int] = None,
) -> List[ResultadoTareaAsync]:
    """Ejecuta una colección de tareas de plugins concurrentemente sobre múltiples archivos C."""
    if not tareas:
        return []

    workers = max_workers or min(len(tareas), os.cpu_count() or 4)
    resultados: List[ResultadoTareaAsync] = []

    def _invocar(item: tuple[str, Path, Callable[[Path], Any]]) -> ResultadoTareaAsync:
        nombre, ruta, fn = item
        t0 = time.perf_counter()
        try:
            res = fn(ruta)
            duracion = (time.perf_counter() - t0) * 1000.0
            return ResultadoTareaAsync(
                nombre_tarea=nombre,
                archivo=ruta,
                exito=True,
                tiempo_ms=round(duracion, 2),
                resultado=res,
            )
        except Exception as e:
            duracion = (time.perf_counter() - t0) * 1000.0
            return ResultadoTareaAsync(
                nombre_tarea=nombre,
                archivo=ruta,
                exito=False,
                tiempo_ms=round(duracion, 2),
                resultado=None,
                error=str(e),
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futuros = [executor.submit(_invocar, t) for t in tareas]
        for f in concurrent.futures.as_completed(futuros):
            resultados.append(f.result())

    return resultados
