"""Preventive security scanner for C source files."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Sequence

from ripley.config import SecurityConfig


@dataclass
class SecurityViolation:
    filename: str
    line: int
    symbol: str
    message: str


def strip_c_comments_and_strings(code: str) -> str:
    """Elimina comentarios y cadenas literales manteniendo los saltos de línea para conservar número de línea."""

    def replacer(match: re.Match) -> str:
        s = match.group(0)
        if s.startswith("/"):
            # Reemplazar comentarios por espacios en blanco preservando '\n'
            return re.sub(r"[^\n]", " ", s)
        else:
            # String o char literal
            return '""' + re.sub(r"[^\n]", " ", s[2:])

    # Regex para comentarios de bloque, de línea, y strings
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"', re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, code)


class SecurityScanner:
    """Escanea código fuente en C para prevenir llamadas al sistema y headers no permitidos."""

    def __init__(self, config: SecurityConfig) -> None:
        self.config = config

    def scan_code(self, filename: str, code: str) -> List[SecurityViolation]:
        violations: List[SecurityViolation] = []

        # 1. Chequeo de headers prohibidos
        for line_num, line in enumerate(code.splitlines(), start=1):
            stripped_line = line.strip()
            if stripped_line.startswith("#include"):
                for header in self.config.forbidden_headers:
                    if f"<{header}>" in stripped_line or f'"{header}"' in stripped_line:
                        violations.append(
                            SecurityViolation(
                                filename=filename,
                                line=line_num,
                                symbol=header,
                                message=f"Inclusión de header prohibido/peligroso: <{header}>",
                            )
                        )

        # 2. Chequeo de llamadas a funciones prohibidas
        clean_code = strip_c_comments_and_strings(code)
        lines = clean_code.splitlines()

        for line_num, line in enumerate(lines, start=1):
            for func in self.config.forbidden_calls:
                # Buscar nombre de función seguido de paréntesis de invocación
                call_pattern = rf"\b{re.escape(func)}\s*\("
                if re.search(call_pattern, line):
                    violations.append(
                        SecurityViolation(
                            filename=filename,
                            line=line_num,
                            symbol=func,
                            message=f"Llamada a función de sistema/peligrosa prohibida: '{func}()'",
                        )
                    )

        return violations

    def scan_file(self, file_path: str | Path) -> List[SecurityViolation]:
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.scan_code(path.name, content)
        except Exception as e:
            return [
                SecurityViolation(
                    filename=path.name,
                    line=1,
                    symbol="file_read",
                    message=f"No se pudo leer el archivo para análisis de seguridad: {e}",
                )
            ]

    def scan_files(self, file_paths: Sequence[str | Path]) -> List[SecurityViolation]:
        all_violations: List[SecurityViolation] = []
        for fp in file_paths:
            all_violations.extend(self.scan_file(fp))
        return all_violations
