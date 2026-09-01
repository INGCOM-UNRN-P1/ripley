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

