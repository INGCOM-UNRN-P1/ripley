"""Ripley student CLI (ripley-check): self-service verification without teacher tooling.

Este módulo vive en la zona estudiante: NO debe importar ripley.teacher ni
dependencias del flujo docente (ver tests/unit/test_layer_boundaries.py).
"""

import json
import tempfile
from pathlib import Path
from typing import List, Optional

import typer
from rich.table import Table

from ripley import __version__
from ripley.cli._common import console


app = typer.Typer(
    name="ripley-check",
    help="Verificación temprana de entregas C desde la computadora del estudiante.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ripley-check {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de ripley-check y finaliza.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


checks_app = typer.Typer(name="checks", help="Catálogo unificado de verificaciones.", no_args_is_help=True)
app.add_typer(checks_app, name="checks")


# ============================================================================
# Registro de checks y diagnóstico del entorno
# ============================================================================


@checks_app.command("list")
def checks_list(
    scope: str = typer.Option("student", "--scope", "-s", help="Filtrar por scope: student | teacher | both | all."),
) -> None:
    """Lista el catálogo unificado de verificaciones disponibles."""
    from ripley.pipeline.availability import available_map
    from ripley.pipeline.registry import all_checks

    tools = available_map()
    table = Table(title="Catálogo de Verificaciones de Ripley")
    table.add_column("Check ID", style="cyan")
    table.add_column("Capa")
    table.add_column("Scope")
    table.add_column("Herramientas", style="dim")
    table.add_column("Estado")
    for spec in all_checks():
        if scope != "all" and spec.scope != scope:
            continue
        missing = [t for t in spec.requires_tools if not tools.get(t)]
        estado = "[green]lista[/green]" if not missing else f"[yellow]omite: falta {', '.join(missing)}[/yellow]"
        table.add_row(spec.check_id, spec.layer, spec.scope, ", ".join(spec.requires_tools) or "-", estado)
    console.print(table)


@app.command("doctor")
def doctor() -> None:
    """Diagnóstico del entorno: herramientas externas presentes y checks afectados."""
    from ripley.pipeline.availability import probe_all
    from ripley.pipeline.registry import is_runnable, iter_student

    statuses = probe_all()
    tools = {s.name: s.available for s in statuses}
    table = Table(title="Disponibilidad de Herramientas Externas")
    table.add_column("Herramienta", style="cyan")
    table.add_column("Estado")
    table.add_column("Impacto si falta", style="dim")
    for s in statuses:
        estado = "[green]disponible[/green]" if s.available else "[red]falta[/red]"
        table.add_row(s.name, estado, s.description)
    console.print(table)

    omitidos = [s.check_id for s in iter_student() if not is_runnable(s, tools)]
    if omitidos:
        console.print(f"\n[yellow]Checks estudiantiles que se omitirán: {', '.join(omitidos)}[/yellow]")
    else:
        console.print("\n[green]Todos los checks estudiantiles son ejecutables en este entorno.[/green]")



# ============================================================================
# Verificación temprana contra paquetes de práctica
# ============================================================================


@app.command("run")
def cmd_run(
    sources: List[Path] = typer.Argument(..., help="Archivos .c del estudiante a verificar."),
    practica: str = typer.Option(..., "--practica", "-p", help="Ruta al paquete .ripkg de la práctica."),
    strict: bool = typer.Option(False, "--strict", help="Salir con código 1 si hay hallazgos, no solo errores."),
    verify_signature: bool = typer.Option(False, "--verify-signature", help="Exigir firma GPG válida del paquete."),
) -> None:
    """Verificación temprana completa: compila, corre testcases públicos y aplica los checks del manifiesto."""
    from ripley.pipeline.bundle import BundleError
    from ripley.pipeline.student_runner import run_bundle

    for s in sources:
        if not Path(s).exists():
            console.print(f"[bold red]Fuente no encontrada: {s}[/bold red]")
            raise typer.Exit(code=1)

    try:
        report = run_bundle(Path(practica), [Path(s) for s in sources], verify_signature=verify_signature)
    except BundleError as e:
        console.print(f"[bold red]Paquete inválido: {e}[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Verificación temprana — {report.practica}[/bold]")
    estado = "[green]OK[/green]" if report.compiled_ok else "[red]FALLÓ[/red]"
    console.print(f"  Compilación      : {estado}")
    if not report.compiled_ok:
        console.print(f"  [dim]{report.compile_errors[:600]}[/dim]")
    if report.tests_total:
        color = "green" if report.tests_passed == report.tests_total else "red"
        console.print(f"  Testcases públicos: [{color}]{report.tests_passed}/{report.tests_total}[/{color}]")
    else:
        console.print("  Testcases públicos: ninguno incluido en el paquete")

    for check_id, obs in report.findings.items():
        if not obs:
            console.print(f"  {check_id}: [green]sin hallazgos[/green]")
            continue
        errores = sum(1 for o in obs if o["severidad"] == "ERROR")
        color = "red" if errores else "yellow"
        console.print(f"  {check_id}: [{color}]{len(obs)} hallazgos ({errores} ERROR)[/{color}]")
        for o in obs[:5]:
            console.print(f"    · {o['archivo']}:{o['linea']} {o['mensaje'][:100]}")

    if report.omitted:
        console.print(f"  [dim]Omitidos por falta de herramientas: {', '.join(report.omitted)}[/dim]")
    if report.signature_verified:
        console.print("  Firma GPG verificada.")

    exito = report.success and (not strict or report.total_findings == 0)
    if exito:
        console.print("\n[bold green]✓ Listo para entregar.[/bold green]\n")
    else:
        console.print("\n[bold yellow]⚠ Revisá los puntos anteriores antes de entregar.[/bold yellow]\n")
        raise typer.Exit(code=1)




def generar_seccion_markdown(result) -> str:
    """Genera sección de auditoría estática, reglas P1 y compilación de Ripley para Dredd."""
    lines = ["<!-- dredd-section: ripley v1.0.0 -->\n## Evaluación Pedagógica Integral (Ripley)\n"]
    comp_ok = result.compilation.get("success", False)
    estado_comp = "✓ Compilación Exitosa" if comp_ok else "❌ Falló Compilación"
    lines.append(f"- **Compilación GCC:** {estado_comp}")
    lines.append(f"- **Hallazgos de estilo y AST:** {len(result.ast_findings)}")
    tests_tot = result.tests.get("total", 0)
    if tests_tot > 0:
        lines.append(f"- **Pruebas automáticas:** {result.tests.get('passed', 0)}/{tests_tot} pasadas")
    lines.append("")

    if not result.ast_findings and comp_ok:
        lines.append("> [!TIP]\n> **Excelente Calidad:** El código cumple con todas las reglas P1 y estándares arquitectónicos sin observaciones.\n")
    elif result.ast_findings:
        lines.append("> [!WARNING]\n> **Observaciones Pedagógicas y Reglas P1:**\n")
        lines.append("| Ubicación | Regla | Severidad | Mensaje / Sugerencia |")
        lines.append("| :--- | :---: | :---: | :--- |")
        for f in result.ast_findings:
            loc = f"`{Path(f.get('file', '')).name}:{f.get('line', '')}`".replace("|", "\\|")
            sug = f" — *Sugerencia:* {f.get('suggestion')}".replace("|", "\\|") if f.get("suggestion") else ""
            rule_id = str(f.get("rule_id", "")).replace("|", "\\|")
            sev = str(f.get("severity", "WARN")).replace("|", "\\|")
            msg = str(f.get("message", "")).replace("|", "\\|")
            lines.append(f"| {loc} | `{rule_id}` | **{sev}** | {msg}{sug} |")
        lines.append("")
    return "\n".join(lines)


@app.command("check")
def cmd_check(
    target: Path = typer.Argument(Path("."), help="Ruta al archivo .c o directorio del proyecto a verificar."),
    strict: bool = typer.Option(False, "--strict", help="Salir con código de error si se detectan advertencias."),
    output_format: str = typer.Option("rich", "--format", help="Formato de salida: 'rich' (consola interactiva), 'json' o 'sarif'."),
    socratic: bool = typer.Option(False, "--socratic", "-s", help="Modo tutor socrático: muestra pistas conceptuales progresivas en vez de soluciones directas."),
    bench: Optional[str] = typer.Option(None, "--bench", help="complexity-bench: cota esperada (O(1), O(n), O(n log n), O(n^2))."),
    bench_pattern: str = typer.Option("{n}\\n", "--bench-pattern", help="Entrada por tamaño; '{n}' se reemplaza por N."),
    strict_ub: bool = typer.Option(False, "--strict-ub", help="ub-sentinel: auditoría de comportamiento indefinido tras compilar."),
    ub_level: int = typer.Option(2, "--ub-level", min=1, max=4, help="Nivel máximo del pipeline ub-sentinel (1=sanitizers, 2=+clang-analyzer, 3=+Frama-C, 4=+TSan)."),
    ub_timeout: int = typer.Option(30, "--ub-timeout", help="Timeout en segundos por testcase del ub-sentinel."),
    html: Optional[Path] = typer.Option(None, "--html", help="Generar informe interactivo HTML con badges de cátedra."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
    profile: str = typer.Option("strict", "--profile", "-p", help="Perfil de rigurosidad: 'strict', 'relaxed' o 'exam'."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Modo silencioso sin volcado a consola (para pre-commit hooks)."),
    exit_zero: bool = typer.Option(False, "--exit-zero", help="Forzar código de salida 0 incluso ante advertencias o fallas."),
    as_json: bool = typer.Option(False, "--json", help="Alias para emitir reporte en formato JSON (--format json)."),
) -> None:
    """Verificación unificada y pedagógica de código C: AST, reglas P1, compilación y AddressSanitizer."""
    from ripley.core.engine import analyze_target

    if as_json:
        output_format = "json"

    if not target.exists():
        if not quiet:
            console.print(f"[bold red]Ruta inexistente: {target}[/bold red]")
        raise typer.Exit(code=0 if exit_zero else 1)

    result = analyze_target(target)

    if output_md:
        md_text = generar_seccion_markdown(result)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        if not quiet:
            console.print(f"[green]✓ Sección Markdown generada en:[/green] [cyan]{output_md}[/cyan]")
        raise typer.Exit(code=0 if (exit_zero or result.compilation.get("success", False)) else 1)

    if output_format.lower() == "sarif":
        from ripley.core.sarif import exportar_sarif
        sarif_data = exportar_sarif(result)
        print(json.dumps(sarif_data, indent=2, ensure_ascii=False))
        if strict and (not result.compilation.get("success", False) or result.metrics.get("ast_findings_count", 0) > 0) and not exit_zero:
            raise typer.Exit(code=1)
        return

    if output_format.lower() == "json":
        print(result.to_json())
        if (not result.compilation.get("success", False) or (strict and result.metrics.get("ast_findings_count", 0) > 0)) and not exit_zero:
            raise typer.Exit(code=1)
        return

    comp = result.compilation
    findings = result.ast_findings
    tests = result.tests

    # Visualización Rich
    if not quiet:
        console.print(f"\n[bold cyan]─── Verificación Ripley: {target.name} ───[/bold cyan]\n")

        # 1. Compilación
        if comp.get("success"):
            console.print("  [bold green]✓ Compilación GCC / Clang:[/bold green] Exitosa sin errores bloqueantes.")
        else:
            console.print("  [bold red]✗ Fallo de Compilación:[/bold red]")
            if comp.get("human_summary"):
                console.print(f"    [yellow]{comp['human_summary']}[/yellow]")
            for d in comp.get("translated_diagnostics", []):
                console.print(f"    · [bold]{d.get('file')}:{d.get('line')}[/bold] [{d.get('severity')}] {d.get('translated_message')}")
                if d.get("suggestion"):
                    console.print(f"      [dim]💡 {d.get('suggestion')}[/dim]")
            if comp.get("raw_stderr") and not comp.get("translated_diagnostics"):
                console.print(f"    [dim]{comp['raw_stderr'][:400]}[/dim]")

        # 2. Reglas AST y Calidad
        if findings:
            table = Table(title="Hallazgos de Calidad, Reglas P1 y AST")
            table.add_column("Archivo:Línea", style="cyan", justify="left")
            table.add_column("Regla", style="bold")
            table.add_column("Severidad", justify="center")
            table.add_column("Diagnóstico y Sugerencia Pedagógica")

            for f in findings:
                sev = f.get("severity", "ADVERTENCIA")
                color = "red" if sev == "ERROR" else ("yellow" if "WARN" in sev or "ADV" in sev else "blue")
                msg = f"{f.get('message')}\n[dim]💡 {f.get('suggestion')}[/dim]" if f.get("suggestion") else f.get("message")
                table.add_row(
                    f"{f.get('file')}:{f.get('line')}",
                    f.get("rule_id"),
                    f"[{color}]{sev}[/{color}]",
                    msg,
                )
            console.print("\n")
            console.print(table)
        else:
            console.print("  [bold green]✓ Reglas de Estilo y AST:[/bold green] Sin observaciones.")

        # 3. Pruebas y Memoria
        if tests.get("total", 0) > 0:
            passed = tests.get("passed", 0)
            total = tests.get("total", 0)
            color = "green" if passed == total else "red"
            console.print(f"\n  [bold]Pruebas Funcionales:[/bold] [{color}]{passed}/{total} aprobadas[/{color}]")
            for tc in tests.get("cases", []):
                status = "[green]PASÓ[/green]" if tc.get("passed") else "[red]FALLÓ[/red]"
                leak = " [bold red][Fuga de Memoria][/bold red]" if tc.get("memory_leak") else ""
                console.print(f"    · {tc.get('name')}: {status}{leak}")
                if not tc.get("passed") and tc.get("sanitizer_error"):
                    console.print(f"      [dim red]{tc.get('sanitizer_error')[:300]}[/dim red]")

        # 3.b ub-sentinel: comportamiento indefinido (opcional)
        if strict_ub:
            from ripley.core.ub_sentinel import auditar_ub

            base_ub = target if target.is_dir() else target.parent
            fuentes_ub = [base_ub / rel for rel in result.c_files]
            casos = sorted((base_ub / "tests").glob("caso_*.in")) if (base_ub / "tests").is_dir() else []
            reporte_ub = auditar_ub(fuentes_ub, casos, nivel_maximo=ub_level, timeout=ub_timeout)
            console.print(f"\n[bold]ub-sentinel[/bold] — {reporte_ub.resumen()}")
            for h in reporte_ub.hallazgos:
                sev_color = "red" if h.severidad == "ERROR" else "yellow"
                donde = f"{h.archivo}:{h.linea}" if h.linea else str(h.archivo)
                console.print(f"  [{sev_color}]N{h.nivel}·{h.categoria}[/{sev_color}] {donde}: {h.mensaje}")
                if h.sugerencia:
                    console.print(f"    [dim]💡 {h.sugerencia}[/dim]")
            if not reporte_ub.hallazgos and not reporte_ub.omitidos:
                console.print("  [green]✓ Sin comportamiento indefinido detectado.[/green]")
            if reporte_ub.hay_errores:
                result.metrics["ast_errors_count"] = result.metrics.get("ast_errors_count", 0) + len(reporte_ub.errores)

        # 4. complexity-bench: verificar cota asintótica exigida (opcional)
        if bench:
            if not comp.get("success"):
                console.print("[yellow]--bench omitido: el proyecto no compila.[/yellow]")
            else:
                from ripley.core.bench import compilar_optimizado, normalizar_cota, verificar_cota

                base = target if target.is_dir() else target.parent
                fuentes = [base / rel for rel in result.c_files]
                bin_bench = Path(tempfile.mkdtemp(prefix="ripley_bench_")) / "bench.bin"
                ok_compile, err = compilar_optimizado(fuentes, bin_bench, include_dirs=[base])
                if not ok_compile:
                    console.print(f"[red]complexity-bench: no se pudo compilar optimizado:[/red] {err}")
                    raise typer.Exit(code=1)
                ok_cota, resumen = verificar_cota(bin_bench, bench, patron_entrada=bench_pattern)
                console.print(f"\n[bold]complexity-bench[/bold] ({normalizar_cota(bench)}): {resumen}")
                if ok_cota is False:
                    console.print("[bold red]✗ El algoritmo excede la cota exigida por la consigna.[/bold red]")
                    raise typer.Exit(code=1)
                if ok_cota is None:
                    console.print("[yellow]⚠ Medición inconclusa: no se penaliza esta vez.[/yellow]")
                else:
                    console.print("[green]✓ La complejidad empírica respeta la cota exigida.[/green]")

    # Generación de informe HTML opcional
    if html:
        from ripley.core.html_reporter import generate_interactive_html_report
        eval_data = {
            "student": target.name,
            "activity": "Verificación Ripley",
            "passed": comp.get("success", False) and result.metrics.get("ast_errors_count", 0) == 0,
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
        if not quiet:
            console.print(f"  [bold green]✓ Reporte HTML interactivo generado en:[/bold green] [cyan]{html}[/cyan]")

    # Veredicto final
    has_errors = not comp.get("success", False) or (profile != "relaxed" and (result.metrics.get("ast_errors_count", 0) > 0 or tests.get("failed", 0) > 0))
    if profile == "exam":
        has_errors = has_errors or result.metrics.get("ast_findings_count", 0) > 0

    if has_errors:
        if not quiet:
            console.print("\n[bold red]✗ Se encontraron errores o violaciones que impiden la entrega.[/bold red]\n")
        raise typer.Exit(code=0 if exit_zero else 1)
    elif (strict or profile == "exam") and result.metrics.get("ast_findings_count", 0) > 0:
        if not quiet:
            console.print("\n[bold yellow]⚠ Modo estricto: Existen advertencias pendientes de corrección.[/bold yellow]\n")
        raise typer.Exit(code=0 if exit_zero else 1)
    else:
        if not quiet:
            console.print("\n[bold green]✓ Proyecto verificado con éxito y listo para entregar.[/bold green]\n")


# Registro de comandos y re-exports (deben ir tras definir los objetos compartidos)
from ripley.cli.student_show import cmd_show_ripkg, cmd_watch  # noqa: E402,F401
from ripley.cli.student_plugins import plugins_app  # noqa: E402,F401
from ripley.cli.student_extra import cmd_explain  # noqa: E402,F401
