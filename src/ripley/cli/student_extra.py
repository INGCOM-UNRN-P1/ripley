"""Comandos auxiliares de ripley-check (explain, analyze, report, badge, lsp, history...)."""

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.table import Table

from ripley import __version__
from ripley.cli._common import console

from ripley.cli.student import app, generar_seccion_markdown


@app.command("explain")
def cmd_explain(
    rule_code: str = typer.Argument(..., help="Código de regla de cátedra (ej. 0x1001h, 0x0001h, 'all' o palabra clave de búsqueda)."),
) -> None:
    """Explica una regla pedagógica de cátedra o busca por palabras clave en el catálogo canónico."""
    from rich.panel import Panel
    from rich.syntax import Syntax
    from ripley.core.p1_rules import P1_RULES_CATALOG

    if rule_code.lower() == "all":
        table = Table(title="Catálogo de Reglas Pedagógicas P1 (0xXXXXh)")
        table.add_column("Código", style="cyan")
        table.add_column("Categoría")
        table.add_column("Severidad", justify="center")
        table.add_column("Título")
        for code, rule in sorted(P1_RULES_CATALOG.items()):
            sev_color = "red" if rule.severity == "ERROR" else ("yellow" if rule.severity == "ADVERTENCIA" else "blue")
            table.add_row(code, rule.category, f"[{sev_color}]{rule.severity}[/{sev_color}]", rule.title)
        console.print(table)
        return

    code_norm = rule_code.strip()
    if not (code_norm.startswith("0x") and code_norm.endswith("h")):
        # Búsqueda interactiva por palabra clave en el catálogo
        query = code_norm.lower()
        coincidencias = [
            (c, r) for c, r in P1_RULES_CATALOG.items()
            if query in c.lower() or query in r.title.lower() or query in r.description.lower() or query in r.category.lower() or query in r.rationale.lower()
        ]
        if coincidencias:
            table = Table(title=f"Reglas P1 encontradas para '{rule_code}' ({len(coincidencias)})")
            table.add_column("Código", style="cyan")
            table.add_column("Categoría")
            table.add_column("Severidad", justify="center")
            table.add_column("Título")
            for c, r in sorted(coincidencias):
                sev_color = "red" if r.severity == "ERROR" else ("yellow" if r.severity == "ADVERTENCIA" else "blue")
                table.add_row(c, r.category, f"[{sev_color}]{r.severity}[/{sev_color}]", r.title)
            console.print(table)
            return

    if not code_norm.startswith("0x"):
        code_norm = f"0x{code_norm}"
    if not code_norm.endswith("h"):
        code_norm = f"{code_norm}h"

    rule = P1_RULES_CATALOG.get(code_norm)
    if not rule:
        console.print(f"[bold red]Regla desconocida: '{rule_code}'[/bold red]")
        console.print("[dim]Utilizá 'ripley-check explain all' para listar todas las reglas disponibles o buscá por palabra clave.[/dim]")
        raise typer.Exit(code=1)

    sev_color = "red" if rule.severity == "ERROR" else ("yellow" if rule.severity == "ADVERTENCIA" else "blue")
    console.print(f"\n[bold cyan]📖 Regla P1 {rule.code}: {rule.title}[/bold cyan]")
    console.print(f"  • [bold]Categoría:[/bold] {rule.category}")
    console.print(f"  • [bold]Severidad:[/bold] [{sev_color}]{rule.severity}[/{sev_color}]")
    console.print(f"  • [bold]Descripción:[/bold] {rule.description}\n")

    if rule.rationale:
        console.print(Panel(rule.rationale, title="💡 Justificación Pedagógica de Cátedra", border_style="cyan"))

    inc_code = rule.incorrect_example or "/* Antipatrón o incumplimiento de la norma */"
    cor_code = rule.correct_example or "/* Código estructurado según las pautas de cátedra */"

    console.print(Panel(Syntax(inc_code, "c", theme="monokai", line_numbers=True), title="❌ Código Incorrecto (Antipatrón)", border_style="red"))
    console.print(Panel(Syntax(cor_code, "c", theme="monokai", line_numbers=True), title="✅ Código Correcto (Refactorización sugerida)", border_style="green"))
    console.print("")


