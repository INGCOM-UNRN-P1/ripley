"""Reglas que una actividad no evalúa (QoL #808).

La supresión por comentario (`// ripley:disable=...`, ver p1_suppressions.py) es del estudiante y
de una línea o un archivo. Esta es del docente y de toda la actividad: en el TP1, por ejemplo, no
se evalúan las reglas de módulos. Se declara en el ripley.toml de la actividad

    [reglas]
    ignorar = ["0x40*h", "gaff:0x0101h", "MAGIC_NUMBER"]

o en un `.ripleyignore` (un patrón por línea, `#` para comentarios) junto al proyecto. Un patrón
es un código, un comodín (`fnmatch`, sin distinguir mayúsculas) o `herramienta:código`.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _de_ripleyignore(archivo: Path) -> List[str]:
    patrones = []
    for linea in archivo.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea:
            patrones.append(linea)
    return patrones


def patrones_de_la_actividad(base: Optional[Path]) -> List[str]:
    """Los patrones del ripley.toml y del .ripleyignore del proyecto (o del directorio actual)."""
    from ripley.config import load_config

    directorio = Path(base or Path.cwd())
    if directorio.is_file():
        directorio = directorio.parent
    patrones: List[str] = []
    for candidato in dict.fromkeys((directorio, Path.cwd())):
        toml = candidato / "ripley.toml"
        if toml.is_file():
            try:
                patrones += load_config(toml).reglas.ignorar
            except Exception:  # noqa: BLE001 — un ripley.toml roto lo informa `ripley config`, no este filtro
                pass
        ignore = candidato / ".ripleyignore"
        if ignore.is_file():
            patrones += _de_ripleyignore(ignore)
        if patrones:
            break
    return patrones


def _nombres(hallazgo: Dict[str, Any]) -> Iterable[str]:
    from ripley.core.engine import normalize_rule_code

    codigo = str(hallazgo.get("rule_code") or hallazgo.get("codigo") or "")
    herramienta = str(hallazgo.get("source_plugin") or "")
    for c in dict.fromkeys((codigo, normalize_rule_code(codigo) if codigo else "")):
        if c:
            yield c.lower()
            if herramienta:
                yield f"{herramienta}:{c}".lower()


def filtrar_ignoradas(hallazgos: List[Dict[str, Any]], patrones: List[str]) -> List[Dict[str, Any]]:
    if not patrones:
        return hallazgos
    patrones_min = [p.lower() for p in patrones]
    return [h for h in hallazgos
            if not any(fnmatch.fnmatchcase(n, p) for n in _nombres(h) for p in patrones_min)]
