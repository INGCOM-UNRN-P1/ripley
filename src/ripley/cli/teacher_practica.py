"""Comandos `practica` del flujo docente."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.prompt import Prompt
from rich.table import Table

from ripley.cli._common import console
from ripley.teacher.practice import (
    ExerciseTemplateSpec,
    PracticeSpec,
    init_practice,
    list_practices,
    sync_practice_testcases,
)

from ripley.cli.teacher import practica_app


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


@practica_app.command("show")
def cmd_practica_show(
    paquete: str = typer.Argument(..., help="Ruta al archivo .ripkg (o slug de la práctica)."),
    enunciado: bool = typer.Option(False, "--enunciado", "-e", help="Mostrar el enunciado / consigna Markdown."),
    pistas: bool = typer.Option(False, "--pistas", "-p", help="Mostrar las pistas progresivas / pautas."),
    tests: bool = typer.Option(False, "--tests", "-t", help="Mostrar casos de prueba públicos del payload."),
    checks: bool = typer.Option(False, "--checks", "-c", help="Mostrar checks y reglas habilitadas en el manifiesto."),
    archivos: bool = typer.Option(False, "--archivos", "-f", help="Mostrar listado de archivos del payload e integridad SHA-256."),
    meta: bool = typer.Option(False, "--meta", "-m", help="Mostrar metadatos del paquete (flags de compilador, versión, firma)."),
    todos: bool = typer.Option(False, "--todos", "-a", help="Mostrar todas las secciones."),
    verify_signature: bool = typer.Option(False, "--verify-signature", help="Verificar firma GPG del paquete."),
    raw: bool = typer.Option(False, "--raw", help="Salida en texto plano sin formato Rich."),
) -> None:
    """Inspecciona y muestra el contenido, metadatos, enunciado y testcases de un .ripkg."""
    from ripley.cli.student import cmd_show_ripkg

    cmd_show_ripkg(
        paquete=paquete,
        enunciado=enunciado,
        pistas=pistas,
        tests=tests,
        checks=checks,
        archivos=archivos,
        meta=meta,
        todos=todos,
        verify_signature=verify_signature,
        raw=raw,
    )


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
    from ripley.core.graphics_eval import GraphicsEvaluator

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
    from ripley.core.graphics_eval import GraphicsEvaluator

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
