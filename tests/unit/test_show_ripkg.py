"""Tests para el comando 'ripley show' y 'ripley practica show' de inspección de paquetes .ripkg."""

from pathlib import Path
from typer.testing import CliRunner

from ripley.cli import app
from ripley.pipeline.bundle import build_manifest, write_bundle

runner = CliRunner()


def test_ripley_show_command(tmp_path: Path):
    # 1. Crear un .ripkg dummy
    payload = {
        "enunciado.md": b"# Practica 1: Punteros\n\nConsigna detallada del ejercicio.",
        "pistas.txt": b"1. Recordar verificar punteros NULL.\n2. Cuidado con el off-by-one.",
        "testcases/caso_01.in": b"5\n1 2 3 4 5\n",
        "testcases/caso_01.out": b"5 4 3 2 1\n",
        "testcases/caso_01.argv": b"--reverse\n",
    }
    manifest = build_manifest(
        practica_slug="punteros-tp1",
        enabled_check_ids=["p1.naming", "security.banned_functions"],
        compiler_executable="gcc",
        compiler_flags=["-Wall", "-Wextra", "-std=c99"],
        payload_files=payload,
    )
    ripkg_path = tmp_path / "punteros-tp1.ripkg"
    write_bundle(ripkg_path, manifest, payload)

    # 2. Probar 'ripley show' por defecto (enunciado, pistas y casos)
    res = runner.invoke(app, ["show", str(ripkg_path)])
    assert res.exit_code == 0
    assert "Practica 1: Punteros" in res.stdout
    assert "Pistas y Pautas" in res.stdout
    assert "caso_01" in res.stdout
    assert "p1.naming" not in res.stdout

    # 3. Probar control granular de secciones
    # Solo meta
    res_m = runner.invoke(app, ["show", str(ripkg_path), "-m"])
    assert res_m.exit_code == 0
    assert "punteros-tp1" in res_m.stdout
    assert "Practica 1: Punteros" not in res_m.stdout

    # Solo enunciado
    res_e = runner.invoke(app, ["show", str(ripkg_path), "-e"])
    assert res_e.exit_code == 0
    assert "Practica 1: Punteros" in res_e.stdout
    assert "caso_01" not in res_e.stdout

    # Solo tests
    res_t = runner.invoke(app, ["show", str(ripkg_path), "-t"])
    assert res_t.exit_code == 0
    assert "caso_01" in res_t.stdout
    assert "--reverse" in res_t.stdout
    assert "Pistas y Pautas" not in res_t.stdout

    # Solo pistas
    res_p = runner.invoke(app, ["show", str(ripkg_path), "-p"])
    assert res_p.exit_code == 0
    assert "Recordar verificar punteros NULL" in res_p.stdout

    # Solo checks
    res_c = runner.invoke(app, ["show", str(ripkg_path), "-c"])
    assert res_c.exit_code == 0
    assert "security.banned_functions" in res_c.stdout

    # Solo archivos de payload
    res_f = runner.invoke(app, ["show", str(ripkg_path), "-f"])
    assert res_f.exit_code == 0
    assert "testcases/caso_01.in" in res_f.stdout

    # Salida raw
    res_raw = runner.invoke(app, ["show", str(ripkg_path), "--todos", "--raw"])
    assert res_raw.exit_code == 0
    assert "Practica: punteros-tp1" in res_raw.stdout
    assert "--- ENUNCIADO ---" in res_raw.stdout
    assert "--- PISTAS / PAUTAS ---" in res_raw.stdout
    assert "--- TESTCASES ---" in res_raw.stdout
    assert "--- CHECKS HABILITADOS ---" in res_raw.stdout
    assert "--- ARCHIVOS PAYLOAD ---" in res_raw.stdout

    # Probar alias 'ripley practica show'
    res_sub = runner.invoke(app, ["practica", "show", str(ripkg_path), "--raw", "-e"])
    assert res_sub.exit_code == 0
    assert "--- ENUNCIADO ---" in res_sub.stdout
    assert "Consigna detallada" in res_sub.stdout
