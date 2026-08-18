"""Unit tests for testcase management module."""

from ripley.testcases import (
    check_testcases_integrity,
    create_testcase_skeleton,
    discover_testcases,
)


def test_create_testcase_skeleton_and_discover(tmp_path):
    ws = tmp_path
    act_slug = "entrega-1_1228009"
    created = create_testcase_skeleton(
        workspace_dir=ws,
        activity_slug=act_slug,
        exercise="ejercicio1",
        cases_count=2,
        with_argv=True,
    )
    assert len(created) == 6  # 2 .in, 2 .out, 2 .argv

    discovered = discover_testcases(ws, act_slug)
    assert "ejercicio1" in discovered
    assert len(discovered["ejercicio1"]) == 2

    tc1 = discovered["ejercicio1"][0]
    assert tc1.case_name == "caso1"
    assert tc1.in_file.exists()
    assert tc1.out_file.exists()
    assert tc1.argv_file.exists()
    assert tc1.is_complete is True


def test_check_testcases_integrity(tmp_path):
    ws = tmp_path
    act_slug = "entrega-1_1228009"

    # Caso completo
    create_testcase_skeleton(
        workspace_dir=ws,
        activity_slug=act_slug,
        exercise="ejercicio1",
        cases_count=1,
    )
    is_valid, errors = check_testcases_integrity(ws, act_slug)
    assert is_valid is True
    assert len(errors) == 0

    # Romper integridad borrando .out
    out_file = ws / "practicas" / act_slug / "ejercicios" / "ejercicio1" / "tests" / "caso1.out"
    out_file.unlink()


    is_valid, errors = check_testcases_integrity(ws, act_slug)
    assert is_valid is False
    assert any("Falta archivo de salida esperada" in err for err in errors)
