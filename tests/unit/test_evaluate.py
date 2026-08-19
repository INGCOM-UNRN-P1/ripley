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


def test_evaluator_activity_custom_verification_tools(tmp_path):
    ws = tmp_path
    act_slug = "tp-custom_999"
    student_slug = "gomez-ana_999"

    student_dir = ws / act_slug / student_slug
    r1_dir = student_dir / "r1"
    r1_dir.mkdir(parents=True, exist_ok=True)
    (r1_dir / "ejercicio1.c").write_text(
        "int main(void) { return 0; }\n",
        encoding="utf-8",
    )

    db = DatabaseManager(student_dir / ".metadata.db")
    db.upsert_student(
        StudentRecord(
            student_id="999",
            full_name="Gomez Ana",
            slug=student_slug,
            submission_id="999",
        )
    )
    db.add_revision(
        student_slug=student_slug,
        version_num=1,
        sources_hash="sha999",
        folder_path=str(r1_dir),
        sources=[{"filename": "ejercicio1.c", "file_hash": "sha999", "size_bytes": 30}],
        ignored=[],
    )

    # Crear ripley.toml en practicas/<act_slug> con cppcheck y valgrind desactivados
    practice_dir = ws / "practicas" / act_slug
    practice_dir.mkdir(parents=True, exist_ok=True)
    (practice_dir / "ripley.toml").write_text(
        """
        [compiler]
        enabled = true

        [cppcheck]
        enabled = false

        [valgrind]
        enabled = false

        [style]
        enabled = false

        [rubric]
        peso_compilacion = 0.5
        peso_linter = 0.0
        peso_estilo = 0.0
        peso_pruebas = 0.5
        """,
        encoding="utf-8",
    )

    evaluator = Evaluator(config=RipleyConfig(), workspace_dir=ws)
    res = evaluator.evaluate_student(act_slug, student_dir)

    assert res is not None
    assert res.compiled is True
    report_text = res.report_file.read_text(encoding="utf-8")
    assert "Desactivado" in report_text
    assert f"practicas/{act_slug}/ripley.toml" in report_text


def test_evaluator_runs_custom_cli_tools(tmp_path):
    ws = tmp_path
    act_slug = "tp-custom-tools_111"
    student_slug = "lopez-maria_111"

    student_dir = ws / act_slug / student_slug
    r1_dir = student_dir / "r1"
    r1_dir.mkdir(parents=True, exist_ok=True)
    (r1_dir / "ejercicio1.c").write_text(
        "int main(void) { return 0; }\n",
        encoding="utf-8",
    )

    db = DatabaseManager(student_dir / ".metadata.db")
    db.upsert_student(
        StudentRecord(
            student_id="111",
            full_name="Lopez Maria",
            slug=student_slug,
            submission_id="111",
        )
    )
    db.add_revision(
        student_slug=student_slug,
        version_num=1,
        sources_hash="sha111",
        folder_path=str(r1_dir),
        sources=[{"filename": "ejercicio1.c", "file_hash": "sha111", "size_bytes": 30}],
        ignored=[],
    )

    # Crear ripley.toml con una custom_tool
    practice_dir = ws / "practicas" / act_slug
    practice_dir.mkdir(parents=True, exist_ok=True)
    (practice_dir / "ripley.toml").write_text(
        """
        [compiler]
        enabled = true

        [[custom_tools]]
        name = "auditor_personalizado"
        command = "echo Auditoria_OK_para_{filename}"
        enabled = true
        stage = "source"
        fail_on_error = false
        """,
        encoding="utf-8",
    )

    evaluator = Evaluator(config=RipleyConfig(), workspace_dir=ws)
    res = evaluator.evaluate_student(act_slug, student_dir)

    assert res is not None
    report_text = res.report_file.read_text(encoding="utf-8")
    assert "auditor_personalizado" in report_text
    assert "Auditoria_OK_para_ejercicio1.c" in report_text


def test_evaluator_runs_diagrams_and_advanced_verifications(tmp_path):
    ws = tmp_path
    act_slug = "tp-diagrams_222"
    student_slug = "diaz-carlos_222"

    student_dir = ws / act_slug / student_slug
    r1_dir = student_dir / "r1"
    r1_dir.mkdir(parents=True, exist_ok=True)
    (r1_dir / "ejercicio1.c").write_text(
        """
        #include <stdio.h>
        struct Nodo {
            int dato;
            struct Nodo *sig;
        };

        void procesar(int x) {
            if (x > 0) {
                printf("Positivo\\n");
            }
        }

        int main(void) {
            procesar(10);
            return 0;
        }
        """,
        encoding="utf-8",
    )

    db = DatabaseManager(student_dir / ".metadata.db")
    db.upsert_student(
        StudentRecord(
            student_id="222",
            full_name="Diaz Carlos",
            slug=student_slug,
            submission_id="222",
        )
    )
    db.add_revision(
        student_slug=student_slug,
        version_num=1,
        sources_hash="sha222",
        folder_path=str(r1_dir),
        sources=[{"filename": "ejercicio1.c", "file_hash": "sha222", "size_bytes": 120}],
        ignored=[],
    )

    practice_dir = ws / "practicas" / act_slug
    practice_dir.mkdir(parents=True, exist_ok=True)
    (practice_dir / "ripley.toml").write_text(
        """
        [compiler]
        enabled = true

        [flowchart]
        enabled = true
        format = "mermaid"

        [memory_visualizer]
        enabled = true

        [callgraph]
        enabled = true
        format = "mermaid"

        [ast_auditors]
        enabled = true
        """,
        encoding="utf-8",
    )

    evaluator = Evaluator(config=RipleyConfig(), workspace_dir=ws)
    res = evaluator.evaluate_student(act_slug, student_dir)

    assert res is not None
    report_text = res.report_file.read_text(encoding="utf-8")
    assert "Diagrama de Flujo" in report_text
    assert "Diagrama de Topología de Memoria" in report_text
    assert "Grafo de Invocación / Call Graph" in report_text



