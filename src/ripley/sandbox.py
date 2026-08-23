"""Unprivileged Linux-namespace sandboxing (Bubblewrap / unshare) for isolated test execution."""

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional, Sequence


@dataclass
class SandboxResult:
    success: bool
    strategy: str  # "bubblewrap" | "unshare" | "none"
    isolated: bool
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    message: str = ""


class NamespaceSandbox:
    """Ejecuta binarios dentro de espacios de nombres Linux sin privilegios de
    root. Estrategias en orden de preferencia:

    1. **bubblewrap**: PID + Mount + Network + IPC + UTS namespaces completos.
    2. **unshare --user --map-root-user --net --mount --pid --fork**: userns
       no privilegiado cuando bwrap no está disponible.
    3. Sin aislamiento (fallback explícito y reportado).
    """

    def __init__(self, timeout_sec: float = 10.0) -> None:
        self.timeout_sec = timeout_sec
        self._strategy_cache: Optional[str] = None

    # ------------------------------------------------------------------
    # Detección de estrategias disponibles
    # ------------------------------------------------------------------
    def _build_bwrap_cmd(
        self,
        cmd: Sequence[str],
        writable_dir: Optional[Path],
        extra_ro_binds: Optional[Sequence[Path]] = None,
    ) -> List[str]:
        base = [
            "bwrap",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
        ]
        env_vars = ["PATH=/usr/bin:/bin:/usr/sbin:/sbin"]
        result: List[str] = list(base)
        for var in env_vars:
            result += ["--setenv", *var.split("=", 1)]
        for path in extra_ro_binds or []:
            result += ["--ro-bind", str(path), str(path)]
        if writable_dir is not None:
            result += ["--bind", str(writable_dir), str(writable_dir)]
        return result + list(cmd)

    def _build_unshare_cmd(self, cmd: Sequence[str]) -> List[str]:
        return [
            "unshare",
            "--user",
            "--map-root-user",
            "--mount",
            "--net",
            "--pid",
            "--fork",
            "--kill-child",
            *cmd,
        ]

    def detect_strategy(self) -> str:
        """Detecta la mejor estrategia de sandbox disponible (con probe real)."""
        if self._strategy_cache is not None:
            return self._strategy_cache

        if shutil.which("bwrap"):
            try:
                probe = subprocess.run(
                    self._build_bwrap_cmd(["/bin/true"], None),
                    capture_output=True,
                    timeout=10,
                )
                if probe.returncode == 0:
                    self._strategy_cache = "bubblewrap"
                    return self._strategy_cache
            except (OSError, subprocess.TimeoutExpired):
                pass

        if shutil.which("unshare"):
            try:
                probe = subprocess.run(
                    self._build_unshare_cmd(["/bin/true"]),
                    capture_output=True,
                    timeout=10,
                )
                if probe.returncode == 0:
                    self._strategy_cache = "unshare"
                    return self._strategy_cache
            except (OSError, subprocess.TimeoutExpired):
                pass

        self._strategy_cache = "none"
        return self._strategy_cache

    @property
    def available(self) -> bool:
        return self.detect_strategy() in ("bubblewrap", "unshare")

    # ------------------------------------------------------------------
    # Ejecución aislada
    # ------------------------------------------------------------------
    def run(
        self,
        binary_path: Path | str,
        stdin_data: str = "",
        cli_args: Sequence[str] = (),
        writable_dir: Optional[Path] = None,
    ) -> SandboxResult:
        bin_path = Path(binary_path)
        if not bin_path.exists():
            return SandboxResult(
                success=False,
                strategy=self.detect_strategy(),
                isolated=False,
                message="Binario no encontrado.",
            )

        target_cmd = [str(bin_path), *cli_args]
        strategy = self.detect_strategy()

        if strategy == "bubblewrap":
            cmd = self._build_bwrap_cmd(
                target_cmd,
                writable_dir,
                extra_ro_binds=[bin_path.parent],
            )
        elif strategy == "unshare":
            cmd = self._build_unshare_cmd(target_cmd)
        else:
            cmd = target_cmd

        try:
            proc = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
            )
            return SandboxResult(
                success=True,
                strategy=strategy,
                isolated=strategy != "none",
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                message="Ejecución finalizada bajo namespace aislado."
                if strategy != "none"
                else "Fallback sin aislamiento: ni bubblewrap ni unshare user-ns disponibles.",
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                strategy=strategy,
                isolated=strategy != "none",
                message=f"Timeout ({self.timeout_sec}s excedidos) durante ejecución sandbox.",
            )
        except OSError as e:
            return SandboxResult(
                success=False,
                strategy=strategy,
                isolated=False,
                message=f"Error lanzando el sandbox: {e}",
            )

    def self_test(self) -> SandboxResult:
        """Valida que la estrategia elegida puede ejecutar procesos reales."""
        strategy = self.detect_strategy()
        try:
            proc = subprocess.run(
                self._resolve_cmd(["/bin/sh", "-c", "echo ok"], strategy),
                capture_output=True,
                text=True,
                timeout=10,
            )
            ok = proc.returncode == 0 and "ok" in proc.stdout
            return SandboxResult(
                success=ok,
                strategy=strategy,
                isolated=strategy != "none",
                stdout=proc.stdout.strip(),
                stderr=proc.stderr.strip()[:300],
                message="Sandbox operativo." if ok else f"La estrategia '{strategy}' no pudo ejecutar /bin/sh.",
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return SandboxResult(success=False, strategy=strategy, isolated=False, message=f"Self-test falló: {e}")

    def _resolve_cmd(self, cmd: Sequence[str], strategy: str) -> List[str]:
        if strategy == "bubblewrap":
            return self._build_bwrap_cmd(cmd, None)
        if strategy == "unshare":
            return self._build_unshare_cmd(cmd)
        return list(cmd)
