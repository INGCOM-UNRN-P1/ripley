"""`ripley check --md --sarif` para sulaco (Ola 25): una sola corrida, veredicto del perfil y
devolución con secciones colapsables y enlaces al apunte."""

import json

from typer.testing import CliRunner

from ripley.cli import app

CON_GOTO = "#include <stdio.h>\n\nint main(void)\n{\n    goto fin;\nfin:\n    return 0;\n}\n"


def _entrega(tmp_path, codigo):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.c").write_text(codigo, encoding="utf-8")


def test_md_falla_con_un_error_de_reglas_aunque_compile(tmp_path, monkeypatch):
    """Antes --md salía con 0 si compilaba: el modo bloqueante de sulaco no frenaba nada."""
    _entrega(tmp_path, CON_GOTO)
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(app, ["check", "src", "--md", "dev.md", "--sarif", "r.sarif", "--quiet"])
    assert res.exit_code == 1
    md = (tmp_path / "dev.md").read_text(encoding="utf-8")
    assert "status=fail" in md and "<details open>" in md and "🔎 Observaciones" in md
    assert "📚 Para estudiar" in md and "](https://" in md
    sarif = json.loads((tmp_path / "r.sarif").read_text(encoding="utf-8"))
    assert any(r["ruleId"] == "0x1006h" for r in sarif["runs"][0]["results"])


def test_relaxed_no_bloquea_por_reglas(tmp_path, monkeypatch):
    _entrega(tmp_path, CON_GOTO)
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(app, ["check", "src", "--md", "dev.md", "--profile", "relaxed", "--quiet"])
    assert res.exit_code == 0


def test_exit_zero_respeta_la_devolucion(tmp_path, monkeypatch):
    _entrega(tmp_path, CON_GOTO)
    monkeypatch.chdir(tmp_path)
    assert CliRunner().invoke(app, ["check", "src", "--md", "dev.md", "--exit-zero", "--quiet"]).exit_code == 0
