"""Los errores de ASan, traducidos por tetsuo cuando está instalado (N-ECO-12)."""

import sys
import types

from ripley.core import ub_sentinel


def test_sin_tetsuo_devuelve_none(monkeypatch):
    monkeypatch.setitem(sys.modules, "tetsuo.core.sanitizer_parser", None)
    assert ub_sentinel._asan_con_tetsuo("==1==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x1") is None


def test_con_tetsuo_usa_su_traduccion(monkeypatch):
    diag = types.SimpleNamespace(sanitizer_type=types.SimpleNamespace(name="ASAN"), title_es="Desborde",
                                 explanation_es="e", suggestion_es="s", file_path="a.c", line_number=3)
    modulo = types.ModuleType("tetsuo.core.sanitizer_parser")
    modulo.parse_sanitizer_output = lambda texto: [diag]
    monkeypatch.setitem(sys.modules, "tetsuo.core.sanitizer_parser", modulo)
    assert ub_sentinel._asan_con_tetsuo("x") == [diag]
