"""Ripley teacher CLI: ingestion, mapping, plagiarism, grading and exports."""

from pathlib import Path
from typing import Optional
import json

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ripley.cli._common import console
from ripley.config import load_config
from ripley.teacher.evaluate import Evaluator
from ripley.teacher.templates import check_templates, init_templates, list_templates
from ripley.teacher.practice import (
    ExerciseTemplateSpec,
    PracticeSpec,
    init_practice,
    list_practices,
    sync_practice_testcases,
)
from ripley.tools.fuzzing import Fuzzer
from ripley.tools.testcases import (
    check_testcases_integrity,
    create_testcase_skeleton,
    discover_testcases,
)


app = typer.Typer(
    name="ripley-teacher",
    help="Comandos del flujo docente.",
    no_args_is_help=True,
)
template_app = typer.Typer(name="template", help="Gestión y verificación de plantillas Markdown Jinja2.", no_args_is_help=True)
testcase_app = typer.Typer(name="testcase", help="Gestión y esqueletos de casos de prueba.", no_args_is_help=True)
practica_app = typer.Typer(name="practica", help="Gestión de prácticas en ./practicas.", no_args_is_help=True)

app.add_typer(template_app, name="template")
app.add_typer(testcase_app, name="testcase")
app.add_typer(practica_app, name="practica")


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
    """(Migrado a Dredd) Procesa e ingesta un archivo ZIP de entregas de Moodle."""
    console.print(
        "\n[bold yellow]⚠ El comando 'ingest' ha sido migrado al orquestador Dredd.[/bold yellow]"
    )
    console.print("  Para procesar entregas de Moodle, ejecutá:")
    console.print(f"  [bold cyan]dredd moodle ingest {zip_path}[/bold cyan]\n")


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
    activity = Path(activity).name or activity.strip("/\\")
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
    activity: str = typer.Option(..., "--activity", "-a", help="Slug de la actividad."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """(Migrado a Dredd) Mapeo interactivo de archivos fuente a ejercicios."""
    console.print(
        "\n[bold yellow]⚠ El comando 'map' ha sido migrado al orquestador Dredd.[/bold yellow]"
    )
    console.print("  Para mapear archivos de una actividad, ejecutá:")
    console.print(f"  [bold cyan]dredd map {activity}[/bold cyan]\n")


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
    activity = Path(activity).name or activity.strip("/\\")
    practice_tests = Path(workspace) / "practicas" / activity / "ejercicios" / exercise / "tests"
    target_dir = practice_tests if practice_tests.parent.exists() else Path(workspace) / "tests" / activity / exercise
    fuzzer = Fuzzer()

    ref_path = Path(solution) if solution else Path(workspace) / "practicas" / activity / "ejercicios" / exercise / "solucion_modelo.c"
    ref_to_use = ref_path if ref_path.exists() else None

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
            f"\n[bold green]✓ Se generaron {len(pairs)} casos de prueba por fuzzing en '{target_dir}':[/bold green]\n"
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
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """(Migrado a Dredd) Analiza similitud de código y sospechas de plagio entre entregas."""
    console.print(
        "\n[bold yellow]⚠ El comando 'plagiarism' ha sido migrado al orquestador Dredd.[/bold yellow]"
    )
    console.print("  Para auditar la cohorte de entregas con el algoritmo Winnowing, ejecutá:")
    console.print(f"  [bold cyan]dredd plagiarism {activity} --threshold {threshold}[/bold cyan]\n")
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
    activity = Path(activity).name or activity.strip("/\\")
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
    """(Migrado a Dredd) Exporta las calificaciones para Moodle (CSV), el ZIP masivo y el dashboard."""
    console.print(
        "\n[bold yellow]⚠ El comando 'export' ha sido migrado al orquestador Dredd.[/bold yellow]"
    )
    console.print("  Para generar CSV, ZIP y Dashboard docente, ejecutá:")
    console.print(f"  [bold cyan]dredd export {activity}[/bold cyan]\n")


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
            force=force,
        )
        console.print(f"\n[bold green]✓ Práctica inicializada exitosamente en:[/bold green] [cyan]{p_dir}[/cyan]\n")
        console.print(f" - [bold]Enunciado general:[/bold] {p_dir}/enunciado.md")
        console.print(f" - [bold]Pautas de evaluación:[/bold] {p_dir}/pautas_evaluacion.md")
        console.print(f" - [bold]Configuración de corrección:[/bold] {p_dir}/ripley.toml")
        console.print(f" - [bold]Ejercicios generados ({len(ex_list)}):[/bold]")
        for ex in ex_list:
            console.print(f"   * [cyan]{ex.slug}[/cyan] (enunciado, solucion_modelo.c, {cases} testcases en {p_dir}/ejercicios/{ex.slug}/tests/)")
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
    base_dir: str = typer.Option("practicas", "--path", "-p", help="Directorio de prácticas."),
) -> None:
    """Verifica y valida los casos de prueba dentro de ./practicas/<activity>/ejercicios/*/tests/."""
    p_dir = Path(base_dir) / activity
    if not p_dir.exists():
        console.print(f"[bold red]La práctica '{activity}' no existe en '{base_dir}'.[/bold red]")
        raise typer.Exit(code=1)

    count = sync_practice_testcases(p_dir)
    console.print(
        f"\n[bold green]✓ Se verificaron {count} archivos de casos de prueba en '{p_dir}/ejercicios/'[/bold green]\n"
    )





