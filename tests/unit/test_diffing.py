"""Unit tests for diffing module."""

from pathlib import Path
from ripley.core.diffing import clean_content_for_diff, generate_unified_diff


def test_clean_content_for_diff():
    code = """
    // Comentario
    int x = 10;

    /* Bloque */
    int y = 20;
    """
    cleaned = clean_content_for_diff(code, ignore_comments=True, ignore_blank_lines=True)
    joined = "".join(cleaned)
    assert "// Comentario" not in joined
    assert "/* Bloque */" not in joined
    assert "int x = 10;" in joined
    assert "int y = 20;" in joined


def test_generate_unified_diff_initial_version(tmp_path):
    r1 = tmp_path / "r1"
    r1.mkdir()
    (r1 / "main.c").write_text("int main() { return 0; }\n", encoding="utf-8")

    diff = generate_unified_diff(old_folder=None, new_folder=r1)
    assert diff == ""



def test_generate_unified_diff_two_revisions(tmp_path):
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    r1.mkdir()
    r2.mkdir()

    (r1 / "main.c").write_text("int main() {\n    return 0;\n}\n", encoding="utf-8")
    (r2 / "main.c").write_text("int main() {\n    return 42;\n}\n", encoding="utf-8")

    diff = generate_unified_diff(old_folder=r1, new_folder=r2)
    assert "--- a/main.c" in diff
    assert "+++ b/main.c" in diff
    assert "-    return 0;" in diff
    assert "+    return 42;" in diff
