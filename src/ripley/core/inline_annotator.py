"""Renderizador de diagnósticos inline en terminal estilo Rustc / Clang con subrayados ondulados."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def renderizar_anotacion_inline(
    archivo: Path,
    linea_num: int,
    columna: int,
    codigo_error: str,
    mensaje: str,
    severidad: str = "warning",
    contexto_lineas: int = 1,
    console: Optional[Console] = None,
) -> str:
    """Genera una vista enriquecida en terminal con flechas y subrayados sobre la línea exacta."""
    cons = console or Console()
    path = Path(archivo)

    if not path.is_file():
        return ""

    lineas = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if linea_num < 1 or linea_num > len(lineas):
        return ""

    idx_linea = linea_num - 1
    linea_afectada = lineas[idx_linea]
    col = max(1, columna)

    color_sev = "red" if severidad.lower() in ("error", "fatal", "bloqueante") else "yellow"
    
    # Construcción de puntero y ondulado: ~~~^~~~
    prefix_spaces = " " * (col - 1)
    pointer = f"{prefix_spaces}[{color_sev}]^~~~ [{codigo_error}] {mensaje}[/{color_sev}]"

    resultado_lines = [
        f"[{color_sev} bold]{severidad.upper()}[/{color_sev} bold]: {mensaje} [{codigo_error}]",
        f"  --> {path.name}:{linea_num}:{col}",
        f"   |",
        f"{linea_num:4d} | {linea_afectada}",
        f"   | {pointer}",
        f"   |",
    ]

    out = "\n".join(resultado_lines)
    cons.print(out)
    return out
