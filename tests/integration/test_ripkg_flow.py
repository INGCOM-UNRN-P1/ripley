"""End-to-end tests for .ripkg practice bundles: teacher pack -> student run."""

import shutil
import tomllib
from pathlib import Path

import pytest

from ripley.pipeline import bundle as bundle_mod
from ripley.pipeline.bundle import BundleError, load_bundle, write_bundle
from ripley.pipeline.student_runner import run_bundle
from ripley.teacher.pack import _enabled_check_ids, pack_practice


def _gcc() -> bool:
    return shutil.which("gcc") is not None


@pytest.fixture()
def practice_dir(tmp_path):
    pdir = tmp_path / "practicas" / "demo_ripkg"
    tc = pdir / "testcases"
    tc.mkdir(parents=True)
    (pdir / "ripley.toml").write_text(
        """
[compiler]
executable = "gcc"
flags = ["-std=c11", "-Wall", "-fsanitize=address,undefined"]

[limits]
timeout_segundos = 5

[ast_auditors]
enabled = true
backward_goto = true
deprecated_api = true

[padding]
enabled = true
""",
        encoding="utf-8",
    )
    (tc / "caso1.in").write_text("5\n", encoding="utf-8")
    (tc / "caso1.out").write_text("15\n", encoding="utf-8")
    return pdir


@pytest.fixture()
def good_source(tmp_path):
    src = tmp_path / "solucion.c"
    src.write_text(
        "#include <stdio.h>\nint main(void){ long n; if(scanf(\"%ld\",&n)!=1) return 1;"
        " printf(\"%ld\\n\", n*(n+1)/2); return 0; }\n",
        encoding="utf-8",
    )
    return src


@pytest.mark.skipif(not _gcc(), reason="gcc no disponible")
def test_pack_creates_bundle_with_manifest_and_testcases(practice_dir):
    result = pack_practice(practice_dir)
    assert result.output_path.exists()
    assert result.checks_enabled >= 3  # ast.* + padding
    assert result.payload_files == 2

    loaded = load_bundle(result.output_path)
    assert loaded.practica == "demo_ripkg"
    assert "ast.backward_goto" in loaded.manifest["checks"]
    assert loaded.manifest["compiler"]["flags"] == ["-std=c11", "-Wall", "-fsanitize=address,undefined"]
    assert "caso1.in" in bundle_mod.payload_of(loaded)


@pytest.mark.skipif(not _gcc(), reason="gcc no disponible")
def test_student_run_passes_on_correct_solution(practice_dir, good_source):
    packed = pack_practice(practice_dir)
    report = run_bundle(packed.output_path, [good_source])
    assert report.compiled_ok
    assert report.tests_total == 1
    assert report.tests_passed == 1
    assert report.success
    assert "ast.backward_goto" in report.executed_checks


@pytest.mark.skipif(not _gcc(), reason="gcc no disponible")
def test_student_run_flags_violation_and_failing_tests(tmp_path, practice_dir):
    packed = pack_practice(practice_dir)

    bad = tmp_path / "mala.c"
    bad.write_text(
        """
#include <stdio.h>
int main(void) {
    int i = 0;
    while (i < 10) {
        printf("no termina\\n");
    }
    char *lit = "hola";
    lit[0] = 'H';
    return 0;
}
""",
        encoding="utf-8",
    )
    report = run_bundle(packed.output_path, [bad])
    assert report.tests_passed < report.tests_total  # nunca imprime 15
    assert any(o["severidad"] == "ADVERTENCIA" for o in report.findings.get("ast.loop_termination", []))
    assert any("rodata" in o["mensaje"] for o in report.findings.get("ast.string_literal_write", []))
    assert not report.success


def test_bundle_tamper_detection(tmp_path):
    payload = {"datos.txt": b"contenido original"}
    manifest = bundle_mod.build_manifest("t", [], "gcc", [], payload)
    out = write_bundle(tmp_path / "t.ripkg", manifest, payload)
    zipfile_rewrite(out, replace={f"{bundle_mod.PAYLOAD_PREFIX}datos.txt": b"manipulado"})
    with pytest.raises(BundleError, match="Integridad"):
        load_bundle(out)


def zipfile_rewrite(path: Path, replace: dict) -> None:
    """Reescribe el zip sustituyendo entradas (simula manipulación del payload)."""
    import zipfile

    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.namelist():
            data = zin.read(item)
            zout.writestr(item, replace.get(item, data))
    tmp.replace(path)
