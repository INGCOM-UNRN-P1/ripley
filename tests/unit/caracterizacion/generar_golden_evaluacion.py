"""Genera golden_evaluacion.json: el informe y el resumen de `Evaluator.evaluate_student` para un
estudiante con dos revisiones (una que no compila y una correcta con observaciones de estilo). Se
generó ANTES de partir la función: si test_caracterizacion_evaluacion.py falla, cambió algo."""

import json
import re
import tempfile
from pathlib import Path

AQUI = Path(__file__).parent
R1 = "#include <stdio.h>\nint main(void)\n{\n    int n = 0\n    return n;\n}\n"
R2 = ("#include <stdio.h>\n\nint main(void)\n{\n    int n = 0;\n    if (scanf(\"%d\", &n) == 1)\n    {\n"
      "        printf(\"%d\\n\", n * 2);\n    }\n    return 0;\n}\n")


def evaluar() -> dict:
    from ripley.config import RipleyConfig
    from ripley.teacher.db import DatabaseManager, StudentRecord
    from ripley.teacher.evaluate import Evaluator

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        act, alumno = "entrega-1_1228009", "perez-juan_12345"
        sdir = ws / act / alumno
        db = None
        for v, codigo in ((1, R1), (2, R2)):
            rdir = sdir / f"r{v}"
            rdir.mkdir(parents=True)
            (rdir / "ejercicio1.c").write_text(codigo, encoding="utf-8")
            if db is None:
                db = DatabaseManager(sdir / ".metadata.db")
                db.upsert_student(StudentRecord(student_id="12345", full_name="Perez Juan", slug=alumno, submission_id="12345"))
            db.add_revision(student_slug=alumno, version_num=v, sources_hash=f"sha{v}", folder_path=str(rdir),
                            sources=[{"filename": "ejercicio1.c", "file_hash": f"sha{v}", "size_bytes": 100}], ignored=[])
        casos = ws / "practicas" / act / "ejercicios" / "ejercicio1" / "tests"
        casos.mkdir(parents=True)
        (casos / "caso1.in").write_text("5\n", encoding="utf-8")
        (casos / "caso1.out").write_text("10\n", encoding="utf-8")
        (res,) = Evaluator(config=RipleyConfig(), workspace_dir=ws).evaluate_activity(activity_slug=act, parallel=False)
        informe = res.report_file.read_text(encoding="utf-8")
        informe = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?", "<fecha>", informe)
        informe = informe.replace(tmp, "<tmp>")
        informe = re.sub(r"\d+(\.\d+)? ?ms\b", "<ms>", informe)
        informe = re.sub(r"==\d+==", "==<pid>==", informe)
        informe = re.sub(r"/tmp/[\w.-]+", "<tmp>", informe)
        return {"informe": informe.splitlines(), "compilo": res.compiled, "nota": res.preliminary_grade,
                "pruebas": [res.tests_passed, res.total_tests], "estilo": res.style_score, "version": res.version_evaluated}


if __name__ == "__main__":
    # El mismo entorno que pytest (tests/conftest.py): los src/ de las herramientas hermanas primero.
    import sys
    for src in sorted(AQUI.parents[3].glob("*/src")):
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
    (AQUI / "golden_evaluacion.json").write_text(json.dumps(evaluar(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
