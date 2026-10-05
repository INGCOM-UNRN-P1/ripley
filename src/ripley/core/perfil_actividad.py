"""Perfil de satélites por actividad y hallazgos en la forma común (revisión 07, ripley).

Perfil: qué satélites corren según el tema de la actividad. Antes había que activarlos a mano; con
`[actividad] tema = "punteros"` en el ripley.toml corren los de base y los del tema (bishop y tetsuo
para punteros), incluidos los dinámicos. `satelites = [...]` los fija explícitamente.

Hallazgos: el JSON de ripley suma `hallazgos`, cada observación en la forma común del ecosistema
(`yutani.hallazgos`), con categoría y enlace al apunte: el sobre único que dredd y el apunte leen sin
saber de qué satélite vino cada una.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

BASE = ("gaff", "spunkmeyer", "kaneda")
TEMAS: Dict[str, tuple] = {
    "introduccion": (),
    "control": ("dietrich",),
    "funciones": ("giger", "corbel"),
    "recursion": ("sebastian", "giger"),
    "punteros": ("bishop", "tetsuo"),
    "memoria": ("bishop", "tetsuo", "vasquez"),
    "arreglos": ("tetsuo", "drake"),
    "cadenas": ("tetsuo", "drake"),
    "estructuras": ("brett", "bishop"),
    "archivos": ("kane", "vasquez"),
    "tad": ("motoko", "corbel", "wierzbowski"),
    "modulos": ("wierzbowski", "motoko", "corbel"),
    "macros": ("zhora",),
    "pruebas": ("vassili", "dietrich", "tyrell"),
    "rendimiento": ("ferro",),
}


def satelites_de_la_actividad(base: Path) -> Optional[Set[str]]:
    """Las herramientas a correr según el ripley.toml del proyecto, o None si no fija un perfil."""
    directorio = base if base.is_dir() else base.parent
    for candidato in dict.fromkeys((directorio / "ripley.toml", Path.cwd() / "ripley.toml")):
        if not candidato.is_file():
            continue
        try:
            actividad = tomllib.loads(candidato.read_text(encoding="utf-8")).get("actividad", {})
        except (OSError, tomllib.TOMLDecodeError):
            return None
        if not isinstance(actividad, dict):
            return None
        if actividad.get("satelites"):
            return {str(s).lower() for s in actividad["satelites"]}
        tema = str(actividad.get("tema", "")).lower()
        if tema in TEMAS:
            return set(BASE) | set(TEMAS[tema])
        return None
    return None


def incluido(nombre_plugin: str, herramienta: Optional[str], perfil: Set[str]) -> bool:
    return nombre_plugin.lower() in perfil or (herramienta or "").lower() in perfil


_REGLA = re.compile(r"^0x[0-9A-Fa-f]{4}h$")
_POR_FAMILIA = {"0": "estilo", "1": "control", "2": "funciones", "3": "memoria", "4": "archivos",
                "5": "seguridad", "6": "compilacion", "7": "funciones", "8": "pruebas"}
_POR_HERRAMIENTA = {"kaneda": "seguridad", "security": "seguridad", "tetsuo": "memoria", "bishop": "memoria",
                    "corbel": "documentacion", "documentation": "documentacion", "motoko": "tad",
                    "tda_encapsulation": "tad", "brett": "estructuras", "padding": "estructuras",
                    "wierzbowski": "compilacion", "zhora": "compilacion", "compiler": "compilacion"}


def a_hallazgos(observaciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from yutani.hallazgos import hallazgo

    resultado = []
    for o in observaciones:
        codigo = str(o.get("rule_code") or o.get("codigo") or "").strip()
        if not codigo:
            continue
        herramienta = (str(o.get("source_plugin") or "ripley").strip().lower() or "ripley").replace(":", "_")
        categoria = (_POR_FAMILIA.get(codigo[2], "estilo") if _REGLA.match(codigo)
                     else _POR_HERRAMIENTA.get(herramienta, "estilo"))
        severidad = str(o.get("severity") or o.get("severidad") or "advertencia")
        try:
            resultado.append(hallazgo(herramienta, codigo, categoria, severidad, str(o.get("message") or ""),
                                      archivo=o.get("file"), linea=o.get("line") or None))
        except ValueError:
            resultado.append(hallazgo(herramienta, codigo, categoria, "advertencia", str(o.get("message") or ""),
                                      archivo=o.get("file"), linea=o.get("line") or None))
    return resultado
