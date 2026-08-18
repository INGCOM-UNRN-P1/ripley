"""Ripley CLI interface."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table


from ripley.ast_auditors import (
    BackwardGotoLinter,
    ConstCorrectnessLinter,
    DanglingStackPointerLinter,
    DeepFreeLinter,
    EvaluationOrderLinter,
    FloatComparisonLinter,
    IWYULinter,
    OverengineeringLinter,
    ShortCircuitLinter,
    StringLiteralWriteLinter,
    StringNullPointerLinter,
    VariableShadowingLinter,
)
from ripley.callgraph import CallGraphGenerator
from ripley.config import load_config
from ripley.doxygen import DoxygenAuditor
from ripley.embedded import EmbeddedMemoryRunner
from ripley.evaluate import Evaluator
from ripley.exporter import MoodleExporter
from ripley.flowchart import FlowchartGenerator
from ripley.fuzzing import Fuzzer
from ripley.heap_simulator import HeapMemorySimulator
from ripley.ingest import MoodleIngestor
from ripley.linters import DeadCodeLinter, InternalCloneLinter, MagicNumberLinter, NamingConventionLinter
from ripley.mapping import InteractiveMapper
from ripley.memory_visualizer import DynamicMemoryVisualizer
from ripley.mocks import MockGenerator
from ripley.p1_rules import P1RuleChecker
from ripley.plagiarism import PlagiarismDetector
from ripley.pure_functions import PureFunctionAnalyzer



from ripley.practice import (
    ExerciseTemplateSpec,
    PracticeSpec,
    init_practice,
    list_practices,
    sync_practice_testcases,
)
from ripley.property_testing import PropertyTestRunner
from ripley.sanitizers import SanitizerAnalyzer
from ripley.semantic_diff import SemanticDiffer
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
practica_app = typer.Typer(
    name="practica",
    help="Gestión, enunciados, casos de prueba y configuración de prácticas en ./practicas.",
    no_args_is_help=True,
)
mock_app = typer.Typer(
    name="mock",
    help="Generador y gestor de arneses y funciones simuladas (mocks) en C.",
    no_args_is_help=True,
)

app.add_typer(template_app, name="template")
app.add_typer(testcase_app, name="testcase")
app.add_typer(practica_app, name="practica")
app.add_typer(mock_app, name="mock")


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


@testcase_app.command("fuzz")
def cmd_testcase_fuzz(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad (ej. entrega-1_1228009)."),
    exercise: str = typer.Option(..., "--exercise", "-e", help="Nombre del ejercicio (ej. ejercicio1)."),
    cases: int = typer.Option(4, "--cases", "-c", help="Cantidad de casos de borde a generar por fuzzing."),
    solution: Optional[str] = typer.Option(
        None,
        "--solution",
        "-s",
        help="Ruta al código C o binario de solución de referencia docente para generar las salidas esperadas (.out).",
    ),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Genera automáticamente casos de prueba de borde y entradas fuzzed."""
    target_dir = Path(workspace) / "tests" / activity / exercise
    fuzzer = Fuzzer()

    # Si no se pasó solución pero existe en practicas/<activity>/ejercicios/<exercise>/solucion_modelo.c
    ref_path = Path(solution) if solution else Path(workspace) / "practicas" / activity / "ejercicios" / exercise / "solucion_modelo.c"
    ref_to_use = ref_path if ref_path.exists() else None

    # Detectar el índice de inicio
    existing = list(target_dir.glob("caso*.in")) if target_dir.exists() else []
    start_idx = len(existing) + 1

    try:
        pairs = fuzzer.generate_testcases(
            target_dir=target_dir,
            cases_count=cases,
            reference_source_or_binary=ref_to_use,
            start_index=start_idx,
        )
        console.print(
            f"\n[bold green]✓ Se generaron {len(pairs)} casos de prueba por fuzzing en 'tests/{activity}/{exercise}/':[/bold green]\n"
        )
        for in_f, out_f in pairs:
            console.print(f" - [cyan]{in_f.name}[/cyan] / [cyan]{out_f.name}[/cyan]")
        if ref_to_use:
            console.print(f"\n[green]Salidas esperadas (.out) calculadas automáticamente con la solución modelo: '{ref_to_use}'[/green]\n")
    except Exception as e:
        console.print(f"[bold red]Error durante el fuzzing de casos de prueba:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("plagiarism")
def cmd_plagiarism(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad a analizar."),
    threshold: float = typer.Option(
        0.70,
        "--threshold",
        "-t",
        help="Umbral de similitud mínima para sospecha de plagio (0.0 a 1.0).",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Archivo donde guardar el informe de plagio (por defecto <actividad>/plagiarism_report.md).",
    ),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Analiza la similitud estructural de código y sospechas de plagio entre entregas de la cohorte."""
    act_dir = Path(workspace) / activity
    if not act_dir.exists():
        console.print(f"[bold red]Directorio de actividad no encontrado: '{act_dir}'[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold green]Analizando similitud de código para la actividad:[/bold green] [cyan]{activity}[/cyan] (Umbral: {int(threshold * 100)}%)\n")
    detector = PlagiarismDetector(threshold=threshold)
    matches = detector.analyze_activity(act_dir, threshold=threshold)

    if not matches:
        console.print(f"[bold green]✓ No se detectaron pares de estudiantes con similitud superior al {int(threshold * 100)}%.[/bold green]\n")
    else:
        table = Table(title=f"Sospechas de Similitud / Plagio ({activity})")
        table.add_column("Estudiante A", style="bold")
        table.add_column("Estudiante B", style="bold")
        table.add_column("Similitud", justify="right", style="bold red")
        table.add_column("Huellas Compartidas", justify="center")
        table.add_column("Archivos", style="dim")

        for m in matches:
            table.add_row(
                m.student_a,
                m.student_b,
                f"{m.similarity_pct:.1f}%",
                str(m.shared_fingerprints_count),
                ", ".join(m.common_files) or "-",
            )

        console.print(table)

    report_content = detector.generate_report(activity, matches)
    out_path = Path(output) if output else act_dir / "plagiarism_report.md"
    out_path.write_text(report_content, encoding="utf-8")
    console.print(f"\n[bold cyan]Informe guardado en:[/bold cyan] {out_path}\n")


@app.command("evaluate")
def cmd_evaluate(
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad a evaluar (ej. entrega-1_1228009)."),
    parallel: bool = typer.Option(True, "--parallel/--no-parallel", help="Procesamiento concurrente."),
    check_plagiarism: bool = typer.Option(
        False,
        "--check-plagiarism",
        help="Ejecutar análisis de similitud/plagio al finalizar la evaluación.",
    ),
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

    if check_plagiarism:
        cmd_plagiarism(activity=activity, workspace=workspace)



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
@practica_app.command("init")
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


@practica_app.command("list")
def cmd_practice_list(
    base_dir: str = typer.Option("practicas", "--path", "-p", help="Directorio base de prácticas."),
) -> None:
    """Lista las prácticas configuradas en ./practicas/."""
    practices = list_practices(base_dir)
    if not practices:
        console.print(f"[yellow]No se encontraron prácticas en '{base_dir}/'. Usá './ripley practica init' para crear una.[/yellow]")
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


@practica_app.command("sync")
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

    count = sync_practice_testcases(p_dir, workspace)
    console.print(
        f"\n[bold green]✓ Se sincronizaron {count} archivos de casos de prueba hacia tests/{activity}/[/bold green]\n"
    )


@app.command("flowchart")

def cmd_flowchart(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    function: Optional[str] = typer.Option(
        None,
        "--function",
        help="Nombre específico de la función a graficar (por defecto todas las funciones).",
    ),
    output_format: str = typer.Option(
        "mermaid",
        "--format",
        help="Formato de salida del diagrama ('mermaid' o 'dot').",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Ruta donde guardar el archivo generado (ej. flujo.md o flujo.dot).",
    ),
) -> None:
    """Genera diagramas de flujo con la notación tradicional (ISO/ANSI) a partir de código C."""
    generator = FlowchartGenerator()
    try:
        diagrams = generator.generate_for_file(
            c_file_path=file_path,
            target_function=function,
            output_format=output_format,
        )

        if not diagrams:
            console.print(f"[yellow]No se detectaron funciones en '{file_path}'.[/yellow]")
            return

        combined_output = []
        for fname, chart in diagrams.items():
            if output_format == "mermaid":
                combined_output.append(f"### Diagrama de Flujo: `{fname}()`\n\n```mermaid\n{chart}\n```\n")
            else:
                combined_output.append(f"// --- Función {fname} ---\n{chart}\n")

        full_text = "\n".join(combined_output)

        if output:
            out_p = Path(output)
            out_p.write_text(full_text, encoding="utf-8")
            console.print(f"\n[bold green]✓ Diagrama(s) de flujo guardado(s) exitosamente en:[/bold green] [cyan]{out_p}[/cyan]\n")
        else:
            console.print(f"\n[bold green]Diagramas de Flujo Tradicionales ({file_path}):[/bold green]\n")
            for fname, chart in diagrams.items():
                console.print(f"[bold cyan]Función {fname}():[/bold cyan]")
                console.print(f"```{output_format}\n{chart}\n```\n")
    except Exception as e:
        console.print(f"[bold red]Error al generar diagrama de flujo:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("callgraph")
def cmd_callgraph(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    format_type: str = typer.Option("mermaid", "--format", help="Formato de salida ('mermaid' o 'dot')."),
    stdlib: bool = typer.Option(False, "--stdlib", help="Incluir llamadas a funciones de biblioteca estándar."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Archivo donde guardar el callgraph."),
) -> None:
    """Genera el árbol de llamadas (Call Graph) entre funciones C en formato Mermaid o DOT."""
    cg_gen = CallGraphGenerator()
    try:
        graph_text = cg_gen.generate_for_file(
            file_path=file_path,
            output_format=format_type,
            include_stdlib=stdlib,
        )

        if output:
            out_p = Path(output)
            out_p.write_text(graph_text, encoding="utf-8")
            console.print(f"\n[bold green]✓ Árbol de llamadas guardado en:[/bold green] [cyan]{out_p}[/cyan]\n")
        else:
            console.print(f"\n[bold green]Árbol de Llamadas ({file_path}):[/bold green]\n")
            console.print(f"```{format_type}\n{graph_text}\n```\n")
    except Exception as e:
        console.print(f"[bold red]Error al generar callgraph:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("lint")
def cmd_lint(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    magic_numbers: bool = typer.Option(True, "--magic-numbers/--no-magic-numbers", help="Auditar números mágicos."),
    clones: bool = typer.Option(True, "--clones/--no-clones", help="Auditar código duplicado (copy-paste)."),
    naming: bool = typer.Option(True, "--naming/--no-naming", help="Auditar convenciones de nombres."),
    dead_code: bool = typer.Option(True, "--dead-code/--no-dead-code", help="Auditar funciones/código inalcanzable."),
    doxygen: bool = typer.Option(False, "--doxygen/--no-doxygen", help="Auditar completitud de Doxygen."),
    advanced: bool = typer.Option(True, "--advanced/--no-advanced", help="Auditar reglas avanzadas de AST (float, const, short-circuit, deep-free, shadowing, dangling)."),
    p1_rules: bool = typer.Option(True, "--p1-rules/--no-p1-rules", help="Auditar reglas de estilo oficiales de Programación I (0xXXXXh)."),
) -> None:
    """Ejecuta análisis de números mágicos, código duplicado, convenciones, código muerto y reglas de estilo P1 (0xXXXXh)."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Archivo no encontrado: {path}[/bold red]")
        raise typer.Exit(code=1)

    code = path.read_text(encoding="utf-8", errors="replace")
    all_obs = []

    if p1_rules:
        p1_obs = P1RuleChecker().analyze(code, filename=path.name)
        for p in p1_obs:
            all_obs.append(
                LinterObservation(
                    linter_name=f"{p.rule_code} ({p.title})",
                    filename=path.name,
                    line=p.line,
                    severity=p.severity,
                    message=p.message,
                    suggestion=p.suggestion,
                )
            )

    if magic_numbers:
        all_obs.extend(MagicNumberLinter().analyze(code, filename=path.name))


    if naming:
        all_obs.extend(NamingConventionLinter().analyze(code, filename=path.name))

    if dead_code:
        all_obs.extend(DeadCodeLinter().analyze(code, filename=path.name))

    if clones:
        dup_matches = InternalCloneLinter().analyze(code, filename=path.name)
        for d in dup_matches:
            all_obs.append(
                LinterObservation(
                    linter_name="copy_paste_detector",
                    filename=path.name,
                    line=d.line_a,
                    severity="ADVERTENCIA",
                    message=d.description,
                    suggestion="Extraé la lógica común en una función auxiliar parametrizada.",
                )
            )

    if doxygen:
        dox_obs = DoxygenAuditor().audit_code(code, filename=path.name)
        for dox in dox_obs:
            all_obs.append(
                LinterObservation(
                    linter_name="doxygen",
                    filename=path.name,
                    line=dox.line,
                    severity="ESTILO",
                    message=dox.message,
                    suggestion="Agregá @brief, @param y @return en el bloque de documentación.",
                )
            )

    if advanced:
        all_obs.extend(FloatComparisonLinter().analyze(code, filename=path.name))
        all_obs.extend(IWYULinter().analyze(code, filename=path.name))
        all_obs.extend(ConstCorrectnessLinter().analyze(code, filename=path.name))
        all_obs.extend(ShortCircuitLinter().analyze(code, filename=path.name))
        all_obs.extend(DeepFreeLinter().analyze(code, filename=path.name))
        all_obs.extend(StringNullPointerLinter().analyze(code, filename=path.name))
        all_obs.extend(VariableShadowingLinter().analyze(code, filename=path.name))
        all_obs.extend(DanglingStackPointerLinter().analyze(code, filename=path.name))
        all_obs.extend(OverengineeringLinter().analyze(code, filename=path.name))
        all_obs.extend(EvaluationOrderLinter().analyze(code, filename=path.name))
        all_obs.extend(StringLiteralWriteLinter().analyze(code, filename=path.name))
        all_obs.extend(BackwardGotoLinter().analyze(code, filename=path.name))

    if not all_obs:
        console.print(f"\n[bold green]✓ No se detectaron desvíos en '{path.name}'. Código limpio y modular.[/bold green]\n")
        return

    table = Table(title=f"Observaciones de Calidad y Estilo - {path.name}")
    table.add_column("Línea", justify="right", style="bold")
    table.add_column("Regla", style="cyan")
    table.add_column("Severidad", justify="center")
    table.add_column("Mensaje")
    table.add_column("Sugerencia Pedagógica", style="dim")

    for obs in all_obs:
        if obs.severity == "ERROR":
            sev_style = "[bold red]ERROR[/bold red]"
        elif obs.severity == "ADVERTENCIA":
            sev_style = "[bold yellow]ADVERTENCIA[/bold yellow]"
        else:
            sev_style = "[cyan]ESTILO[/cyan]"

        table.add_row(
            str(obs.line),
            obs.linter_name,
            sev_style,
            obs.message,
            obs.suggestion,
        )

    console.print(table)


@app.command("heap-simulate")
def cmd_heap_simulate(
    capacity: int = typer.Option(1024, "--capacity", "-c", help="Capacidad del heap simulado en bytes."),
    allocations: str = typer.Option("128,256,64,512", "--allocations", "-a", help="Tamaños de asignación separados por coma."),
    frees: str = typer.Option("1,3", "--frees", "-f", help="Índices 1-based de asignaciones a liberar separados por coma."),
) -> None:
    """Simula un montículo (Heap) para analizar patrones de fragmentación externa e interna."""
    sim = HeapMemorySimulator(capacity=capacity)
    sizes = [int(s.strip()) for s in allocations.split(",") if s.strip()]
    free_indices = [int(idx.strip()) for idx in frees.split(",") if idx.strip()]

    allocated_offsets = []
    for i, sz in enumerate(sizes):
        offset = sim.allocate(sz, tag=f"alloc_{i+1}")
        allocated_offsets.append(offset)

    for f_idx in free_indices:
        if 1 <= f_idx <= len(allocated_offsets):
            off = allocated_offsets[f_idx - 1]
            if off is not None:
                sim.free(off)

    rep = sim.get_report()

    console.print(f"\n[bold green]Reporte de Fragmentación de Memoria Heap ({capacity} B):[/bold green]")
    console.print(f" - [cyan]Memoria Ocupada Actual:[/cyan] {rep.current_allocated} B / {rep.total_capacity} B (Pico: {rep.peak_allocated} B)")
    console.print(f" - [cyan]Memoria Libre Total:[/cyan] {rep.total_free} B")
    console.print(f" - [cyan]Bloque Libre Contiguo Mayor:[/cyan] {rep.largest_free_block} B")
    console.print(f" - [cyan]Índice de Fragmentación Externa:[/cyan] [bold yellow]{rep.fragmentation_index * 100:.1f}%[/bold yellow]")
    console.print(f" - [cyan]Mapa de Memoria:[/cyan] {rep.memory_map}\n")


@app.command("pure-audit")
def cmd_pure_audit(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    mode: str = typer.Option("pure", "--mode", "-m", help="Modo de auditoría ('pure' o 'const')."),
    verify_compiler: bool = typer.Option(True, "--verify-compiler/--no-verify-compiler", help="Verificar inyectando atributos con GCC."),
) -> None:
    """Audita la pureza y ausencia de efectos colaterales en funciones C (__attribute__((pure|const)))."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Archivo no encontrado: {path}[/bold red]")
        raise typer.Exit(code=1)

    code = path.read_text(encoding="utf-8", errors="replace")
    analyzer = PureFunctionAnalyzer()
    obs_list = analyzer.analyze_static(code)

    table = Table(title=f"Auditoría de Funciones Puras - {path.name}")
    table.add_column("Línea", justify="right", style="bold")
    table.add_column("Función", style="cyan")
    table.add_column("Pureza", justify="center")
    table.add_column("Atributo Sugerido", justify="center")
    table.add_column("Violaciones Detectadas", style="dim")

    for obs in obs_list:
        p_str = "[bold green]PURA[/bold green]" if obs.is_pure else "[bold red]IMPURA[/bold red]"
        viol_str = ", ".join(obs.violations) if obs.violations else "Sin efectos secundarios"
        table.add_row(
            str(obs.line),
            obs.function_name,
            p_str,
            obs.suggested_attribute,
            viol_str,
        )

    console.print(table)

    if verify_compiler:
        ok, msg = analyzer.verify_with_compiler(path, mode=mode)
        if ok:
            console.print(f"\n[bold green]✓ Verificación con compilador exitosa:[/bold green] {msg}\n")
        else:
            console.print(f"\n[bold yellow]! Advertencia del compilador:[/bold yellow] {msg}\n")


@app.command("memory-visualize")
def cmd_memory_visualize(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C con estructuras (.c o .h)."),
    format_type: str = typer.Option("mermaid", "--format", help="Formato de salida ('mermaid' o 'dot')."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Archivo de salida."),
) -> None:
    """Genera diagramas visuales de la topología de estructuras dinámicas de datos en memoria."""
    vis = DynamicMemoryVisualizer()
    try:
        diagram = vis.generate_diagram(c_file=file_path, output_format=format_type)
        if output:
            out_p = Path(output)
            out_p.write_text(diagram, encoding="utf-8")
            console.print(f"\n[bold green]✓ Diagrama de memoria guardado en:[/bold green] [cyan]{out_p}[/cyan]\n")
        else:
            console.print(f"\n[bold green]Topología de Estructuras Dinámicas ({file_path}):[/bold green]\n")
            console.print(f"```{format_type}\n{diagram}\n```\n")
    except Exception as e:
        console.print(f"[bold red]Error al visualizar memoria:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("embedded-test")
def cmd_embedded_test(
    binary: str = typer.Option(..., "--binary", "-b", help="Ruta al binario compilado."),
    limit_kb: int = typer.Option(64, "--limit-kb", "-l", help="Límite máximo de memoria en KB."),
    stdin_data: str = typer.Option("", "--stdin", help="Entrada estándar."),
) -> None:
    """Ejecuta un binario bajo límites estrictos de memoria de sistemas embebidos."""
    runner = EmbeddedMemoryRunner(memory_limit_kb=limit_kb)
    res = runner.run(binary_path=binary, stdin_data=stdin_data)

    if res.success:
        console.print(f"\n[bold green]✓ {res.message}[/bold green]\n")
    else:
        console.print(f"\n[bold red]✗ {res.message}[/bold red]")
        if res.stderr:
            console.print(f"[yellow]Stderr:[/yellow] {res.stderr}\n")
        raise typer.Exit(code=1)




@mock_app.command("generate")
def cmd_mock_generate(
    header: str = typer.Option(..., "--header", "-h", help="Ruta al archivo de cabecera (.h) o fuente (.c)."),
    output_dir: str = typer.Option(".", "--output-dir", "-o", help="Directorio de destino."),
) -> None:
    """Genera automáticamente arneses mock (.h y .c) para pruebas unitarias en C."""
    generator = MockGenerator()
    try:
        h_file, c_file = generator.generate_files(input_file=header, output_dir=output_dir)
        console.print(f"\n[bold green]✓ Arneses Mock generados exitosamente:[/bold green]\n")
        console.print(f" - [cyan]{h_file}[/cyan]")
        console.print(f" - [cyan]{c_file}[/cyan]\n")
    except Exception as e:
        console.print(f"[bold red]Error al generar mocks:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("doxygen")
def cmd_doxygen(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c o .h)."),
) -> None:
    """Audita la presencia y completitud de comentarios Doxygen (@brief, @param, @return)."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Archivo no encontrado: {path}[/bold red]")
        raise typer.Exit(code=1)

    code = path.read_text(encoding="utf-8", errors="replace")
    auditor = DoxygenAuditor()
    obs = auditor.audit_code(code, filename=path.name)

    if not obs:
        console.print(f"\n[bold green]✓ Todas las funciones en '{path.name}' están correctamente documentadas en Doxygen.[/bold green]\n")
        return

    table = Table(title=f"Auditoría Doxygen - {path.name}")
    table.add_column("Línea", justify="right", style="bold")
    table.add_column("Función", style="cyan")
    table.add_column("Faltantes", style="yellow")

    for o in obs:
        table.add_row(str(o.line), f"{o.function_name}()", ", ".join(o.missing_items))

    console.print(table)


