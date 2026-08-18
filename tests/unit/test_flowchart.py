"""Unit tests for traditional flowchart generator."""

from pathlib import Path
from ripley.flowchart import FlowNodeType, FlowchartBuilder, FlowchartGenerator
from ripley.semantic_diff import extract_c_functions


def test_flowchart_builder_traditional_notation_shapes():
    code = """
    #include <stdio.h>

    int main() {
        int a = 0;
        scanf("%d", &a);
        if (a > 10) {
            printf("Mayor: %d\\n", a);
        } else {
            printf("Menor o igual\\n");
        }
        return 0;
    }
    """
    funcs = extract_c_functions(code)
    assert "main" in funcs

    builder = FlowchartBuilder("main")
    mermaid = builder.build_from_function(funcs["main"])

    # 1. Terminales (Óvalos)
    assert "([" in mermaid and "])" in mermaid
    assert "Inicio: main()" in mermaid
    assert "Fin" in mermaid

    # 2. Entrada (Paralelogramo [/ ... /])
    assert "[/" in mermaid and "/]" in mermaid
    assert "Leer:" in mermaid

    # 3. Salida (Paralelogramo [\\ ... \\])
    assert "[\\" in mermaid and "\\]" in mermaid
    assert "Mostrar:" in mermaid

    # 4. Decisión (Rombo { ... }) y ramas Sí / No
    assert "{" in mermaid and "}" in mermaid
    assert "-->|Sí|" in mermaid
    assert "-->|No|" in mermaid

    # 5. Proceso (Rectángulo [ ... ])
    assert '["' in mermaid and '"]' in mermaid


def test_flowchart_while_and_for_loops():
    code = """
    void contar(int n) {
        int i = 0;
        while (i < n) {
            printf("%d\\n", i);
            i++;
        }
    }
    """
    funcs = extract_c_functions(code)
    builder = FlowchartBuilder("contar")
    mermaid = builder.build_from_function(funcs["contar"])

    assert '{"¿i < n?"}' in mermaid
    assert "-->|Sí|" in mermaid
    assert "-->|No|" in mermaid



def test_flowchart_generator_file_and_dot_format(tmp_path):
    c_file = tmp_path / "programa.c"
    c_file.write_text(
        """
        #include <stdio.h>
        int duplicar(int x) {
            return x * 2;
        }
        int main() {
            int n = 5;
            printf("%d\\n", duplicar(n));
            return 0;
        }
        """,
        encoding="utf-8",
    )

    generator = FlowchartGenerator()

    # Formato Mermaid para todo el archivo
    charts = generator.generate_for_file(c_file, output_format="mermaid")
    assert len(charts) == 2
    assert "duplicar" in charts
    assert "main" in charts

    # Formato DOT para una función específica
    dot_charts = generator.generate_for_file(c_file, target_function="duplicar", output_format="dot")
    assert len(dot_charts) == 1
    assert "digraph" in dot_charts["duplicar"]
    assert "shape=oval" in dot_charts["duplicar"]
