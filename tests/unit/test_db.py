"""Unit tests for SQLite database manager."""

from ripley.db import DatabaseManager, StudentRecord


def test_db_init_and_student_upsert(tmp_path):
    db_file = tmp_path / ".metadata.db"
    db = DatabaseManager(db_file)

    student = StudentRecord(
        student_id="1848964",
        full_name="Yucra Agustin Daniel",
        slug="yucra-agustin-daniel_1848964",
        submission_id="1848964",
    )
    db.upsert_student(student)

    # Re-upsert with updated name
    student.full_name = "Yucra Agustin D."
    db.upsert_student(student)


def test_add_and_retrieve_revisions(tmp_path):
    db_file = tmp_path / ".metadata.db"
    db = DatabaseManager(db_file)

    student_slug = "test-student_101"
    db.upsert_student(
        StudentRecord(
            student_id="101",
            full_name="Test Student",
            slug=student_slug,
            submission_id="101",
        )
    )

    # Revision 1
    rev1_id = db.add_revision(
        student_slug=student_slug,
        version_num=1,
        sources_hash="hash_v1",
        folder_path="/tmp/r1",
        sources=[{"filename": "main.c", "file_hash": "h1", "size_bytes": 100}],
        ignored=[{"filename": "doc.pdf", "reason": "No permitido"}],
    )
    assert rev1_id == 1

    latest = db.get_latest_revision(student_slug)
    assert latest["version_num"] == 1
    assert latest["sources_hash"] == "hash_v1"

    # Revision 2
    rev2_id = db.add_revision(
        student_slug=student_slug,
        version_num=2,
        sources_hash="hash_v2",
        folder_path="/tmp/r2",
        sources=[{"filename": "main.c", "file_hash": "h2", "size_bytes": 120}],
        ignored=[],
    )
    assert rev2_id == 2

    latest2 = db.get_latest_revision(student_slug)
    assert latest2["version_num"] == 2
    assert latest2["sources_hash"] == "hash_v2"

    all_revs = db.get_all_revisions(student_slug)
    assert len(all_revs) == 2


def test_save_and_get_evaluation(tmp_path):
    db_file = tmp_path / ".metadata.db"
    db = DatabaseManager(db_file)

    student_slug = "eval-student_202"
    db.upsert_student(
        StudentRecord(
            student_id="202",
            full_name="Eval Student",
            slug=student_slug,
            submission_id="202",
        )
    )

    rev_id = db.add_revision(
        student_slug=student_slug,
        version_num=1,
        sources_hash="h1",
        folder_path="/tmp/r1",
        sources=[],
        ignored=[],
    )

    db.save_evaluation(
        revision_id=rev_id,
        compilation_status="OK",
        preliminary_grade=9.5,
        grade_compilation=10.0,
        grade_style=9.0,
        grade_linter=9.0,
        grade_tests=10.0,
        unified_diff="+ new code",
        compilation_logs="Compiled cleanly",
        test_results=[
            {
                "exercise": "ejercicio1",
                "test_case": "caso1",
                "cli_args": "--help",
                "result": "PASSED",
                "exec_time_ms": 12.5,
            }
        ],
    )

    eval_data = db.get_student_evaluation(rev_id)
    assert eval_data is not None
    assert eval_data["compilation_status"] == "OK"
    assert eval_data["preliminary_grade"] == 9.5
    assert len(eval_data["test_results"]) == 1
    assert eval_data["test_results"][0]["test_case"] == "caso1"
