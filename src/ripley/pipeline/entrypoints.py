"""Descubrimiento dinámico de plugins y subherramientas desacopladas vía entrypoints (re-export desde core)."""

from __future__ import annotations

from ripley.core.entrypoints import DiscoveredPlugin, discover_entrypoint_plugins

__all__ = ["DiscoveredPlugin", "discover_entrypoint_plugins"]

