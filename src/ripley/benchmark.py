"""Energy consumption and CPU cycle benchmarking for computer architecture courses."""

from dataclasses import dataclass
import statistics
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Sequence

from ripley.instruction_counter import InstructionCounter

# Modelo energético simplificado (estimación didáctica, no medición física):
#  - Costo dinámico: instrucciones ejecutadas x energía por instrucción.
#  - Costo estático: tiempo en CPU x potencia de fuga del chip.
JOULES_PER_INSTRUCTION = 1.15e-9  # ~1.15 nJ/instrucción (referencia literatura x86_64)
STATIC_POWER_WATTS = 5.0  # Potencia de reposo estimada durante la ejecución
DEFAULT_CYCLES_PER_INSTRUCTION = 1.0  # IPC asumido para estimar ciclos


@dataclass
class BenchmarkResult:
    binary: str
    repeats: int
    wall_times_ms: List[float]
    mean_time_ms: float
    min_time_ms: float
    max_time_ms: float
    stddev_time_ms: float
    instruction_count: int
    estimated_cycles: int
    estimated_energy_joules: float
    instructions_per_second: float
    counters_available: bool

    @property
    def throughput_score(self) -> float:
        """Instrucciones por milisegundo: mayor es mejor."""
        if self.mean_time_ms <= 0:
            return 0.0
        return self.instruction_count / self.mean_time_ms


class EnergyBenchmark:
    """Mide tiempo de ejecución y cuenta de instrucciones para estimar consumo
    energético relativo entre entregas de los alumnos."""

    def __init__(
        self,
        repeats: int = 5,
        timeout_sec: float = 10.0,
        cycles_per_instruction: float = DEFAULT_CYCLES_PER_INSTRUCTION,
        joules_per_instruction: float = JOULES_PER_INSTRUCTION,
        static_power_watts: float = STATIC_POWER_WATTS,
    ) -> None:
        if repeats < 1:
            raise ValueError("repeats debe ser >= 1")
        self.repeats = repeats
        self.timeout_sec = timeout_sec
        self.cycles_per_instruction = cycles_per_instruction
        self.joules_per_instruction = joules_per_instruction
        self.static_power_watts = static_power_watts
        self._counter = InstructionCounter()

    def run(
        self,
        binary_path: Path | str,
        stdin_data: str = "",
        cli_args: Sequence[str] = (),
    ) -> BenchmarkResult:
        bin_path = Path(binary_path)
        wall_times: List[float] = []
        counters_available = True

        for _ in range(self.repeats):
            start = time.perf_counter()
            try:
                subprocess.run(
                    [str(bin_path), *cli_args],
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                )
            except subprocess.TimeoutExpired:
                wall_times.append(self.timeout_sec * 1000)
            wall_times.append((time.perf_counter() - start) * 1000)

        count_result = self._counter.count_instructions(bin_path, stdin_data=stdin_data, cli_args=cli_args)
        instruction_count = count_result.instruction_count
        if not self._counter.valgrind_path:
            counters_available = False

        mean_time = statistics.fmean(wall_times)
        est_cycles = int(instruction_count / self.cycles_per_instruction) if self.cycles_per_instruction > 0 else 0
        dynamic_joules = instruction_count * self.joules_per_instruction
        static_joules = (mean_time / 1000.0) * self.static_power_watts
        estimated_energy = dynamic_joules + static_joules

        return BenchmarkResult(
            binary=str(bin_path),
            repeats=self.repeats,
            wall_times_ms=[round(t, 3) for t in wall_times],
            mean_time_ms=round(mean_time, 3),
            min_time_ms=round(min(wall_times), 3),
            max_time_ms=round(max(wall_times), 3),
            stddev_time_ms=round(statistics.pstdev(wall_times), 3) if len(wall_times) > 1 else 0.0,
            instruction_count=instruction_count,
            estimated_cycles=est_cycles,
            estimated_energy_joules=round(estimated_energy, 12),
            instructions_per_second=round(instruction_count / (mean_time / 1000.0), 2) if mean_time > 0 else 0.0,
            counters_available=counters_available,
        )
