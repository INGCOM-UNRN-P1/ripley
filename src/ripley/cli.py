"""Ripley CLI interface."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table


from ripley.config import load_config
from ripley.evaluate import Evaluator
from ripley.exporter import MoodleExporter
from ripley.ingest import MoodleIngestor
from ripley.mapping import InteractiveMapper
from ripley.practice import (
    ExerciseTemplateSpec,
    PracticeSpec,
    init_practice,
    list_practices,
    sync_practice_testcases,
)
from ripley.templates import check_templates, init_templates, list_templates
from ripley.testcases import (
    check_testcases_integrity,
    create_testcase_skeleton,
    discover_testcases,
)

app = typer.Typer(
    name="ripley",
    help="CLI para procesar, compilar, probar y evaluar entregas de C descargadas de Moodle.",
    no_args_is_help=True,
)
template_app = typer.Typer(
    name="template",
    help="Gestión y verificación de plantillas Markdown Jinja2.",
    no_args_is_help=True,
)
testcase_app = typer.Typer(
    name="testcase",
    help="Gestión y esqueletos de casos de prueba.",
    no_args_is_help=True,
)
practice_app = typer.Typer(
    name="practice",
    help="Gestión, enunciados, casos de prueba y configuración de prácticas en ./practicas.",
    no_args_is_help=True,
)

app.add_typer(template_app, name="template")
app.add_typer(testcase_app, name="testcase")
app.add_typer(practice_app, name="practice")
app.add_typer(practice_app, name="practica")

console = Console()




@app.command("ingest")
def cmd_ingest(
    zip_path: str = typer.Argument(..., help="Ruta al archivo ZIP de Moodle."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Simula la extracción y sanitización sin escribir en disco.",
    ),
    workspace: str = typer.Option(
        ".",
        "--workspace",
        "-w",
        help="Directorio raíz del workspace donde se almacenarán las actividades.",
    ),
) -> None:
    """Procesa e ingesta un archivo ZIP de entregas descargado de Moodle."""
    ingestor = MoodleIngestor(workspace_dir=workspace)
    try:
        moodle_info, results = ingestor.process_zip(zip_path, dry_run=dry_run)
    except Exception as e:
        console.print(f"[bold red]Error durante la ingesta:[/bold red] {e}")
        raise typer.Exit(code=1)

    mode_str = "[bold yellow](DRY-RUN)[/bold yellow] " if dry_run else ""
    console.print(
        f"\n{mode_str}[bold green]Actividad procesada:[/bold green] {moodle_info.activity_name} (ID: {moodle_info.activity_id}) -> [cyan]{moodle_info.activity_slug}/[/cyan]\n"
    )

    table = Table(title="Resumen de Entregas Procesadas")
    table.add_column("Estudiante", style="bold")
    table.add_column("Slug", style="dim")
    table.add_column("Revisión", justify="center")
    table.add_column("Fuentes .c/.h", justify="center")
    table.add_column("Archivos Ignorados", justify="center")
    table.add_column("Estado", style="bold")

    for res in results:
        status_str = (
            f"[green]Nueva (r{res.version_created})[/green]"
            if res.is_new_revision
            else "[blue]Sin cambios[/blue]"
        )
        table.add_row(
            res.student_name,
            res.student_slug,
            f"r{res.version_created}" if res.version_created else "-",
            str(len(res.sources)),
            str(len(res.ignored)),
            status_str,
        )

    console.print(table)



@template_app.command("init")
def cmd_template_init(
    path: Optional[str] = typer.Option(
        None,
        "--path",
        "-p",
        help="Ruta al directorio de plantillas (por defecto se lee de ripley.toml).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Sobrescribir plantillas existentes.",
    ),
) -> None:
    """Genera o restaura las plantillas Jinja2 por defecto."""
    cfg = load_config()
    target_dir = path or cfg.templates.ruta_plantillas
    created = init_templates(target_dir=target_dir, force=force)
    if created:
        console.print(
            f"[bold green]Plantillas inicializadas exitosamente en '{target_dir}':[/bold green]"
        )
        for p in created:
            console.print(f" - [cyan]{p.name}[/cyan]")
    else:
        console.print(
            f"[yellow]No se crearon plantillas nuevas en '{target_dir}'. Usá --force para sobrescribir existentes.[/yellow]"
        )


@template_app.command("skeleton")
def cmd_template_skeleton(
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Directorio de destino."),
    force: bool = typer.Option(False, "--force", "-f", help="Sobrescribir existentes."),
) -> None:
    """Alias de 'template init' para generar el esqueleto de plantillas."""
    cmd_template_init(path=path, force=force)


@template_app.command("list")
def cmd_template_list(
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Directorio de plantillas.")
) -> None:
    """Lista las plantillas requeridas e indica su disponibilidad."""
    cfg = load_config()
    target_dir = path or cfg.templates.ruta_plantillas
    status = list_templates(target_dir)

    table = Table(title=f"Plantillas Jinja2 en '{target_dir}'")
    table.add_column("Plantilla Requerida", style="bold")
    table.add_column("Estado", style="bold")

    for name, exists in status.items():
        state_str = "[green]✓ Presente[/green]" if exists else "[red]✗ Faltante[/red]"
        table.add_row(name, state_str)

    console.print(table)


@template_app.command("check")
def cmd_template_check(
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Directorio de plantillas.")
) -> None:
    """Valida la sintaxis Jinja2 y variables críticas en las plantillas."""
    cfg = load_config()
    target_dir = path or cfg.templates.ruta_plantillas
    is_valid, errors = check_templates(target_dir)

    if is_valid:
        console.print(
            f"[bold green]✓ Todas las plantillas en '{target_dir}' son válidas y cumplen los requisitos.[/bold green]"
        )
    else:
        console.print(
            f"[bold red]✗ Se encontraron {len(errors)} error(es) en las plantillas:[/bold red]"
        )
        for err in errors:
            console.print(f" [red]- {err}[/red]")
        raise typer.Exit(code=1)


@testcase_app.command("skeleton")
def cmd_testcase_skeleton(
    activity: str = typer.Option(..., "--activity", "-a", help="Nombre o slug de la actividad (ej. entrega-1_1228009)."),
    exercise: str = typer.Option(..., "--exercise", "-e", help="Nombre del ejercicio (ej. ejercicio1)."),
    cases: int = typer.Option(2, "--cases", "-c", help="Cantidad de casos de prueba a generar."),
    with_argv: bool = typer.Option(False, "--with-argv", help="Generar archivos .argv de argumentos CLI."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Genera esqueletos de casos de prueba (.in, .out, .argv) para una actividad y ejercicio."""
    created = create_testcase_skeleton(
        workspace_dir=workspace,
        activity_slug=activity,
        exercise=exercise,
        cases_count=cases,
        with_argv=with_argv,
    )
    if created:
        console.print(
            f"[bold green]Se generaron {len(created)} archivos de prueba en 'tests/{activity}/{exercise}/':[/bold green]"
        )
        for p in created:
            console.print(f" - [cyan]{p.name}[/cyan]")
    else:
        console.print("[yellow]Los archivos de prueba ya existían o no se crearon nuevos.[/yellow]")


