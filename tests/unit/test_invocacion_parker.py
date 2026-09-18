"""Regresión de PARKER-D0902: ripley invocaba `parker audit` con una forma que parker rechazaba.

`parker audit` recibe la cabecera como argumento y el binario con `--binary`;
ripley pasaba el binario como segundo argumento posicional y el resultado era un
error de uso disfrazado de hallazgo.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ripley.core.entrypoints import SatellitePluginAdapter


def _adaptador():
    return SatellitePluginAdapter(
        name="abi_audit", tool_name="parker", cli_command="parker", entry_point=None, instance=None
    )


def test_el_binario_viaja_con_la_opcion_binary(tmp_path: Path, monkeypatch):
    llamadas = []

    def falso_run(args, capture_output=True, text=True, timeout=20):
        llamadas.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps({"passed": True, "issues": []}), stderr="")

    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr("subprocess.run", falso_run)

    _adaptador()._execute_cli(tmp_path, {"header": "lib.h", "binary": "lib.so"})

    assert llamadas == [["parker", "audit", "lib.h", "--binary", "lib.so", "--json"]]


def test_sin_cabecera_y_binario_configurados_no_se_ejecuta_nada(tmp_path: Path, monkeypatch):
    def no_debe_correr(*args, **kwargs):
        raise AssertionError("no debería lanzar parker sin header y binary")

    monkeypatch.setattr("subprocess.run", no_debe_correr)
    resultado = _adaptador()._execute_cli(tmp_path, {})
    assert resultado["ok"] is True and resultado["issues"] == []


@pytest.mark.skipif(
    not (shutil.which("parker") and shutil.which("gcc")), reason="requiere parker y gcc instalados"
)
def test_parker_real_acepta_la_invocacion_de_ripley(tmp_path: Path):
    (tmp_path / "lib.h").write_text("int suma(int a, int b);\nint faltante(void);\n", encoding="utf-8")
    (tmp_path / "lib.c").write_text("int suma(int a, int b) { return a + b; }\n", encoding="utf-8")
    subprocess.run(["gcc", "-c", str(tmp_path / "lib.c"), "-o", str(tmp_path / "lib.o")], check=True)

    resultado = _adaptador()._execute_cli(
        tmp_path, {"header": str(tmp_path / "lib.h"), "binary": str(tmp_path / "lib.o")}
    )

    simbolos = {o.get("symbol") or o.get("message", "") for o in resultado["observaciones"]}
    assert any("faltante" in str(s) for s in simbolos), resultado
    assert resultado["passed"] is False
