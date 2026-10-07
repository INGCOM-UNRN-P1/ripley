"""Ripley CLI package: flat `ripley` app combining teacher and student commands."""

import typer
from yutani.cli import crear_app

from ripley import __version__
from ripley.cli import student as _student
from ripley.cli import teacher as _teacher

# Contrato de línea de comandos del ecosistema (-h/--help, --version/-v, errores de datos como
# mensajes) y textos de Typer en español, desde yutani (N-ECO-14).
app = crear_app(
    "ripley",
    __version__,
    "CLI para procesar, compilar, probar y evaluar entregas de C descargadas de Moodle.",
)


def _merge(target: typer.Typer, source: typer.Typer) -> None:
    """Copia comandos planos y grupos preservando nombres originales."""
    for cmd in source.registered_commands:
        if cmd.callback is not None:
            target.command(name=cmd.name)(cmd.callback)
    for grp in source.registered_groups:
        if grp.typer_instance is not None:
            target.add_typer(grp.typer_instance, name=grp.name)


_merge(app, _teacher.app)
_merge(app, _student.app)


if __name__ == "__main__":
    app()
