"""UndefinedBehaviorSanitizer (UBSan) and Uninitialized Variable analyzer."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional

from ripley.tools.compiler import CompilationResult, Compiler
from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig


@dataclass
class SanitizerFinding:
    category: str  # "INTEGER_OVERFLOW", "DIVISION_BY_ZERO", "UNINITIALIZED_VAR", "SHIFT_OVERFLOW"
    filename: str
    line: int
    message: str
    pedagogical_hint: str
    raw_output: str


class SanitizerAnalyzer:
    """Audita desbordamientos de enteros (UBSan) y variables no inicializadas."""

    def __init__(self) -> None:
        self.compiler = Compiler(
            compiler_cfg=CompilerConfig(
                executable="gcc",
                flags=[
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Wuninitialized",
                    "-Wmaybe-uninitialized",
                    "-fsanitize=signed-integer-overflow,shift,integer-divide-by-zero",
                ],
            ),
            limits_cfg=LimitsConfig(timeout_segundos=5),
            sandbox_cfg=SandboxConfig(),
        )

    def parse_compiler_uninitialized_warnings(self, stderr: str) -> List[SanitizerFinding]:
        """Detecta advertencias de variables no inicializadas en la salida del compilador."""
        findings: List[SanitizerFinding] = []

        # Regex para advertencias de GCC -Wuninitialized
        pattern = re.compile(
            r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s*(?:warning|error):\s*'(?P<var>[^']+)'\s*(?:is|may be)\s*used uninitialized",
            re.MULTILINE,
        )

        for match in pattern.finditer(stderr):
            fname = match.group("file")
            line = int(match.group("line"))
            var_name = match.group("var")

            findings.append(
                SanitizerFinding(
                    category="UNINITIALIZED_VAR",
                    filename=fname,
                    line=line,
                    message=f"La variable `{var_name}` es leída antes de ser inicializada con un valor.",
                    pedagogical_hint=(
                        f"En C, las variables locales no inicializadas contienen basura de memoria. "
                        f"Inicializá siempre `{var_name}` en su declaración (ej. `int {var_name} = 0;`)."
                    ),
                    raw_output=match.group(0),
                )
            )

        return findings

    def parse_ubsan_runtime_errors(self, stderr: str) -> List[SanitizerFinding]:
        """Parsea errores en tiempo de ejecución emitidos por UBSan."""
        findings: List[SanitizerFinding] = []

        # 1. Desbordamiento de enteros con signo
        overflow_pattern = re.compile(
            r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s*runtime error:\s*signed integer overflow:\s*(?P<expr>[^\n]+)",
            re.MULTILINE,
        )
        for match in overflow_pattern.finditer(stderr):
            findings.append(
                SanitizerFinding(
                    category="INTEGER_OVERFLOW",
                    filename=match.group("file"),
                    line=int(match.group("line")),
                    message=f"Desbordamiento de entero con signo (Integer Overflow): {match.group('expr')}.",
                    pedagogical_hint=(
                        "El resultado de la operación aritmética excede el rango representable del tipo entero "
                        "(comportamiento indefinido en C). Considerá usar tipos de mayor capacidad como `long long` o validar rangos."
                    ),
                    raw_output=match.group(0),
                )
            )

        # 2. División por cero
        div_zero_pattern = re.compile(
            r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s*runtime error:\s*division by zero",
            re.MULTILINE,
        )
        for match in div_zero_pattern.finditer(stderr):
            findings.append(
                SanitizerFinding(
                    category="DIVISION_BY_ZERO",
                    filename=match.group("file"),
                    line=int(match.group("line")),
                    message="División por cero en tiempo de ejecución.",
                    pedagogical_hint="Validá siempre que el divisor sea distinto de cero antes de realizar `/` o `%`.",
                    raw_output=match.group(0),
                )
            )

        # 3. Desalineación de memoria (UBSan -fsanitize=alignment)
        align_pattern = re.compile(
            r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s*runtime error:\s*(?P<msg>(?:member access within|load of|store to)\s+misaligned address\s+0x[0-9a-fA-F]+[^\n]*)",
            re.MULTILINE,
        )
        for match in align_pattern.finditer(stderr):
            findings.append(
                SanitizerFinding(
                    category="UNALIGNED_ACCESS",
                    filename=match.group("file"),
                    line=int(match.group("line")),
                    message=f"Acceso a memoria no alineada (Unaligned Memory Access): {match.group('msg')}.",
                    pedagogical_hint=(
                        "Accediste a una estructura o puntero cuya dirección no cumple con la alineación natural del tipo en la CPU. "
                        "Evitá casteos de punteros incompatibles (ej. `char*` a `int*`) sin respetar múltiplos de alineación."
                    ),
                    raw_output=match.group(0),
                )
            )

        return findings

    def parse_conversion_warnings(self, stderr: str) -> List[SanitizerFinding]:
        """Detecta conversiones implícitas peligrosas (-Wsign-conversion, -Wconversion)."""
        findings: List[SanitizerFinding] = []

        pattern = re.compile(
            r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s*(?:warning|error):\s*(?P<msg>conversion (?:to|from) '[^']+' (?:to|from) '[^']+'[^\n]*)",
            re.MULTILINE,
        )

        for match in pattern.finditer(stderr):
            findings.append(
                SanitizerFinding(
                    category="SIGN_CONVERSION",
                    filename=match.group("file"),
                    line=int(match.group("line")),
                    message=f"Conversión implícita peligrosa: {match.group('msg')}.",
                    pedagogical_hint=(
                        "La conversión automática entre tipos con y sin signo (o con distinta precisión) puede alterar el valor o "
                        "provocar desbordamientos silenciosos. Usá un casting explícito o unificá los tipos (ej. `size_t` con `size_t`)."
                    ),
                    raw_output=match.group(0),
                )
            )

        return findings

