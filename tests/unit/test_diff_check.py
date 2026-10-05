"""Verificación incremental desde una referencia de git (QoL #818)."""

import subprocess
from pathlib import Path

import pytest

from ripley.core.diff_check import SinGit, filtrar, lineas_cambiadas


def _git(d: Path, *args):
    subprocess.run(["git", "-C", str(d), *args], check=True, capture_output=True)


def test_lineas_cambiadas_y_filtro(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.c").write_text("int a;\nint b;\nint c;\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    (tmp_path / "a.c").write_text("int a;\nint bb;\nint c;\nint d;\n", encoding="utf-8")
    (tmp_path / "nuevo.c").write_text("int x;\n", encoding="utf-8")
    cambios = lineas_cambiadas(tmp_path)
    assert cambios == {"a.c": {2, 4}, "nuevo.c": set()}
    hallazgos = [{"file": "a.c", "line": 1}, {"file": "a.c", "line": 2}, {"file": "nuevo.c", "line": 1}, {"file": "otro.c", "line": 2}]
    assert filtrar(hallazgos, cambios) == [{"file": "a.c", "line": 2}, {"file": "nuevo.c", "line": 1}]


def test_sin_git(tmp_path):
    with pytest.raises(SinGit):
        lineas_cambiadas(tmp_path)
