"""Graphics assignment evaluation: SDL2/Raylib binaries under a virtual framebuffer (Xvfb).

Pipeline por caso:
    1. Levantar Xvfb en un display libre con la resolución configurada.
    2. Ejecutar el binario del alumno con DISPLAY apuntando al Xvfb.
    3. Esperar el tiempo de asentamiento y capturar la ventana raíz
       (`import -window root`): al no haber window manager, la raíz ES la
       salida del programa — captura determinista sin dependencias de WM.
    4. Comparar contra la imagen dorada con `compare -metric AE`
       (cantidad de píxeles distintos) y umbral configurable.

Sin Xvfb/ImageMagick instalados, todos los métodos devuelven reportes
estructurados de indisponibilidad en lugar de fallar.
"""

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import shutil
import subprocess
import time
from typing import List, Optional

from ripley.config import GraphicsConfig


@dataclass
class CaptureResult:
    ok: bool
    screenshot_path: Optional[Path] = None
    message: str = ""
    display: Optional[str] = None


@dataclass
class GraphicsCaseResult:
    expected: str
    passed: bool = False
    diff_pixels: int = -1
    threshold: int = 0
    screenshot: Optional[Path] = None
    message: str = ""


@dataclass
class GraphicsReport:
    available: bool
    cases: List[GraphicsCaseResult] = field(default_factory=list)
    message: str = ""

    @property
    def all_passed(self) -> bool:
        return self.available and bool(self.cases) and all(c.passed for c in self.cases)


def probe_graphics(cfg: Optional[GraphicsConfig] = None) -> tuple:
    """Verifica Xvfb + capture/compare de ImageMagick. Devuelve (ok, motivo)."""
    cfg = cfg or GraphicsConfig()
    faltan = [
        nombre for nombre in ("Xvfb", cfg.capture_executable, cfg.compare_executable)
        if not shutil.which(nombre)
    ]
    if faltan:
        return False, f"Faltan herramientas para evaluación gráfica: {', '.join(faltan)}."
    return True, "Xvfb e ImageMagick disponibles."


def pick_display(base: int = 90) -> int:
    """Primer número de display sin socket ocupado, buscando desde base."""
    for n in range(base, base + 50):
        if not Path(f"/tmp/.X11-unix/X{n}").exists():
            return n
    raise RuntimeError("No se encontró un display Xlibre.")


def compare_images(
    image_a: Path | str,
    image_b: Path | str,
    compare_executable: str = "compare",
) -> Optional[int]:
    """Cantidad de píxeles diferentes (métrica AE). None si la herramienta falla."""
    compare_bin = shutil.which(compare_executable)
    if not compare_bin:
        return None
    try:
        proc = subprocess.run(
            [compare_bin, "-metric", "AE", str(image_a), str(image_b), "null:"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    # compare escribe la métrica en stderr; rc=1 significa "imágenes distintas" (normal).
    m = re.search(r"(\d+)", proc.stderr)
    return int(m.group(1)) if m else None


class GraphicsEvaluator:
    def __init__(self, cfg: Optional[GraphicsConfig] = None) -> None:
        self.cfg = cfg or GraphicsConfig()
        self._probe_ok, self._probe_msg = probe_graphics(self.cfg)

    @property
    def available(self) -> bool:
        return self._probe_ok

    # ------------------------------------------------------------------
    def capture_screenshot(
        self,
        binary_path: Path | str,
        cli_args: tuple = (),
        stdin_data: str = "",
        workdir: Optional[Path] = None,
    ) -> CaptureResult:
        """Ejecuta el binario bajo Xvfb y captura la ventana raíz."""
        if not self._probe_ok:
            return CaptureResult(ok=False, message=self._probe_msg)

        bin_path = Path(binary_path)
        if not bin_path.exists():
            return CaptureResult(ok=False, message=f"Binario no encontrado: {bin_path}")

        try:
            n = pick_display(self.cfg.display_base)
        except RuntimeError as e:
            return CaptureResult(ok=False, message=str(e))
        display = f":{n}"

        xvfb_proc = None
        app_proc = None
        shot = (workdir or Path.cwd()) / f"capture_{n}.png"
        try:
            xvfb_proc = subprocess.Popen(
                ["Xvfb", display, "-screen", "0", self.cfg.screen, "-nolisten", "tcp"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            socket_path = Path(f"/tmp/.X11-unix/X{n}")
            deadline = time.monotonic() + 5.0
            while not socket_path.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            if not socket_path.exists():
                return CaptureResult(ok=False, message="Xvfb no creó su socket a tiempo.", display=display)

            env = dict(os.environ, DISPLAY=display)
            app_proc = subprocess.Popen(
                [str(bin_path), *cli_args],
                stdin=subprocess.PIPE if stdin_data else subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=env,
            )
            if stdin_data and app_proc.stdin:
                try:
                    app_proc.stdin.write(stdin_data.encode())
                    app_proc.stdin.close()
                except OSError:
                    pass

            time.sleep(self.cfg.settle_seconds)

            import_bin = shutil.which(self.cfg.capture_executable)
            cap = subprocess.run(
                [import_bin, "-display", display, "-window", "root", str(shot)],
                capture_output=True, text=True, timeout=30,
            )
            if cap.returncode != 0 or not shot.exists():
                return CaptureResult(ok=False, display=display,
                                     message=f"Captura fallida: {cap.stderr.strip()[:200]}")
            return CaptureResult(ok=True, screenshot_path=shot, display=display,
                                 message="Captura obtenida.")
        except OSError as e:
            return CaptureResult(ok=False, message=f"Error lanzando proceso gráfico: {e}")
        finally:
            for proc in (app_proc, xvfb_proc):
                if proc is not None and proc.poll() is None:
                    proc.terminate()
            deadline = time.monotonic() + 3.0
            for proc in (app_proc, xvfb_proc):
                if proc is not None and proc.poll() is None and time.monotonic() < deadline:
                    proc.wait(timeout=max(0.1, deadline - time.monotonic()))

    # ------------------------------------------------------------------
    def evaluate_case(
        self,
        binary_path: Path | str,
        expected_image: Path | str,
        cli_args: tuple = (),
        stdin_data: str = "",
        workdir: Optional[Path] = None,
    ) -> GraphicsCaseResult:
        """Un caso: ejecuta, captura y compara contra la imagen dorada."""
        result = GraphicsCaseResult(expected=str(expected_image),
                                    threshold=self.cfg.max_diff_pixels)
        if not self._probe_ok:
            result.message = self._probe_msg
            return result
        expected = Path(expected_image)
        if not expected.exists():
            result.message = f"Imagen dorada inexistente: {expected}"
            return result

        cap = self.capture_screenshot(binary_path, cli_args, stdin_data, workdir)
        if not cap.ok or cap.screenshot_path is None:
            result.message = cap.message
            return result
        result.screenshot = cap.screenshot_path

        diff = compare_images(cap.screenshot_path, expected, self.cfg.compare_executable)
        if diff is None:
            result.message = "La comparación de imágenes falló (¿ImageMagick corrupto?)."
            return result

        result.diff_pixels = diff
        result.passed = diff <= self.cfg.max_diff_pixels
        result.message = (
            f"{diff} píxeles distintos (umbral {self.cfg.max_diff_pixels})."
        )
        return result
