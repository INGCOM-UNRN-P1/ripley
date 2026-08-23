"""Unit tests for InstructionCounter."""

from pathlib import Path
from ripley.tools.instruction_counter import InstructionCounter


def test_instruction_counter_execution_and_threshold(tmp_path, monkeypatch):
    counter = InstructionCounter(max_instructions=1000)
    bin_file = tmp_path / "prog"
    bin_file.touch()

    # Si valgrind no está presente o mockeado, retorna estructura válida
    res = counter.count_instructions(bin_file)
    assert res.limit == 1000
    assert isinstance(res.instruction_count, int)
    assert isinstance(res.is_infinite_loop, bool)
