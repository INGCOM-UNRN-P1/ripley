"""Pruebas del comando `ripley style` (c-style-guide)."""

from pathlib import Path
import tempfile

from typer.testing import CliRunner

from ripley.cli import app

runner = CliRunner()


def test_style_reporta_observaciones_y_falla(tmp_path):
    src = tmp_path / "malo.c"
    src.write_text("int main( ) {\n    int x=1;   \n    if(x==1){ return 0; }\n}\n")

    resultado = runner.invoke(app, ["style", str(src)])

    # el código con vicios de estilo no aprueba: exit 1 con observaciones
    assert resultado.exit_code == 1
    assert "observaciones de estilo" in resultado.output


def test_style_directorio_vacio_falla(tmp_path):
    resultado = runner.invoke(app, ["style", str(tmp_path)])
    assert resultado.exit_code == 1


def test_style_archivo_allman_limpio_aprueba():
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "limpio.c"
        src.write_text(
            "int main(void)\n{\n"
            "    int x = 1;\n"
            "    if (x == 1)\n"
            "    {\n"
            "        return 0;\n"
            "    }\n"
            "    return 1;\n"
            "}\n"
        )
        resultado = runner.invoke(app, ["style", str(src)])
        assert resultado.exit_code == 0, resultado.output
        assert "0 observaciones" in resultado.output


def test_ruta_inexistente_falla(tmp_path):
    resultado = runner.invoke(app, ["style", str(tmp_path / "fantasma.c")])
    assert resultado.exit_code == 1