@testcase_app.command("list")
def cmd_testcase_list(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Lista los casos de prueba asociados a cada ejercicio."""
    exercises = discover_testcases(workspace_dir=workspace, activity_slug=activity)
    if not exercises:
        console.print(f"[yellow]No se encontraron casos de prueba en 'tests/{activity}/'.[/yellow]")
        return

    table = Table(title=f"Casos de Prueba para '{activity}'")
    table.add_column("Ejercicio", style="bold")
    table.add_column("Caso", justify="center")
    table.add_column("Entrada (.in)", justify="center")
    table.add_column("Salida (.out)", justify="center")
    table.add_column("CLI Args (.argv)", justify="center")

    for ex_name, cases in exercises.items():
        for tc in cases:
            in_str = "[green]✓[/green]" if tc.in_file else "[red]✗[/red]"
            out_str = "[green]✓[/green]" if tc.out_file else "[red]✗[/red]"
            argv_str = "[cyan]✓[/cyan]" if tc.argv_file else "[dim]-[/dim]"
            table.add_row(ex_name, tc.case_name, in_str, out_str, argv_str)

    console.print(table)


@testcase_app.command("check")
def cmd_testcase_check(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Valida la integridad de parejas .in / .out en los casos de prueba."""
    is_valid, errors = check_testcases_integrity(workspace_dir=workspace, activity_slug=activity)
    if is_valid:
        console.print(
            f"[bold green]✓ Todos los casos de prueba para '{activity}' son íntegros y válidos.[/bold green]"
        )
    else:
        console.print(
            f"[bold red]✗ Se encontraron {len(errors)} error(es) en los casos de prueba de '{activity}':[/bold red]"
        )
        for err in errors:
            console.print(f" [red]- {err}[/red]")
        raise typer.Exit(code=1)


@testcase_app.command("map")
@app.command("map")
def cmd_testcase_map(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad (ej. entrega-1_1228009)."),
    unmapped_only: bool = typer.Option(
        False,
        "--unmapped-only",
        "-u",
        help="Revisar únicamente los archivos que no pudieron ser conectados automáticamente.",
    ),
    all_files: bool = typer.Option(
        False,
        "--all",
        help="Revisar todos los archivos (conectados y no conectados).",
    ),
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Aplica automáticamente las coincidencias heurísticas no ambiguas.",
    ),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Herramienta interactiva para revisar el mapeo de archivos fuente (.c) a testcases."""
    # Descubrir ejercicios existentes
    exercises = discover_testcases(workspace_dir=workspace, activity_slug=activity)
    available_exercises = list(exercises.keys())

    mapper = InteractiveMapper(
        workspace_dir=workspace,
        activity_slug=activity,
        console=console,
    )

    # Por defecto, si no se especifica --all, se revisan los no mapeados
    review_unmapped = not all_files if not unmapped_only else True

    try:
        changes = mapper.run_interactive_session(
            available_exercises=available_exercises,
            unmapped_only=review_unmapped,
            auto_apply=auto,
        )
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Sesión interactiva cancelada.[/yellow]")
        return


@app.command("evaluate")

def cmd_evaluate(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad a evaluar (ej. entrega-1_1228009)."),
    parallel: bool = typer.Option(True, "--parallel/--no-parallel", help="Procesamiento concurrente."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Ejecuta la compilación, linters, estilo, pruebas y calificación de los estudiantes."""
    cfg = load_config()
    evaluator = Evaluator(config=cfg, workspace_dir=workspace)

    console.print(f"\n[bold green]Iniciando evaluación para la actividad:[/bold green] [cyan]{activity}[/cyan]\n")

    try:
        results = evaluator.evaluate_activity(
            activity_slug=activity,
            parallel=parallel,
        )
    except Exception as e:
        console.print(f"[bold red]Error durante la evaluación:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not results:
        console.print("[yellow]No se encontraron estudiantes para evaluar en la actividad indicada.[/yellow]")
        return

    table = Table(title=f"Resultados de Evaluación - {activity}")
    table.add_column("Estudiante", style="bold")
    table.add_column("Revisión", justify="center")
    table.add_column("Compilación", justify="center")
    table.add_column("Estilo", justify="center")
    table.add_column("Tests I/O", justify="center")
    table.add_column("Nota Estimada", justify="right", style="bold green")

    for res in results:
        comp_str = "[green]OK[/green]" if res.compiled else "[red]FAIL[/red]"
        test_str = f"{res.tests_passed}/{res.total_tests}" if res.compiled else "-"
        table.add_row(
            res.student_slug,
            f"r{res.version_evaluated}",
            comp_str,
            f"{res.style_score:.1f}/10",
            test_str,
            f"{res.preliminary_grade:.2f} / 10",
        )

    console.print(table)
    console.print(f"\n[bold green]✓ Evaluación finalizada exitosamente para {len(results)} estudiantes.[/bold green]\n")


@app.command("export")
def cmd_export(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad a exportar (ej. entrega-1_1228009)."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Exporta las calificaciones para Moodle (CSV), el ZIP masivo de retroalimentación y el dashboard."""
    exporter = MoodleExporter(workspace_dir=workspace)
    try:
        csv_path = exporter.export_grades_csv(activity)
        zip_path = exporter.export_feedback_zip(activity)
        dash_path = exporter.generate_dashboard(activity)

        console.print(f"\n[bold green]Exportación completada exitosamente para '{activity}':[/bold green]\n")
        console.print(f" - [cyan]Libro de Calificaciones CSV:[/cyan] {csv_path.name}")
        console.print(f" - [cyan]ZIP de Retroalimentación:[/cyan] {zip_path.name}")
        console.print(f" - [cyan]Dashboard Consolidado Docente:[/cyan] {dash_path.name}\n")
    except Exception as e:
        console.print(f"[bold red]Error durante la exportación:[/bold red] {e}")
@practice_app.command("init")
def cmd_practice_init(
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Nombre de la práctica (ej. 'Práctica 1 - Punteros y Arreglos').",
    ),
    practice_id: Optional[str] = typer.Option(
        None,
        "--id",
        help="ID interno o de actividad Moodle (ej. '1228009').",
    ),
    exercises: Optional[str] = typer.Option(
        None,
        "--exercises",
        "-e",
        help="Cantidad de ejercicios (ej. 2) o nombres separados por coma (ej. 'ejercicio1,ejercicio2').",
    ),
    cases: int = typer.Option(
        2,
        "--cases",
        "-c",
        help="Cantidad de casos de prueba iniciales por ejercicio.",
    ),
    with_argv: bool = typer.Option(
        False,
        "--with-argv",
        help="Generar archivos .argv en los esqueletos de prueba.",
    ),
    sync_tests: bool = typer.Option(
        True,
        "--sync-tests/--no-sync-tests",
        help="Sincronizar automáticamente los casos de prueba hacia tests/<slug_practica>/.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Sobrescribir si la práctica ya existe.",
    ),
    base_dir: str = typer.Option(
        "practicas",
        "--path",
        "-p",
        help="Directorio base donde se almacenan las prácticas.",
    ),
) -> None:
    """Inicializa una práctica completa con enunciados, corrección, testcases y pautas en ./practicas."""
    # Si no se pasó nombre, solicitarlo interactivamente
    p_name = name or Prompt.ask("Nombre de la práctica", default="Práctica 1 - Introducción a C").strip()
    p_id = practice_id or Prompt.ask("ID de la actividad (opcional)", default="").strip()

    # Procesar ejercicios
    ex_list: List[ExerciseTemplateSpec] = []
    if exercises:
        if exercises.isdigit():
            count = int(exercises)
            for i in range(1, count + 1):
                ex_list.append(
                    ExerciseTemplateSpec(
                        slug=f"ejercicio{i}",
                        title=f"Ejercicio {i}",
                        description=f"Consigna del Ejercicio {i}.",
                        cases_count=cases,
                        with_argv=with_argv,
                    )
                )
        else:
            names = [n.strip() for n in exercises.split(",") if n.strip()]
            for n in names:
                ex_list.append(
                    ExerciseTemplateSpec(
                        slug=n,
                        title=n.capitalize(),
                        description=f"Consigna para {n}.",
                        cases_count=cases,
                        with_argv=with_argv,
                    )
                )
    else:
        # Por defecto 2 ejercicios
        ex_list = [
            ExerciseTemplateSpec(
                slug="ejercicio1",
                title="Ejercicio 1",
                description="Consigna del Ejercicio 1.",
                cases_count=cases,
                with_argv=with_argv,
            ),
            ExerciseTemplateSpec(
                slug="ejercicio2",
                title="Ejercicio 2",
                description="Consigna del Ejercicio 2.",
                cases_count=cases,
                with_argv=with_argv,
            ),
        ]

    spec = PracticeSpec(
        name=p_name,
        practice_id=p_id,
        description=f"Práctica académica de C: {p_name}.",
        exercises=ex_list,
    )

    try:
        p_dir = init_practice(
            spec=spec,
            base_dir=base_dir,
            workspace_tests_dir="." if sync_tests else None,
            force=force,
        )
        console.print(f"\n[bold green]✓ Práctica inicializada exitosamente en:[/bold green] [cyan]{p_dir}[/cyan]\n")
        console.print(f" - [bold]Enunciado general:[/bold] {p_dir}/enunciado.md")
        console.print(f" - [bold]Pautas de evaluación:[/bold] {p_dir}/pautas_evaluacion.md")
        console.print(f" - [bold]Configuración de corrección:[/bold] {p_dir}/ripley.toml")
        console.print(f" - [bold]Ejercicios generados ({len(ex_list)}):[/bold]")
        for ex in ex_list:
            console.print(f"   * [cyan]{ex.slug}[/cyan] (enunciado, solucion_modelo.c, {cases} testcases)")

        if sync_tests:
            console.print(f"\n[green]✓ Casos de prueba sincronizados en 'tests/{spec.slug}/'.[/green]\n")
    except Exception as e:
        console.print(f"[bold red]Error al inicializar la práctica:[/bold red] {e}")
        raise typer.Exit(code=1)


@practice_app.command("list")
def cmd_practice_list(
    base_dir: str = typer.Option("practicas", "--path", "-p", help="Directorio base de prácticas."),
) -> None:
    """Lista las prácticas configuradas en ./practicas/."""
    practices = list_practices(base_dir)
    if not practices:
        console.print(f"[yellow]No se encontraron prácticas en '{base_dir}/'. Usá './ripley practice init' para crear una.[/yellow]")
        return

    table = Table(title=f"Prácticas en '{base_dir}/'")
    table.add_column("Slug / Directorio", style="bold cyan")
    table.add_column("Ejercicios", justify="center")
    table.add_column("Enunciado", justify="center")
    table.add_column("Pautas Eval", justify="center")
    table.add_column("Config TOML", justify="center")

    for p in practices:
        enun_str = "[green]✓[/green]" if p["has_enunciado"] else "[red]✗[/red]"
        paut_str = "[green]✓[/green]" if p["has_pautas"] else "[red]✗[/red]"
        cfg_str = "[green]✓[/green]" if p["has_config"] else "[red]✗[/red]"
        table.add_row(
            p["slug"],
            f"{p['exercises_count']} ({', '.join(p['exercises']) or '-'})",
            enun_str,
            paut_str,
            cfg_str,
        )

    console.print(table)


@practice_app.command("sync")
def cmd_practice_sync(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la práctica en ./practicas/."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
    base_dir: str = typer.Option("practicas", "--path", "-p", help="Directorio de prácticas."),
) -> None:
    """Sincroniza los casos de prueba desde ./practicas/<activity>/ a tests/<activity>/."""
    p_dir = Path(base_dir) / activity
    if not p_dir.exists():
        console.print(f"[bold red]La práctica '{activity}' no existe en '{base_dir}'.[/bold red]")
        raise typer.Exit(code=1)

    copied = sync_practice_testcases(practice_dir=p_dir, workspace_dir=workspace)
    console.print(f"[bold green]✓ Se sincronizaron {copied} archivos de prueba hacia 'tests/{activity}/'.[/bold green]")


if __name__ == "__main__":
    app()




