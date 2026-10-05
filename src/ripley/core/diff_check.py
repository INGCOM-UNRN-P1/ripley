"""Verificación incremental (QoL #818): solo lo que cambió desde una referencia de git.

Con sulaco en cada push, la devolución de todo el proyecto repite lo de siempre. `ripley-check
diff-check` analiza el proyecto completo (para compilar hace falta) pero informa solo las
observaciones en las líneas que cambiaron desde `--base` (por defecto `HEAD`: lo que todavía no se
commiteó), más las de los archivos nuevos. Sin caché: git ya sabe qué cambió.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class SinGit(RuntimeError):
    """El directorio no es un repositorio git o la referencia no existe."""


def _git(raiz: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise SinGit(res.stderr.strip() or f"git {' '.join(args)} falló")
    return res.stdout


def lineas_cambiadas(raiz: Path, base: str = "HEAD") -> Dict[str, Set[int]]:
    """Archivo (nombre) → líneas nuevas o modificadas desde `base`, incluidas las sin commitear.
    Un archivo nuevo sin seguimiento cuenta entero (conjunto vacío = todas sus líneas)."""
    cambios: Dict[str, Set[int]] = {}
    actual = None
    for linea in _git(raiz, "diff", "-U0", base, "--", "*.c", "*.h").splitlines():
        if linea.startswith("+++ "):
            ruta = linea[4:].strip()
            actual = None if ruta == "/dev/null" else Path(ruta.removeprefix("b/")).name
            if actual:
                cambios.setdefault(actual, set())
            continue
        m = _HUNK.match(linea)
        if m and actual:
            inicio, cantidad = int(m.group(1)), int(m.group(2) or "1")
            cambios[actual].update(range(inicio, inicio + cantidad))
    for ruta in _git(raiz, "ls-files", "--others", "--exclude-standard", "--", "*.c", "*.h").splitlines():
        cambios[Path(ruta).name] = set()
    return cambios


def filtrar(hallazgos: List[dict], cambios: Dict[str, Set[int]]) -> List[dict]:
    resultado = []
    for h in hallazgos:
        archivo = Path(str(h.get("file") or h.get("archivo") or "")).name
        if archivo not in cambios:
            continue
        lineas = cambios[archivo]
        linea = int(h.get("line") or h.get("linea") or 0)
        if not lineas or linea in lineas or linea == 0:
            resultado.append(h)
    return resultado
