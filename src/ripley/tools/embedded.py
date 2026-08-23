"""Restricted memory emulator for embedded systems and low-footprint constraints."""

from dataclasses import dataclass
from pathlib import Path
import resource
import subprocess
from typing import Optional, Sequence


@dataclass
class EmbeddedRunResult:
    success: bool
    memory_limit_kb: int
    exit_code: int
    stdout: str
    stderr: str
    message: str


class EmbeddedMemoryRunner:
    """Ejecuta binarios C bajo límites estrictos de memoria de sistemas embebidos."""

    def __init__(self, memory_limit_kb: int = 64) -> None:
        self.memory_limit_kb = memory_limit_kb

    def run(
        self,
        binary_path: Path | str,
        stdin_data: str = "",
        cli_args: Sequence[str] = (),
        timeout_seconds: float = 3.0,
        override_limit_kb: Optional[int] = None,
    ) -> EmbeddedRunResult:
        limit_kb = override_limit_kb or self.memory_limit_kb
        limit_bytes = limit_kb * 1024
        bin_path = Path(binary_path)

        if not bin_path.exists():
            return EmbeddedRunResult(
                success=False,
                memory_limit_kb=limit_kb,
                exit_code=-1,
                stdout="",
                stderr="Binario no encontrado.",
                message=f"Archivo binario no existe: {bin_path}",
            )

        def preexec_limits() -> None:
            # Establecer límite estricto de memoria de datos (Heap + Stack)
            try:
                resource.setrlimit(resource.RLIMIT_AS, (limit_bytes * 16, limit_bytes * 16))
                resource.setrlimit(resource.RLIMIT_DATA, (limit_bytes, limit_bytes))
            except (ValueError, resource.error):
                pass

        try:
            proc = subprocess.run(
                [str(bin_path)] + list(cli_args),
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                preexec_fn=preexec_limits,
            )

            success = proc.returncode == 0
            msg = (
                f"Ejecución exitosa dentro del límite embebido de {limit_kb} KB."
                if success
                else f"Falla en ejecución con código {proc.returncode} bajo límite de {limit_kb} KB."
            )

            return EmbeddedRunResult(
                success=success,
                memory_limit_kb=limit_kb,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                message=msg,
            )
        except subprocess.TimeoutExpired:
            return EmbeddedRunResult(
                success=False,
                memory_limit_kb=limit_kb,
                exit_code=-1,
                stdout="",
                stderr="Timeout excedido.",
                message=f"Timeout superado ejecutando bajo límite embebido de {limit_kb} KB.",
            )
