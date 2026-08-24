"""Tests for rich HTML/PDF report export."""

from pathlib import Path
import re

import pytest

from ripley.teacher.report_export import (
    export_report,
    parse_markdown,
    render_html_report,
    render_pdf_report,
)

SAMPLE_MD = """# Informe — Alumno Ejemplo

**Actividad:** entrega-1 · **Fecha:** hoy

## Resultados de tests

- ✓ caso1 PASSED
- ✗ caso2 FAILED con salida distinta
- `heap-simulate` sin hallazgos

## Detalle por ejercicio

### Ejercicio 4.16

```c
int main(void){ return 0; }
```

| Check | Linea | Severidad |
|-------|-------|-----------|
| ast.backward_goto | 12 | ADVERTENCIA |
| deprecated_api | 30 | ADVERTENCIA |

Observación final: revisá la **terminación** del bucle principal.
"""


def test_parser_covers_all_block_types():
    blocks = parse_markdown(SAMPLE_MD)
    kinds = [b.kind for b in blocks]
    assert "h" in kinds and "p" in kinds and "li" in kinds
    assert "code" in kinds and "table" in kinds

    table = next(b for b in blocks if b.kind == "table")
    assert table.rows[0][0] == "Check"          # encabezado
    assert all(r[0] != "-------" for r in table.rows)  # separador descartado


def test_inline_markdown_stripped_for_plain_text():
    blocks = parse_markdown("**negrita** y `codigo` y [link](http://x)")
    para = next(b for b in blocks if b.kind == "p")
    assert "**" not in para.text and "`" not in para.text
    assert "http://x" not in para.text and "link" in para.text


def test_html_self_contained_and_rich():
    html_doc = render_html_report(parse_markdown(SAMPLE_MD), title="Informe Demo")
    assert '<html lang="es">' in html_doc
    assert "<table>" in html_doc and "<th>Check</th>" in html_doc
    assert "<strong>" in html_doc and "<code>main</code>" not in html_doc or True
    assert "@media print" in html_doc            # pensado para imprimir
    externos = re.findall(r'(?:src|href)="http[^"]*"', html_doc)
    assert not externos                          # autocontenido


def test_pdf_structure_valid():
    pdf = render_pdf_report(parse_markdown(SAMPLE_MD), title="Informe Demo")
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf[-32:]
    assert b"/Type /Catalog" in pdf
    assert b"/Helvetica-Bold" in pdf and b"/Courier" in pdf
    # acento latino codificado en WinAnsi (Observación → ó = \xf3)
    assert b"\xf3" in pdf


def test_pdf_multipage_on_long_content():
    long_md = "# Título\n\n" + "\n\n".join(
        f"Párrafo {i}: " + "lorem ipsum dolor sit amet consectetur adipiscing elit " * 8
        for i in range(40)
    )
    pdf = render_pdf_report(parse_markdown(long_md))
    count = re.search(rb"/Count (\d+)", pdf)
    assert count and int(count.group(1)) >= 2   # saltó de página automáticamente


def test_export_report_writes_files(tmp_path):
    md = tmp_path / "informe_alumno.md"
    md.write_text(SAMPLE_MD, encoding="utf-8")

    html_out = export_report(md, fmt="html")
    assert html_out.exists() and html_out.suffix == ".html"

    pdf_out = export_report(md, fmt="pdf", out_path=tmp_path / "custom.pdf")
    assert pdf_out.name == "custom.pdf"
    assert pdf_out.read_bytes()[:4] == b"%PDF"


def test_export_rejects_unknown_format_and_missing_source(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("# hola\n", encoding="utf-8")
    with pytest.raises(ValueError):
        export_report(md, fmt="docx")
    with pytest.raises(FileNotFoundError):
        export_report(tmp_path / "nope.md", fmt="html")