@practica_app.command("pack")
def cmd_practica_pack(
    practica_slug: str = typer.Argument(..., help="Slug de la práctica en ./practicas."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Ruta del .ripkg (default: junto a la práctica)."),
    sign_key: Optional[str] = typer.Option(None, "--sign-key", help="Huella GPG para firmar el manifiesto."),
) -> None:
    """Empaqueta una práctica (.ripkg) con checks y testcases públicos para el estudiante."""
    from ripley.teacher.pack import pack_practice

    pdir = Path("practicas") / practica_slug
    try:
        result = pack_practice(pdir, sign_key=sign_key)
    except FileNotFoundError as e:
        console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1)

    out = Path(output) if output else result.output_path
    if output and out != result.output_path:
        import shutil

        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(result.output_path), str(out))

    console.print(f"\n[bold green]Paquete creado:[/bold green] {out}")
    console.print(f"  Checks habilitados : {result.checks_enabled}")
    console.print(f"  Archivos payload   : {result.payload_files}")
    console.print(f"  Firmado            : {'sí' if result.signed else 'no (unsigned=true)'}")


@practica_app.command("graphics-capture")
def cmd_practica_graphics_capture(
    binary_path: Path = typer.Argument(..., help="Binario gráfico (SDL2/Raylib) a ejecutar."),
    output: Path = typer.Option("golden.png", "--output", "-o", help="PNG dorado a generar."),
    args_str: str = typer.Option("", "--args", help="Argumentos CLI para el binario."),
    stdin_file: Optional[str] = typer.Option(None, "--stdin", "-i", help="Entrada estándar opcional."),
) -> None:
    """Genera la imagen dorada de referencia ejecutando el binario bajo Xvfb."""
    import shlex

    from ripley.config import load_config
    from ripley.tools.graphics_eval import GraphicsEvaluator

    cfg = load_config().graphics
    evaluator = GraphicsEvaluator(cfg)
    if not evaluator.available:
        console.print(f"[bold red]{evaluator._probe_msg}[/bold red]")
        raise typer.Exit(code=1)

    cli_args = tuple(shlex.split(args_str)) if args_str else ()
    stdin_data = Path(stdin_file).read_text(encoding="utf-8") if stdin_file else ""
    cap = evaluator.capture_screenshot(binary_path, cli_args=cli_args,
                                       stdin_data=stdin_data, workdir=output.parent)
    if not cap.ok or cap.screenshot_path is None:
        console.print(f"[bold red]{cap.message}[/bold red]")
        raise typer.Exit(code=1)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil_move(cap.screenshot_path, output)
    console.print(f"[green]✓ Golden generado:[/green] {output} (display {cap.display})")


