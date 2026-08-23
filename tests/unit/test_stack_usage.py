"""Unit tests for -fstack-usage peak stack auditing."""

import shutil

import pytest

from ripley.tools.stack_usage import StackUsageAuditor


def _gcc_available() -> bool:
    return shutil.which("gcc") is not None


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_stack_audit_detects_oversized_local_array(tmp_path):
    src = tmp_path / "grande.c"
    src.write_text(
        """
#include <stdio.h>

int chico(void) {
    int a = 1;
    return a + 1;
}

int grande(void) {
    int buffer[100000];
    buffer[0] = 7;
    return buffer[0];
}

int main(void) { return chico() + grande(); }
""",
        encoding="utf-8",
    )
    report = StackUsageAuditor(threshold_bytes=1024).audit([src])
    assert report.available
    funciones = {e.function: e for e in report.entries}
    assert "grande" in funciones
    assert "chico" in funciones
    assert funciones["grande"].size_bytes >= 400000
    assert any(e.function == "grande" for e in report.offenders)
    assert not any(e.function == "chico" for e in report.offenders)


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_stack_audit_flags_vla_dynamic(tmp_path):
    src = tmp_path / "vla.c"
    src.write_text(
        """
int suma(int n) {
    int v[n];
    for (int i = 0; i < n; i++) v[i] = i;
    return v[0];
}
int main(void) { return suma(4); }
""",
        encoding="utf-8",
    )
    report = StackUsageAuditor().audit([src])
    assert report.available
    assert len(report.dynamic_entries) >= 1
    assert all(e.qualifier == "dynamic" for e in report.dynamic_entries)


def test_stack_audit_missing_compiler_degrades():
    auditor = StackUsageAuditor(compiler_executable="no_existe_xyz")
    report = auditor.audit([])
    assert not report.available
    assert not report.compiler_available
