"""Tests unitarios para el descubrimiento dinámico de plugins vía entrypoints en Ripley."""

from pathlib import Path
from ripley.pipeline.entrypoints import discover_entrypoint_plugins


def test_discover_entrypoint_plugins():
    plugins = discover_entrypoint_plugins()
    # Verifica que la función retorne una lista de plugins registrados
    assert isinstance(plugins, list)


def test_discovered_plugin_execute_adapter(tmp_path: Path):
    from ripley.pipeline.entrypoints import DiscoveredPlugin

    class DummyExecutePlugin:
        name = "dummy_exec"

        def execute(self, workspace, config):
            return {"ok": True, "observaciones": [{"codigo": "DUMMY01", "mensaje": "ok"}]}

    class DummyRunPlugin:
        name = "dummy_run"

        def run(self, context):
            return {
                "passed": False,
                "issues": [
                    {
                        "code": "RUN01",
                        "severity": "ERROR",
                        "location": "foo.c",
                        "line": 10,
                        "column": 5,
                        "message": "run issue",
                        "suggestion": "fix it",
                    }
                ],
            }

    p1 = DiscoveredPlugin(name="dummy_exec", group="ripley.plugins", entry_point=None, instance=DummyExecutePlugin())
    res1 = p1.execute(tmp_path)
    assert res1["ok"] is True
    assert len(res1["observaciones"]) == 1

    p2 = DiscoveredPlugin(name="dummy_run", group="ripley.plugins", entry_point=None, instance=DummyRunPlugin())
    res2 = p2.execute(tmp_path)
    assert res2["ok"] is False
    assert len(res2["observaciones"]) == 1
    assert res2["observaciones"][0]["codigo"] == "RUN01"
    # Verificar esquema canónico normalizado
    obs = res2["observaciones"][0]
    assert obs["rule_code"] == "RUN01"
    assert obs["source_plugin"] == "dummy_run"
    assert obs["severity"] == "ERROR"
    assert obs["line"] == 10
    assert obs["column"] == 5


def test_satellite_plugin_adapter_cli_fallback(tmp_path: Path, monkeypatch):
    import subprocess
    from ripley.core.entrypoints import SatellitePluginAdapter

    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")

    def fake_subprocess_run(args, capture_output=True, text=True, timeout=20):
        output = {
            "ok": True,
            "observaciones": [
                {
                    "rule_code": "CLI_01",
                    "rule_name": "Alerta CLI",
                    "severity": "ADVERTENCIA",
                    "file": "test.c",
                    "line": 4,
                    "column": 2,
                    "message": "Mensaje desde CLI simulado",
                    "suggestion": "Arreglo CLI",
                }
            ],
        }
        import json
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps(output), stderr="")

    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    adapter = SatellitePluginAdapter(
        name="style",
        tool_name="gaff",
        cli_command="gaff",
        entry_point=None,
        instance=None,
    )
    assert adapter.execution_mode == "cli"
    assert adapter.is_available is True

    res = adapter.execute(tmp_path)
    assert res["ok"] is True
    assert len(res["observaciones"]) == 1
    obs = res["observaciones"][0]
    assert obs["rule_code"] == "CLI_01"
    assert obs["source_plugin"] == "style"
    assert obs["message"] == "Mensaje desde CLI simulado"


def test_satellite_plugin_adapter_missing_tool(tmp_path: Path, monkeypatch):
    from ripley.core.entrypoints import SatellitePluginAdapter

    # Simular que el binario no existe en PATH
    monkeypatch.setattr("shutil.which", lambda cmd: None)

    adapter = SatellitePluginAdapter(
        name="callahan",
        tool_name="callahan",
        cli_command="callahan",
        entry_point=None,
        instance=None,
    )
    assert adapter.is_available is False
    assert adapter.execution_mode == "unavailable"

    # En modo normal emite ADVERTENCIA y no bloquea (ok=True)
    res = adapter.execute(tmp_path, strict=False)
    assert res["ok"] is True
    assert res.get("missing_tool") is True
    assert len(res["observaciones"]) == 1
    obs = res["observaciones"][0]
    assert obs["rule_code"] == "MISSING_TOOL_CALLAHAN"
    assert obs["severity"] == "ADVERTENCIA"
    assert "uv tool install callahan" in obs["suggestion"]

    # Bajo --strict se eleva a ERROR y falla (ok=False)
    res_strict = adapter.execute(tmp_path, strict=True)
    assert res_strict["ok"] is False
    assert res_strict["observaciones"][0]["severity"] == "ERROR"


def test_satellite_plugin_adapter_fail_open_resilience(tmp_path: Path):
    from ripley.core.entrypoints import SatellitePluginAdapter

    class FaultyPlugin:
        def execute(self, workspace, config):
            raise RuntimeError("Fallo catastrófico no controlado en analizador externo")

    adapter = SatellitePluginAdapter(
        name="security",
        tool_name="kaneda",
        instance=FaultyPlugin(),
    )
    res = adapter.execute(tmp_path)
    assert res["ok"] is False
    assert len(res["observaciones"]) == 1
    obs = res["observaciones"][0]
    assert obs["rule_code"] == "PLUGIN_ERROR_KANEDA"
    assert obs["severity"] == "ERROR"
    assert "Fallo catastrófico" in obs["message"]


def test_fuzzing_entrypoint_resolves_to_drake(monkeypatch):
    import shutil
    from ripley.core.entrypoints import SatellitePluginAdapter

    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}" if cmd == "drake" else None)

    adapter = SatellitePluginAdapter(
        name="fuzzing",
        entry_point=None,
        instance=None,
    )
    assert adapter.tool_name == "drake"
    assert adapter.cli_command == "drake"
    assert adapter.is_available is True
    assert adapter.execution_mode == "cli"


def test_brett_padding_normalization(tmp_path: Path):
    from ripley.core.entrypoints import SatellitePluginAdapter

    class BrettPlugin:
        def execute(self, workspace, config):
            return {
                "total_structs": 1,
                "total_wasted_bytes": 12,
                "structs": [
                    {
                        "name": "struct Nodo",
                        "size_bytes": 32,
                        "wasted_padding_bytes": 12,
                        "file": "list.c",
                        "line": 15,
                    }
                ]
            }

    adapter = SatellitePluginAdapter(name="padding", tool_name="brett", instance=BrettPlugin())
    res = adapter.execute(tmp_path)
    assert res["ok"] is True
    assert len(res["observaciones"]) == 1
    obs = res["observaciones"][0]
    assert obs["rule_code"] == "PADDING_INEFFICIENT"
    assert obs["severity"] == "ADVERTENCIA"
    assert "12 bytes de padding" in obs["message"]
    assert obs["line"] == 15


def test_wierzbowski_cycles_and_guards_normalization(tmp_path: Path):
    from ripley.core.entrypoints import SatellitePluginAdapter

    class WierzbowskiPlugin:
        def execute(self, workspace, config):
            return {
                "ok": True,
                "guard_issues": ["El archivo header.h carece de include guard o #pragma once."],
                "cycles": [
                    {
                        "cycle": ["a.h", "b.h", "a.h"],
                        "description": "Dependencia circular detectada entre a.h y b.h"
                    }
                ]
            }

    adapter = SatellitePluginAdapter(name="headers_audit", tool_name="wierzbowski", instance=WierzbowskiPlugin())
    res = adapter.execute(tmp_path)
    assert res["ok"] is True
    assert len(res["observaciones"]) == 2
    codes = {o["rule_code"] for o in res["observaciones"]}
    assert "GUARD_MISSING" in codes
    assert "CIRCULAR_DEPENDENCY" in codes



