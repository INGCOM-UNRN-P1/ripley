"""Tests for the accessible visual glossary."""

import pytest

from ripley.core.glossary import (
    ENTRIES,
    get_entry,
    get_theme,
    list_concepts,
    render_entry_svg,
    render_glossary_html,
)


def test_catalog_integrity():
    ids = [e.concept_id for e in ENTRIES]
    assert len(ids) == len(set(ids)), "ids duplicados"
    by_id = set(ids)
    for e in ENTRIES:
        assert e.summary and e.long_description, f"{e.concept_id} sin textos"
        assert callable(e.draw)
        for rid in e.related:
            assert rid in by_id or rid == "recursion", f"relacionado inexistente: {rid}"


def _ids():
    return [e.concept_id for e in list_concepts()]


@pytest.mark.parametrize("cid", _ids())
def test_every_diagram_is_accessible_svg(cid):
    entry = get_entry(cid)
    svg = entry.draw(get_theme("dark"))
    uid = entry.concept_id
    assert svg.startswith("<svg")
    assert 'role="img"' in svg
    assert f'id="t-{uid}"' in svg and f'id="d-{uid}"' in svg
    assert "<desc" in svg and "<title" in svg


def test_themes_and_large_text_scale():
    normal = get_theme("light")
    grande = get_theme("light", large_text=True)
    assert grande.font_scale > normal.font_scale
    hc = get_theme("high-contrast")
    assert hc.bg == "#000000" and hc.text == "#ffffff"
    with pytest.raises(KeyError):
        get_theme("neon")


def test_high_contrast_theme_changes_render():
    dark = render_entry_svg(get_entry("puntero"), get_theme("dark"))
    hc = render_entry_svg(get_entry("puntero"), get_theme("high-contrast"))
    assert "#000000" in hc and "#000000" not in dark


def test_html_self_contained_and_semantic():
    html_doc = render_glossary_html(["puntero", "heap", "dangling-pointer"], get_theme("high-contrast"))
    assert '<html lang="es">' in html_doc
    assert html_doc.count("<section") == 3
    assert "Descripción accesible:" in html_doc
    assert "aria-labelledby" in html_doc and 'role="img"' in html_doc
    import re

    externos = re.findall(r'(?:src|href)="http[^"]*"', html_doc)
    assert not externos, f"recursos externos: {externos}"
    assert "prefers-reduced-motion" in html_doc


def test_related_links_resolve_to_anchors():
    html_doc = render_glossary_html(["puntero"], get_theme("light"))
    assert 'href="#c-dangling-pointer"' in html_doc
    assert 'id="c-puntero"' in html_doc


def test_get_entry_rejects_unknown():
    with pytest.raises(KeyError):
        get_entry("quantum-entanglement")
