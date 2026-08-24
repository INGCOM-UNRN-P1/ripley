"""Integration tests for the complete Ripley grading and evaluation pipeline."""

from pathlib import Path
import zipfile
import pytest

from ripley.config import RipleyConfig
from ripley.teacher.evaluate import Evaluator
from ripley.tools.runner import DynamicTestRunner
from ripley.tools.testcases import create_testcase_skeleton, TestCaseInfo


def test_complete_end_to_end_pipeline(tmp_path):
    ws = tmp_path / "workspace"
    templates_dir = tmp_path / "templates"
    from ripley.teacher.templates import init_templates
    init_templates(templates_dir)

    # 1. Crear estructura de entrega directa para 2 estudiantes
    activity_slug = "entrega-1_1228009"
    yucra_dir = ws / activity_slug / "yucra-agustin-daniel_1848964" / "r1"
    yucra_dir.mkdir(parents=True, exist_ok=True)
    (yucra_dir / "ejercicio1.c").write_text(
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
        """,
        encoding="utf-8",
    )

    perez_dir = ws / activity_slug / "perez-maria_223344" / "r1"
    perez_dir.mkdir(parents=True, exist_ok=True)
    (perez_dir / "ejercicio1.c").write_text(
        """
        #include <stdio.h>
        int main(void)
        {
            syntax_error_here;
            return 0;
        }
        """,
        encoding="utf-8",
    )

    from ripley.teacher.db import DatabaseManager, StudentRecord
    db1 = DatabaseManager(yucra_dir.parent / ".metadata.db")
    db1.upsert_student(StudentRecord("1848964", "Yucra Agustin Daniel", "yucra-agustin-daniel_1848964", "1848964"))
    db1.add_revision("yucra-agustin-daniel_1848964", 1, "hash1", str(yucra_dir), [{"filename": "ejercicio1.c", "file_hash": "h1", "size_bytes": 100}], [])

    db2 = DatabaseManager(perez_dir.parent / ".metadata.db")
    db2.upsert_student(StudentRecord("223344", "Perez Maria", "perez-maria_223344", "223344"))
    db2.add_revision("perez-maria_223344", 1, "hash2", str(perez_dir), [{"filename": "ejercicio1.c", "file_hash": "h2", "size_bytes": 100}], [])

    # 3. Crear Casos de Prueba
    create_testcase_skeleton(
        workspace_dir=ws,
        activity_slug=activity_slug,
        exercise="ejercicio1",
        cases_count=2,
    )
    # Configurar entradas y salidas esperadas
    t_dir = ws / "practicas" / activity_slug / "ejercicios" / "ejercicio1" / "tests"
    (t_dir / "caso1.in").write_text("10\n", encoding="utf-8")
    (t_dir / "caso1.out").write_text("Resultado: 20\n", encoding="utf-8")
    (t_dir / "caso2.in").write_text("25\n", encoding="utf-8")
    (t_dir / "caso2.out").write_text("Resultado: 50\n", encoding="utf-8")

    # 4. Evaluación inicial
    cfg = RipleyConfig()
    cfg.templates.ruta_plantillas = str(templates_dir)
    evaluator = Evaluator(config=cfg, workspace_dir=ws)

    eval_results = evaluator.evaluate_activity(activity_slug, parallel=False)
    assert len(eval_results) == 2

    yucra_res = next(r for r in eval_results if "yucra" in r.student_slug)
    assert yucra_res.compiled is True
    assert yucra_res.tests_passed == 2
    assert yucra_res.preliminary_grade > 8.0
    assert yucra_res.report_file.exists()

    perez_res = next(r for r in eval_results if "perez" in r.student_slug)
    assert perez_res.compiled is False
    assert perez_res.preliminary_grade == 0.0



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
