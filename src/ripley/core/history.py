"""Gestor de historial de progreso y corrección de errores en Ripley."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table


HISTORIAL_FILE = ".ripley_history.json"


def registrar_progreso(
    target_dir: Path,
    hallazgos_count: int,
    calificacion: float,
    fuentes: List[str],
) -> Dict[str, Any]:
    """Registra una instantánea de auditoría en el historial local."""
    target_path = Path(target_dir).resolve()
    hist_file = target_path / HISTORIAL_FILE

    datos: List[Dict[str, Any]] = []
    if hist_file.is_file():
        try:
            datos = json.loads(hist_file.read_text(encoding="utf-8"))
        except Exception:
            datos = []

    nuevo_registro = {
        "timestamp": datetime.now().isoformat(),
        "hallazgos": hallazgos_count,
        "calificacion": calificacion,
        "fuentes": fuentes,
    }
    datos.append(nuevo_registro)
    hist_file.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    return nuevo_registro


def mostrar_historial_progreso(target_dir: Path, console: Optional[Console] = None) -> List[Dict[str, Any]]:
    """Muestra una tabla de evolución de errores corregidos a lo largo del tiempo."""
    cons = console or Console()
    hist_file = Path(target_dir).resolve() / HISTORIAL_FILE

    if not hist_file.is_file():
        cons.print("[yellow]No hay historial de progreso registrado aún para este directorio.[/yellow]")
        return []

    try:
        registros = json.loads(hist_file.read_text(encoding="utf-8"))
    except Exception:
        cons.print("[red]Error al leer archivo de historial corrupto.[/red]")
        return []

    tabla = Table(title="📈 Historial de Progreso y Calidad del Código (Ripley)", border_style="cyan")
    tabla.add_column("#", justify="center")
    tabla.add_column("Fecha y Hora", style="dim")
    tabla.add_column("Violaciones", justify="center")
    tabla.add_column("Calificación", justify="right")
    tabla.add_column("Tendencia", justify="center")

    prev_hallazgos = None
    for i, reg in enumerate(registros, 1):
        h = reg.get("hallazgos", 0)
        c = reg.get("calificacion", 0.0)
        ts = reg.get("timestamp", "").replace("T", " ")[:19]

        if prev_hallazgos is None:
            tendencia = "—"
        elif h < prev_hallazgos:
            tendencia = f"[green]↓ Mejoró (-{prev_hallazgos - h})[/green]"
        elif h > prev_hallazgos:
            tendencia = f"[red]↑ Aumentó (+{h - prev_hallazgos})[/red]"
        else:
            tendencia = "[blue]= Estable[/blue]"

        prev_hallazgos = h
        tabla.add_row(str(i), ts, str(h), f"{c:.1f} / 10.0", tendencia)

    cons.print(tabla)
    return registros
