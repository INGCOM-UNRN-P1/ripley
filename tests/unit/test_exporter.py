"""Unit tests for Moodle exporter, CSV, feedback zip and cohort dashboard."""

import csv
from pathlib import Path
import zipfile

from ripley.db import DatabaseManager, StudentRecord
from ripley.exporter import MoodleExporter


def test_exporter_grades_csv_feedback_zip_and_dashboard(tmp_path):
    ws = tmp_path
    act_slug = "entrega-1_1228009"
    student_slug = "yucra-agustin-daniel_1848964"

    student_dir = ws / act_slug / student_slug
    student_dir.mkdir(parents=True, exist_ok=True)

    # Base de datos con estudiante y evaluación
    db = DatabaseManager(student_dir / ".metadata.db")
    db.upsert_student(
        StudentRecord(
            student_id="1848964",
            full_name="Yucra Agustin Daniel",
            slug=student_slug,
            submission_id="1848964",
        )
    )
    rev_id = db.add_revision(
        student_slug=student_slug,
        version_num=1,
        sources_hash="hash1",
        folder_path=str(student_dir / "r1"),
        sources=[],
        ignored=[],
    )
    db.save_evaluation(
        revision_id=rev_id,
        compilation_status="OK",
        preliminary_grade=9.25,
        grade_compilation=10.0,
        grade_style=9.0,
        grade_linter=10.0,
        grade_tests=8.5,
        unified_diff="",
        compilation_logs="",
        test_results=[],
    )

    # Reporte markdown
    report_file = student_dir / f"{student_slug}_{act_slug}.md"
    report_file.write_text("# Informe de Evaluacion\nNota: 9.25", encoding="utf-8")

    exporter = MoodleExporter(workspace_dir=ws)

    # 1. Export CSV
    csv_file = exporter.export_grades_csv(act_slug)
    assert csv_file.exists()

    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        row = reader[0]
        assert row["Nombre completo"] == "Yucra Agustin Daniel"
        assert row["Número de ID"] == "1848964"
        assert row["Calificación"] == "9.25"

    # 2. Export Feedback Zip
    zip_file = exporter.export_feedback_zip(act_slug)
    assert zip_file.exists()

    with zipfile.ZipFile(zip_file, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 1
        assert "Yucra Agustin Daniel_1848964_assignsubmission_file" in namelist[0]

    # 3. Generate Dashboard
    dash_file = exporter.generate_dashboard(act_slug)
    assert dash_file.exists()
    dash_text = dash_file.read_text(encoding="utf-8")
    assert "Dashboard de Cohorte" in dash_text
    assert "100.0%" in dash_text
    assert "Yucra Agustin Daniel" in dash_text
