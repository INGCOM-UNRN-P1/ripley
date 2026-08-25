"""complexity-bench — Verificación empírica de cotas de complejidad (nuevas.md §2.2).

Estrategia de duplicación: se mide el tiempo de ejecución del programa con una
entrada de tamaño N y con 8·N; el cociente t(8N)/t(N) se compara contra el que
predice la cota Big-O exigida (8^exp). Es más estable que ajustar regresiones
sobre tiempos microscópicos y traduce directo a la intuición pedagógica:
"si multiplico la entrada por 8, ¿cuánto crece el tiempo?".
"""

from __future__ import annotations

import re
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Sequence


#: Exponente que representa cada cota pedagógica aceptada.
COTAS: Dict[str, float] = {
    "O(1)": 0.0,
    "O(log n)": 0.5,
    "O(n)": 1.0,
    "O(n log n)": 1.5,
    "O(n^2)": 2.0,
    "O(n²)": 2.0,
}

FACTOR_DUPLICACION = 8          # medimos t(8N) contra t(N)
TOLERANCIA_RELATIVA = 1.9       # margen holgado: falla sólo si crece bastante más
MARGEN_ABSOLUTO_SEG = 0.05      # absorbe el overhead de proceso en entradas chicas


def normalizar_cota(texto: str) -> Optional[str]:
    """Acepta variantes escritas ('O(nlogn)', 'o(n^2)', 'O(n log n)')."""
    limpio = texto.strip().replace(" ", "").replace("·", "").lower()
    limpio = limpio.replace("logn", "logn").replace("nlogn", "n log n")
    limpio = limpio.replace("^", "")
    alias = {
        "o(1)": "O(1)",
        "o(logn)": "O(log n)",
        "o(n)": "O(n)",
        "o(nlogn)": "O(n log n)",
        "o(n2)": "O(n^2)",
    }
    return alias.get(limpio)


def extraer_cota_de_ripley_toml(toml_texto: str) -> Optional[str]:
    """Lee `[bench] expect = "O(n)"` de un ripley.toml si existe."""
    m = re.search(r'\[bench\][^[]*?expect\s*=\s*"([^"]+)"', toml_texto, re.DOTALL)
    return m.group(1) if m else None


def compilar_optimizado(fuentes: Sequence[Path], salida: Path,
                        include_dirs: Sequence[Path] = (),
                        timeout: int = 30) -> tuple[bool, str]:
    """Compila con `-O2` sin sanitizers: las mediciones deben ser limpias."""
    gcc = shutil.which("gcc")
    if gcc is None:
        return False, "gcc no está disponible"
    cmd = [gcc, "-std=c11", "-O2", "-Wall", "-o", str(salida)]
    for inc in include_dirs:
        cmd += ["-I", str(inc)]
    cmd += [str(f) for f in fuentes]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "compilación excedió el tiempo límite"
    if proc.returncode != 0:
        return False, proc.stderr.strip()[:500]
    return True, ""


def _n_base(exponente: float) -> int:
    """Elige N inicial tal que la cota esperada cueste ~30 ms por corrida."""
    exp = max(exponente, 0.35)
    n = int((30_000_000 ** (1.0 / exp)))
    return max(256, min(40_000_000, n))


def _ejecutar_y_medir(binario: Path, n: int, patron: str,
                      timeout_seg: float = 20.0, repeats: int = 3) -> Optional[float]:
    entrada = (patron.replace("{n}", str(n)).replace("\\n", "\n")).encode()
    tiempos = []
    for _ in range(max(1, repeats)):
        inicio = time.perf_counter()
        try:
            proc = subprocess.run([str(binario)], input=entrada,
                                  capture_output=True, timeout=timeout_seg)
        except subprocess.TimeoutExpired:
            return None
        duracion = time.perf_counter() - inicio
        if proc.returncode != 0:
            return None
        tiempos.append(duracion)
    return statistics.median(tiempos)


TECHO_POR_CORRIDA_SEG = 1.5


def verificar_cota(binario: Path, cota_esperada: str,
                   patron_entrada: str = "{n}\\n",
                   sizes: Optional[Sequence[int]] = None,
                   repeats: int = 3,
                   r_squared_minimo: float = 0.0) -> tuple[Optional[bool], str]:
    """Escalera adaptativa de duplicación contra la cota exigida.

    Arranca en un N cuyo costo esperado es pequeño y multiplica por 8 hasta
    4 mediciones o hasta que una corrida tarde más de ``TECHO_POR_CORRIDA_SEG``.
    En cada par consecutivo calcula cuánto creció el tiempo y lo compara con el
    crecimiento que permite la cota (8^exp + margen). Si algún par excede,
    falla temprano; si una corrida se cuelga después de tener un par válido,
    también (un programa dentro de su cota no se cuelga en ese tamaño).
    """
    cota = normalizar_cota(cota_esperada)
    if cota is None:
        return None, f"Cota no reconocida: '{cota_esperada}'. Usá una de: {', '.join(COTAS)}"
    exponente = COTAS[cota]

    if sizes and len(sizes) >= 2:
        escalera = list(sizes)
    else:
        n0 = _n_base(exponente)
        escalera = [n0 * (FACTOR_DUPLICACION ** i) for i in range(4)]

    ratio_limite = FACTOR_DUPLICACION ** exponente * TOLERANCIA_RELATIVA + \
        MARGEN_ABSOLUTO_SEG / 0.005  # margen extra proporcional a corridas cortas

    anterior: Optional[tuple[int, float]] = None
    ultimo_resumen = ""
    for n in escalera:
        t = _ejecutar_y_medir(binario, n, patron_entrada, timeout_seg=TECHO_POR_CORRIDA_SEG,
                              repeats=repeats)
        if t is None:
            if anterior is None:
                return False, (
                    f"se excede el tiempo límite ({TECHO_POR_CORRIDA_SEG:.0f}s) incluso con "
                    f"la entrada mínima de calibración (N={n}): tu algoritmo no respeta "
                    f"la cota {cota} o está muy lejos de ella"
                )
            return False, (
                f"timeout con N={n}: tras crecer ×{FACTOR_DUPLICACION} el tiempo ya "
                f"no respeta la cota {cota} ({ultimo_resumen})"
            )
        if anterior is not None:
            n0, t0 = anterior
            ratio = t / t0
            ok_par = ratio <= ratio_limite
            ultimo_resumen = (
                f"t({n0})={t0 * 1000:.0f} ms → t({n})={t * 1000:.0f} ms "
                f"(creció ×{ratio:.1f}; la cota {cota} permite ≈×{FACTORES_TEXTO(exponente)})"
            )
            if not ok_par:
                return False, ultimo_resumen
        elif t > TECHO_POR_CORRIDA_SEG:
            return False, (
                f"con N={n} ya tarda {t:.1f}s: excede el presupuesto de la cota {cota}"
            )
        anterior = (n, t)

    return True, (ultimo_resumen or "sin mediciones suficientes")


def FACTORES_TEXTO(exponente: float) -> str:
    return f"{FACTOR_DUPLICACION ** exponente:.1f}"
