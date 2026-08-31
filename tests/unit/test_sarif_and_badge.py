import pytest
from ripley.core.sarif import exportar_sarif
from ripley.core.badge import calcular_puntaje_calidad, generar_badge_svg


class DummyResult:
    def __init__(self, success=True, findings=None, total_tests=5, passed_tests=5):
        self.compilation = {"success": success}
        self.ast_findings = findings or []
        self.tests = {"total": total_tests, "passed": passed_tests}


def test_exportar_sarif():
    dummy = DummyResult(
        findings=[
            {
                "rule_id": "0x1001h",
                "title": "Cast redundante en malloc",
                "severity": "WARN",
                "message": "Evitá castear malloc en C",
                "suggestion": "Escribí p = malloc(...)",
                "file": "main.c",
                "line": 10,
                "column": 5,
            }
        ]
    )
    sarif = exportar_sarif(dummy)
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "Ripley"
    assert len(sarif["runs"][0]["results"]) == 1
    assert sarif["runs"][0]["results"][0]["ruleId"] == "0x1001h"


def test_calcular_puntaje_y_badge():
    perfect = DummyResult()
    score_perfect = calcular_puntaje_calidad(perfect)
    assert score_perfect == 10.0
    svg = generar_badge_svg(score_perfect)
    assert "10.0/10 PASS" in svg
    assert "<svg" in svg

    failed_comp = DummyResult(success=False)
    score_failed = calcular_puntaje_calidad(failed_comp)
    assert score_failed == 0.0
    svg_failed = generar_badge_svg(score_failed)
    assert "0.0/10 REVISAR" in svg_failed


def test_lsp_server_messages(tmp_path):
    from ripley.core.lsp_server import procesar_lsp_mensaje

    init_msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    res_init = procesar_lsp_mensaje(init_msg)
    assert res_init["result"]["serverInfo"]["name"] == "ripley-lsp"

    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { return 0; }\n", encoding="utf-8")

    open_msg = {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {"textDocument": {"uri": f"file://{c_file.resolve()}"}},
    }
    res_open = procesar_lsp_mensaje(open_msg)
    assert res_open["method"] == "textDocument/publishDiagnostics"


def test_history_and_progress(tmp_path):
    from ripley.core.history import registrar_progreso, mostrar_historial_progreso
    from rich.console import Console

    registrar_progreso(tmp_path, hallazgos_count=3, calificacion=8.5, fuentes=["main.c"])
    registrar_progreso(tmp_path, hallazgos_count=1, calificacion=9.5, fuentes=["main.c"])

    cons = Console(record=True)
    regs = mostrar_historial_progreso(tmp_path, console=cons)
    assert len(regs) == 2
    out = cons.export_text()
    assert "Mejoró" in out


def test_autofix_corrections(tmp_path):
    from ripley.core.autofix import proponer_correcciones, aplicar_autofix_interactivo

    c_file = tmp_path / "bad.c"
    c_file.write_text('int *p = (int*)malloc(sizeof(int));\nfflush(stdin);\n', encoding="utf-8")

    propuestas = proponer_correcciones(c_file)
    assert len(propuestas) >= 2

    aplicados = aplicar_autofix_interactivo(c_file, auto_apply=True)
    assert aplicados >= 2
    nuevo_txt = c_file.read_text(encoding="utf-8")
    assert "(int*)malloc" not in nuevo_txt
    assert "fflush(stdin);" not in nuevo_txt


def test_inline_annotator(tmp_path):
    from ripley.core.inline_annotator import renderizar_anotacion_inline
    from rich.console import Console

    c_file = tmp_path / "annot.c"
    c_file.write_text("int x = 1;\nint *p = (int*)malloc(10);\n", encoding="utf-8")

    cons = Console(record=True)
    res = renderizar_anotacion_inline(c_file, linea_num=2, columna=10, codigo_error="0x300Ah", mensaje="Cast redundante", console=cons)
    assert "0x300Ah" in res
    assert "^~~~" in res


def test_style_compliance(tmp_path):
    from ripley.core.style_compliance import auditar_conformidad_estilo
    from rich.console import Console

    c_file = tmp_path / "clean.c"
    c_file.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    cons = Console(record=True)
    res = auditar_conformidad_estilo([c_file], console=cons)
    assert "indice_conformidad" in res
    assert res["indice_conformidad"] >= 0.0

