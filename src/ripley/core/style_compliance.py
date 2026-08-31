"""Auditor de conformidad con el estándar pedagógico de estilo de cátedra en Ripley."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table

from ripley.core.engine import run_ast_linters


def auditar_conformidad_estilo(
    fuentes: List[Path],
    console: Optional[Console] = None,
) -> Dict[str, Any]:
    """Evalúa el código contra las reglas de cátedra y emite reporte de conformidad."""
    cons = console or Console()
    hallazgos = run_ast_linters(fuentes)
    total_violaciones = len(hallazgos)

    tabla = Table(title="📐 Auditoría de Conformidad con el Estándar de Cátedra", border_style="cyan")
    tabla.add_column("Archivo", style="bold white")
    tabla.add_column("Línea:Col", justify="center")
    tabla.add_column("Regla", style="cyan")
    tabla.add_column("Descripción / Sugerencia Didáctica", style="yellow")

    for h in hallazgos:
        archivo = Path(h.get("archivo", "fuente.c")).name
        loc = f"{h.get('linea', 1)}:{h.get('columna', 1)}"
        codigo = h.get("codigo", "0x0000h")
        desc = f"{h.get('mensaje', '')} → {h.get('sugerencia', '')}"
        tabla.add_row(archivo, loc, codigo, desc)

    cons.print(tabla)

    cumplimiento = max(0.0, 10.0 - (total_violaciones * 0.5))
    estado = "[bold green]CONFORME[/bold green]" if total_violaciones == 0 else f"[bold yellow]REVISAR ({total_violaciones} desviaciones)[/bold yellow]"

    cons.print(f"\n[bold]Índice de Conformidad:[/bold] {cumplimiento:.1f} / 10.0 — Estado: {estado}")

    return {
        "total_violaciones": total_violaciones,
        "indice_conformidad": cumplimiento,
        "conforme": total_violaciones == 0,
        "hallazgos": hallazgos,
    }
