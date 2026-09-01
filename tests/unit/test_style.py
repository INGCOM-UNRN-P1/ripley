"""Unit tests for C code style and formatting analyzer."""

from ripley.config import StyleConfig
from ripley.core.style import StyleAnalyzer


def test_style_analyzer_allman_vs_kr():
    # En Allman, la llave en la misma línea que if es violación
    cfg_allman = StyleConfig(brace_style="allman", require_braces=True)
    analyzer_allman = StyleAnalyzer(cfg_allman)

    code_kr = """
    #include <stdio.h>

    int main() {
        if (1) {
            printf("ok\\n");
        }
        return 0;
    }
    """
    res_allman = analyzer_allman.analyze_code("kr.c", code_kr)
    assert not res_allman.passed
    assert any(o.regla == "brace_style" for o in res_allman.observaciones)

    # En K&R, la llave en la misma línea es válida
    cfg_kr = StyleConfig(brace_style="k&r", require_braces=True)
    analyzer_kr = StyleAnalyzer(cfg_kr)

    code_allman = """
    #include <stdio.h>

    int main()
    {
        if (1)
        {
            printf("ok\\n");
        }
        return 0;
    }
    """
    res_kr = analyzer_kr.analyze_code("allman.c", code_allman)
    assert any(o.regla == "brace_style" for o in res_kr.observaciones)


def test_style_analyzer_require_braces():
    cfg = StyleConfig(brace_style="allman", require_braces=True)
    analyzer = StyleAnalyzer(cfg)

    # if en una sola línea sin llaves
    code_no_braces = """
    int foo(int x)
    {
        if (x > 0) return 1;
        else return 0;
    }
    """
    res = analyzer.analyze_code("nobraces.c", code_no_braces)
    assert not res.passed
    braces_obs = [o for o in res.observaciones if o.regla == "require_braces"]
    assert len(braces_obs) >= 1


def test_style_analyzer_keyword_spacing_and_trailing_whitespace():
    cfg = StyleConfig(
        brace_style="allman",
        spacing_keywords=True,
        no_trailing_whitespace=True,
    )
    analyzer = StyleAnalyzer(cfg)

    code = "int main()\n{\n    if(x == 1)   \n    {\n        return 0;\n    }\n}\n"
    res = analyzer.analyze_code("spacing.c", code)
    rules = [o.regla for o in res.observaciones]

    assert "spacing_keywords" in rules
    assert "trailing_whitespace" in rules


def test_style_analyzer_indentation_spaces_vs_tabs():
    cfg = StyleConfig(indent_style="spaces", indent_size=4)
    analyzer = StyleAnalyzer(cfg)

    code_with_tab = "int main()\n{\n\treturn 0;\n}\n"
    res = analyzer.analyze_code("tab.c", code_with_tab)
    assert any(o.regla == "indent_style" for o in res.observaciones)


def test_style_analyzer_delegates_to_gaff(monkeypatch):
    import gaff.core.linter as gaff_linter

    called = False

    def fake_analizar_archivo(path, reglas_excluidas=None):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(gaff_linter, "analizar_archivo", fake_analizar_archivo)

    cfg = StyleConfig(brace_style="allman")
    analyzer = StyleAnalyzer(cfg)
    res = analyzer.analyze_code("dummy.c", "int main(void) { return 0; }\n")
    assert called is True
    assert res.passed is True

