"""Shared data contracts used across Ripley layers."""

from dataclasses import dataclass


@dataclass
class LinterObservation:
    """Hallazgo uniforme de cualquier analizador estático de fuente C."""

    linter_name: str
    filename: str
    line: int
    severity: str  # "ADVERTENCIA" | "ESTILO" | "ERROR"
    message: str
    suggestion: str = ""
