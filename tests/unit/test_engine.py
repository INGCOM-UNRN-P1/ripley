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

