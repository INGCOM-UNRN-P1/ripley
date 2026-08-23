"""Unit tests for the empirical asymptotic complexity profiler."""

import shutil
import subprocess
from pathlib import Path

import pytest

from ripley.complexity_profiler import ComplexityProfiler, _classify, _linear_fit


def _gcc_available() -> bool:
    return shutil.which("gcc") is not None


def test_linear_fit_and_classification_helpers():
    slope, intercept = _linear_fit([0.0, 1.0, 2.0], [0.0, 2.0, 4.0])
    assert abs(slope - 2.0) < 1e-9
    assert abs(intercept) < 1e-9

    assert "O(N^2)" in _classify(2.05)
    assert "O(N)" in _classify(1.02)
    assert "O(1)" in _classify(0.01)


def test_profile_classifies_quadratic_program_monkeypatched(tmp_path, monkeypatch):
    """Determinista: sustituye el reloj para sintetizar tiempos O(N^2)."""
    import ripley.complexity_profiler as cp

    binary = tmp_path / "fake.out"
    binary.write_text("", encoding="utf-8")

    sizes = [100, 200, 400]
    # El profiler lee el reloj en pares (inicio, fin) por cada repetición.
    readings = []
    for n in sizes:
        readings.extend([0.0, max((n * n) * 1e-6, 0.001) / 1000.0])
    clock = iter(readings)
    monkeypatch.setattr(cp.time, "perf_counter", lambda: next(clock, 0.0))

    class FakeProc:
        returncode = 0

    monkeypatch.setattr(cp.subprocess, "run", lambda *a, **k: FakeProc())

    profiler = ComplexityProfiler(sizes=sizes, repeats_per_size=1)
    report = profiler.profile(binary, input_pattern="{n}\n")
    assert report.available
    assert len(report.measurements) == 3
    assert [m.n for m in report.measurements] == sizes
    assert report.slope == pytest.approx(2.0, abs=0.05)
    assert "O(N^2)" in report.classification


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_profile_real_quadratic_binary(tmp_path):
    src = tmp_path / "quad.c"
    src.write_text(
        """
#include <stdio.h>
int main(void) {
    long n;
    if (scanf("%ld", &n) != 1) return 1;
    volatile long acc = 0;
    for (long i = 0; i < n; i++)
        for (long j = 0; j < n; j++)
            acc += i + j;
    return 0;
}
""",
        encoding="utf-8",
    )
    binary = tmp_path / "quad.out"
    res = subprocess.run(
        ["gcc", "-std=c11", "-O0", str(src), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0

    # N grandes para que el cómputo domine el overhead de arranque del proceso.
    profiler = ComplexityProfiler(sizes=[2000, 5000, 10000], repeats_per_size=2)
    report = profiler.profile(binary, input_pattern="{n}\n")
    assert report.available
    assert report.r_squared > 0.8
    assert report.slope > 1.5


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_profile_reports_unavailable_for_unexecutable_file(tmp_path):
    fake_binary = tmp_path / "no_es_binario"
    fake_binary.write_text("esto no es ejecutable\n", encoding="utf-8")
    profiler = ComplexityProfiler(sizes=[10, 20], repeats_per_size=1)
    report = profiler.profile(fake_binary, input_pattern="{n}\n")
    assert not report.available
    assert report.measurements == []
