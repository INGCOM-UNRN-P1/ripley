"""Unit tests for the pedagogical GCC diagnostic translator."""

from ripley.core.gcc_translator import (
    summarize_for_humans,
    translate_diagnostic_line,
    translate_stderr,
)


def test_missing_semicolon():
    d = translate_diagnostic_line(
        "main.c:5:12: error: expected ';' before 'return'"
    )
    assert d is not None and d.translated
    assert "punto y coma" in d.title.lower()
    assert d.line == 5


def test_undeclared_variable_names_the_symbol():
    d = translate_diagnostic_line(
        "sol.c:8:5: error: 'contador' undeclared (first use in this function)"
    )
    assert "contador" in d.title
    assert "declar" in d.explanation
    assert "contador" in d.suggestion


def test_linker_undefined_reference_suggests_modular_build():
    d = translate_diagnostic_line(
        "/usr/bin/ld: /tmp/ccX.o: in function `main': undefined reference to `lista_vacia'"
    )
    # La línea de ld no matchea el formato file:line:col: error → None;
    # el patrón de referencia indefinida se prueba vía gcc wrapper:
    d2 = translate_diagnostic_line(
        "main.c:12:1: error: undefined reference to 'lista_vacia'"
    )
    assert d2 is not None
    assert "lista_vacia" in d2.title
    assert "modular" in d2.suggestion or "TODOS" in d2.suggestion
    assert d is None  # línea pura del enlazador no es diagnóstico file:line:col


def test_printf_format_mismatch():
    d = translate_diagnostic_line(
        'app.c:21:14: warning: format \'%s\' expects argument of type \'char *\', '
        "but argument 2 has type 'int' [-Wformat=]"
    )
    assert d is not None
    assert "%s" in (d.title + d.explanation)
    assert d.level == "warning"


def test_non_void_function_without_return():
    d = translate_diagnostic_line(
        "utils.c:30:1: warning: control reaches end of non-void function [-Wreturn-type]"
    )
    assert d is not None and "return" in d.suggestion.lower()


def test_unknown_error_falls_back_gracefully():
    d = translate_diagnostic_line("x.c:1:1: error: stray '@' in program")
    assert d is not None
    assert not d.translated  # sin regla específica
    assert d.title == "Error de compilación"
    assert "stray" in d.explanation


def test_translate_stderr_skips_context_lines():
    stderr = (
        "In file included from main.c:2:\n"
        "main.c:4:5: error: expected ';' before '}' token\n"
        "\n"
        "main.c:9:10: error: 'total' undeclared (first use in this function)\n"
    )
    diags = translate_stderr(stderr)
    assert len(diags) == 2
    assert all(d.file == "main.c" for d in diags)


def test_human_summary_block():
    stderr = "a.c:3:5: error: expected ';' before 'printf'\nb.c:7:2: error: 'y' undeclared (first use in this function)\n"
    block = summarize_for_humans(translate_stderr(stderr))
    assert block.count("→") == 2
    assert "Sugerencia:" in block


def test_summary_limits_items():
    stderr = "".join(f"f{i}.c:{i}:1: error: 'v{i}' undeclared (first use in this function)\n" for i in range(10))
    block = summarize_for_humans(translate_stderr(stderr), max_items=3)
    assert block.count("→") == 3
    assert "7 diagnósticos más" in block
