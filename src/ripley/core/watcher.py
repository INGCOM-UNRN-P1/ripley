"""File watcher en segundo plano para re-ejecución continua de Ripley ante modificaciones."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel

from ripley.core.engine import run_ast_linters


def obtener_mtimes(fuentes: List[Path]) -> Dict[Path, float]:
    """Obtiene mapa de mtimes de los archivos dados."""
    mtimes = {}
    for f in fuentes:
        p = Path(f)
        if p.exists():
            mtimes[p] = p.stat().st_mtime
    return mtimes


def ejecutar_ciclo_watch(
    fuentes: List[Path],
    console: Optional[Console] = None,
) -> Dict[str, Any]:
    """Ejecuta una pasada de verificación y renderiza resumen en vivo."""
    cons = console or Console()
    cons.clear()
    cons.print(f"[bold cyan]🔍 Ripley Watcher activo[/bold cyan] — Monitoreando {len(fuentes)} archivos...\n")

    hallazgos = run_ast_linters(fuentes)
    calif = max(0.0, 10.0 - (len(hallazgos) * 0.5))

    if not hallazgos:
        cons.print(Panel("[bold green]✓ Código limpio: 0 violaciones detectadas.[/bold green]", title="Estado", border_style="green"))
    else:
        cons.print(Panel(f"[bold yellow]⚠️ Se detectaron {len(hallazgos)} advertencias / violaciones. Calificación: {calif:.1f}/10.0[/bold yellow]", title="Estado", border_style="yellow"))
        for h in hallazgos[:5]:
            cons.print(f"  • [cyan]{h.get('codigo')}[/cyan]: {h.get('mensaje')} (Línea {h.get('linea')})")
        if len(hallazgos) > 5:
            cons.print(f"  [dim]... y {len(hallazgos) - 5} observaciones más.[/dim]")

    return {"hallazgos": len(hallazgos), "calificacion": calif}