def shutil_move(src: Path, dst: Path) -> None:
    import shutil as _sh

    dst.parent.mkdir(parents=True, exist_ok=True)
    _sh.move(str(src), str(dst))


@practica_app.command("graphics-eval")
def cmd_practica_graphics_eval(
    binary_path: Path = typer.Argument(..., help="Binario del alumno a evaluar."),
    golden: list[Path] = typer.Option(..., "--golden", "-g", help="Imagen(es) doradas contra las que comparar."),
    args_str: str = typer.Option("", "--args", help="Argumentos CLI para el binario (mismo escenario por golden)."),
    stdin_file: Optional[str] = typer.Option(None, "--stdin", "-i", help="Entrada estándar opcional."),
) -> None:
    """Evalúa un TP gráfico: captura bajo Xvfb y compara píxeles contra los goldens."""
    import shlex

    from ripley.config import load_config
    from ripley.tools.graphics_eval import GraphicsEvaluator

    cfg = load_config().graphics
    if not cfg.enabled:
        console.print("[yellow][graphics] enabled=false en ripley.toml; evaluando de todos modos.[/yellow]")
    evaluator = GraphicsEvaluator(cfg)
    if not evaluator.available:
        console.print(f"[bold red]{evaluator._probe_msg}[/bold red]")
        raise typer.Exit(code=1)

    cli_args = tuple(shlex.split(args_str)) if args_str else ()
    stdin_data = Path(stdin_file).read_text(encoding="utf-8") if stdin_file else ""

    table = Table(title=f"Evaluación Gráfica — {binary_path.name}")
    table.add_column("Golden", style="cyan")
    table.add_column("Dif. píxeles", justify="right")
    table.add_column("Umbral", justify="right")
    table.add_column("Resultado")
    fallas = 0
    for expected in golden:
        res = evaluator.evaluate_case(binary_path, expected, cli_args=cli_args,
                                      stdin_data=stdin_data)
        if res.diff_pixels < 0 and not res.passed:
            console.print(f"[bold red]{res.message}[/bold red]")
            raise typer.Exit(code=1)
        ok = res.passed
        fallas += 0 if ok else 1
        table.add_row(expected.name, str(res.diff_pixels), str(res.threshold),
                      "[green]APROBADO[/green]" if ok else "[red]RECHAZADO[/red]")
    console.print(table)
    if fallas:
        raise typer.Exit(code=1)


# ============================================================================
# Flujo de auditoría docente: estados por entrega + bitácora
# ============================================================================

audit_app = typer.Typer(
    name="audit",
    help="Flujo de auditoría docente: tablero de estados, transiciones e historia.",
    no_args_is_help=True,
)
app.add_typer(audit_app, name="audit")


