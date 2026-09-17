"""Ripley CLI package: flat `ripley` app combining teacher and student commands."""

from typing import Optional

import typer

from ripley import __version__
from ripley.cli import student as _student
from ripley.cli import teacher as _teacher

app = typer.Typer(
    name="ripley",
    help="CLI para procesar, compilar, probar y evaluar entregas de C descargadas de Moodle.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ripley {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de ripley y finaliza.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


def _merge(target: typer.Typer, source: typer.Typer) -> None:
    """Copia comandos planos y grupos preservando nombres originales."""
    for cmd in source.registered_commands:
        target.command(name=cmd.name)(cmd.callback)
    for grp in source.registered_groups:
        target.add_typer(grp.typer_instance, name=grp.name)


_merge(app, _teacher.app)
_merge(app, _student.app)


if __name__ == "__main__":
    app()
