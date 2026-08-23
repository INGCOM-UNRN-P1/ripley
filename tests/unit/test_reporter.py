"""Unit tests for Markdown reporter and Jinja2 rendering."""

from pathlib import Path
from ripley.teacher.reporter import (
    MarkdownReporter,
    StudentReportContext,
    VersionReportContext,
)


def test_markdown_reporter_render_and_write(tmp_path):
    reporter = MarkdownReporter()

    v1 = VersionReportContext(
        numero_version=1,
        fecha_hora="2026-08-18 10:00:00",
        archivos_nuevos="1",
        archivos_modificados="0",
        archivos_sin_cambios="0",
        archivos_ignorados="0",
        diff_unificado="+int main() {}",
        resultados_compilacion=[
            {
                "nombre_archivo": "main.c",
                "estado": "OK",
                "estado_estilo": "10/10",
                "estado_valgrind": "Limpio",
                "estado_cppcheck": "0 advertencias",
            }
        ],
        observaciones_estilo=[],
        logs_detallados_compilacion="Compilación limpia",
        resultados_pruebas=[
            {
                "ejercicio": "ejercicio1",
                "nombre_caso": "caso1",
                "argumentos_cli": "--help",
                "resultado": "PASSED",
                "tiempo_ms": 5.4,
            }
        ],
        nota_preliminar=10.0,
        nota_compilacion=10.0,
        nota_estilo=10.0,
        nota_linter=10.0,
        nota_pruebas=10.0,
    )

    ctx = StudentReportContext(
        estudiante_nombre="Perez Juan",
        estudiante_id="123456",
        actividad_nombre="Entrega #1",
        actividad_id="999",
        revision_actual="r1",
        fecha_generacion="2026-08-18 10:00:00",
        versiones=[v1],
        nota_final_preliminar=10.0,
    )

    out_file = tmp_path / "perez-juan_123456_entrega-1_999.md"
    written_path = reporter.write_student_report(out_file, ctx)

    assert written_path.exists()
    content = written_path.read_text(encoding="utf-8")
    assert "Perez Juan" in content
    assert "123456" in content
    assert "Configuración:" in content
    assert "Versión 1" in content
    assert "Nota Preliminar Estimada: 10.0 / 10" in content
    assert "ejercicio1" in content

