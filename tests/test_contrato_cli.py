"""Contrato de línea de comandos (LINEAMIENTOS §3.2, N-ECO-04): el test reutilizable de yutani (N-ECO-14).

Vale para los dos ejecutables: `ripley` (docente y estudiante) y `ripley-check` (solo estudiante).
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner
from yutani.testing import pruebas_de_contrato

from ripley import __version__
from ripley.cli import app
from ripley.cli.student import app as app_check

test_ayuda, test_version, test_doctor_json = pruebas_de_contrato(app)
test_ayuda_check, test_version_check, test_doctor_json_check = pruebas_de_contrato(app_check)


@pytest.mark.parametrize("aplicacion, nombre", [(app, "ripley"), (app_check, "ripley-check")])
def test_la_version_nombra_el_ejecutable(aplicacion, nombre):
    assert CliRunner().invoke(aplicacion, ["--version"]).output.strip() == f"{nombre} {__version__}"


def test_la_ayuda_esta_en_espanol():
    salida = CliRunner().invoke(app, ["--help"], env={"COLUMNS": "150"}).output
    assert "Comandos" in salida and "Muestra esta ayuda y sale." in salida
