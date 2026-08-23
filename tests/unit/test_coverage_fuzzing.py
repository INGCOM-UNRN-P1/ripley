"""Unit tests for coverage-guided fuzzing (gcov feedback)."""

import shutil

import pytest

from ripley.tools.coverage_fuzzing import CoverageGuidedFuzzer


def _gcc_and_gcov_available() -> bool:
    return shutil.which("gcc") is not None and shutil.which("gcov") is not None


@pytest.fixture()
def branchy_source(tmp_path):
    src = tmp_path / "branchy.c"
    src.write_text(
        """
#include <stdio.h>
int clasificar(int x) {
    if (x > 100) {
        return 1;
    } else if (x < -100) {
        return -1;
    }
    return 0;
}
int main(void) {
    int v;
    if (scanf("%d", &v) != 1) return 1;
    printf("%d\\n", clasificar(v));
    return 0;
}
""",
        encoding="utf-8",
    )
    return src


@pytest.mark.skipif(not _gcc_and_gcov_available(), reason="gcc/gcov no disponible")
def test_coverage_fuzz_discovers_new_lines(branchy_source):
    fuzzer = CoverageGuidedFuzzer(seed=7)
    report = fuzzer.fuzz(branchy_source, seed_inputs=["0\n"], max_iterations=40, stall_limit=25)
    assert report.available
    assert report.iterations >= 1
    # Con mutaciones de enteros interesantes debe alcanzar las ramas x>100 y x<-100.
    assert report.final_coverage_lines >= 4
    assert not report.crashes or all(c.returncode != 0 for c in report.crashes)


@pytest.mark.skipif(not _gcc_and_gcov_available(), reason="gcc/gcov no disponible")
def test_coverage_fuzz_detects_crash(branchy_source):
    # Fuente que aborta con el valor centinela 999.
    crashy = branchy_source.with_name("crashy.c")
    code = branchy_source.read_text(encoding="utf-8").replace(
        'if (scanf("%d", &v) != 1) return 1;',
        'if (scanf("%d", &v) != 1) return 1;\n    if (v == 999) { int *p = 0; *p = 1; }',
    )
    crashy.write_text(code, encoding="utf-8")

    fuzzer = CoverageGuidedFuzzer(seed=3)
    report = fuzzer.fuzz(crashy, seed_inputs=["500\n"], max_iterations=120, stall_limit=60)
    assert report.available
    assert len(report.crashes) >= 1


def test_coverage_fuzz_unavailable_on_syntax_error(tmp_path):
    bad = tmp_path / "bad.c"
    bad.write_text("int main( { esto no es C", encoding="utf-8")
    fuzzer = CoverageGuidedFuzzer()
    report = fuzzer.fuzz(bad, max_iterations=5)
    assert not report.available
    assert "compilar" in report.message
