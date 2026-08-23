"""Specialized crash, recursion/stack overflow, deadlock, and dangling pointer diagnostics."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import List, Optional, Tuple

from ripley.plagiarism import tokenize_c_code
from ripley.core.security import strip_c_comments_and_strings


class DiagnosisType(str, Enum):
    STACK_OVERFLOW = "STACK_OVERFLOW"
    STDIN_DEADLOCK = "STDIN_DEADLOCK"
    USE_AFTER_FREE = "USE_AFTER_FREE"
    DANGLING_POINTER = "DANGLING_POINTER"
    DOUBLE_FREE = "DOUBLE_FREE"
    NULL_DEREFERENCE = "NULL_DEREFERENCE"
    TIMEOUT = "TIMEOUT"
    CLEAN = "CLEAN"


@dataclass
class DiagnosticResult:
    diagnosis: DiagnosisType
    message: str
    pedagogical_hint: str
    symbol_or_location: Optional[str] = None


def diagnose_runtime_crash(
    returncode: int,
    stdout: str,
    stderr: str,
    timeout: bool,
    input_data: str,
) -> DiagnosticResult:
    """Analiza logs de ejecución, señales y sanitizadores para diagnosticar causas de falla específicas."""
    combined_err = f"{stderr}\n{stdout}"

    # 1. Diagnóstico de Stack Overflow / Recursión Infinita
    if (
        "stack-overflow" in combined_err.lower()
        or "stack overflow" in combined_err.lower()
        or "stack exhaustion" in combined_err.lower()
        or (returncode in (-11, 139) and "recursive" in combined_err.lower())
    ):
        return DiagnosticResult(
            diagnosis=DiagnosisType.STACK_OVERFLOW,
            message="Desbordamiento de pila (Stack Overflow) por recursión infinita o buffers locales masivos.",
            pedagogical_hint=(
                "Revisá la condición de corte (caso base) de tus funciones recursivas. "
                "Si la función se llama a sí misma indefinidamente, agota la memoria del stack."
            ),
        )

    # 2. Diagnóstico de Use-After-Free y Dangling Pointer Dinámico
    if (
        "heap-use-after-free" in combined_err
        or "address is inside a block of size" in combined_err.lower()
        and "free'd" in combined_err.lower()
    ):
        return DiagnosticResult(
            diagnosis=DiagnosisType.USE_AFTER_FREE,
            message="Uso de memoria después de ser liberada (Use-After-Free / Puntero Colgante).",
            pedagogical_hint=(
                "Intentaste acceder o modificar un puntero cuya memoria ya fue devuelta al sistema con free(). "
                "Buenas prácticas: asigná siempre `p = NULL;` inmediatamente después de `free(p);`."
            ),
        )

    if "double free" in combined_err.lower() or "double-free" in combined_err.lower():
        return DiagnosticResult(
            diagnosis=DiagnosisType.DOUBLE_FREE,
            message="Doble liberación de memoria detectada (Double Free).",
            pedagogical_hint="Llamaste a free() dos veces sobre la misma dirección de memoria sin reasignarla.",
        )

    # 3. Diagnóstico de Desreferencia Nula
    if (
        "null-dereference" in combined_err.lower()
        or "address 0x00000000" in combined_err.lower()
        or "address 0x0," in combined_err.lower()
        or "null pointer" in combined_err.lower()
    ):
        return DiagnosticResult(
            diagnosis=DiagnosisType.NULL_DEREFERENCE,
            message="Desreferencia de puntero nulo (NULL Pointer Dereference).",
            pedagogical_hint="Verificá que el puntero sea distinto de NULL antes de acceder a sus miembros o desreferenciarlo con `*p`.",
        )

    # 4. Diagnóstico de Bloqueo en Stdin (I/O Deadlock) vs Timeout general
    if timeout:
        input_lines = [l for l in input_data.splitlines() if l.strip()]
        # Si había entrada provista pero el programa se quedó colgado esperando más lecturas
        if input_data.strip() and len(input_lines) <= 2:
            return DiagnosticResult(
                diagnosis=DiagnosisType.STDIN_DEADLOCK,
                message="Bloqueo de E/S en Stdin (I/O Deadlock): El programa quedó esperando más entradas que las provistas.",
                pedagogical_hint=(
                    "El programa se detuvo indefinidamente esperando una lectura por teclado/stdin (scanf/getchar/fgets). "
                    "Asegurate de validar siempre el valor de retorno de `scanf` o verificar `EOF`."
                ),
            )
        return DiagnosticResult(
            diagnosis=DiagnosisType.TIMEOUT,
            message="Tiempo límite de ejecución excedido (Timeout / Bucle Infinito).",
            pedagogical_hint="El programa entró en un bucle infinito de procesamiento o tardó más del tiempo asignado.",
        )


    return DiagnosticResult(
        diagnosis=DiagnosisType.CLEAN,
        message="Ejecución finalizada.",
        pedagogical_hint="",
    )


def detect_static_dangling_pointers(code: str) -> List[Tuple[int, str, str]]:
    """Analiza estáticamente patrones de punteros colgantes (acceso tras free o falta de nullificación)."""
    clean = strip_c_comments_and_strings(code)
    violations: List[Tuple[int, str, str]] = []

    # Buscar patrones `free(var);`
    free_regex = re.compile(r"\bfree\s*\(\s*(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*\)\s*;", re.MULTILINE)

    lines = clean.splitlines()
    for idx, line in enumerate(lines):
        match = free_regex.search(line)
        if match:
            var_name = match.group("var")
            line_num = idx + 1

            # Revisar las líneas siguientes dentro del mismo bloque para ver si se vuelve a usar var sin asignar
            # o si no se asigna a NULL
            following_code = "\n".join(lines[idx + 1 : min(idx + 10, len(lines))])

            # Patrón 1: desreferencia directa tras free: `*var` o `var->` o `var[...]`
            use_regex = re.compile(rf"(\*{var_name}\b|{var_name}\s*->|{var_name}\s*\[)", re.MULTILINE)
            if use_regex.search(following_code):
                violations.append(
                    (
                        line_num,
                        var_name,
                        f"Puntero colgante (Dangling Pointer): `{var_name}` es usado tras ser liberado con free().",
                    )
                )

    return violations
