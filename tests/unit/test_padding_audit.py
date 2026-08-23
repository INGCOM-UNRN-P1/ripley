"""Unit tests for struct padding zeroing auditor."""

from ripley.padding_audit import StructPaddingAuditor


def test_struct_with_padding_sent_without_memset():
    code = """
    struct registro {
        char inicial;
        int saldo;
    };
    int main() {
        struct registro r;
        FILE *f = fopen("datos.bin", "wb");
        fwrite(&r, sizeof(r), 1, f);
        fclose(f);
        return 0;
    }
    """
    obs = StructPaddingAuditor().analyze(code, "test.c")
    assert len(obs) == 1
    assert obs[0].linter_name == "struct_padding_leak"
    assert "padding" in obs[0].message
    assert "memset" in obs[0].suggestion


def test_struct_with_padding_and_memset_is_clean():
    code = """
    struct registro {
        char inicial;
        int saldo;
    };
    int main() {
        struct registro r;
        memset(&r, 0, sizeof(r));
        r.inicial = 'A';
        r.saldo = 10;
        FILE *f = fopen("datos.bin", "wb");
        fwrite(&r, sizeof(r), 1, f);
        fclose(f);
        return 0;
    }
    """
    obs = StructPaddingAuditor().analyze(code, "test.c")
    assert len(obs) == 0


def test_padded_struct_never_sent_is_clean():
    code = """
    struct registro {
        char inicial;
        int saldo;
    };
    int main() {
        struct registro r;
        r.saldo = 42;
        return r.saldo;
    }
    """
    obs = StructPaddingAuditor().analyze(code, "test.c")
    assert len(obs) == 0


def test_layout_computation_detects_holes():
    auditor = StructPaddingAuditor()
    layout = auditor.compute_struct_layout(
        "mixto",
        "\n char c;\n double d;\n char e;\n",
    )
    assert layout is not None
    # char(1) + hueco(7) + double(8) + char(1) + relleno final(7) = 24 bytes
    assert layout.total_size == 24
    assert layout.padding_bytes == 14
    assert layout.has_padding


def test_compact_layout_without_padding_ignored():
    code = """
    struct punto {
        int x;
        int y;
    };
    int main() {
        struct punto p;
        p.x = 1; p.y = 2;
        FILE *f = fopen("puntos.bin", "wb");
        fwrite(&p, sizeof(p), 1, f);
        fclose(f);
        return 0;
    }
    """
    obs = StructPaddingAuditor().analyze(code, "test.c")
    assert len(obs) == 0
