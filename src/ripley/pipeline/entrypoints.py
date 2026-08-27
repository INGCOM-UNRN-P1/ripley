"""Descubrimiento dinámico de plugins y subherramientas desacopladas vía entrypoints."""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DiscoveredPlugin:
    name: str
    group: str
    entry_point: Any
    instance: Any = None
    is_available: bool = True

    def execute(self, workspace: Path, manifest_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.instance:
            cls = self.entry_point.load()
            self.instance = cls()
        if hasattr(self.instance, "execute"):
            return self.instance.execute(workspace, manifest_config or {})
        return {"ok": True, "observaciones": []}


def discover_entrypoint_plugins() -> List[DiscoveredPlugin]:
    """Descubre todos los plugins registrados en el grupo 'ripley.plugins'."""
    plugins = []
    try:
        eps = importlib.metadata.entry_points(group="ripley.plugins")
        for ep in eps:
            try:
                cls = ep.load()
                inst = cls()
                avail = inst.is_available() if hasattr(inst, "is_available") else True
                plugins.append(DiscoveredPlugin(
                    name=ep.name,
                    group="ripley.plugins",
                    entry_point=ep,
                    instance=inst,
                    is_available=avail,
                ))
            except Exception:
                plugins.append(DiscoveredPlugin(
                    name=ep.name,
                    group="ripley.plugins",
                    entry_point=ep,
                    is_available=False,
                ))
    except Exception:
        pass
    return plugins
