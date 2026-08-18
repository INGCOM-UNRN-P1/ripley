"""Unit tests for EmbeddedMemoryRunner."""

from pathlib import Path
from ripley.compiler import Compiler
from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig
from ripley.embedded import EmbeddedMemoryRunner


def test_embedded_memory_runner(tmp_path):
    src = tmp_path / "simple.c"
    bin_file = tmp_path / "simple"
    src.write_text(
        """
        #include <stdio.h>
        int main() {
            printf("OK\\n");
            return 0;
        }
        """,
        encoding="utf-8",
    )

    compiler = Compiler(
        compiler_cfg=CompilerConfig(executable="gcc", flags=["-std=c11"]),
        limits_cfg=LimitsConfig(timeout_segundos=5),
        sandbox_cfg=SandboxConfig(),
    )
    res_comp = compiler.compile([src], bin_file)
    assert res_comp.success is True

    runner = EmbeddedMemoryRunner(memory_limit_kb=1024)
    res_run = runner.run(bin_file)

    assert res_run.success is True
    assert res_run.memory_limit_kb == 1024
    assert "OK" in res_run.stdout
