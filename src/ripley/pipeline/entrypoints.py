"""Descubrimiento dinámico de plugins y subherramientas desacopladas vía entrypoints (re-export desde core)."""

from __future__ import annotations

from ripley.core.entrypoints import (
    DiscoveredPlugin,
    SatellitePluginAdapter,
    discover_entrypoint_plugins,
    get_satellite_plugin,
)

__all__ = [
    "DiscoveredPlugin",
    "SatellitePluginAdapter",
    "discover_entrypoint_plugins",
    "get_satellite_plugin",
]

