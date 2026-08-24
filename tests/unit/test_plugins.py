"""Tests for the lifecycle plugin system and git-hook shims."""

import stat
from pathlib import Path

import pytest

from ripley.pipeline.plugins import (
    HOOKS,
    PluginContext,
    PluginError,
    PluginManager,
    collect_git_staged_c_sources,
    discover_plugins,
    install_git_hook,
    is_ripley_git_hook,
    uninstall_git_hook,
)


@pytest.fixture()
def plugins_dir(tmp_path):
    d = tmp_path / "plugins"
    d.mkdir()
    return d


def _write_plugin(d: Path, name: str, body: str) -> Path:
    f = d / name
    f.write_text(body, encoding="utf-8")
    return f


def test_discover_ignores_private_and_collects_hooks(plugins_dir):
    _write_plugin(plugins_dir, "a_primero.py", "def pre_compile(ctx):\n    ctx.set('x', 1)\n")
    _write_plugin(plugins_dir, "_secreto.py", "raise SystemExit\n")
    (plugins_dir / "notas.txt").write_text("no soy python")

    loaded = discover_plugins(plugins_dir)
    assert [p.name for p in loaded] == ["a_primero"]
    assert "pre_compile" in loaded[0].hooks


def test_dispatch_order_follows_filename_and_shares_context(plugins_dir):
    _write_plugin(plugins_dir, "b_segundo.py", "def post_checks(ctx):\n    ctx.set('orden', ctx.get('orden', '') + 'B')\n")
    _write_plugin(plugins_dir, "a_primero.py", "def post_checks(ctx):\n    ctx.set('orden', ctx.get('orden', '') + 'A')\n")

    manager = PluginManager(plugins_dir)
    ctx = PluginContext(phase="post_checks", workspace_dir=plugins_dir.parent)
    errors = manager.dispatch("post_checks", ctx)
    assert errors == 0
    assert ctx.get("orden") == "AB"


def test_plugin_exception_is_fail_open_but_counted(plugins_dir):
    _write_plugin(plugins_dir, "roto.py", "def session_start(ctx):\n    raise ValueError('boom')\n")
    _write_plugin(plugins_dir, "sano.py", "def session_start(ctx):\n    ctx.set('ok', True)\n")

    manager = PluginManager(plugins_dir)
    ctx = PluginContext(phase="session_start", workspace_dir=plugins_dir.parent)
    errors = manager.dispatch("session_start", ctx)
    assert errors == 1 and ctx.get("ok") is True
    assert "boom" in manager.errors[0]


def test_strict_mode_raises(plugins_dir):
    _write_plugin(plugins_dir, "roto.py", "def pre_compile(ctx):\n    1 / 0\n")
    manager = PluginManager(plugins_dir, strict=True)
    with pytest.raises(PluginError):
        manager.dispatch("pre_compile", PluginContext(phase="pre_compile", workspace_dir=plugins_dir.parent))


def test_unknown_hook_rejected(plugins_dir):
    manager = PluginManager(plugins_dir)
    with pytest.raises(ValueError, match="desconocido"):
        manager.dispatch("teleport", PluginContext(phase="x", workspace_dir=plugins_dir.parent))


def test_env_var_disables_plugins(tmp_path, monkeypatch):
    monkeypatch.setenv("RIPLEY_DISABLE_PLUGINS", "1")
    d = tmp_path / "plugins"
    d.mkdir()
    _write_plugin(d, "algo.py", "def session_start(ctx):\n    pass\n")
    manager = PluginManager(d)
    assert manager.plugins == []
    assert manager.disabled


def test_git_hook_install_preserves_previous_and_uninstall_restores(tmp_path):
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    original = hooks / "pre-commit"
    original.write_text("#!/bin/sh\necho hook del profe\n")
    original.chmod(0o755)

    install_git_hook(tmp_path, "pre-commit")
    shim = original.read_text(encoding="utf-8")
    assert "Instalado por Ripley" in shim
    assert "pre_commit_git" in shim
    assert original.stat().st_mode & stat.S_IXUSR

    backup = hooks / "pre-commit.ripley.bak"
    assert backup.exists() and "hook del profe" in backup.read_text()

    assert uninstall_git_hook(tmp_path, "pre-commit") is True
    assert "hook del profe" in original.read_text()
    assert not backup.exists()


def test_uninstall_refuses_foreign_hooks(tmp_path):
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    ajeno = hooks / "pre-commit"
    ajeno.write_text("#!/bin/sh\necho mío\n")

    assert uninstall_git_hook(tmp_path, "pre-commit") is False
    assert ajeno.exists()  # intacto


def test_status_detects_ripley_shim(tmp_path):
    install_git_hook(tmp_path, "pre-commit")
    assert is_ripley_git_hook(tmp_path, "pre-commit") is True


def test_collect_staged_sources_filters_c(tmp_path, monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = "main.c\nREADME.md\nlib/util.c\ndocs/nota.c.txt\nborrado.c\n"

    def fake_run(*args, **kwargs):
        return FakeProc()

    (tmp_path / "main.c").write_text("int main(){}\n")
    sub = tmp_path / "lib"
    sub.mkdir()
    (sub / "util.c").write_text("int u;\n")

    import ripley.pipeline.plugins as pl

    monkeypatch.setattr(pl.subprocess, "run", fake_run)
    srcs = collect_git_staged_c_sources(tmp_path)
    names = {p.name for p in srcs}
    assert names == {"main.c", "util.c"}  # README y .txt fuera; borrado.c no existe en disco


def test_all_declared_hooks_are_documented_names():
    assert HOOKS[0] == "session_start" and HOOKS[-2] == "session_end" and HOOKS[-1] == "pre_commit_git"
