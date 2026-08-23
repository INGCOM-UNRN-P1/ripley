"""Moodle grades exporter, feedback packager and cohort dashboard generator."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import zipfile

from ripley.teacher.db import DatabaseManager


@dataclass
class CohortMetrics:
    total_students: int
    compiled_count: int
    compilation_rate_pct: float
    avg_grade: float
    avg_style: float
    top_style_errors: List[tuple[str, int]]
    student_summaries: List[Dict[str, Any]]


class MoodleExporter:
    """Exporta calificaciones y retroalimentación compatibles con Moodle y genera el dashboard docente."""

    def __init__(self, workspace_dir: str | Path = ".") -> None:
        self.workspace_dir = Path(workspace_dir)

    def _get_all_activity_data(self, activity_slug: str) -> List[Dict[str, Any]]:
        activity_dir = self.workspace_dir / activity_slug
        if not activity_dir.exists():
            raise FileNotFoundError(f"Directorio de actividad no encontrado: {activity_dir}")

        students_data: List[Dict[str, Any]] = []

        for s_dir in sorted(activity_dir.iterdir()):
            if not s_dir.is_dir() or s_dir.name.startswith("."):
                continue

            db_path = s_dir / ".metadata.db"
            if not db_path.exists():
                continue

            db = DatabaseManager(db_path)
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM students WHERE slug = ?", (s_dir.name,))
                student_row = cursor.fetchone()

                latest_rev = db.get_latest_revision(s_dir.name)
                if not latest_rev:
                    continue

                cursor.execute(
                    "SELECT * FROM evaluations WHERE revision_id = ?", (latest_rev["id"],)
                )
                eval_row = cursor.fetchone()

                clean_slug = Path(activity_slug).name or activity_slug.strip("/\\")
                rep_candidate = s_dir / f"{s_dir.name}_{clean_slug}.md"
                if not rep_candidate.exists():
                    # Fallback si existe con nombre simple <student_slug>.md o cualquier .md
                    if (s_dir / f"{s_dir.name}.md").exists():
                        rep_candidate = s_dir / f"{s_dir.name}.md"
                    else:
                        mds = [f for f in s_dir.glob("*.md") if f.is_file()]
                        if mds:
                            rep_candidate = mds[0]

                s_dict = {
                    "slug": s_dir.name,
                    "student_name": student_row["full_name"] if student_row else s_dir.name,
                    "student_id": student_row["student_id"] if student_row else "0",
                    "submission_id": student_row["submission_id"] if student_row else "0",
                    "version_num": latest_rev["version_num"],
                    "folder_path": latest_rev["folder_path"],
                    "compilation_status": eval_row["compilation_status"] if eval_row else "NO_EVAL",
                    "preliminary_grade": eval_row["preliminary_grade"] if eval_row else 0.0,
                    "grade_compilation": eval_row["grade_compilation"] if eval_row else 0.0,
                    "grade_style": eval_row["grade_style"] if eval_row else 0.0,
                    "grade_linter": eval_row["grade_linter"] if eval_row else 0.0,
                    "grade_tests": eval_row["grade_tests"] if eval_row else 0.0,
                    "report_file": rep_candidate,
                }
                students_data.append(s_dict)


        return students_data

    def export_grades_csv(
        self,
        activity_slug: str,
        output_file: Optional[Path | str] = None,
    ) -> Path:
        """Exporta CSV estructurado para importar al Libro de Calificaciones de Moodle."""
        activity_dir = self.workspace_dir / activity_slug
        csv_path = Path(output_file) if output_file else activity_dir / "moodle_grades.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        data = self._get_all_activity_data(activity_slug)

        fieldnames = [
            "Identificador",
            "Nombre completo",
            "Número de ID",
            "Calificación",
            "Última modificación (calificación)",
            "Comentarios de retroalimentación",
        ]

        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in data:
                grade_str = f"{item['preliminary_grade']:.2f}"
                feedback = (
                    f"Revisión r{item['version_num']} | "
                    f"Compilación: {item['compilation_status']} | "
                    f"Estilo: {item['grade_style']:.1f}/10 | "
                    f"Tests: {item['grade_tests']:.1f}/10"
                )
                writer.writerow(
                    {
                        "Identificador": f"Participante {item['submission_id']}",
                        "Nombre completo": item["student_name"],
                        "Número de ID": item["student_id"],
                        "Calificación": grade_str,
                        "Última modificación (calificación)": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Comentarios de retroalimentación": feedback,
                    }
                )

        return csv_path

    def export_feedback_zip(
        self,
        activity_slug: str,
        output_file: Optional[Path | str] = None,
    ) -> Path:
        """Empaqueta los informes Markdown en un ZIP listo para retroalimentación masiva de Moodle."""
        activity_dir = self.workspace_dir / activity_slug
        zip_path = Path(output_file) if output_file else activity_dir / "retroalimentacion_moodle.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        data = self._get_all_activity_data(activity_slug)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in data:
                report_file = item["report_file"]
                if report_file.exists():
                    # Formato de subida masiva de retroalimentación de Moodle
                    moodle_folder_name = f"{item['student_name']}_{item['submission_id']}_assignsubmission_file"
                    arcname = f"{moodle_folder_name}/{report_file.name}"
                    zf.write(report_file, arcname=arcname)

        return zip_path

    def generate_dashboard(
        self,
        activity_slug: str,
        output_file: Optional[Path | str] = None,
    ) -> Path:
        """Genera un reporte consolidado dashboard.md para el docente con métricas de la cohorte."""
        activity_dir = self.workspace_dir / activity_slug
        dash_path = Path(output_file) if output_file else activity_dir / "dashboard.md"
        dash_path.parent.mkdir(parents=True, exist_ok=True)

        data = self._get_all_activity_data(activity_slug)
        total = len(data)
        if total == 0:
            dash_path.write_text(f"# Dashboard de Cohorte - {activity_slug}\n\nSin entregas evaluadas.\n", encoding="utf-8")
            return dash_path

        compiled_count = sum(1 for d in data if d["compilation_status"] == "OK")
        compilation_rate = (compiled_count / total) * 100.0
        avg_grade = sum(d["preliminary_grade"] for d in data) / total
        avg_style = sum(d["grade_style"] for d in data) / total

        lines: List[str] = [
            f"# Dashboard de Cohorte - Actividad: {activity_slug}",
            f"**Fecha de generación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Total de entregas evaluadas:** {total}\n",
            "## Métricas Generales\n",
            f"- **Tasa de Compilación:** {compilation_rate:.1f}% ({compiled_count}/{total})",
            f"- **Promedio de Nota Preliminar:** {avg_grade:.2f} / 10.0",
            f"- **Cumplimiento de Estilo Promedio:** {avg_style:.2f} / 10.0\n",
            "## Resumen Consolidado por Estudiante\n",
            "| Estudiante | ID Entrega | Revisión | Compilación | Estilo | Tests I/O | Nota Preliminar |",
            "| ---------- | ---------- | -------- | ----------- | ------ | --------- | --------------- |",
        ]

        for item in data:
            comp_badge = "✓ OK" if item["compilation_status"] == "OK" else "✗ FAIL"
            lines.append(
                f"| `{item['student_name']}` | {item['submission_id']} | r{item['version_num']} | {comp_badge} | {item['grade_style']:.1f} | {item['grade_tests']:.1f} | **{item['preliminary_grade']:.2f}** |"
            )

        lines.append("\n---\n*Generado automáticamente por Ripley.*")

        dash_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return dash_path
