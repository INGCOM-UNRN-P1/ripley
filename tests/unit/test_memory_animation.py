"""Unit tests for the step-by-step memory animation generator."""

import pytest

from ripley.core.memory_animation import (
    AnimationError,
    MemoryAnimator,
    export_gif,
    render_animation_svg,
    render_frame_svg,
)


def _sample_events() -> list:
    return [
        {"op": "decl", "var": "n", "type": "int", "value": "3"},
        {"op": "ptr", "var": "lista", "target": "#nodo1"},
        {"op": "malloc", "tag": "nodo1", "size": 32},
        {"op": "assign", "var": "n", "value": "4"},
        {"op": "free", "tag": "nodo1"},
    ]


def test_folding_produces_one_frame_per_event():
    frames = MemoryAnimator().apply(_sample_events())
    assert len(frames) == 5
    assert frames[0].caption.startswith("int n = 3")
    assert frames[2].heap[0].tag == "nodo1"
    assert frames[3].stack[0].value == "4"


def test_free_marks_cell_and_dangles_pointers():
    frames = MemoryAnimator().apply(_sample_events())
    last = frames[-1]
    assert last.heap[0].state == "freed"
    punteros = {p.name: p.target for p in last.pointers}
    assert punteros["lista"] == "DANGLING"


def test_double_free_rejected():
    animator = MemoryAnimator()
    with pytest.raises(AnimationError, match="double free"):
        animator.apply([
            {"op": "malloc", "tag": "x", "size": 8},
            {"op": "free", "tag": "x"},
            {"op": "free", "tag": "x"},
        ])


def test_leak_warning_appended_to_last_caption():
    frames = MemoryAnimator().apply([{"op": "malloc", "tag": "fuga", "size": 16}])
    assert "fuga" in frames[-1].caption and "sin liberar" in frames[-1].caption


def test_assign_undeclared_rejected():
    with pytest.raises(AnimationError, match="no declarada"):
        MemoryAnimator().apply([{"op": "assign", "var": "fantasma", "value": "1"}])


def test_unknown_op_rejected():
    with pytest.raises(AnimationError, match="desconocida"):
        MemoryAnimator().apply([{"op": "teleport"}])


def test_from_heap_ops_shorthand():
    frames = MemoryAnimator().from_heap_ops("malloc:32:n1,malloc:64:n2,free:n1,caption:estado final")
    assert len(frames) == 4
    # El caption final se anota con la fuga detectada de n2.
    assert frames[-1].caption.startswith("estado final")
    assert "n2 sin liberar" in frames[-1].caption
    assert [c.tag for c in frames[-1].heap] == ["n1", "n2"]
    states = {c.tag: c.state for c in frames[-1].heap}
    assert states == {"n1": "freed", "n2": "alloc"}


def test_frame_svg_contains_panels_and_escapes_html():
    animator = MemoryAnimator()
    frames = animator.apply([
        {"op": "decl", "var": "a<b>", "type": "int", "value": "1"},
        {"op": "malloc", "tag": "&cel", "size": 4},
    ])
    svg = render_frame_svg(frames[-1])
    assert svg.startswith("<svg")
    assert "STACK" in svg and "HEAP" in svg and "PUNTEROS" in svg
    assert "&lt;b&gt;" in svg  # escapado
    assert "<b>" not in svg


def test_animation_svg_has_frames_buttons_and_script():
    frames = MemoryAnimator().apply(_sample_events())
    svg = render_animation_svg(frames)
    for i in range(5):
        assert f'id="fr{i}"' in svg
    assert "toggle_auto" in svg and "show(frame_idx+1)" in svg
    assert svg.count("display:inline") == 1  # solo el primer frame visible
    assert f"var FRAMES = 5" in svg


def test_export_gif_graceful_without_imagemagick(tmp_path, monkeypatch):
    import shutil as sh

    monkeypatch.setattr(sh, "which", lambda name: None if name == "convert" else sh.which(name))
    ok, msg = export_gif([tmp_path / "inexistente.svg"], tmp_path / "out.gif")
    # sin convert → mensaje claro; con convert pero sin archivos → también mensaje
    assert ok is False
    assert msg
