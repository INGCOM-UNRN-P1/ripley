"""Flujo de auditoría docente: tablero, transiciones, historia y publicación."""

from typing import Optional

import typer
from rich.table import Table

from ripley.cli._common import console

from ripley.cli.teacher import app


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
    from ripley.teacher.audit import AuditWorkflow
    
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
