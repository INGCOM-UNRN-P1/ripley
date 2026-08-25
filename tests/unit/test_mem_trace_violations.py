"""Pruebas del trazador de memoria: use-after-free, double-free y aliases."""

from ripley.core.mem_trace import MemoryTracer


def _violaciones(codigo: str):
    tracer = MemoryTracer()
    tracer.extract_events(codigo)
    return [(v.line, v.op, v.detail) for v in tracer.violations]


def test_double_free_detectado():
    v = _violaciones(
        "int main(void){\n"
        "    int *p = malloc(4);\n"
        "    free(p);\n"
        "    free(p);\n"
        "}\n"
    )
    assert any(op == "double-free" and "ya liberado" in det for _, op, det in v)


def test_use_after_free_directo():
    v = _violaciones(
        "#include <stdlib.h>\n"
        "int main(void){\n"
        "    int *a = malloc(4);\n"
        "    free(a);\n"
        "    *a = 5;\n"
        "}\n"
    )
    assert any(op == "use-after-free" for _, op, _ in v)


def test_use_after_free_por_alias():
    v = _violaciones(
        "int main(void){\n"
        "    int *p = malloc(16);\n"
        "    int *q = p;\n"
        "    free(p);\n"
        '    printf("%d", q[0]);\n'
        "}\n"
    )
    assert any(op == "use-after-free" and "'q'" in det for _, op, det in v)


def test_copiar_puntero_colgante():
    v = _violaciones(
        "int main(void){\n"
        "    int *a = malloc(8);\n"
        "    int *b;\n"
        "    free(a);\n"
        "    b = a;\n"
        "}\n"
    )
    assert any("b ← valor de 'a'" in det for _, _, det in v)


def test_asignar_null_revive_sin_falsos_positivos():
    assert _violaciones(
        "#include <stdlib.h>\n"
        "int main(void){\n"
        "    int *p = malloc(sizeof(int));\n"
        "    if (p == NULL) return 1;\n"
        "    *p = 42;\n"
        "    free(p);\n"
        "    p = NULL;\n"
        "    return 0;\n"
        "}\n"
    ) == []


def test_realloc_encadenado_no_es_uaf():
    assert _violaciones(
        "#include <stdlib.h>\n"
        "int main(void){\n"
        "    int *p = malloc(4);\n"
        "    p = realloc(p, 8);\n"
        "    free(p);\n"
        "    return 0;\n"
        "}\n"
    ) == []


def test_revivir_con_malloc_nuevo_limpia_el_estado():
    v = _violaciones(
        "int main(void){\n"
        "    int *p = malloc(4);\n"
        "    free(p);\n"
        "    p = malloc(4);\n"
        "    free(p);\n"
        "}\n"
    )
    assert not [x for x in v if x[1] == "use-after-free"]
