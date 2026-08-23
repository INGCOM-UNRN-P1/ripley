"""Empirical asymptotic complexity profiler: O(N) vs O(N^2) regression fitting."""

from dataclasses import dataclass, field
import math
import statistics
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Sequence

# Exponentes canónicos para clasificación del slope log-log
COMPLEXITY_CLASSES = [
    (0.0, "O(1) / O(log N)"),
    (0.5, "O(sqrt(N))"),
    (1.0, "O(N)"),
    (1.5, "O(N log N)"),
    (2.0, "O(N^2)"),
    (3.0, "O(N^3)"),
]


@dataclass
class ComplexityMeasurement:
    n: int
    time_ms: float


@dataclass
class ComplexityReport:
    available: bool
    measurements: List[ComplexityMeasurement] = field(default_factory=list)
    slope: float = 0.0
    intercept: float = 0.0
    r_squared: float = 0.0
    classification: str = "Indeterminada"
    message: str = ""

    def summary(self) -> str:
        if not self.available or not self.measurements:
            return self.message
        points = ", ".join(f"N={m.n}: {m.time_ms:.2f}ms" for m in self.measurements)
        return f"{points} | pendiente log-log: {self.slope:.2f} (R²={self.r_squared:.3f}) → {self.classification}"


def _render_input(pattern: str, n: int) -> str:
    """Sustituye el placeholder {n} en la plantilla de entrada."""
    return pattern.replace("{n}", str(n))


def _linear_fit(xs: Sequence[float], ys: Sequence[float]) -> tuple:
    """Mínimos cuadrados simple; devuelve (slope, intercept)."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var = sum((x - mean_x) ** 2 for x in xs)
    if var == 0:
        return 0.0, mean_y
    slope = cov / var
    return slope, mean_y - slope * mean_x


def _classify(slope: float) -> str:
    best_label, best_distance = COMPLEXITY_CLASSES[0][1], abs(slope - COMPLEXITY_CLASSES[0][0])
    for exponent, label in COMPLEXITY_CLASSES[1:]:
        distance = abs(slope - exponent)
        if distance < best_distance:
            best_label, best_distance = label, distance
    return best_label


class ComplexityProfiler:
    """Ejecuta el binario con entradas de tamaño creciente y ajusta una curva
    de regresión no lineal sobre los tiempos para estimar la complejidad empírica."""

    def __init__(
        self,
        sizes: Optional[Sequence[int]] = None,
        repeats_per_size: int = 3,
        timeout_per_run_sec: float = 10.0,
        min_measurable_ms: float = 0.01,
    ) -> None:
        self.sizes = list(sizes or [10, 100, 1000, 10000])
        self.repeats_per_size = max(1, repeats_per_size)
        self.timeout_per_run_sec = timeout_per_run_sec
        self.min_measurable_ms = min_measurable_ms

    def profile(
        self,
        binary_path: str | Path,
        input_pattern: str = "{n}\n",
        cli_args: Sequence[str] = (),
    ) -> ComplexityReport:
        bin_path = str(binary_path)
        measurements: List[ComplexityMeasurement] = []

        for n in self.sizes:
            stdin_data = _render_input(input_pattern, n)
            times: List[float] = []
            crashed = False
            for _ in range(self.repeats_per_size):
                start = time.perf_counter()
                try:
                    proc = subprocess.run(
                        [bin_path, *cli_args],
                        input=stdin_data,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_per_run_sec,
                    )
                    elapsed_ms = max((time.perf_counter() - start) * 1000, self.min_measurable_ms)
                except subprocess.TimeoutExpired:
                    measurements.append(ComplexityMeasurement(n=n, time_ms=self.timeout_per_run_sec * 1000))
                    crashed = True
                    break
                except OSError:
                    # Binario inexistente o sin permiso de ejecución.
                    crashed = True
                    break
                if proc.returncode != 0:
                    crashed = True
                    break
                times.append(elapsed_ms)
            if crashed and not times:
                break
            if times:
                measurements.append(ComplexityMeasurement(n=n, time_ms=statistics.fmean(times)))

        if len(measurements) < 2:
            missing_sizes = set(self.sizes) - {m.n for m in measurements}
            return ComplexityReport(
                available=False,
                measurements=measurements,
                message=f"No se obtuvieron suficientes mediciones válidas (fallas en N={sorted(missing_sizes)} o binario sin ejecutar).",
            )

        xs = [math.log(m.n) for m in measurements]
        ys = [math.log(m.time_ms) for m in measurements]
        slope, intercept = _linear_fit(xs, ys)

        mean_y = sum(ys) / len(ys)
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0

        return ComplexityReport(
            available=True,
            measurements=measurements,
            slope=round(slope, 3),
            intercept=round(intercept, 3),
            r_squared=round(r_squared, 4),
            classification=_classify(slope),
            message="Perfilado de complejidad completado.",
        )