@app.command("property-test")
def cmd_property_test(
    source: str = typer.Option(..., "--source", "-s", help="Ruta al archivo C del estudiante."),
    function: str = typer.Option(..., "--function", "-f", help="Nombre de la función a evaluar."),
    property_type: str = typer.Option(
        "IDEMPOTENCE",
        "--property",
        "-p",
        help="Tipo de invariante a verificar ('IDEMPOTENCE', 'COMMUTATIVITY', 'SORT_INVARIANT').",
    ),
    iterations: int = typer.Option(100, "--iterations", "-i", help="Cantidad de iteraciones aleatorias a ejecutar."),
) -> None:
    """Ejecuta pruebas basadas en propiedades (Property-Based Testing) sobre funciones en C."""
    runner = PropertyTestRunner()
    console.print(
        f"\n[bold green]Iniciando Property-Based Testing:[/bold green] [cyan]{function}()[/cyan] | Propiedad: [bold]{property_type}[/bold] ({iterations} iteraciones)\n"
    )

    res = runner.run_property_test(
        student_source=source,
        property_type=property_type,
        target_function=function,
        iterations=iterations,
    )

    if res.passed:
        console.print(f"[bold green]✓ {res.message}[/bold green]\n")
    else:
        console.print(f"[bold red]✗ {res.message}[/bold red]")
        if res.counterexample_output:
            console.print(f"[yellow]Contraejemplo hallado:[/yellow] {res.counterexample_output}\n")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()







