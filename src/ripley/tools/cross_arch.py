"""Cross-architecture compilation and execution matrix using QEMU user-mode emulation."""

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import List, Optional, Sequence

from ripley.config import LimitsConfig
from ripley.tools.compiler import Compiler, CompilerConfig, SandboxConfig


@dataclass
class CrossTargetResult:
    architecture: str
    compiler_used: Optional[str]
    emulator_used: Optional[str]
    compiled: bool
    ran: bool = False
    output_matched: bool = False
    exit_code: int = 0
    stdout: str = ""
    message: str = ""


@dataclass
class CrossArchReport:
    source: str
    targets: List[CrossTargetResult]

    @property
    def available_targets(self) -> List[CrossTargetResult]:
        return [t for t in self.targets if t.compiled or t.compiler_used is None]


# (arquitectura, prefijo del cross-compiler, binario QEMU, notas)
TARGET_MATRIX: List[tuple] = [
    ("x86_64", "", "", "Nativo de referencia"),
    ("aarch64", "aarch64-linux-gnu-", "qemu-aarch64", "ARM64 little-endian"),
    ("riscv64", "riscv64-linux-gnu-", "qemu-riscv64", "RISC-V RV64 little-endian"),
    ("mips", "mips-linux-gnu-", "qemu-mips", "MIPS big-endian: valida orden de bytes"),
]


class CrossArchitectureTester:
    """Compila la misma fuente para múltiples arquitecturas y ejecuta los
    binarios bajo QEMU user-mode comparando salidas contra el nativo."""

    def __init__(self, timeout_sec: float = 10.0) -> None:
        self.timeout_sec = timeout_sec

    def _detect_toolchain(self, prefix: str, emulator: str) -> tuple:
        gcc = shutil.which(f"{prefix}gcc")
        qemu = shutil.which(emulator) if emulator else "native"
        return gcc, qemu

    def test(
        self,
        source_path: Path | str,
        stdin_data: str = "",
        expected_output: Optional[str] = None,
        cli_args: Sequence[str] = (),
    ) -> CrossArchReport:
        src = Path(source_path)
        results: List[CrossTargetResult] = []
        native_stdout: Optional[str] = None

        with tempfile.TemporaryDirectory(prefix="ripley_cross_") as temp_dir:
            workdir = Path(temp_dir)
            for arch, prefix, emulator, note in TARGET_MATRIX:
                gcc_bin, qemu_bin = self._detect_toolchain(prefix, emulator)

                if gcc_bin is None:
                    results.append(
                        CrossTargetResult(
                            architecture=arch,
                            compiler_used=None,
                            emulator_used=qemu_bin,
                            compiled=False,
                            message=f"Toolchain '{prefix}gcc' no instalado ({note}).",
                        )
                    )
                    continue

                binary = workdir / f"app_{arch}"
                static_flags = ["-static"] if qemu_bin != "native" else []
                compiler = Compiler(
                    CompilerConfig(executable=gcc_bin, flags=["-std=c11", "-Wall", *static_flags]),
                    LimitsConfig(timeout_segundos=15),
                    SandboxConfig(),
                )
                comp = compiler.compile([src], binary)
                if not comp.success:
                    # Reintento dinámico si falla el enlazado estático.
                    if static_flags:
                        compiler = Compiler(
                            CompilerConfig(executable=gcc_bin, flags=["-std=c11", "-Wall"]),
                            LimitsConfig(timeout_segundos=15),
                            SandboxConfig(),
                        )
                        comp = compiler.compile([src], binary)
                if not comp.success:
                    results.append(
                        CrossTargetResult(
                            architecture=arch,
                            compiler_used=gcc_bin,
                            emulator_used=qemu_bin,
                            compiled=False,
                            message=f"Fallo de compilación: {comp.stderr.strip()[:200]}",
                        )
                    )
                    continue

                run_cmd = ([qemu_bin] if qemu_bin != "native" else []) + [str(binary), *cli_args]
                try:
                    proc = subprocess.run(
                        run_cmd,
                        input=stdin_data,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_sec,
                    )
                except subprocess.TimeoutExpired:
                    results.append(
                        CrossTargetResult(
                            architecture=arch,
                            compiler_used=gcc_bin,
                            emulator_used=qemu_bin,
                            compiled=True,
                            ran=False,
                            message=f"Timeout ejecutando bajo {emulator or 'nativo'}.",
                        )
                    )
                    continue
                except OSError as e:
                    results.append(
                        CrossTargetResult(
                            architecture=arch,
                            compiler_used=gcc_bin,
                            emulator_used=qemu_bin,
                            compiled=True,
                            ran=False,
                            message=f"No se pudo ejecutar {emulator}: {e}",
                        )
                    )
                    continue

                matched: Optional[bool] = None
                if arch == "x86_64":
                    native_stdout = proc.stdout
                    matched = True
                elif native_stdout is not None:
                    reference = expected_output if expected_output is not None else native_stdout
                    matched = proc.stdout.rstrip("\n") == reference.rstrip("\n")

                results.append(
                    CrossTargetResult(
                        architecture=arch,
                        compiler_used=gcc_bin,
                        emulator_used=qemu_bin,
                        compiled=True,
                        ran=True,
                        output_matched=bool(matched),
                        exit_code=proc.returncode,
                        stdout=proc.stdout[:500],
                        message="Ejecución consistente con el nativo."
                        if matched
                        else "Salida difiere del binario nativo (posible dependencia de arquitectura)."
                        if matched is False
                        else "Sin salida nativa de referencia.",
                    )
                )

        return CrossArchReport(source=str(src), targets=results)
