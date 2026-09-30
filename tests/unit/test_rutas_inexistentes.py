"""Un archivo o carpeta que no existe es un error de uso (N-ECO-18).

`ripley history no_existe` respondía «No hay historial de progreso registrado aún» con código 0;
run, check y analyze sobre una ruta inexistente fallaban cada uno a su manera. Ahora todos los
argumentos de ruta de entrada exigen que exista (código 2, mensaje en español por yutani).
"""

import pytest
from typer.testing import CliRunner

from ripley.cli import app
from ripley.cli.student import app as app_check

runner = CliRunner()


@pytest.mark.parametrize("aplicacion", [app, app_check])
@pytest.mark.parametrize("comando", ["history", "run", "check", "analyze", "report", "badge", "style-check"])
def test_una_ruta_que_no_existe_es_un_error_de_uso(aplicacion, comando, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(aplicacion, [comando, "no_existe.c"], env={"COLUMNS": "200"})
    if res.exit_code == 2 and "No existe el comando" in res.output:
        pytest.skip(f"{comando} no está en esta aplicación")
    assert res.exit_code == 2, res.output
    assert "no_existe.c" in res.output
