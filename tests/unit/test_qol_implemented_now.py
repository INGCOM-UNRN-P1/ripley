"""Tests unitarios para las mejoras QoL implementadas en Ripley:
1. async_runner (ejecución paralela de tareas/plugins)
2. perfiles de rigurosidad (--profile <strict|relaxed|exam>)
3. modo silencioso y no bloqueante (--quiet --exit-zero)
4. explain interactivo con búsqueda de palabras clave
"""

from pathlib import Path
import pytest
from typer.testing import CliRunner

from ripley.cli.student import app
from ripley.core.async_runner import ejecutar_tareas_paralelo, ResultadoTareaAsync

runner = CliRunner()


def test_async_runner(tmp_path: Path):
    # Crear 3 archivos de prueba
    f1 = tmp_path / "a.c"
    f2 = tmp_path / "b.c"
    f3 = tmp_path / "c.c"
    f1.write_text("int a = 1;\n")
    f2.write_text("int b = 2;\n")
    f3.write_text("int c = 3;\n")

    def tarea_contar_lineas(p: Path) -> int:
        return len(p.read_text().splitlines())

    tareas = [
        ("contar_a", f1, tarea_contar_lineas),
        ("contar_b", f2, tarea_contar_lineas),
        ("contar_c", f3, tarea_contar_lineas),
    ]

    resultados = ejecutar_tareas_paralelo(tareas, max_workers=2)
    assert len(resultados) == 3
    assert all(r.exito for r in resultados)
    assert {r.resultado for r in resultados} == {1}


def test_cli_explain_keyword():
    # Búsqueda por palabra clave "espacio" o "puntero"
    res = runner.invoke(app, ["explain", "espacio"])
    assert res.exit_code == 0
    assert "Reglas P1 encontradas" in res.stdout or "0x0004h" in res.stdout

    # Código directo 0x0001h
    res_direct = runner.invoke(app, ["explain", "0x0001h"])
    assert res_direct.exit_code == 0
    assert "0x0001h" in res_direct.stdout


def test_cli_check_quiet_and_exit_zero(tmp_path: Path):
    c_file = tmp_path / "prueba.c"
    c_file.write_text("int main(void) { return 0; }\n")

    # Flag --quiet y --exit-zero
    res = runner.invoke(app, ["check", str(c_file), "--quiet", "--exit-zero"])
    assert res.exit_code == 0
    # No debería haber impreso el banner ruidoso de inicio
    assert "─── Verificación Ripley:" not in res.stdout


def test_cli_check_profiles(tmp_path: Path):
    c_file = tmp_path / "prueba.c"
    c_file.write_text("int main(void) { return 0; }\n")

    # Perfil relaxed
    res_relaxed = runner.invoke(app, ["check", str(c_file), "--profile", "relaxed", "--exit-zero"])
    assert res_relaxed.exit_code == 0

    # Perfil exam
    res_exam = runner.invoke(app, ["check", str(c_file), "--profile", "exam", "--exit-zero"])
    assert res_exam.exit_code == 0
