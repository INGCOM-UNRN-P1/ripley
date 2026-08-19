"""Unit tests for Moodle ZIP ingestion, sanitization, encoding and versioning."""

import io
from pathlib import Path
import zipfile

from ripley.ingest import (
    MoodleIngestor,
    normalize_encoding,
    parse_moodle_zip_filename,
    parse_student_folder_name,
)


def test_parse_moodle_zip_filename():
    # Caso típico Moodle
    zip_name1 = "- (B6003) - 40- Programación I COM 1 - 2026-Entrega #1-1228009.zip"
    parsed1 = parse_moodle_zip_filename(zip_name1)
    assert parsed1.activity_name == "Entrega #1"
    assert parsed1.activity_id == "1228009"
    assert parsed1.activity_slug == "entrega-1_1228009"

    # Caso simple
    zip_name2 = "TP1-987654.zip"
    parsed2 = parse_moodle_zip_filename(zip_name2)
    assert parsed2.activity_name == "TP1"
    assert parsed2.activity_id == "987654"
    assert parsed2.activity_slug == "tp1_987654"


def test_parse_student_folder_name():
    raw_folder = "Yucra Agustin Daniel_1848964_assignsubmission_file"
    parsed = parse_student_folder_name(raw_folder)
    assert parsed.student_name == "Yucra Agustin Daniel"
    assert parsed.submission_id == "1848964"
    assert parsed.student_slug == "yucra-agustin-daniel_1848964"


def test_normalize_encoding():
    # UTF-8
    utf8_data = "int año = 2026; /* programación */".encode("utf-8")
    text_utf8, enc = normalize_encoding(utf8_data)
    assert "año" in text_utf8
    assert "programación" in text_utf8

    # ISO-8859-1 / Latin-1
    latin1_data = "int año = 2026; /* programación */".encode("iso-8859-1")
    text_latin1, enc = normalize_encoding(latin1_data)
    assert "año" in text_latin1
    assert "programación" in text_latin1

    # Windows-1252 con caracteres específicos (ej. comillas curvas o símbolo euro)
    cp1252_data = "int main() { char *s = \"‘test’\"; }".encode("windows-1252")
    text_cp1252, _ = normalize_encoding(cp1252_data)
    assert "‘test’" in text_cp1252


def create_synthetic_moodle_zip(
    zip_path: Path, student_folder: str, files: dict[str, bytes]
) -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fpath, content in files.items():
            full_path = f"{student_folder}/{fpath}"
            zf.writestr(full_path, content)


def test_ingest_process_zip_flattening_and_filtering(tmp_path):
    ws = tmp_path / "workspace"
    zip_file = tmp_path / "Entrega #1-1228009.zip"

    student_folder = "Perez Juan_998877_assignsubmission_file"
    files = {
        "ejercicio1.c": b'#include <stdio.h>\nint main() { return 0; }\n',
        "nested/subfolder/ejercicio2.c": b'#include <stdio.h>\nvoid foo() {}\n',
        "nested/subfolder/helper.h": b'#ifndef H\n#define H\n#endif\n',
        "informe.pdf": b'%PDF-1.4 dummy pdf content',
        "nested/binary.exe": b'MZ binary header',
    }
    create_synthetic_moodle_zip(zip_file, student_folder, files)

    ingestor = MoodleIngestor(workspace_dir=ws)
    moodle_info, results = ingestor.process_zip(zip_file, dry_run=False)

    assert moodle_info.activity_slug == "entrega-1_1228009"
    assert len(results) == 1
    res = results[0]
    assert res.student_slug == "perez-juan_998877"
    assert res.version_created == 1
    assert res.is_new_revision is True
    assert len(res.sources) == 3  # ejercicio1.c, ejercicio2.c, helper.h (flattened)
    assert len(res.ignored) == 2  # informe.pdf, binary.exe

    student_dir = ws / "entrega-1_1228009" / "perez-juan_998877"
    r1_dir = student_dir / "r1"
    assert (r1_dir / "ejercicio1.c").exists()
    assert (r1_dir / "ejercicio2.c").exists()  # Extracted from nested folder
    assert (r1_dir / "helper.h").exists()
    assert not (r1_dir / "informe.pdf").exists()


def test_ingest_deterministic_hash_and_resubmissions(tmp_path):
    ws = tmp_path / "workspace"
    zip_file = tmp_path / "Entrega #1-1228009.zip"
    student_folder = "Gomez Maria_554433_assignsubmission_file"

    files_v1 = {
        "tp.c": b'int main() { return 1; }\n',
    }
    create_synthetic_moodle_zip(zip_file, student_folder, files_v1)

    ingestor = MoodleIngestor(workspace_dir=ws)
    _, results1 = ingestor.process_zip(zip_file)
    assert results1[0].version_created == 1
    assert results1[0].is_new_revision is True

    # Re-ingest mismo ZIP sin cambios -> no debe crear r2
    _, results_same = ingestor.process_zip(zip_file)
    assert results_same[0].is_new_revision is False
    assert results_same[0].version_created is None

    # Reentrega con código modificado -> debe crear r2
    files_v2 = {
        "tp.c": b'int main() { return 0; /* modificado */ }\n',
    }
    create_synthetic_moodle_zip(zip_file, student_folder, files_v2)
    _, results_v2 = ingestor.process_zip(zip_file)
    assert results_v2[0].version_created == 2
    assert results_v2[0].is_new_revision is True

    student_dir = ws / "entrega-1_1228009" / "gomez-maria_554433"
    assert (student_dir / "r1" / "tp.c").exists()
    assert (student_dir / "r2" / "tp.c").exists()


def test_ingest_dry_run(tmp_path):
    ws = tmp_path / "workspace"
    zip_file = tmp_path / "Entrega #1-1228009.zip"
    student_folder = "DryRun User_111111_assignsubmission_file"
    files = {"main.c": b'int main() { return 0; }\n'}
    create_synthetic_moodle_zip(zip_file, student_folder, files)

    ingestor = MoodleIngestor(workspace_dir=ws)
    _, results = ingestor.process_zip(zip_file, dry_run=True)
    assert len(results) == 1
    assert not ws.exists()  # Dry run no crea directorios en disco


def test_cmd_ingest_creates_blank_practice_if_missing(tmp_path):
    from typer.testing import CliRunner
    from ripley.cli import app

    runner = CliRunner()
    ws = tmp_path / "workspace"
    ws.mkdir()
    zip_file = tmp_path / "(B6003)-40-Programación I COM 1-2026-Entrega #2-999999.zip"
    student_folder = "Alumno Test_123456_assignsubmission_file"
    files = {"ej1.c": b'int main() { return 0; }\n'}
    create_synthetic_moodle_zip(zip_file, student_folder, files)

    # Ingest con flag -y (auto-confirmar creacion de practica)
    res = runner.invoke(app, ["ingest", str(zip_file), "-w", str(ws), "-y"])
    assert res.exit_code == 0
    assert "Actividad procesada" in res.output

    # Verificar que se creo la practica en blanco dentro de practicas/ y NO en tests/
    practice_dir = ws / "practicas" / "entrega-2_999999"
    assert practice_dir.exists()
    assert (practice_dir / "enunciado.md").exists()
    assert (practice_dir / "pautas_evaluacion.md").exists()
    assert (practice_dir / "ripley.toml").exists()
    assert not (ws / "tests" / "entrega-2_999999").exists()


