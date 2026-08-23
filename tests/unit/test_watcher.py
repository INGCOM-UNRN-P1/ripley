"""Unit tests for the poll-based watch session (no external deps)."""

import time
from pathlib import Path

from ripley.tools.watcher import (
    ChangeSet,
    WatchSession,
    collect_source_files,
    snapshot_mtimes,
)


def test_collect_sources_expands_dirs_and_filters(tmp_path):
    (tmp_path / "a.c").write_text("int main(){return 0;}\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.c").write_text("int x;\n")
    (tmp_path / "notas.txt").write_text("hola\n")

    files = collect_source_files([tmp_path])
    names = {f.name for f in files}
    assert names == {"a.c", "b.c"}

    solo = collect_source_files([tmp_path / "a.c"])
    assert [f.name for f in solo] == ["a.c"]


def test_snapshot_reflects_mtime_changes(tmp_path):
    f = tmp_path / "x.c"
    f.write_text("uno\n")
    s1 = snapshot_mtimes([f])
    time.sleep(0.01)
    f.write_text("dos\n")
    s2 = snapshot_mtimes([f])
    assert s1[str(f)] != s2[str(f)]


def test_iter_changes_yields_only_on_change(tmp_path):
    src = tmp_path / "y.c"
    src.write_text("v1\n")
    session = WatchSession([src], interval_sec=0.02)

    it = session.iter_changes()
    # Primer sondeo sin cambios: no rinde nada en un par de iteraciones internas.
    # El generador solo avanza al haber cambio, así que forzamos uno:
    def trigger():
        time.sleep(0.05)
        src.write_text("v2\n")

    import threading

    threading.Thread(target=trigger, daemon=True).start()
    change = next(it)
    assert isinstance(change, ChangeSet)
    assert src in change.changed


def test_deleted_file_reported(tmp_path):
    src = tmp_path / "z.c"
    src.write_text("temporal\n")
    session = WatchSession([src], interval_sec=0.02)

    import threading

    def trigger():
        time.sleep(0.05)
        src.unlink()

    threading.Thread(target=trigger, daemon=True).start()
    change = next(session.iter_changes())
    assert src in change.deleted
    assert change.any


def test_invalid_interval_rejected(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        WatchSession([tmp_path], interval_sec=0)
