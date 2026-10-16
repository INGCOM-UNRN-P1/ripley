"""Compilación de la evaluación docente con daedalus (N-RIPLEY-03).

Reemplaza al compilador interno deprecado (`ripley.core.compiler.Compiler`) en `ripley
evaluate`, con la misma semántica:

- los flags son los de la actividad (`[compiler] flags`), no se suman a los de cátedra;
- con `[sandbox] enabled` y proveedor bubblewrap, daedalus compila dentro del sandbox de
  nostromo (el código no ve archivos fuera de sus fuentes); sin bwrap utilizable compila con
  límites de recursos, como antes;
- si el toolchain no trae libasan/libubsan (MSYS2), se reintenta sin `-fsanitize`;
- el tiempo límite es el doble del de ejecución y el binario no puede superar
  `max_tamano_ejecutable_mb`.

daedalus y nostromo vienen con el extra `ecosistema` de ripley (el que instala mother). Sin
daedalus se usa el compilador interno, que hace lo mismo con su propio bwrap.
"""

from __future__ import annotations

import shutil
import warnings
from pathlib import Path
from typing import Sequence

from ripley.config_modelos import CompilerConfig, LimitsConfig, SandboxConfig
from ripley.core.compiler import ES_WINDOWS, CompilationResult


class CompiladorActividad:
    """Compila las entregas de una actividad con daedalus."""

    def __init__(self, compiler_cfg: CompilerConfig, limits_cfg: LimitsConfig, sandbox_cfg: SandboxConfig) -> None:
        self.compiler_cfg = compiler_cfg
        self.limits_cfg = limits_cfg
        self.sandbox_cfg = sandbox_cfg
        try:
            from daedalus.core.compiler import compilar_archivos
        except ImportError:
            self._compilar = None
        else:
            self._compilar = compilar_archivos

    @property
    def aislar(self) -> bool:
        return self.sandbox_cfg.enabled and self.sandbox_cfg.provider == "bubblewrap"

    def compile(self, source_files: Sequence[str | Path], output_binary: str | Path) -> CompilationResult:
        if self._compilar is None:
            return self._interno(source_files, output_binary)
        out_bin = Path(output_binary)
        out_bin.parent.mkdir(parents=True, exist_ok=True)
        compilador = self.compiler_cfg.executable
        if not shutil.which(compilador) and not Path(compilador).exists():
            return CompilationResult(
                success=False,
                binary_path=None,
                stdout="",
                stderr=f"Compilador '{compilador}' no encontrado en el sistema.",
                returncode=-1,
                error_message=f"Compilador '{compilador}' no encontrado.",
            )
        timeout = self.limits_cfg.timeout_segundos * 2
        res = self._compilar(
            [Path(s) for s in source_files],
            binario_salida=out_bin,
            flags=list(self.compiler_cfg.flags),
            compilador=compilador,
            timeout=timeout,
            aislar=self.aislar,
            reintentar_sin_sanitizers=True,
        )
        if res.codigo_retorno == 124 and not res.exito:
            return CompilationResult(
                success=False,
                binary_path=None,
                stdout="",
                stderr=f"Timeout durante la compilación ({timeout}s excedidos).",
                returncode=-1,
                error_message="Timeout de compilación.",
            )
        # En Windows gcc agrega .exe al binario (N-ECO-10).
        if ES_WINDOWS and not out_bin.exists() and out_bin.with_name(out_bin.name + ".exe").exists():
            out_bin = out_bin.with_name(out_bin.name + ".exe")
        exito = res.exito and out_bin.exists()
        if exito and out_bin.stat().st_size > self.limits_cfg.max_tamano_ejecutable_mb * 1024 * 1024:
            out_bin.unlink(missing_ok=True)
            return CompilationResult(
                success=False,
                binary_path=None,
                stdout=res.stdout_crudo,
                stderr=res.stderr_crudo
                + f"\nError: El tamaño del ejecutable supera el límite de {self.limits_cfg.max_tamano_ejecutable_mb} MB.",
                returncode=-1,
                error_message="Tamaño de binario excedido.",
            )
        return CompilationResult(
            success=exito,
            binary_path=out_bin if exito else None,
            stdout=res.stdout_crudo,
            stderr=res.stderr_crudo,
            returncode=res.codigo_retorno,
        )

    def _interno(self, source_files: Sequence[str | Path], output_binary: str | Path) -> CompilationResult:
        from ripley.core.compiler import Compiler

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            compilador = Compiler(self.compiler_cfg, self.limits_cfg, self.sandbox_cfg)
        return compilador.compile(source_files, output_binary)
