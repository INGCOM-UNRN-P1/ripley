"""Secure compilation and isolated execution module for C sources."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import warnings
from typing import Callable, Optional, Sequence

try:
    import resource  # solo POSIX
except ImportError:  # pragma: no cover - Windows (Python nativo o el de MSYS2 UCRT64)
    resource = None  # type: ignore[assignment]

ES_WINDOWS = os.name == "nt"
# Señales de que el toolchain no tiene los sanitizers (glibc: «cannot find libasan…»; MinGW: «cannot
# find -lasan»): se reintenta sin -fsanitize.
SIN_SANITIZERS = ("libasan", "libubsan", "-lasan", "-lubsan")

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


def set_process_limits(
    memory_limit_mb: int,
    cpu_timeout_sec: int,
    enforce_data_limit: bool = False,
) -> None:
    """Configura los límites de recursos de Unix en el proceso hijo antes de ejecutar.

    RLIMIT_DATA solo se aplica con ``enforce_data_limit=True``: los binarios
    instrumentados con AddressSanitizer reservan regiones virtuales masivas
    (shadow memory y arena del allocator) que el kernel contabiliza en dicho
    límite, por lo que forzarlo provoca el aborto inmediato del proceso
    auditado. La protección de memoria queda delegada a los sanitizadores,
    Valgrind y el timeout de CPU. En Windows no hay límites por proceso: no hace nada.
    """
    if resource is None:
        return
    try:
        # Límite de CPU
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_timeout_sec, cpu_timeout_sec + 2))
    except (ValueError, OSError):
        pass

    if enforce_data_limit:
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



def limites_para_subprocess(memory_limit_mb: int, cpu_timeout_sec: int) -> Optional[Callable[[], None]]:
    """El `preexec_fn` que aplica los límites en el hijo, o None donde no existen.

    En Windows no hay `resource` y `subprocess` rechaza `preexec_fn`: la ejecución queda acotada
    solo por el timeout (antes, importar este módulo ya fallaba y con él los comandos que ejecutan
    los programas del estudiante).
    """
    if resource is None or os.name == "nt":
        return None
    return lambda: set_process_limits(memory_limit_mb, cpu_timeout_sec)


class Compiler:
    """Compila archivos C de forma segura aplicando restricciones y sanitizadores.

    .. deprecated:: 0.2.0
       Módulo monolítico de compilación interna deprecado en favor de SatellitePluginAdapter.
    """

    def __init__(
        self,
        compiler_cfg: CompilerConfig,
        limits_cfg: LimitsConfig,
        sandbox_cfg: SandboxConfig,
    ) -> None:
        warnings.warn(
            "Compiler interno de ripley está deprecado. La compilación debe consolidarse "
            "a través de SatellitePluginAdapter ('compiler' / daedalus).",
            DeprecationWarning,
            stacklevel=2,
        )
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
            if proc.returncode != 0 and "cannot find" in proc.stderr and any(s in proc.stderr for s in SIN_SANITIZERS):
                clean_flags = [f for f in self.compiler_cfg.flags if not f.startswith("-fsanitize=")]
                fallback_cmd = [compiler_bin] + clean_flags + [str(s) for s in sources] + ["-o", str(out_bin)]
                proc = subprocess.run(
                    fallback_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.limits_cfg.timeout_segundos * 2,
                )

            # En Windows gcc agrega .exe al binario (N-ECO-10).
            if ES_WINDOWS and not out_bin.exists() and out_bin.with_name(out_bin.name + ".exe").exists():
                out_bin = out_bin.with_name(out_bin.name + ".exe")
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
