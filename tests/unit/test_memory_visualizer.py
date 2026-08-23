"""Unit tests for DynamicMemoryVisualizer."""

from pathlib import Path
from ripley.core.memory_visualizer import DynamicMemoryVisualizer


def test_memory_visualizer_extracts_structs_and_generates_diagrams(tmp_path):
    c_file = tmp_path / "lista.c"
    c_file.write_text(
        """
        struct Nodo {
            int valor;
            struct Nodo *siguiente;
        };

        struct Lista {
            struct Nodo *cabeza;
            int longitud;
        };
        """,
        encoding="utf-8",
    )

    vis = DynamicMemoryVisualizer()
    structs = vis.extract_structs(c_file.read_text(encoding="utf-8"))

    assert "Nodo" in structs
    assert "Lista" in structs
    assert len(structs["Nodo"].fields) == 2
    assert structs["Nodo"].fields[1].is_pointer is True

    # Mermaid format
    mermaid = vis.to_mermaid(structs)
    assert "class Nodo" in mermaid
    assert "class Lista" in mermaid

    # DOT format
    dot = vis.to_dot(structs)
    assert "digraph DataStructures" in dot
    assert "node_Nodo" in dot