@app.command("gcc-explain")
def cmd_gcc_explain(
    target: str = typer.Argument("-", help="Ruta al archivo con la salida de error de GCC/ld o '-' para leer de stdin."),
    as_json: bool = typer.Option(False, "--json", help="Emitir diagnósticos traducidos en formato JSON estructurado."),
) -> None:
    """Traduce mensajes de error y advertencias de GCC/ld a explicaciones claras en español."""
    import sys
    from ripley.core.gcc_translator import translate_stderr
    from rich.panel import Panel

    if target == "-":
        content = sys.stdin.read()
    else:
        path = Path(target)
        if not path.exists():
            console.print(f"[bold red]Archivo inexistente: {target}[/bold red]")
            raise typer.Exit(code=1)
        content = path.read_text(encoding="utf-8", errors="replace")

    diagnostics = translate_stderr(content)

    if as_json:
        out = {
            "version": __version__,
            "total_diagnostics": len(diagnostics),
            "diagnostics": [
                {
                    "file": d.file,
                    "line": d.line,
                    "column": d.col,
                    "level": d.level,
                    "title": d.title,
                    "explanation": d.explanation,
                    "suggestion": d.suggestion,
                    "original": d.original,
                    "translated": d.translated,
                }
                for d in diagnostics
            ],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if not diagnostics:
        console.print("[green]No se detectaron errores ni advertencias traducibles de GCC/ld en la entrada.[/green]")
        return

    for d in diagnostics:
        loc = f"{d.file}:{d.line}:{d.col}" if d.file else f"Línea {d.line}"
        border_color = "red" if d.level == "error" else "yellow"
        body = f"[bold]{d.explanation}[/bold]\n\n[cyan]💡 Sugerencia:[/cyan] {d.suggestion}\n\n[dim]Original: {d.original}[/dim]"
        console.print(Panel(body, title=f"[{border_color}]{loc} · {d.title}[/{border_color}]", border_style=border_color))



@app.command("analyze")
def cmd_analyze(
    target: Path = typer.Argument(Path("."), help="Ruta al archivo .c o directorio del proyecto a analizar."),
    format: str = typer.Option("json", "--format", help="Formato de salida ('json')."),
    html: Optional[Path] = typer.Option(None, "--html", help="Generar informe interactivo HTML con badges de cátedra."),
) -> None:
    """Análisis programático sin estado para orquestadores (dredd, CI/CD, scripts)."""
    from ripley.core.engine import analyze_target

    if not target.exists():
        error_res = {
            "version": __version__,
            "error": f"Target not found: {target}",
            "compilation": {"success": False},
        }
        print(json.dumps(error_res, indent=2))
        raise typer.Exit(code=1)

    result = analyze_target(target)
    if html:
        from ripley.core.html_reporter import generate_interactive_html_report
        eval_data = {
            "student": target.name,
            "activity": "Análisis Ripley",
            "passed": result.compilation.get("success", False) and result.metrics.get("ast_errors_count", 0) == 0,
            "score": max(0.0, 10.0 - result.metrics.get("ast_errors_count", 0) * 2.0 - result.metrics.get("ast_warnings_count", 0) * 0.5),
            "observations": [
                {
                    "rule_code": f.get("rule_code", "AST"),
                    "title": f.get("rule_name", "Regla P1"),
                    "severity": f.get("severity", "INFO"),
                    "message": f.get("message", ""),
                    "suggestion": f.get("suggestion", ""),
                    "filename": f.get("file", ""),
                    "line": f.get("line", 0),
                    "code_snippet": f.get("code_snippet", ""),
                }
                for f in result.ast_findings
            ],
        }
        generate_interactive_html_report(eval_data, html)

    print(result.to_json())
    if not result.compilation.get("success", False):
        raise typer.Exit(code=1)


@app.command("report")
def cmd_report(
    target: Path = typer.Argument(Path("."), help="Ruta al archivo .c o directorio del proyecto a verificar."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
) -> None:
    """Genera directamente la sección de reporte Markdown de RIPLEY para Dredd."""
    from ripley.core.engine import analyze_target
    if not target.exists():
        console.print(f"[bold red]Ruta inexistente: {target}[/bold red]")
        raise typer.Exit(code=1)
    result = analyze_target(target)
    md_content = generar_seccion_markdown(result)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


@app.command("badge")
def cmd_badge(
    target: Path = typer.Argument(Path("."), help="Ruta al archivo .c o directorio del proyecto a evaluar."),
    output: Path = typer.Option(Path("ripley_badge.svg"), "--output", "-o", help="Ruta de destino del archivo SVG."),
    label: str = typer.Option("ripley", "--label", "-l", help="Etiqueta izquierda del badge SVG."),
) -> None:
    """Genera un badge SVG con la calificación pedagógica del estudiante."""
    from ripley.core.engine import analyze_target
    from ripley.core.badge import calcular_puntaje_calidad, generar_badge_svg

    if not target.exists():
        console.print(f"[bold red]Ruta inexistente: {target}[/bold red]")
        raise typer.Exit(code=1)

    result = analyze_target(target)
    score = calcular_puntaje_calidad(result)
    svg_content = generar_badge_svg(score, label=label)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg_content, encoding="utf-8")
    console.print(f"[bold green]✓ Badge SVG generado:[/bold green] [cyan]{output}[/cyan] (Puntaje: [yellow]{score}/10[/yellow])")


@app.command("lsp")
def cmd_lsp() -> None:
    """Inicia el servidor Language Server Protocol (LSP) de Ripley en stdio."""
    from ripley.core.lsp_server import run_lsp_server_stdio
    run_lsp_server_stdio()


@app.command("fix-interactive")
def cmd_fix_interactive(
    source: Path = typer.Argument(..., help="Archivo .c a corregir interactivamente."),
    auto_apply: bool = typer.Option(True, "--auto", "-y", help="Aplicar correcciones sin confirmación manual."),
) -> None:
    """Aplica auto-correcciones pedagógicas para vicios comunes de C."""
    from ripley.core.autofix import aplicar_autofix_interactivo

    if not source.exists():
        console.print(f"[bold red]Archivo no encontrado: {source}[/bold red]")
        raise typer.Exit(code=1)

    aplicar_autofix_interactivo(source, auto_apply=auto_apply, console=console)


@app.command("style-check")
def cmd_style_check(
    sources: List[Path] = typer.Argument(..., help="Archivos .c/.h a auditar contra el estándar de cátedra."),
) -> None:
    """Verifica la conformidad del código con el estándar estilístico oficial de la cátedra."""
    from ripley.core.style_compliance import auditar_conformidad_estilo

    valid_sources = [Path(s) for s in sources if Path(s).exists()]
    if not valid_sources:
        console.print("[bold red]No se encontraron archivos válidos para auditar.[/bold red]")
        raise typer.Exit(code=1)

    auditar_conformidad_estilo(valid_sources, console=console)


@app.command("history")
def cmd_history(
    target: Path = typer.Argument(Path("."), help="Directorio raíz del proyecto estudiantil."),
) -> None:
    """Muestra el historial de evolución de corrección de errores del alumno."""
    from ripley.core.history import mostrar_historial_progreso

    mostrar_historial_progreso(target, console=console)
