"""Unit tests for HeapMemorySimulator."""

from ripley.core.heap_simulator import HeapMemorySimulator


def test_heap_simulator_allocation_and_coalescence():
    sim = HeapMemorySimulator(capacity=1024)

    # 1. Asignaciones sucesivas
    off1 = sim.allocate(100, tag="a")
    off2 = sim.allocate(200, tag="b")
    off3 = sim.allocate(300, tag="c")

    assert off1 == 0
    assert off2 == 100 or off2 == 104  # depending on 4-byte alignment
    assert sim.peak_allocated > 0

    # 2. Liberación intermedia crea fragmentación
    assert sim.free(off2) is True
    total_free, largest_free, frag_index = sim.calculate_fragmentation()
    assert frag_index > 0.0

    # 3. Liberar bloques adyacentes produce coalescencia (compactación)
    assert sim.free(off1) is True
    assert sim.free(off3) is True

    total_free_after, largest_free_after, frag_after = sim.calculate_fragmentation()
    assert total_free_after == 1024
    assert largest_free_after == 1024
    assert frag_after == 0.0
    assert len(sim.blocks) == 1

    # Reporte
    rep = sim.get_report()
    assert rep.total_capacity == 1024
    assert "░" in rep.memory_map