@audit_app.command("board")
def cmd_audit_board(
    actividad: str = typer.Argument(..., help="Slug de la actividad/práctica."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Tablero del flujo de auditoría: alumnos agrupados por estado."""
    from ripley.teacher.audit import ESTADOS, AuditWorkflow
    
    workflow = AuditWorkflow(workspace_dir=workspace)
    board = workflow.tablero(actividad)

    total = sum(len(v) for v in board.values())
    console.print(f"\n[bold]Tablero de auditoría[/bold] · {actividad} · {total} entregas\n")
    table = Table()
    table.add_column("Estado", style="cyan")
    table.add_column("Cant.", justify="right")
    table.add_column("Alumnos", style="dim")
    for estado, items in board.items():
        if not items and estado != "ingresada":
            continue
        nombres = ", ".join(i["alumno"] for i in items[:6])
        if len(items) > 6:
            nombres += f" … (+{len(items)-6})"
        table.add_row(estado, str(len(items)), nombres or "-")
    console.print(table)
    console.print(
        "\n[dim]Circuito principal: ingresada → evaluada → en_revision → calificada → publicada"
        "\nDerivas: observada (reentrega), sospechosa (plagio), apelada (tras publicar). "
        "Detalle: ripley audit history.[/dim]"
    )


@audit_app.command("transition")
def cmd_audit_transition(
    actividad: str = typer.Argument(...),
    alumno: str = typer.Argument(...),
    destino: str = typer.Argument(..., help=f"Uno de: ingresada, evaluada, en_revision, observada, sospechosa, calificada, publicada, apelada."),
    actor: Optional[str] = typer.Option(None, "--actor", "-a", help="Docente responsable (default: usuario del sistema)."),
    note: str = typer.Option("", "--nota", "-n", help="Nota de la transición (queda en la bitácora)."),
    force: bool = typer.Option(False, "--force", help="Permitir saltos fuera de la máquina de estados (queda registrado)."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Mueve una entrega al estado indicado dejando evento de auditoría."""
    from ripley.teacher.audit import AuditWorkflow, EstadoInvalido, TransicionInvalida

    workflow = AuditWorkflow(workspace_dir=workspace, actor=actor)
    try:
        ev = workflow.transicionar(actividad, alumno, destino, nota=note, actor=actor, force=force)
    except (EstadoInvalido, TransicionInvalida) as e:
        console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1)
    forzado = " [yellow](FORZADA)[/yellow]" if ev.forzado else ""
    console.print(
        f"[green]✓[/green] {alumno} @ {actividad}: "
        f"{ev.estado_anterior} → [bold]{ev.estado_nuevo}[/bold]{forzado} · actor: {ev.actor}"
    )
    if ev.nota:
        console.print(f"  nota: {ev.nota}")


@audit_app.command("history")
def cmd_audit_history(
    actividad: str = typer.Argument(...),
    alumno: str = typer.Argument(...),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Bitácora completa (append-only) de una entrega."""
    from ripley.teacher.audit import AuditWorkflow

    workflow = AuditWorkflow(workspace_dir=workspace)
    eventos = workflow.historia(actividad, alumno)
    if not eventos:
        console.print("[yellow]Sin eventos registrados para esta entrega.[/yellow]")
        return
    table = Table(title=f"Historia · {alumno} @ {actividad}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Cuando", style="dim")
    table.add_column("Transición")
    table.add_column("Actor")
    table.add_column("Nota")
    for ev in eventos:
        transicion = f"{ev.estado_anterior or '∅'} → [bold]{ev.estado_nuevo}[/bold]"
        if ev.forzado:
            transicion += " [yellow](forzada)[/yellow]"
        table.add_row(str(ev.id), ev.created_at, transicion, ev.actor, ev.nota[:60])
    console.print(table)


@audit_app.command("publish")
def cmd_audit_publish(
    actividad: str = typer.Argument(...),
    actor: Optional[str] = typer.Option(None, "--actor", "-a"),
    note: str = typer.Option("", "--nota", "-n"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Publica masivamente todas las entregas calificadas de la actividad."""
    from ripley.teacher.audit import AuditWorkflow

    workflow = AuditWorkflow(workspace_dir=workspace, actor=actor)
    eventos = workflow.publicar_calificadas(actividad, nota=note, actor=actor)
    if not eventos:
        console.print("[yellow]No hay entregas calificadas para publicar.[/yellow]")
        return
    console.print(f"[green]✓ Publicadas {len(eventos)} entregas:[/green]")
    for ev in eventos:
        console.print(f"  · {ev.alumno} → publicada")


# ============================================================================
# Exportación de informes a HTML enriquecido y PDF
# ============================================================================


@app.command("export-report")
def cmd_export_report(
    source_md: Path = typer.Argument(..., help="Informe Markdown (.md)."),
    format_: str = typer.Option("html", "--format", "-f", help="Formato de salida: html | pdf."),
) -> None:
    """(Migrado a Dredd) Convierte informes Markdown a HTML enriquecido autocontenido o PDF."""
    console.print(
        "\n[bold yellow]⚠ El comando 'export-report' ha sido migrado al orquestador Dredd.[/bold yellow]"
    )
    console.print("  Para exportar informes a HTML o PDF, ejecutá:")
    console.print(f"  [bold cyan]dredd export-report {source_md} --format {format_}[/bold cyan]\n")

