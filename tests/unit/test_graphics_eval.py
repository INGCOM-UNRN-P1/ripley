"""Tests for Xvfb-based graphics evaluation (graceful degradation included)."""

import shutil
from pathlib import Path

import pytest

from ripley.config import GraphicsConfig
from ripley.tools.graphics_eval import (
    GraphicsEvaluator,
    compare_images,
    pick_display,
    probe_graphics,
)


def _xvfb_available() -> bool:
    return shutil.which("Xvfb") is not None


def _imagemagick_available() -> bool:
    return shutil.which("compare") is not None and shutil.which("import") is not None


def test_probe_reports_missing_tools_with_names():
    ok, msg = probe_graphics(GraphicsConfig())
    if _xvfb_available() and _imagemagick_available():
        assert ok
    else:
        assert not ok
        assert "Faltan" in msg
        # nombra al menos la primera herramienta ausente
        if not shutil.which("Xvfb"):
            assert "Xvfb" in msg


def test_pick_display_returns_free_slot():
    base = 700
    n = pick_display(base)
    assert base <= n < base + 50
    assert not Path(f"/tmp/.X11-unix/X{n}").exists()


def test_compare_images_parses_ae_metric(tmp_path, monkeypatch):
    if not _imagemagick_available():
        pytest.skip("ImageMagick no disponible")

    import subprocess

    calls = {}

    def fake_run(*args, **kwargs):
        calls["cmd"] = args[0]

        class P:
            returncode = 1  # imágenes distintas: comportamiento normal de compare
            stderr = "42"
            stdout = ""

        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    diff = compare_images(tmp_path / "a.png", tmp_path / "b.png")
    assert diff == 42
    assert "-metric" in calls["cmd"] and "AE" in calls["cmd"]


def test_evaluate_case_without_xvfb_structured_failure(tmp_path, monkeypatch):
    """Sin Xvfb el resultado es un reporte estructurado, nunca una excepción."""
    evaluator = GraphicsEvaluator(GraphicsConfig())
    if evaluator.available:
        pytest.skip("Xvfb disponible: se cubre en test de integración real")
    res = evaluator.evaluate_case(tmp_path / "noexiste.out", tmp_path / "gold.png")
    assert res.passed is False
    assert "Faltan" in res.message or "Xvfb" in res.message


def test_evaluate_case_missing_golden_reported(tmp_path):
    if not (_xvfb_available() and _imagemagick_available()):
        pytest.skip("Xvfb/ImageMagick no disponibles")
    evaluator = GraphicsEvaluator(GraphicsConfig())
    fake_bin = tmp_path / "app.out"
    fake_bin.write_bytes(b"\x7fELF")  # existe pero no correrá; golden falta primero
    res = evaluator.evaluate_case(fake_bin, tmp_path / "inexistente.png")
    assert res.passed is False
    assert "dorada inexistente" in res.message


@pytest.mark.integration
@pytest.mark.skipif(not (_xvfb_available() and _imagemagick_available()),
                    reason="requiere Xvfb + ImageMagick")
def test_root_capture_pipeline_self_compare(tmp_path):
    """Pipeline completo sin cliente gráfico: raíz vacía comparada consigo misma."""
    cfg = GraphicsConfig(settle_seconds=0.3, max_diff_pixels=0)

    class RootOnlyEvaluator(GraphicsEvaluator):
        def capture_screenshot(self, binary_path=None, cli_args=(), stdin_data="", workdir=None):
            # Ignora el binario: valida Xvfb+captura+comparación del pipeline.
            return super()._capture_root_only(workdir or tmp_path)

    ev = RootOnlyEvaluator(cfg)

    def _capture_root_only(self, workdir):
        import os
        import subprocess
        import time

        from ripley.tools.graphics_eval import pick_display

        n = pick_display(self.cfg.display_base)
        display = f":{n}"
        xvfb = subprocess.Popen(
            ["Xvfb", display, "-screen", "0", self.cfg.screen, "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            socket = Path(f"/tmp/.X11-unix/X{n}")
            deadline = time.monotonic() + 5
            while not socket.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            shot = Path(workdir) / f"root_{n}.png"
            cap = subprocess.run(
                [shutil.which(self.cfg.capture_executable), "-display", display,
                 "-window", "root", str(shot)],
                capture_output=True, timeout=30)
            assert cap.returncode == 0 and shot.exists()
            return type("C", (), {"ok": True, "screenshot_path": shot, "message": "", "display": display})()
        finally:
            xvfb.terminate()

    import types
    ev._capture_root_only = types.MethodType(_capture_root_only, ev)

    cap = ev.capture_screenshot(tmp_path / "unused.out", workdir=tmp_path)
    assert cap.ok
    diff = compare_images(cap.screenshot_path, cap.screenshot_path)
    assert diff == 0  # auto-comparación: píxel-idéntica
