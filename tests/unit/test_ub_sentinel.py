"""Pruebas de ub-sentinel: niveles, degradación y clasificación."""

from types import SimpleNamespace

import pytest

from ripley.core import ub_sentinel
from ripley.core.ub_sentinel import (
    HallazgoUB,
    ReporteUB,
    _falta_runtime_sanitizers,
    auditar_ub,
    normalizar_nivel,
)


def test_normalizar_nivel_acota_rango():
    assert normalizar_nivel(0) == 1
    assert normalizar_nivel(2) == 2
    assert normalizar_nivel(9) == 4


def test_falta_runtime_sanitizers_variantes_de_mensaje():
    assert _falta_runtime_sanitizers("/usr/bin/ld.bfd: cannot find /usr/lib64/libasan.so.8.0.0")
    assert _falta_runtime_sanitizers("cannot find -lubsan")
    assert not _falta_runtime_sanitizers("error: expected ';' before 'return'")


def _fake_compilador(exitoso=True):
    def fake(fuentes, salida, enable_asan=False, extra_flags=None):
        return SimpleNamespace(success=exitoso, return_code=0 if exitoso else 1,
                               raw_stderr="", human_summary="",
                               translated_diagnostics=[], binary_path=None)
    return fake


def test_nivel1_omite_cuando_el_host_no_tiene_runtimes(tmp_path, monkeypatch):
    fuente = tmp_path / "m.c"
    fuente.write_text("int main(void){return 0;}\n")

    monkeypatch.setattr(ub_sentinel, "compile_sources", _fake_compilador(exitoso=False))
    # y hacemos que el stderr parezca falta de runtime
    def fake_comp_con_stderr(fuentes, salida, enable_asan=False, extra_flags=None):
        return SimpleNamespace(success=False, return_code=1,
                               raw_stderr="cannot find /usr/lib64/libasan.so.8.0.0",
                               human_summary="", translated_diagnostics=[],
                               binary_path=None)
    monkeypatch.setattr(ub_sentinel, "compile_sources", fake_comp_con_stderr)

    reporte = auditar_ub([fuente], [], nivel_maximo=1)
    assert any("sanitizers" in o for o in reporte.omitidos)
    assert not reporte.hay_errores


def test_nivel1_clasifica_overflow_y_division(tmp_path, monkeypatch):
    fuente = tmp_path / "m.c"
    fuente.write_text("int main(void){return 0;}\n")

    stderr_falso = (
        "m.c:6:12: runtime error: signed integer overflow: 2147483647 + 1 "
        "cannot be represented in type 'int'\n"
        "m.c:10:15: runtime error: division by zero\n"
    )
    monkeypatch.setattr(ub_sentinel, "compile_sources", _fake_compilador(True))
    monkeypatch.setattr(ub_sentinel, "_correr_binario",
                        lambda binario, datos, timeout: SimpleNamespace(
                            returncode=0, stderr=stderr_falso, stdout=""))

    casos = tmp_path / "caso_01.in"
    casos.write_bytes(b"1\n")

    reporte = auditar_ub([fuente], [casos], nivel_maximo=1)
    categorias = {h.categoria for h in reporte.hallazgos}
    assert f"{ub_sentinel.__name__}" == "ripley.core.ub_sentinel"  # sanidad
    assert any("INTEGER_OVERFLOW" in c for c in categorias), categorias
    assert any("DIVISION_BY_ZERO" in c for c in categorias), categorias
    assert reporte.hay_errores


def test_nivel2_registra_omitido_sin_clang(tmp_path, monkeypatch):
    fuente = tmp_path / "m.c"
    fuente.write_text("int main(void){return 0;}\n")
    monkeypatch.setattr(ub_sentinel.shutil, "which", lambda nombre: None)

    reporte = auditar_ub([fuente], [], nivel_maximo=2)
    assert any("clang" in o for o in reporte.omitidos)


def test_nivel4_tsan_solo_con_hilos(tmp_path, monkeypatch):
    fuente_sin_hilos = tmp_path / "sin_hilos.c"
    fuente_sin_hilos.write_text("int main(void){return 0;}\n")

    llamados = []

    def espia(fuentes, salida, enable_asan=False, extra_flags=None):
        llamados.append(list(extra_flags or []))
        return SimpleNamespace(success=False, return_code=1, raw_stderr="",
                               human_summary="", translated_diagnostics=[],
                               binary_path=None)

    monkeypatch.setattr(ub_sentinel, "compile_sources", espia)

    reporte = auditar_ub([fuente_sin_hilos], [], nivel_maximo=4)
    # el nivel 1 compila; el nivel 4 NO debe intentar compilar con -fsanitize=thread
    assert not any("-fsanitize=thread" in f for f in llamados), llamados
    assert all(h.nivel != 4 for h in reporte.hallazgos)


def test_reporte_resumen_incluye_omitidos():
    reporte = ReporteUB(hallazgos=[], omitidos=["clang (nivel 2)"], niveles_ejecutados=[1, 2])
    resumen = reporte.resumen()
    assert "clang" in resumen and "hallazgo(s)" in resumen
