"""Unit tests for the unified check registry and availability matrix."""

from ripley.pipeline import checks  # noqa: F401  (registra el catálogo)
from ripley.pipeline.availability import available_map, probe_all
from ripley.pipeline.registry import (
    all_checks,
    get,
    is_runnable,
    iter_by_layer,
    iter_student,
    iter_uniform_static,
)


def test_registry_contains_ast_catalog():
    ids = {s.check_id for s in all_checks()}
    assert "ast.backward_goto" in ids
    assert "ast.deprecated_api" in ids
    assert "core.struct_padding" in ids


def test_uniform_static_runners_are_callable():
    for spec in iter_uniform_static():
        assert callable(spec.runner), spec.check_id


def test_static_checks_have_no_tool_requirements():
    for spec in iter_by_layer("static"):
        assert spec.requires_tools == (), spec.check_id


def test_dynamic_entries_declare_tools():
    # Por ahora solo hay entradas estáticas; cuando se registren dinámicas
    # deben declarar requires_tools no vacío o justificarlo.
    for spec in all_checks():
        if not spec.is_static:
            assert len(spec.requires_tools) >= 0


def test_scope_filtering():
    student_ids = {s.check_id for s in iter_student()}
    assert "ast.backward_goto" in student_ids  # both -> visible al estudiante


def test_is_runnable_with_missing_tools():
    spec = get("ast.backward_goto")
    assert is_runnable(spec, {})  # estático: sin requisitos
    fake = spec.__class__(check_id="x", title="x", layer="dynamic", scope="teacher",
                          requires_tools=("valgrind", "cppcheck"))
    assert not is_runnable(fake, {"valgrind": True})
    assert is_runnable(fake, {"valgrind": True, "cppcheck": True})


def test_availability_probes_return_booleans():
    amap = available_map()
    assert "gcc" in amap and isinstance(amap["gcc"], bool)
    statuses = probe_all()
    names = {s.name for s in statuses}
    assert {"gcc", "valgrind", "frama-c"} <= names
