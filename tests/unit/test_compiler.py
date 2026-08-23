"""Unit tests for Compiler module."""

from pathlib import Path
import subprocess

from ripley.tools.compiler import Compiler
from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig


def test_compiler_compiles_valid_c_program(tmp_path):
    src_file = tmp_path / "main.c"
    src_file.write_text(
        """
        #include <stdio.h>
        int main() {
            printf("Hello Ripley\\n");
            return 0;
        }
        """,
        encoding="utf-8",
    )
    out_bin = tmp_path / "main.out"

    comp = Compiler(
        compiler_cfg=CompilerConfig(executable="gcc", flags=["-Wall", "-std=c11"]),
        limits_cfg=LimitsConfig(timeout_segundos=5, max_tamano_ejecutable_mb=10),
        sandbox_cfg=SandboxConfig(enabled=False),
    )

    res = comp.compile([src_file], out_bin)
    assert res.success is True
    assert res.binary_path is not None
    assert res.binary_path.exists()
    assert res.returncode == 0


def test_compiler_handles_syntax_error(tmp_path):
    src_file = tmp_path / "broken.c"
    src_file.write_text("int main() { syntax error here }", encoding="utf-8")
    out_bin = tmp_path / "broken.out"

    comp = Compiler(
        compiler_cfg=CompilerConfig(executable="gcc", flags=["-Wall", "-std=c11"]),
        limits_cfg=LimitsConfig(timeout_segundos=5, max_tamano_ejecutable_mb=10),
        sandbox_cfg=SandboxConfig(enabled=False),
    )

    res = comp.compile([src_file], out_bin)
    assert res.success is False
    assert res.binary_path is None
    assert res.returncode != 0
    assert "error" in res.stderr.lower()


def test_compiler_missing_compiler(tmp_path):
    src_file = tmp_path / "main.c"
    src_file.write_text("int main() { return 0; }", encoding="utf-8")
    out_bin = tmp_path / "main.out"

    comp = Compiler(
        compiler_cfg=CompilerConfig(executable="non_existent_compiler_xyz_123"),
        limits_cfg=LimitsConfig(),
        sandbox_cfg=SandboxConfig(),
    )
    res = comp.compile([src_file], out_bin)
    assert res.success is False
    assert "no encontrado" in res.stderr.lower()
