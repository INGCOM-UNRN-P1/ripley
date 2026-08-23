"""Unit tests for hermetic toolchain snapshots."""

from ripley.toolchain import capture_snapshot, compare_snapshots, load_snapshot, save_snapshot


def test_capture_and_save_roundtrip(tmp_path):
    snapshot = capture_snapshot(compile_flags=["-Wall", "-std=c11", "-O2"])
    assert snapshot.compiler_version
    assert snapshot.machine
    assert snapshot.flags_hash

    out = save_snapshot(snapshot, tmp_path / "snap.json")
    loaded = load_snapshot(out)
    assert loaded is not None
    assert loaded.compiler_version == snapshot.compiler_version
    assert loaded.flags_hash == snapshot.flags_hash


def test_compare_identical_snapshots_reproducible():
    a = capture_snapshot()
    b = capture_snapshot()
    comparison = compare_snapshots(a, b)
    # En el mismo sistema no debe divergir nada excepto el timestamp (ignorado).
    assert comparison.reproducible
    assert comparison.differences == []


def test_compare_detects_toolchain_drift():
    a = capture_snapshot()
    b = capture_snapshot()
    b.libc_version = "glibc 9.9.9 (alterada)"
    comparison = compare_snapshots(a, b)
    assert not comparison.reproducible
    assert any("libc_version" in d for d in comparison.differences)


def test_flags_hash_changes_with_flags():
    with_o2 = capture_snapshot(compile_flags=["-O2"])
    with_oz = capture_snapshot(compile_flags=["-Oz"])
    assert with_o2.flags_hash != with_oz.flags_hash


def test_load_missing_snapshot_returns_none(tmp_path):
    assert load_snapshot(tmp_path / "inexistente.json") is None
