"""Unit tests for Ripley Core Engine."""

import json
from pathlib import Path
from typer.testing import CliRunner

from ripley.cli.student import app as student_app
from ripley.core.engine import analyze_target

runner = CliRunner()


def test_engine_analyze_clean_c_code(tmp_path: Path):
    src = tmp_path / "main.c"
    src.write_text(
        """#include <stdio.h>

int sumar(const int a, const int b) {
    return a + b;
}

int main(void) {
    int resultado = sumar(2, 3);
    printf("%d\\n", resultado);
    return 0;
}
""",
        encoding="utf-8",
    )
    result = analyze_target(src)
    assert result.compilation.get("success") is True
    assert result.metrics.get("c_files_count") == 1
    assert result.metrics.get("ast_errors_count") == 0


def test_engine_detects_global_variable(tmp_path: Path):
    src = tmp_path / "global.c"
    src.write_text(
        """#include <stdio.h>

int contador_global = 0;

int main(void) {
    contador_global++;
    return 0;
}
""",
        encoding="utf-8",
    )
    result = analyze_target(src)
    findings = result.ast_findings
    assert any("0x000Bh" in f.get("rule_id", "") or "global" in f.get("message", "").lower() for f in findings)


def test_cli_analyze_json_output(tmp_path: Path):
    src = tmp_path / "hello.c"
    src.write_text(
        """#include <stdio.h>
int main(void) {
    printf("Hola mundo\\n");
    return 0;
}
""",
        encoding="utf-8",
    )
    cli_res = runner.invoke(student_app, ["analyze", str(src)])
    assert cli_res.exit_code == 0
    parsed = json.loads(cli_res.output)
    assert parsed.get("version") == "2.0.0"
    assert parsed.get("compilation", {}).get("success") is True


def test_engine_integrates_satellite_plugins(tmp_path: Path):
    src = tmp_path / "sample.c"
    src.write_text(
        """#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *p = (int *)malloc(sizeof(int) * 10);
    char buf[10];
    gets(buf);
    return 0;
}
""",
        encoding="utf-8",
    )
    result = analyze_target(src)
    findings = result.ast_findings
    rule_codes = {f.get("rule_code") for f in findings}
    assert "0x300Ah" in rule_codes
    assert "KAN001" in rule_codes
    assert "0x300Dh" in rule_codes or "0x5006h" in rule_codes


def test_engine_delegates_to_daedalus_and_nostromo(tmp_path: Path):
    src = tmp_path / "echo.c"
    src.write_text(
        """#include <stdio.h>
int main(void) {
    char s[64];
    if (fgets(s, sizeof(s), stdin)) {
        fputs(s, stdout);
    }
    return 0;
}
""",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "caso_1.in").write_text("hola mundo\n", encoding="utf-8")
    (tests_dir / "caso_1.out").write_text("hola mundo\n", encoding="utf-8")

    result = analyze_target(tmp_path)
    assert result.compilation.get("success") is True
    assert result.tests.get("total") == 1
    assert result.tests.get("passed") == 1
    assert result.tests.get("failed") == 0
    assert result.passed is True


def test_engine_hierarchical_deduplication(tmp_path: Path):
    src = tmp_path / "dedup.c"
    src.write_text(
        """#include <stdlib.h>
int main(void) {
    int *p = (int *)malloc(sizeof(int) * 4);
    free(p);
    return 0;
}
""",
        encoding="utf-8",
    )
    result = analyze_target(src)
    # Verificar que para la línea de malloc no se repita el reporte con códigos equivalentes
    malloc_findings = [
        f for f in result.ast_findings
        if f.get("line") == 3 and f.get("rule_code") in ("0x300Ah", "cast_malloc", "spk_malloc_cast")
    ]
    assert len(malloc_findings) <= 1


def test_engine_strict_mode(tmp_path: Path, monkeypatch):
    src = tmp_path / "ok.c"
    src.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    # En modo normal, código limpio pasa
    res_normal = analyze_target(src, strict=False)
    assert res_normal.compilation.get("success") is True

    # Simular una herramienta ausente requerida bajo strict
    from ripley.core.entrypoints import SatellitePluginAdapter
    import ripley.core.engine as eng

    real_get_plugin = eng.get_satellite_plugin

    def fake_get_plugin(name):
        if name == "sandbox":
            return SatellitePluginAdapter(name="sandbox", is_available=False, execution_mode="unavailable")
        return real_get_plugin(name)

    monkeypatch.setattr(eng, "get_satellite_plugin", fake_get_plugin)

    # Crear carpeta tests para forzar la consulta al sandbox
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "caso_1.in").write_text("1\n")
    (tests_dir / "caso_1.out").write_text("1\n")

    res_strict = analyze_target(tmp_path, strict=True)
    assert res_strict.passed is False
    assert any(f.get("rule_code") == "MISSING_TOOL_NOSTROMO" for f in res_strict.ast_findings)
    assert res_strict.tests.get("omitted") == 1


def test_engine_missing_compiler(tmp_path: Path, monkeypatch):
    src = tmp_path / "test.c"
    src.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    from ripley.core.entrypoints import SatellitePluginAdapter
    import ripley.core.engine as eng

    fake_comp = SatellitePluginAdapter(
        name="compiler",
        tool_name="daedalus",
        is_available=False,
        execution_mode="unavailable",
    )
    monkeypatch.setattr(eng, "get_satellite_plugin", lambda name: fake_comp if name == "compiler" else eng.get_satellite_plugin(name))

    res = analyze_target(src, strict=False)
    assert res.compilation.get("success") is False
    assert res.passed is False
    assert any("MISSING_TOOL_DAEDALUS" in f.get("rule_code", "") for f in res.ast_findings)


