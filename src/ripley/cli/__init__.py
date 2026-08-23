"""Ripley CLI package: flat `ripley` app combining teacher and student commands."""

import typer

from ripley.cli import student as _student
from ripley.cli import teacher as _teacher

app = typer.Typer(
    name="ripley",
    help="CLI para procesar, compilar, probar y evaluar entregas de C descargadas de Moodle.",
    no_args_is_help=True,
)


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
