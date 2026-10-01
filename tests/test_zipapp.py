"""ripley.pyz es autocontenido: corre sin nada instalado (N-RIPLEY-07).

entorno descarga ripley.pyz y lo ejecuta con el Python del estudiante, sin
venv ni pip. Se construye el zipapp y se ejecuta con `python -S` (sin
site-packages): si faltara typer, rich o cualquier otra dependencia, falla.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
# Salida del zipapp en UTF-8 de los dos lados (en Windows, cp1252 por defecto).
UTF8 = {"encoding": "utf-8", "errors": "replace", "env": {**os.environ, "PYTHONIOENCODING": "utf-8"}}

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="build_zipapp.py usa `uv export`")


@pytest.fixture(scope="module")
def zipapp(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("dist") / "ripley.pyz"
    proc = subprocess.run([sys.executable, str(RAIZ / "scripts" / "build_zipapp.py"), "-o", str(destino)],
                          cwd=RAIZ, capture_output=True, **UTF8, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return destino


def test_corre_sin_site_packages(zipapp):
    for args in (["--help"], ["--version"]):
        proc = subprocess.run([sys.executable, "-S", str(zipapp), *args], capture_output=True, **UTF8, timeout=120)
        assert proc.returncode == 0, proc.stderr
    doctor = subprocess.run([sys.executable, "-S", str(zipapp), "doctor", "--json"],
                            capture_output=True, **UTF8, timeout=120)
    assert "schema_version" in json.loads(doctor.stdout)


def test_incluye_dependencias_de_python_puro(zipapp):
    nombres = zipfile.ZipFile(zipapp).namelist()
    for paquete in ("typer/", "rich/", "yaml/", "jinja2/", "slugify/", "yutani/"):  # yutani viene de git
        assert any(n.startswith(paquete) for n in nombres), paquete
    assert not [n for n in nombres if n.endswith((".so", ".pyd", ".dll"))]
    assert "ripley/cli/student.py" in nombres
    assert not any(n.startswith("ripley/teacher/") for n in nombres)


def test_todos_los_modulos_de_ripley_importan(zipapp):
    """Un módulo que el build deja afuera recién falla al usarlo: config_modelos.py (salido de partir
    config.py) no entraba y `ripley check` terminaba en ModuleNotFoundError, con --help y doctor bien."""
    modulos = sorted(n[:-3].replace("/", ".").removesuffix(".__init__") for n in zipfile.ZipFile(zipapp).namelist()
                     if n.startswith("ripley/") and n.endswith(".py"))
    programa = ("import importlib, sys\n"
                f"sys.path.insert(0, {str(zipapp)!r})\n"
                f"fallas = []\n"
                f"for m in {modulos!r}:\n"
                "    try:\n"
                "        importlib.import_module(m)\n"
                "    except Exception as e:\n"
                "        fallas.append(f'{m}: {e!r}')\n"
                "print('\\n'.join(fallas))\n")
    proc = subprocess.run([sys.executable, "-S", "-c", programa], capture_output=True, **UTF8, timeout=120)
    assert proc.returncode == 0 and not proc.stdout.strip(), proc.stdout + proc.stderr


@pytest.mark.skipif(shutil.which("gcc") is None, reason="check compila el proyecto")
def test_check_corre_sobre_un_proyecto(zipapp, tmp_path):
    (tmp_path / "main.c").write_text('#include <stdio.h>\n\nint main(void)\n{\n    printf("hola\\n");\n'
                                     "    return 0;\n}\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, "-S", str(zipapp), "check", str(tmp_path)],
                          capture_output=True, **UTF8, timeout=300, cwd=tmp_path)
    salida = proc.stdout + proc.stderr
    assert proc.returncode in (0, 1), salida  # 1: hallazgos; no un error de uso ni un traceback
    assert "Traceback" not in salida and "ModuleNotFoundError" not in salida, salida
