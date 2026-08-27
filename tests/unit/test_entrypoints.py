"""Tests unitarios para el descubrimiento dinámico de plugins vía entrypoints en Ripley."""

from pathlib import Path
from ripley.pipeline.entrypoints import discover_entrypoint_plugins


def test_discover_entrypoint_plugins():
    plugins = discover_entrypoint_plugins()
    # Verifica que la función retorne una lista de plugins registrados
    assert isinstance(plugins, list)
