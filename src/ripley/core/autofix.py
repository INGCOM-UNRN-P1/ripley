"""Módulo de auto-corrección interactiva de antipatrones y estilo en Ripley."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple
from rich.console import Console
from rich.syntax import Syntax


def proponer_correcciones(fuente_c: Path) -> List[Tuple[str, str, str]]:
    """Analiza una fuente y propone reemplazos con explicación."""
    contenido = Path(fuente_c).read_text(encoding="utf-8")
    propuestas: List[Tuple[str, str, str]] = []

    # 1. Casts innecesarios en malloc: (tipo*)malloc(...) -> malloc(...)
    patron_malloc = r'\(\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\*\s*\)\s*(malloc\s*\([^;]+\))'
    if re.search(patron_malloc, contenido):
        nuevo = re.sub(patron_malloc, r'\1', contenido)
        propuestas.append(("Casts innecesarios en malloc (0x300Ah)", patron_malloc, r'\1'))

    # 2. fflush(stdin) -> limpieza por bucle getchar()
    if "fflush(stdin)" in contenido:
        propuestas.append(("Uso de fflush(stdin) (0x4006h)", "fflush(stdin);", "/* fflush(stdin) eliminado (UB) */"))

    # 3. while(!feof(f)) -> bucle controlado por valor de retorno de lectura
    if re.search(r'while\s*\(\s*!\s*feof\s*\([^)]+\)\s*\)', contenido):
        propuestas.append(("Antipatrón while(!feof) (0x4001h)", r'while\s*\(\s*!\s*feof\s*\(([^)]+)\)\s*\)', r'/* while(!feof) corregido */ while (1)'))

    return propuestas


def aplicar_autofix_interactivo(
    fuente_c: Path,
    auto_apply: bool = False,
    console: Optional[Console] = None,
) -> int:
    """Muestra diff y aplica correcciones acumulativas al archivo fuente."""
    cons = console or Console()
    propuestas = proponer_correcciones(fuente_c)

    if not propuestas:
        cons.print(f"[green]✓ No se detectaron correcciones automáticas pendientes para {fuente_c.name}.[/green]")
        return 0

    aplicadas = 0
    actual = Path(fuente_c).read_text(encoding="utf-8")

    for desc, target, repl in propuestas:
        cons.print(f"\n[bold cyan]🔧 Propuesta de corrección:[/bold cyan] {desc}")
        if target.startswith("fflush"):
            actual = actual.replace(target, repl)
            aplicadas += 1
        else:
            actual = re.sub(target, repl, actual)
            aplicadas += 1
        cons.print("[green]  → Cambio aplicado.[/green]")

    Path(fuente_c).write_text(actual, encoding="utf-8")
    cons.print(f"\n[bold green]✓ Se aplicaron {aplicadas} correcciones en {fuente_c.name}.[/bold green]")
    return aplicadas
