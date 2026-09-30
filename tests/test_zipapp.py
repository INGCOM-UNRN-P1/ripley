"""ripley.pyz es autocontenido: corre sin nada instalado (N-RIPLEY-07).

entorno descarga ripley.pyz y lo ejecuta con el Python del estudiante, sin
venv ni pip. Se construye el zipapp y se ejecuta con `python -S` (sin
site-packages): si faltara typer, rich o cualquier otra dependencia, falla.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="build_zipapp.py usa `uv export`")


@pytest.fixture(scope="module")
def zipapp(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("dist") / "ripley.pyz"
    proc = subprocess.run([sys.executable, str(RAIZ / "scripts" / "build_zipapp.py"), "-o", str(destino)],
                          cwd=RAIZ, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return destino


def test_corre_sin_site_packages(zipapp):
    for args in (["--help"], ["--version"]):
        proc = subprocess.run([sys.executable, "-S", str(zipapp), *args], capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stderr
    doctor = subprocess.run([sys.executable, "-S", str(zipapp), "doctor", "--json"],
                            capture_output=True, text=True, timeout=120)
    assert "schema_version" in json.loads(doctor.stdout)


def test_incluye_dependencias_de_python_puro(zipapp):
    nombres = zipfile.ZipFile(zipapp).namelist()
    for paquete in ("typer/", "rich/", "yaml/", "jinja2/", "slugify/", "yutani/"):  # yutani viene de git
        assert any(n.startswith(paquete) for n in nombres), paquete
    assert not [n for n in nombres if n.endswith((".so", ".pyd", ".dll"))]
    assert "ripley/cli/student.py" in nombres
    assert not any(n.startswith("ripley/teacher/") for n in nombres)
