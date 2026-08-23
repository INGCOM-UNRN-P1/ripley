"""Unit tests for QEMU cross-architecture compilation matrix."""

import shutil

import pytest

from ripley.cross_arch import CrossArchitectureTester, TARGET_MATRIX


def test_target_matrix_contains_expected_architectures():
    archs = {t[0] for t in TARGET_MATRIX}
    assert {"x86_64", "aarch64", "riscv64", "mips"} <= archs


@pytest.mark.skipif(not shutil.which("gcc"), reason="gcc no disponible")
def test_native_target_always_compiles_and_matches(tmp_path):
    src = tmp_path / "eco.c"
    src.write_text(
        """
#include <stdio.h>
int main(void) {
    int v;
    if (scanf("%d", &v) != 1) return 1;
    printf("%d %d\\n", v * 2, v + 1);
    return 0;
}
""",
        encoding="utf-8",
    )
    tester = CrossArchitectureTester()
    report = tester.test(src, stdin_data="21\n")

    native = [t for t in report.targets if t.architecture == "x86_64"][0]
    assert native.compiled
    assert native.ran
    assert native.output_matched
    assert "42 22" in native.stdout


@pytest.mark.skipif(not shutil.which("gcc"), reason="gcc no disponible")
def test_unavailable_targets_reported_without_crash(tmp_path):
    src = tmp_path / "mini.c"
    src.write_text('#include <stdio.h>\nint main(void){ puts("hola"); return 0; }\n', encoding="utf-8")
    tester = CrossArchitectureTester()
    report = tester.test(src)

    assert len(report.targets) == len(TARGET_MATRIX)
    for target in report.targets:
        if target.compiler_used is None:
            # Sin toolchain cruzado instalado: mensaje explicativo, sin excepción.
            assert "no instalado" in target.message
