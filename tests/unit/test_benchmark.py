"""Unit tests for energy/cycle benchmarking."""

import shutil

import pytest

from ripley.tools.benchmark import EnergyBenchmark
from ripley.config import CompilerConfig, SandboxConfig
from ripley.tools.compiler import Compiler, LimitsConfig


def _gcc_available() -> bool:
    return shutil.which("gcc") is not None


@pytest.fixture()
def trivial_binary(tmp_path):
    src = tmp_path / "trivial.c"
    src.write_text(
        '#include <stdio.h>\nint main(void){ printf("ok\\n"); return 0; }\n',
        encoding="utf-8",
    )
    binary = tmp_path / "trivial.out"
    comp = Compiler(
        CompilerConfig(executable="gcc", flags=["-std=c11", "-O2"]),
        LimitsConfig(timeout_segundos=5),
        SandboxConfig(),
    )
    res = comp.compile([src], binary)
    assert res.success
    return binary


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_benchmark_measures_wall_time(trivial_binary):
    bench = EnergyBenchmark(repeats=3)
    result = bench.run(trivial_binary)
    assert result.repeats == 3
    assert len(result.wall_times_ms) == 3
    assert result.mean_time_ms > 0
    assert result.min_time_ms <= result.mean_time_ms <= result.max_time_ms
    assert result.estimated_energy_joules > 0


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_benchmark_counts_instructions_when_valgrind_present(trivial_binary):
    bench = EnergyBenchmark(repeats=1)
    result = bench.run(trivial_binary)
    if not result.counters_available:
        # Sin valgrind el contador devuelve un valor aproximado; solo validamos coherencia.
        assert result.instruction_count >= 0
    else:
        assert result.instruction_count > 100
        assert result.estimated_cycles >= result.instruction_count


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_benchmark_energy_model_components(trivial_binary):
    bench = EnergyBenchmark(repeats=1, joules_per_instruction=2e-9, static_power_watts=10.0)
    result = bench.run(trivial_binary)
    dynamic = result.instruction_count * 2e-9
    static = (result.mean_time_ms / 1000.0) * 10.0
    # El reporte redondea tiempo y energía; tolerancia relativa del 1%.
    assert result.estimated_energy_joules == pytest.approx(dynamic + static, rel=0.01)


def test_benchmark_rejects_zero_repeats():
    with pytest.raises(ValueError):
        EnergyBenchmark(repeats=0)
