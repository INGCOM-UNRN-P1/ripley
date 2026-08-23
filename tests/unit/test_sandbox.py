"""Unit tests for unprivileged Linux-namespace sandboxing."""

import shutil

import pytest

from ripley.tools.sandbox import NamespaceSandbox


def test_detect_strategy_returns_known_value():
    sandbox = NamespaceSandbox()
    strategy = sandbox.detect_strategy()
    assert strategy in {"bubblewrap", "unshare", "none"}


def test_run_trivial_binary(tmp_path):
    src = tmp_path / "eco.c"
    src.write_text('#include <stdio.h>\nint main(void){ puts("sandbox-ok"); return 0; }\n', encoding="utf-8")
    binary = tmp_path / "eco.out"
    if not shutil.which("gcc"):
        pytest.skip("gcc no disponible")
    import subprocess

    res = subprocess.run(["gcc", "-std=c11", str(src), "-o", str(binary)], capture_output=True)
    assert res.returncode == 0

    sandbox = NamespaceSandbox(timeout_sec=10)
    result = sandbox.run(binary)
    assert result.success
    assert "sandbox-ok" in result.stdout
    assert result.strategy == sandbox.detect_strategy()
    assert (result.strategy != "none") == result.isolated


def test_self_test_consistency():
    sandbox = NamespaceSandbox()
    report = sandbox.self_test()
    if sandbox.detect_strategy() == "none":
        assert not report.isolated
    else:
        assert report.success
        assert "ok" in report.stdout


def test_run_missing_binary():
    sandbox = NamespaceSandbox()
    result = sandbox.run("/no/existe/binario_xyz")
    assert not result.success
    assert "Binario no encontrado" in result.message
