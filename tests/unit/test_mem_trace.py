"""Unit tests for the mem-trace (spectre) memory tracer."""

from typer.testing import CliRunner

from ripley.core.mem_trace import MemoryTracer, save_trace
from ripley.cli.student import app

runner = CliRunner()

_SAMPLE_C = """\
#include <stdlib.h>

typedef struct nodo {
    int valor;
    struct nodo *sig;
} nodo_t;
// free(p) dentro de un comentario no cuenta

int main(void) {
    int n = 4;
    nodo_t *lista = malloc(32);
    int *datos = calloc(n, 8);
    nodo_t *copia = lista;
    free(datos);
    free(datos);   /* double free */
    return 0;
}
"""


def _events_of(code: str) -> list:
    events, _records = MemoryTracer().extract_events(code)
    return events


def test_extraccion_eventos_basicos():
    code = (
        "int main(void) {\n"
        "    nodo_t *lista = malloc(32);\n"
        "    int *datos = calloc(4, 8);\n"
        "    nodo_t *copia = lista;\n"
        "    free(datos);\n"
        "}\n"
    )
    events = _events_of(code)
    assert [(e["op"], e.get("tag") or e.get("var")) for e in events] == [
        ("malloc", "lista"),
        ("malloc", "datos"),
        ("ptr", "copia"),
        ("free", "datos"),
    ]
    assert events[0]["size"] == 32
    assert events[1]["size"] == 32  # calloc(4, 8) = producto numérico
    assert events[0]["line"] == 2


def test_free_null_y_comentarios_ignorados():
    code = (
        "// free(p) comentado\n"
        "int main(void) {\n"
        "    free(NULL);\n"
        "    /* free(q); */\n"
        "}\n"
    )
    assert _events_of(code) == []


def test_realloc_se_modela_como_malloc():
    code = (
        "int main(void) {\n"
        "    char *buf = malloc(16);\n"
        "    buf = realloc(buf, 64);\n"
        "}\n"
    )
    events = _events_of(code)
    assert events[-1]["op"] == "malloc"
    assert events[-1]["size"] == 64


def test_tamano_no_literal_usa_estimacion():
    code = "int main(void) {\n    int *v = malloc(n * sizeof(int));\n}\n"
    events = _events_of(code)
    assert len(events) == 1
    assert events[0]["size"] > 0


def test_html_generado_contiene_secciones(tmp_path):
    src = tmp_path / "lista.c"
    src.write_text(_SAMPLE_C, encoding="utf-8")
    out = tmp_path / "traza.html"

    result = save_trace(src, out)

    assert out.exists()
    html_out = out.read_text(encoding="utf-8")
    for marker in ("<svg", "STACK", "HEAP", "Resumen del Heap simulado", "Topología de estructuras"):
        assert marker in html_out, marker
    assert "nodo" in html_out  # struct detectada por DynamicMemoryVisualizer
    assert result.event_count >= 3


def test_doble_free_genera_advertencia_y_frames_parciales(tmp_path):
    src = tmp_path / "doble.c"
    src.write_text(
        "int main(void) {\n    int *p = malloc(8);\n    free(p);\n    free(p);\n}\n",
        encoding="utf-8",
    )

    result = save_trace(src, tmp_path / "traza.html")

    assert any("interrumpido" in w or "double free" in w.lower() for w in result.warnings)
    assert len(result.frames) < result.event_count


def test_capacidad_insuficiente_genera_advertencia(tmp_path):
    src = tmp_path / "grande.c"
    src.write_text("int main(void) {\n    int *p = malloc(128);\n    return 0;\n}\n", encoding="utf-8")

    result = save_trace(src, tmp_path / "traza.html", capacity=64)

    assert any("capacidad" in w for w in result.warnings)


def test_sin_operaciones_de_memoria(tmp_path):
    src = tmp_path / "simple.c"
    src.write_text("int main(void) {\n    int x = 42;\n    return x;\n}\n", encoding="utf-8")
    out = tmp_path / "traza.html"

    result = save_trace(src, out)

    assert result.event_count == 0
    assert "No se detectaron operaciones" in out.read_text(encoding="utf-8")


def test_cli_trace_genera_archivo(tmp_path):
    src = tmp_path / "lista.c"
    src.write_text(_SAMPLE_C, encoding="utf-8")
    out = tmp_path / "traza.html"

    exit_code = runner.invoke(app, ["trace", str(src), "-o", str(out)]).exit_code

    assert exit_code == 0
    assert out.exists()


def test_cli_trace_archivo_inexistente(tmp_path):
    exit_code = runner.invoke(app, ["trace", str(tmp_path / "fantasma.c")]).exit_code
    assert exit_code != 0
