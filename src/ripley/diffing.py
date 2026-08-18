"""Unified diffing module for incremental student revisions."""

import difflib
from pathlib import Path
import re
from typing import List, Optional, Set

from ripley.security import strip_c_comments_and_strings


def clean_content_for_diff(
    content: str,
    ignore_comments: bool = False,
    ignore_blank_lines: bool = False,
) -> List[str]:
    """Limpia comentarios y/o líneas en blanco para comparación."""
    text = content
    if ignore_comments:
        text = strip_c_comments_and_strings(text)

    lines = text.splitlines(keepends=True)
    cleaned: List[str] = []

    for line in lines:
        if ignore_blank_lines and not line.strip():
            continue
        cleaned.append(line)

    return cleaned


def generate_unified_diff(
    old_folder: Optional[Path | str],
    new_folder: Path | str,
    ignore_comments: bool = False,
    ignore_blank_lines: bool = False,
) -> str:
    """Genera un diff unificado entre dos carpetas de revisión."""
    new_path = Path(new_folder)
    if not new_path.exists():
        return ""

    if old_folder is None or not Path(old_folder).exists():
        # Si es la primera versión, generamos un diff de creación de archivos
        diff_chunks: List[str] = []
        for file in sorted(new_path.glob("*.[ch]")):
            content = file.read_text(encoding="utf-8", errors="replace")
            lines = clean_content_for_diff(content, ignore_comments, ignore_blank_lines)
            diff = difflib.unified_diff(
                [],
                lines,
                fromfile="/dev/null",
                tofile=f"b/{file.name}",
            )
            diff_chunks.extend(diff)
        return "".join(diff_chunks)

    old_path = Path(old_folder)
    diff_chunks: List[str] = []

    old_files = {f.name: f for f in old_path.glob("*.[ch]")}
    new_files = {f.name: f for f in new_path.glob("*.[ch]")}
    all_filenames = sorted(set(old_files.keys()) | set(new_files.keys()))

    for fname in all_filenames:
        old_f = old_files.get(fname)
        new_f = new_files.get(fname)

        if old_f and new_f:
            old_lines = clean_content_for_diff(
                old_f.read_text(encoding="utf-8", errors="replace"),
                ignore_comments,
                ignore_blank_lines,
            )
            new_lines = clean_content_for_diff(
                new_f.read_text(encoding="utf-8", errors="replace"),
                ignore_comments,
                ignore_blank_lines,
            )
            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{fname}",
                tofile=f"b/{fname}",
            )
            diff_chunks.extend(diff)
        elif not old_f and new_f:
            new_lines = clean_content_for_diff(
                new_f.read_text(encoding="utf-8", errors="replace"),
                ignore_comments,
                ignore_blank_lines,
            )
            diff = difflib.unified_diff(
                [],
                new_lines,
                fromfile="/dev/null",
                tofile=f"b/{fname}",
            )
            diff_chunks.extend(diff)
        elif old_f and not new_f:
            old_lines = clean_content_for_diff(
                old_f.read_text(encoding="utf-8", errors="replace"),
                ignore_comments,
                ignore_blank_lines,
            )
            diff = difflib.unified_diff(
                old_lines,
                [],
                fromfile=f"a/{fname}",
                tofile="/dev/null",
            )
            diff_chunks.extend(diff)

    return "".join(diff_chunks)
