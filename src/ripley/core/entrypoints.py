"""Descubrimiento dinámico de plugins y subherramientas desacopladas vía entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
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
        try:
            if not self.instance:
                cls = self.entry_point.load()
                self.instance = cls()
            if hasattr(self.instance, "execute"):
                return self.instance.execute(workspace, manifest_config or {})
            elif hasattr(self.instance, "run"):
                source_dir = workspace if workspace.is_dir() else workspace.parent
                context = {
                    "source_dir": str(source_dir),
                    "workspace": workspace,
                    "manifest_config": manifest_config or {},
                }
                res = self.instance.run(context)
                if isinstance(res, dict):
                    if "issues" in res and "observaciones" not in res:
                        observaciones = []
                        for iss in res["issues"]:
                            observaciones.append({
                                "codigo": iss.get("code") or self.name,
                                "rule_code": iss.get("code") or self.name,
                                "rule_name": iss.get("symbol") or self.name,
                                "severidad": iss.get("severity", "ADVERTENCIA"),
                                "archivo": iss.get("location") or "",
                                "linea": iss.get("line") or 0,
                                "columna": iss.get("column") or 0,
                                "mensaje": iss.get("message") or "",
                                "sugerencia": iss.get("suggestion") or "",
                            })
                        res["observaciones"] = observaciones
                    if "passed" in res and "ok" not in res:
                        res["ok"] = res["passed"]
                    return res
        except Exception as e:
            return {"ok": False, "error": str(e), "observaciones": []}
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
