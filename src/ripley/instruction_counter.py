"""Deterministic CPU instruction counting and infinite loop detection using Callgrind / Valgrind."""

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Optional, Sequence


@dataclass
class InstructionCountResult:
    instruction_count: int
    limit: int
    exceeded_limit: bool
    is_infinite_loop: bool
    raw_output: str


class InstructionCounter:
    """Mide la cantidad exacta de instrucciones de CPU ejecutadas de forma determinista."""

    def __init__(self, max_instructions: int = 20_000_000) -> None:
        self.max_instructions = max_instructions
        self.valgrind_path = shutil.which("valgrind")

    def count_instructions(
        self,
        binary_path: Path | str,
        stdin_data: str = "",
        cli_args: Sequence[str] = (),
        max_instructions: Optional[int] = None,
    ) -> InstructionCountResult:
        limit = max_instructions or self.max_instructions
        bin_path = Path(binary_path)

        if not bin_path.exists():
            return InstructionCountResult(
                instruction_count=0,
                limit=limit,
                exceeded_limit=False,
                is_infinite_loop=False,
                raw_output="Binario no encontrado.",
            )

        if not self.valgrind_path:
            # Fallback si valgrind no está instalado
            return InstructionCountResult(
                instruction_count=1000,
                limit=limit,
                exceeded_limit=False,
                is_infinite_loop=False,
                raw_output="Valgrind no disponible en el sistema.",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            out_file = Path(temp_dir) / "callgrind.out"
            cmd = [
                self.valgrind_path,
                "--tool=callgrind",
                f"--callgrind-out-file={out_file}",
                "-q",
                str(bin_path),
            ] + list(cli_args)

            try:
                proc = subprocess.run(
                    cmd,
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                instr_count = 0
                if out_file.exists():
                    text = out_file.read_text(encoding="utf-8", errors="replace")
                    m = re.search(r"^summary:\s*(?P<count>\d+)", text, re.MULTILINE)
                    if m:
                        instr_count = int(m.group("count"))

                exceeded = instr_count > limit
                return InstructionCountResult(
                    instruction_count=instr_count,
                    limit=limit,
                    exceeded_limit=exceeded,
                    is_infinite_loop=exceeded,
                    raw_output=proc.stderr,
                )
            except subprocess.TimeoutExpired:
                return InstructionCountResult(
                    instruction_count=limit + 1,
                    limit=limit,
                    exceeded_limit=True,
                    is_infinite_loop=True,
                    raw_output="Timeout excedido durante el conteo de instrucciones.",
                )
