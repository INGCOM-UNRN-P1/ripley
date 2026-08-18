"""Unit tests for evaluation orchestrator."""

from pathlib import Path
from ripley.config import RipleyConfig
from ripley.db import DatabaseManager, StudentRecord
from ripley.evaluate import Evaluator
from ripley.testcases import create_testcase_skeleton


def test_evaluator_evaluates_student_successfully(tmp_path):
    ws = tmp_path
    act_slug = "entrega-1_1228009"
    student_slug = "perez-juan_12345"

    student_dir = ws / act_slug / student_slug
    r1_dir = student_dir / "r1"
    r1_dir.mkdir(parents=True, exist_ok=True)

    # Código C limpio que responde a la prueba
    (r1_dir / "ejercicio1.c").write_text(
        """
        #include <stdio.h>

        int main(void)
        {
            int n = 0;
            if (scanf("%d", &n) == 1)
            {
                printf("%d\\n", n * 2);
            }
            return 0;
        }
        """,
        encoding="utf-8",
    )

    # Base de datos
    db = DatabaseManager(student_dir / ".metadata.db")
    db.upsert_student(
        StudentRecord(
            student_id="12345",
            full_name="Perez Juan",
            slug=student_slug,
            submission_id="12345",
        )
    )
    db.add_revision(
        student_slug=student_slug,
        version_num=1,
        sources_hash="sha123",
        folder_path=str(r1_dir),
        sources=[{"filename": "ejercicio1.c", "file_hash": "sha123", "size_bytes": 100}],
        ignored=[],
    )

    # Crear caso de prueba en practicas/
    tests_ex_dir = ws / "practicas" / act_slug / "ejercicios" / "ejercicio1" / "tests"
    tests_ex_dir.mkdir(parents=True, exist_ok=True)
    (tests_ex_dir / "caso1.in").write_text("5\n", encoding="utf-8")
    (tests_ex_dir / "caso1.out").write_text("10\n", encoding="utf-8")


    cfg = RipleyConfig()
    evaluator = Evaluator(config=cfg, workspace_dir=ws)

    results = evaluator.evaluate_activity(activity_slug=act_slug, parallel=False)

    assert len(results) == 1
    res = results[0]
    assert res.student_slug == student_slug
    assert res.compiled is True
    assert res.tests_passed == 1
    assert res.total_tests == 1
    assert res.preliminary_grade > 8.0
    assert res.report_file.exists()

    # Verificar contenido del reporte acumulativo
    report_text = res.report_file.read_text(encoding="utf-8")
    assert "Versión 1" in report_text
    assert "ejercicio1" in report_text
    assert "PASSED" in report_text
