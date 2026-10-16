"""ripley evaluate compila con daedalus (N-RIPLEY-03): flags de la actividad, sandbox, límites."""

import shutil
import sys
import types

import pytest

from ripley.config_modelos import CompilerConfig, LimitsConfig, SandboxConfig
from ripley.teacher import compilacion
from ripley.teacher.compilacion import CompiladorActividad

necesita_gcc = pytest.mark.skipif(not shutil.which("gcc"), reason="requiere gcc")


def _resultado(**kw):
    base = dict(exito=True, codigo_retorno=0, stdout_crudo="", stderr_crudo="", binario=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


@pytest.fixture
def falso(monkeypatch, tmp_path):
    llamadas = {}

    def compilar(fuentes, binario_salida, **kw):
        llamadas.update(fuentes=fuentes, binario=binario_salida, **kw)
        binario_salida.write_bytes(b"\x7fELF")
        return _resultado(binario=binario_salida)

    c = CompiladorActividad(CompilerConfig(flags=["-std=c99", "-O2"]), LimitsConfig(), SandboxConfig(enabled=True))
    monkeypatch.setattr(c, "_compilar", compilar)
    monkeypatch.setattr(compilacion.shutil, "which", lambda _x: "/usr/bin/gcc")
    return c, llamadas


def test_usa_los_flags_de_la_actividad_y_el_sandbox(falso, tmp_path):
    c, llamadas = falso
    res = c.compile([tmp_path / "a.c"], tmp_path / "bin" / "a")
    assert res.success and res.binary_path == tmp_path / "bin" / "a"
    assert llamadas["flags"] == ["-std=c99", "-O2"]
    assert llamadas["aislar"] is True and llamadas["reintentar_sin_sanitizers"] is True
    assert llamadas["timeout"] == LimitsConfig().timeout_segundos * 2


def test_sin_sandbox_no_aisla(monkeypatch, tmp_path):
    c = CompiladorActividad(CompilerConfig(), LimitsConfig(), SandboxConfig(enabled=False))
    assert c.aislar is False


def test_binario_demasiado_grande(falso, tmp_path, monkeypatch):
    c, _ = falso
    c.limits_cfg = LimitsConfig(max_tamano_ejecutable_mb=1)

    def grande(fuentes, binario_salida, **kw):
        binario_salida.write_bytes(b"0" * (2 * 1024 * 1024))
        return _resultado(binario=binario_salida)

    monkeypatch.setattr(c, "_compilar", grande)
    res = c.compile([tmp_path / "a.c"], tmp_path / "a")
    assert not res.success and res.error_message == "Tamaño de binario excedido."
    assert not (tmp_path / "a").exists()


def test_timeout(falso, tmp_path, monkeypatch):
    c, _ = falso
    monkeypatch.setattr(c, "_compilar", lambda *a, **k: _resultado(exito=False, codigo_retorno=124))
    res = c.compile([tmp_path / "a.c"], tmp_path / "a")
    assert not res.success and res.error_message == "Timeout de compilación."


def test_compilador_inexistente(tmp_path, monkeypatch):
    c = CompiladorActividad(CompilerConfig(executable="no-existe-cc"), LimitsConfig(), SandboxConfig())
    monkeypatch.setattr(c, "_compilar", lambda *a, **k: pytest.fail("no debía compilar"))
    res = c.compile([tmp_path / "a.c"], tmp_path / "a")
    assert not res.success and "no encontrado" in res.error_message


def test_sin_daedalus_usa_el_compilador_interno(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "daedalus.core.compiler", None)
    c = CompiladorActividad(CompilerConfig(), LimitsConfig(), SandboxConfig())
    assert c._compilar is None
    usado = {}

    class Interno:
        def __init__(self, *a):
            usado["interno"] = True

        def compile(self, *a):
            return "resultado"

    monkeypatch.setattr("ripley.core.compiler.Compiler", Interno)
    assert c.compile([tmp_path / "a.c"], tmp_path / "a") == "resultado" and usado["interno"]


@necesita_gcc
def test_compila_de_verdad_con_daedalus(tmp_path):
    pytest.importorskip("daedalus.core.compiler")
    (tmp_path / "a.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    c = CompiladorActividad(CompilerConfig(flags=["-std=c11", "-Wall"]), LimitsConfig(), SandboxConfig(enabled=True))
    res = c.compile([tmp_path / "a.c"], tmp_path / "salida" / "a")
    assert res.success, res.stderr
