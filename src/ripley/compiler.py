"""Secure compilation and isolated execution module for C sources."""

from dataclasses import dataclass
import os
from pathlib import Path
import resource
import shutil
import subprocess
from typing import List, Optional, Sequence

from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig


@dataclass
class CompilationResult:
    success: bool
    binary_path: Optional[Path]
    stdout: str
    stderr: str
    returncode: int
    error_message: Optional[str] = None


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False
    memory_exceeded: bool = False
    duration_ms: float = 0.0


def set_process_limits(memory_limit_mb: int, cpu_timeout_sec: int) -> None:
    """Configura los límites de recursos de Unix en el proceso hijo antes de ejecutar."""
    try:
        # Límite de CPU
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_timeout_sec, cpu_timeout_sec + 2))
    except (ValueError, OSError):
        pass

    try:
        # Límite de segmento de datos (heap)
        mem_bytes = memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_DATA, (mem_bytes, mem_bytes))
    except (ValueError, OSError):
        pass

    try:
        # Límite de tamaño de archivo generado (RLIMIT_FSIZE) a 20MB
        fsize_bytes = 20 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
    except (ValueError, OSError):
        pass



class Compiler:
    """Compila archivos C de forma segura aplicando restricciones y sanitizadores."""

    def __init__(
        self,
        compiler_cfg: CompilerConfig,
        limits_cfg: LimitsConfig,
        sandbox_cfg: SandboxConfig,
    ) -> None:
        self.compiler_cfg = compiler_cfg
        self.limits_cfg = limits_cfg
        self.sandbox_cfg = sandbox_cfg

    def compile(
        self,
        source_files: Sequence[str | Path],
        output_binary: str | Path,
    ) -> CompilationResult:
        sources = [Path(s) for s in source_files]
        out_bin = Path(output_binary)
        out_bin.parent.mkdir(parents=True, exist_ok=True)

        compiler_bin = self.compiler_cfg.executable
        if not shutil.which(compiler_bin) and not Path(compiler_bin).exists():
            return CompilationResult(
                success=False,
                binary_path=None,
                stdout="",
                stderr=f"Compilador '{compiler_bin}' no encontrado en el sistema.",
                returncode=-1,
                error_message=f"Compilador '{compiler_bin}' no encontrado.",
            )

        cmd = [compiler_bin] + self.compiler_cfg.flags + [str(s) for s in sources] + ["-o", str(out_bin)]

        # Si sandbox está activo y el proveedor es bubblewrap
        if self.sandbox_cfg.enabled and self.sandbox_cfg.provider == "bubblewrap" and shutil.which("bwrap"):
            bwrap_cmd = [
                "bwrap",
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib",
                "--ro-bind", "/lib64", "/lib64",
                "--ro-bind", "/etc", "/etc",
                "--bind", str(out_bin.parent), str(out_bin.parent),
                "--proc", "/proc",
                "--dev", "/dev",
                "--unshare-all",
            ]
            cmd = bwrap_cmd + cmd

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.limits_cfg.timeout_segundos * 2,
            )

            # Si falla por falta de libasan/libubsan en el sistema, reintentar sin flags de sanitización
            if proc.returncode != 0 and ("cannot find" in proc.stderr and ("libasan" in proc.stderr or "libubsan" in proc.stderr)):
                clean_flags = [f for f in self.compiler_cfg.flags if not f.startswith("-fsanitize=")]
                fallback_cmd = [compiler_bin] + clean_flags + [str(s) for s in sources] + ["-o", str(out_bin)]
                proc = subprocess.run(
                    fallback_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.limits_cfg.timeout_segundos * 2,
                )

            success = proc.returncode == 0 and out_bin.exists()


            # Validar tamaño máximo de ejecutable
            if success:
                max_bytes = self.limits_cfg.max_tamano_ejecutable_mb * 1024 * 1024
                if out_bin.stat().st_size > max_bytes:
                    out_bin.unlink(missing_ok=True)
                    return CompilationResult(
                        success=False,
                        binary_path=None,
                        stdout=proc.stdout,
                        stderr=proc.stderr
                        + f"\nError: El tamaño del ejecutable supera el límite de {self.limits_cfg.max_tamano_ejecutable_mb} MB.",
                        returncode=-1,
                        error_message="Tamaño de binario excedido.",
                    )

            return CompilationResult(
                success=success,
                binary_path=out_bin if success else None,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False,
                binary_path=None,
                stdout="",
                stderr=f"Timeout durante la compilación ({self.limits_cfg.timeout_segundos * 2}s excedidos).",
                returncode=-1,
                error_message="Timeout de compilación.",
            )
        except Exception as e:
            return CompilationResult(
                success=False,
                binary_path=None,
                stdout="",
                stderr=f"Error inesperado al invocar el compilador: {e}",
                returncode=-1,
                error_message=str(e),
            )
