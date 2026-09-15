"""Analizador de estilo y formato de código C delegando en el linter pedagógico GAFF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional, Set

from ripley.config import StyleConfig


@dataclass
class StyleObservation:
    archivo: str
    linea: int
    regla: str
    mensaje: str


@dataclass
class StyleCheckResult:
    archivo: str
    score: float  # 0.0 a 10.0
    passed: bool
    observaciones: List[StyleObservation]


CONTROL_KEYWORDS = ("if", "for", "while", "switch", "else if")


class StyleAnalyzer:
    """Analiza reglas de estilo de código C delegando todas las verificaciones en GAFF."""

    def __init__(self, config: StyleConfig) -> None:
        self.config = config

    def analyze_code(self, filename: str, code: str) -> StyleCheckResult:
        """Analiza una cadena de código C delegando en GAFF mediante archivo temporal."""
        suffix = Path(filename).suffix if Path(filename).suffix in (".c", ".h") else ".c"
        clean_stem = Path(filename).stem or "source"
        with tempfile.TemporaryDirectory() as td:
            temp_file = Path(td) / f"{clean_stem}{suffix}"
            temp_file.write_text(code, encoding="utf-8", errors="replace")
            return self.analyze_file(temp_file, display_filename=filename, raw_code=code)

    def analyze_file(
        self,
        file_path: str | Path,
        display_filename: Optional[str] = None,
        raw_code: Optional[str] = None,
    ) -> StyleCheckResult:
        """Analiza un archivo fuente C ejecutando las verificaciones de estilo a través de GAFF."""
        path = Path(file_path)
        fname = display_filename or path.name

        if raw_code is None and path.is_file():
            raw_code = path.read_text(encoding="utf-8", errors="replace")

        observaciones: List[StyleObservation] = []

        is_allman = self.config.brace_style.lower() in ("allman", "bsd", "break")
        is_kr = self.config.brace_style.lower() in ("k&r", "attach")

        # 1. Delegar en GAFF mediante modo EXCLUSIÓN (filosofía institucional de cátedra)
        try:
            from gaff.core.linter import analizar_archivo

            reglas_excluidas: Set[str] = set()
            if not is_allman:
                reglas_excluidas.update({"0x0007h", "0x000Bh", "0x0009h"})
            if not self.config.require_braces:
                reglas_excluidas.update({"0x1001h", "0x0008h"})
            if not self.config.spacing_keywords:
                reglas_excluidas.update({"0x0004h", "0x0011h", "0x0022h"})
            if not self.config.spacing_operators:
                reglas_excluidas.update({"0x0003h"})
            if self.config.indent_style != "spaces" and not self.config.no_trailing_whitespace:
                reglas_excluidas.update({"0x0004h", "0x0005h"})
            if not self.config.max_blank_lines:
                reglas_excluidas.update({"0x000Dh"})

            violaciones_gaff = analizar_archivo(path, reglas_excluidas=reglas_excluidas)

            for v in violaciones_gaff:
                cod = str(v.codigo)
                regla_id = cod
                msg_low = v.mensaje.lower()
                if cod in ("0x1001h", "0x0008h") or "sin bloque de llaves" in msg_low:
                    regla_id = "require_braces"
                elif cod in ("0x0007h", "0x0009h", "0x000Bh") or "allman" in msg_low or "estilo allman" in msg_low:
                    regla_id = "brace_style"
                elif cod in ("0x0011h", "0x0022h") or (cod == "0x0004h" and "palabra clave" in msg_low) or "palabra clave" in msg_low:
                    regla_id = "spacing_keywords"
                elif cod in ("0x0003h",) or "operador" in msg_low:
                    regla_id = "spacing_operators"
                elif cod in ("0x0004h", "0x0005h"):
                    if "trailing" in msg_low or "final" in msg_low:
                        regla_id = "trailing_whitespace"
                    else:
                        regla_id = "indent_style"
                elif cod == "0x000Dh":
                    regla_id = "max_blank_lines"
                elif "coma" in msg_low:
                    regla_id = "spacing_comma"

                observaciones.append(
                    StyleObservation(
                        archivo=fname,
                        linea=v.linea,
                        regla=regla_id,
                        mensaje=f"[{cod}] {v.mensaje}",
                    )
                )

        except ImportError:
            # Fallback en caso de que gaff no esté instalado en el entorno de ejecución
            try:
                from ripley.core.entrypoints import get_satellite_plugin
                gaff_plugin = get_satellite_plugin("style")
                if gaff_plugin and gaff_plugin.is_available:
                    res = gaff_plugin.execute(path)
                    raw_obs = res.get("observaciones") or res.get("issues") or []
                    for obs in raw_obs:
                        cod = str(obs.get("codigo") or obs.get("rule_code") or "style")
                        msg = str(obs.get("mensaje") or obs.get("message") or "")
                        linea = int(obs.get("linea") or obs.get("line") or 1)
                        observaciones.append(
                            StyleObservation(
                                archivo=fname,
                                linea=linea,
                                regla=cod,
                                mensaje=f"[{cod}] {msg}",
                            )
                        )
            except Exception:
                pass

        # 2. Verificación adicional para configuraciones explícitas de estilo K&R
        if is_kr and raw_code:
            clean_lines = raw_code.splitlines()
            for idx, line in enumerate(clean_lines, start=1):
                s_line = line.strip()
                for kw in ("if", "for", "while", "switch", "else", "int main()", "void "):
                    if re.search(rf"(?<![a-zA-Z0-9_]){kw}\b", s_line) and not s_line.endswith("{"):
                        for n_i in range(idx, len(clean_lines)):
                            nxt = clean_lines[n_i].strip()
                            if nxt:
                                if nxt.startswith("{"):
                                    observaciones.append(
                                        StyleObservation(
                                            archivo=fname,
                                            linea=n_i + 1,
                                            regla="brace_style",
                                            mensaje=f"Estilo K&R violado: la llave tras '{kw}' debe ir en la misma línea.",
                                        )
                                    )
                                break

        # 3. Cálculo de puntaje final de estilo
        penalty_per_violation = 1.0
        score = max(0.0, 10.0 - (len(observaciones) * penalty_per_violation))
        passed = len(observaciones) == 0

        return StyleCheckResult(
            archivo=fname,
            score=round(score, 2),
            passed=passed,
            observaciones=observaciones,
        )
