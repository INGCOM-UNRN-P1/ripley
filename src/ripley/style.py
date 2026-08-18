"""C code style and formatting analyzer based on customizable ripley.toml rules."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Sequence

from ripley.config import StyleConfig
from ripley.security import strip_c_comments_and_strings


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
    """Analiza reglas de estilo de código C según la configuración."""

    def __init__(self, config: StyleConfig) -> None:
        self.config = config

    def analyze_code(self, filename: str, code: str) -> StyleCheckResult:
        observaciones: List[StyleObservation] = []
        raw_lines = code.splitlines()
        clean_code = strip_c_comments_and_strings(code)
        clean_lines = clean_code.splitlines()

        # 1. Chequeo de espacios finales (trailing whitespace) y líneas en blanco consecutivas
        blank_line_streak = 0
        for idx, r_line in enumerate(raw_lines, start=1):
            if self.config.no_trailing_whitespace and re.search(r"[ \t]+$", r_line):
                observaciones.append(
                    StyleObservation(
                        archivo=filename,
                        linea=idx,
                        regla="trailing_whitespace",
                        mensaje="Espacios en blanco al final de la línea.",
                    )
                )

            if not r_line.strip():
                blank_line_streak += 1
                if blank_line_streak > self.config.max_blank_lines:
                    observaciones.append(
                        StyleObservation(
                            archivo=filename,
                            linea=idx,
                            regla="max_blank_lines",
                            mensaje=f"Demasiadas líneas en blanco consecutivas (máximo permitido: {self.config.max_blank_lines}).",
                        )
                    )
            else:
                blank_line_streak = 0

        # 2. Indentación (Spaces vs Tabs y tamaño)
        for idx, (r_line, c_line) in enumerate(zip(raw_lines, clean_lines), start=1):
            if not c_line.strip():
                continue

            leading_whitespace = re.match(r"^([ \t]*)", r_line).group(1)
            if self.config.indent_style == "spaces":
                if "\t" in leading_whitespace:
                    observaciones.append(
                        StyleObservation(
                            archivo=filename,
                            linea=idx,
                            regla="indent_style",
                            mensaje="Uso de tabulaciones (Tab) en la indentación; se requieren espacios.",
                        )
                    )
                elif leading_whitespace and len(leading_whitespace) % self.config.indent_size != 0:
                    observaciones.append(
                        StyleObservation(
                            archivo=filename,
                            linea=idx,
                            regla="indent_size",
                            mensaje=f"La sangría ({len(leading_whitespace)} espacios) no es múltiplo del tamaño configurado ({self.config.indent_size}).",
                        )
                    )
            elif self.config.indent_style == "tabs":
                if " " in leading_whitespace:
                    observaciones.append(
                        StyleObservation(
                            archivo=filename,
                            linea=idx,
                            regla="indent_style",
                            mensaje="Uso de espacios en la sangría; se requieren tabulaciones (Tabs).",
                        )
                    )

        # 3. Espaciado en palabras clave (keyword spacing ej. 'if(' -> 'if (')
        if self.config.spacing_keywords:
            for idx, c_line in enumerate(clean_lines, start=1):
                for kw in ("if", "for", "while", "switch"):
                    # Detectar "if(" o "for(" no precedido de letra/guión bajo
                    kw_match = re.search(rf"(?<![a-zA-Z0-9_]){kw}\(", c_line)
                    if kw_match:
                        observaciones.append(
                            StyleObservation(
                                archivo=filename,
                                linea=idx,
                                regla="spacing_keywords",
                                mensaje=f"Falta espacio entre palabra clave '{kw}' y paréntesis de apertura: use '{kw} ('.",
                            )
                        )

        # 4. Espaciado en operadores binarios y comas
        if self.config.spacing_operators:
            for idx, c_line in enumerate(clean_lines, start=1):
                # Falta de espacio después de coma ej: "foo(a,b)"
                if re.search(r",[^\s\n\)\"]", c_line):
                    observaciones.append(
                        StyleObservation(
                            archivo=filename,
                            linea=idx,
                            regla="spacing_comma",
                            mensaje="Falta espacio después de coma ','.",
                        )
                    )

                # Operadores binarios de comparación y lógicos sin espacios: ==, !=, <=, >=, &&, ||
                for op in ("==", "!=", "<=", ">=", "&&", r"\|\|"):
                    # operador pegado a caracter
                    if re.search(rf"[a-zA-Z0-9_]{op}[a-zA-Z0-9_]", c_line):
                        clean_op = op.replace("\\", "")
                        observaciones.append(
                            StyleObservation(
                                archivo=filename,
                                linea=idx,
                                regla="spacing_operators",
                                mensaje=f"Falta espacio alrededor del operador binario '{clean_op}'.",
                            )
                        )

        # 5. Estilo de Llaves (Allman vs K&R) y Obligatoriedad de Llaves (require_braces)
        is_allman = self.config.brace_style.lower() in ("allman", "bsd", "break")
        is_kr = self.config.brace_style.lower() in ("k&r", "attach")

        for idx, c_line in enumerate(clean_lines, start=1):
            s_line = c_line.strip()
            if not s_line:
                continue

            # Buscar if/for/while/switch
            for kw in ("if", "for", "while", "switch"):
                # Si la línea empieza con o contiene una sentencia de control
                pattern = rf"(?<![a-zA-Z0-9_]){kw}\s*\((.*?)\)"
                match = re.search(pattern, s_line)
                if match:
                    rest_of_line = s_line[match.end():].strip()

                    # Si termina en punto y coma, ej: if (c); o if (c) do_something();
                    if rest_of_line.startswith(";"):
                        # cuerpo vacío con punto y coma
                        continue
                    elif rest_of_line and not rest_of_line.startswith("{") and not rest_of_line.startswith("//"):
                        if self.config.require_braces:
                            observaciones.append(
                                StyleObservation(
                                    archivo=filename,
                                    linea=idx,
                                    regla="require_braces",
                                    mensaje=f"Bloque '{kw}' en una sola línea sin llaves obligatorias {{}}.",
                                )
                            )
                    elif not rest_of_line:
                        # La sentencia de control termina la línea. Mirar la siguiente línea no vacía.
                        next_idx = idx
                        next_line_content = ""
                        for n_i in range(idx, len(clean_lines)):
                            nxt = clean_lines[n_i].strip()
                            if nxt:
                                next_line_content = nxt
                                next_idx = n_i + 1
                                break

                        if next_line_content:
                            if not next_line_content.startswith("{"):
                                if self.config.require_braces:
                                    observaciones.append(
                                        StyleObservation(
                                            archivo=filename,
                                            linea=idx,
                                            regla="require_braces",
                                            mensaje=f"Bloque '{kw}' sin llaves obligatorias {{}} en la siguiente instrucción.",
                                        )
                                    )
                            else:
                                if is_kr:
                                    observaciones.append(
                                        StyleObservation(
                                            archivo=filename,
                                            linea=next_idx,
                                            regla="brace_style",
                                            mensaje=f"Estilo K&R/attach violado: la llave '{{' debe ir en la misma línea que '{kw}'.",
                                        )
                                    )
                    elif rest_of_line.startswith("{"):
                        if is_allman:
                            observaciones.append(
                                StyleObservation(
                                    archivo=filename,
                                    linea=idx,
                                    regla="brace_style",
                                    mensaje=f"Estilo Allman/break violado: la llave '{{' tras '{kw}' debe ir en una nueva línea.",
                                )
                            )

            # Detectar else
            if re.search(r"(?<![a-zA-Z0-9_])else\b", s_line):
                # Verificar si es else if o else
                if not re.search(r"\belse\s+if\b", s_line):
                    rest_else = s_line.split("else", 1)[1].strip()
                    if rest_else.startswith("{"):
                        if is_allman:
                            observaciones.append(
                                StyleObservation(
                                    archivo=filename,
                                    linea=idx,
                                    regla="brace_style",
                                    mensaje="Estilo Allman violado: la llave '{' tras 'else' debe ir en una nueva línea.",
                                )
                            )
                    elif rest_else and not rest_else.startswith("//"):
                        if self.config.require_braces:
                            observaciones.append(
                                StyleObservation(
                                    archivo=filename,
                                    linea=idx,
                                    regla="require_braces",
                                    mensaje="Bloque 'else' en una sola línea sin llaves obligatorias {}.",
                                )
                            )
                    elif not rest_else:
                        # Mirar siguiente línea
                        for n_i in range(idx, len(clean_lines)):
                            nxt = clean_lines[n_i].strip()
                            if nxt:
                                if not nxt.startswith("{") and self.config.require_braces:
                                    observaciones.append(
                                        StyleObservation(
                                            archivo=filename,
                                            linea=idx,
                                            regla="require_braces",
                                            mensaje="Bloque 'else' sin llaves obligatorias {} en la siguiente instrucción.",
                                        )
                                    )
                                elif nxt.startswith("{") and is_kr:
                                    observaciones.append(
                                        StyleObservation(
                                            archivo=filename,
                                            linea=n_i + 1,
                                            regla="brace_style",
                                            mensaje="Estilo K&R violado: la llave '{' tras 'else' debe ir en la misma línea.",
                                        )
                                    )
                                break

        # Cálculo de puntaje de estilo (10.0 base, descontando penalidad por falta hasta 0.0)
        penalty_per_violation = 1.0
        score = max(0.0, 10.0 - (len(observaciones) * penalty_per_violation))
        passed = len(observaciones) == 0

        return StyleCheckResult(
            archivo=filename,
            score=round(score, 2),
            passed=passed,
            observaciones=observaciones,
        )

    def analyze_file(self, file_path: str | Path) -> StyleCheckResult:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.analyze_code(path.name, content)
