"""Integration tests for the complete Ripley grading and evaluation pipeline."""

from pathlib import Path
import zipfile
import pytest

from ripley.config import RipleyConfig
from ripley.evaluate import Evaluator
from ripley.exporter import MoodleExporter
from ripley.ingest import MoodleIngestor
from ripley.tools.runner import DynamicTestRunner
from ripley.tools.testcases import create_testcase_skeleton, TestCaseInfo


def test_complete_end_to_end_pipeline(tmp_path):
    ws = tmp_path / "workspace"
    templates_dir = tmp_path / "templates"
    from ripley.templates import init_templates
    init_templates(templates_dir)

    # 1. Crear ZIP sintético de Moodle con 2 estudiantes
    zip_path = tmp_path / "- (B6003) - 40- Programación I COM 1 - 2026-Entrega #1-1228009.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Estudiante 1: Código C correcto en ISO-8859-1 y con carpeta anidada
        zf.writestr(
            "Yucra Agustin Daniel_1848964_assignsubmission_file/subfolder/ejercicio1.c",
            """
            #include <stdio.h>
            int main(void)
            {
                int val = 0;
                if (scanf("%d", &val) == 1)
                {
                    printf("Resultado: %d\\n", val * 2);
                }
                return 0;
            }
            """.encode("iso-8859-1"),
        )
        # Archivo ignorado
        zf.writestr(
            "Yucra Agustin Daniel_1848964_assignsubmission_file/documento.pdf",
            b"%PDF-1.4 dummy",
        )

        # Estudiante 2: Código con error de sintaxis
        zf.writestr(
            "Perez Maria_223344_assignsubmission_file/ejercicio1.c",
            """
            #include <stdio.h>
            int main(void)
            {
                syntax_error_here;
                return 0;
            }
            """.encode("utf-8"),
        )

    # 2. Ingesta
    ingestor = MoodleIngestor(workspace_dir=ws)
    moodle_info, results_v1 = ingestor.process_zip(zip_path)
    assert moodle_info.activity_slug == "entrega-1_1228009"
    assert len(results_v1) == 2

    # 3. Crear Casos de Prueba
    create_testcase_skeleton(
        workspace_dir=ws,
        activity_slug=moodle_info.activity_slug,
        exercise="ejercicio1",
        cases_count=2,
    )
    # Configurar entradas y salidas esperadas
    t_dir = ws / "practicas" / moodle_info.activity_slug / "ejercicios" / "ejercicio1" / "tests"
    (t_dir / "caso1.in").write_text("10\n", encoding="utf-8")
    (t_dir / "caso1.out").write_text("Resultado: 20\n", encoding="utf-8")
    (t_dir / "caso2.in").write_text("25\n", encoding="utf-8")
    (t_dir / "caso2.out").write_text("Resultado: 50\n", encoding="utf-8")


    # 4. Evaluación inicial
    cfg = RipleyConfig()
    cfg.templates.ruta_plantillas = str(templates_dir)
    evaluator = Evaluator(config=cfg, workspace_dir=ws)

    eval_results = evaluator.evaluate_activity(moodle_info.activity_slug, parallel=False)
    assert len(eval_results) == 2

    yucra_res = next(r for r in eval_results if "yucra" in r.student_slug)
    assert yucra_res.compiled is True
    assert yucra_res.tests_passed == 2
    assert yucra_res.preliminary_grade > 8.0
    assert yucra_res.report_file.exists()

    perez_res = next(r for r in eval_results if "perez" in r.student_slug)
    assert perez_res.compiled is False
    assert perez_res.preliminary_grade == 0.0

    # 5. Exportación
    exporter = MoodleExporter(workspace_dir=ws)
    csv_file = exporter.export_grades_csv(moodle_info.activity_slug)
    zip_file = exporter.export_feedback_zip(moodle_info.activity_slug)
    dash_file = exporter.generate_dashboard(moodle_info.activity_slug)

    assert csv_file.exists()
    assert zip_file.exists()
    assert dash_file.exists()

    dash_content = dash_file.read_text(encoding="utf-8")
    assert "50.0%" in dash_content
    assert "Yucra Agustin Daniel" in dash_content



def test_infinite_loop_timeout(tmp_path):
    from ripley.tools.compiler import Compiler, CompilerConfig, LimitsConfig, SandboxConfig

    src_file = tmp_path / "infinite.c"
    src_file.write_text(
        """
        #include <stdio.h>
        int main(void)
        {
            while (1) {
                // bucle infinito
            }
            return 0;
        }
        """,
        encoding="utf-8",
    )
    bin_file = tmp_path / "infinite.out"

    compiler = Compiler(
        compiler_cfg=CompilerConfig(executable="gcc", flags=["-std=c11"]),
        limits_cfg=LimitsConfig(timeout_segundos=1),
        sandbox_cfg=SandboxConfig(),
    )
    comp_res = compiler.compile([src_file], bin_file)
    assert comp_res.success is True

    tc = TestCaseInfo(
        exercise="loop",
        case_name="caso1",
        in_file=None,
        out_file=None,
        argv_file=None,
    )
    runner = DynamicTestRunner(limits_cfg=LimitsConfig(timeout_segundos=1))
    res = runner.run_case(bin_file, tc)
    assert res.resultado == "TIMEOUT"
