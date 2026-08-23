"""Unified check registry: single source of truth shared by teacher evaluate and student CLI."""

from dataclasses import dataclass, field
import shutil
from typing import Callable, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class CheckSpec:
    """Metadatos declarativos de una verificación de Ripley.

    check_id        Identificador estable ("ast.backward_goto").
    title           Descripción breve para informes y `checks list`.
    layer           "static" (análisis puro) | "dynamic" (ejecuta procesos).
    scope           "student" (útil al estudiante) | "teacher" | "both".
    config_section  Sección de ripley.toml que la gobierna ("" = sin config).
    toggle          Sub-clave booleana dentro de la sección ("" = sección entera / enabled).
    requires_tools  Ejecutables externos necesarios para poder correr.
    prefix          Etiqueta usada en los mensajes del informe docente.
    runner          Para checks estáticos uniformes: fn(code, filename) -> list[LinterObservation].
    """

    check_id: str
    title: str
    layer: str
    scope: str
    config_section: str = ""
    toggle: str = ""
    requires_tools: tuple = ()
    prefix: str = ""
    runner: Optional[Callable] = None

    @property
    def is_static(self) -> bool:
        return self.layer == "static"

    @property
    def is_student_visible(self) -> bool:
        return self.scope in ("student", "both")


_REGISTRY: Dict[str, CheckSpec] = {}


def register(spec: CheckSpec) -> None:
    _REGISTRY[spec.check_id] = spec


def get(check_id: str) -> Optional[CheckSpec]:
    return _REGISTRY.get(check_id)


def all_checks() -> List[CheckSpec]:
    return sorted(_REGISTRY.values(), key=lambda s: s.check_id)


def iter_by_layer(layer: str) -> Iterable[CheckSpec]:
    return [s for s in all_checks() if s.layer == layer]


def iter_uniform_static() -> Iterable[CheckSpec]:
    """Checks estáticos con firma uniforme runner(code, filename) -> observaciones."""
    return [s for s in iter_by_layer("static") if s.runner is not None]


def iter_student() -> Iterable[CheckSpec]:
    return [s for s in all_checks() if s.is_student_visible]


def is_runnable(spec: CheckSpec, tools_available: Dict[str, bool]) -> bool:
    return all(tools_available.get(t, False) for t in spec.requires_tools)
