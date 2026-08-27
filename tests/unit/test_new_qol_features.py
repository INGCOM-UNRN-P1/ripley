"""Tests unitarios para las nuevas features de Ripley: lazy plugins, supresión // ripley:disable, explain y reportes HTML."""

from pathlib import Path
from typer.testing import CliRunner
import pytest

from ripley.cli.student import app as student_app
from ripley.core.p1_rules import P1RuleChecker, P1_RULES_CATALOG
from ripley.core.html_reporter import generate_interactive_html_report
from ripley.pipeline.plugins import discover_plugins, PluginManager, PluginContext

runner = CliRunner()


def test_lazy_plugin_discovery(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    plugin_file = plugins_dir / "custom_hook.py"
    plugin_file.write_text(
        """
def post_compile(ctx):
    ctx.set("custom_ran", True)
"""
    )

    discovered = discover_plugins(plugins_dir)
    assert len(discovered) == 1
    assert discovered[0].name == "custom_hook"
    assert "post_compile" in discovered[0].hooks

    # Dispatch
    pm = PluginManager(plugins_dir)
    ctx = PluginContext(phase="pre_compile", workspace_dir=tmp_path)
    pm.dispatch("post_compile", ctx)
    assert ctx.get("custom_ran") is True


def test_granular_suppression_comment():
    checker = P1RuleChecker()

    # Código con if sin llaves pero con supresión
    code_suppressed = """
int main(void) {
    int x = 5;
    // ripley:disable=0x1001h
    if (x > 0) x++;
    return x;
}
"""
    obs = checker.analyze(code_suppressed, "main.c")
    assert not any(o.rule_code == "0x1001h" for o in obs)

    # Código sin supresión genera observación 0x1001h
    code_unsuppressed = """
int main(void) {
    int x = 5;
    if (x > 0) x++;
    return x;
}
"""
    obs_raw = checker.analyze(code_unsuppressed, "main.c")
    assert any(o.rule_code == "0x1001h" for o in obs_raw)


def test_cli_explain_command():
    res = runner.invoke(student_app, ["explain", "0x1001h"])
    assert res.exit_code == 0
    assert "0x1001h" in res.stdout
    assert "Código Incorrecto" in res.stdout
    assert "Código Correcto" in res.stdout

    res_all = runner.invoke(student_app, ["explain", "all"])
    assert res_all.exit_code == 0
    assert "Catálogo de Reglas Pedagógicas P1" in res_all.stdout


def test_generate_interactive_html_report(tmp_path: Path):
    out_html = tmp_path / "reporte.html"
    eval_data = {
        "student": "Perez Juan",
        "activity": "Entrega 1",
        "passed": True,
        "score": 9.5,
        "date": "2026-08-27",
        "observations": [
            {
                "rule_code": "0x1001h",
                "title": "Estructuras de control con llaves",
                "severity": "ESTILO",
                "message": "Faltan llaves en sentencia if.",
                "suggestion": "Agregá llaves {...}",
                "filename": "main.c",
                "line": 12,
            }
        ],
    }

    res_path = generate_interactive_html_report(eval_data, out_html)
    assert res_path.is_file()
    content = res_path.read_text(encoding="utf-8")
    assert "Perez Juan" in content
    assert "0x1001h" in content
    assert "badge-approved" in content or "badge-observations" in content
