"""Ripley CLI interface."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from ripley.config import load_config
from ripley.ingest import MoodleIngestor
from ripley.templates import check_templates, init_templates, list_templates

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

app.add_typer(template_app, name="template")
app.add_typer(testcase_app, name="testcase")

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


if __name__ == "__main__":
    app()
