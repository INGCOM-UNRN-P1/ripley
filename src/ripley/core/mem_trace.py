"""mem-trace (spectre): generador de trazas visuales de memoria para programas C.

Extrae estáticamente la secuencia de eventos de memoria dinámica de un archivo C
(declaraciones de punteros, malloc/calloc/realloc/free), la pliega en frames con
:class:`ripley.core.memory_animation.MemoryAnimator` y produce un reporte HTML
autocontenido que combina tres motores existentes:

* animación SVG interactiva Stack/Heap/Punteros (``memory_animation``),
* topología de structs del código (:class:`DynamicMemoryVisualizer`),
* reporte de fragmentación de un heap simulado (:class:`HeapMemorySimulator`).

Limitaciones conocidas del análisis estático por patrones: los tamaños no
literales se estiman con un valor por defecto; ``realloc`` se modela como un
``malloc`` nuevo del mismo tag; las asignaciones compuestas en una misma línea
no se detectan.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import html
import re

from ripley.core.heap_simulator import HeapSimulationReport, HeapMemorySimulator
from ripley.core.memory_animation import AnimationError, MemoryAnimator, render_animation_svg
from ripley.core.memory_visualizer import DynamicMemoryVisualizer, StructDefinition
from ripley.core.security import strip_c_comments_and_strings

DEFAULT_ALLOC_SIZE = 16


@dataclass
class TraceRecord:
    """Evento de memoria extraído, para la tabla del reporte."""

    line: int
    op: str
    detail: str


@dataclass
class TraceResult:
    """Resultado completo de una traza generada."""

    output: Path
    source_name: str
    records: List[TraceRecord] = field(default_factory=list)
    frames: list = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    report: Optional[HeapSimulationReport] = None
    structs: Dict[str, StructDefinition] = field(default_factory=dict)

    @property
    def event_count(self) -> int:
        return len(self.records)


# ---------------------------------------------------------------------------
# Extracción estática de eventos
# ---------------------------------------------------------------------------
class MemoryTracer:
    """Analiza código C y produce la secuencia de eventos de memoria dinámica."""

    def __init__(self) -> None:
        self._decl_alloc = re.compile(
            r"^\s*(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:struct\s+)?"
            r"[A-Za-z_]\w*\s*\*+\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*;\s*$"
        )
        self._decl_ptr = re.compile(
            r"^\s*(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:struct\s+)?"
            r"[A-Za-z_]\w*\s*\*+\s*([A-Za-z_]\w*)\s*;\s*$"
        )
        self._assign_alloc = re.compile(
            r"^\s*([A-Za-z_]\w*)\s*=\s*((?:malloc|calloc|realloc)\s*\([^()]*)\)\s*;\s*$"
        )
        self._free_call = re.compile(r"\bfree\s*\(\s*([A-Za-z_]\w*)\s*\)")
        self._alloc_call = re.compile(r"\b(malloc|calloc|realloc)\s*\(((?:[^()]|\([^()]*\))*)\)")

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _parse_size(func: str, args_raw: str) -> Tuple[int, str]:
        args = [a.strip() for a in args_raw.split(",") if a.strip()]
        nums: List[Optional[int]] = []
        for a in args:
            try:
                nums.append(int(a))
            except ValueError:
                nums.append(None)

        if func == "calloc" and len(nums) >= 2 and None not in nums[:2]:
            return nums[0] * nums[1], f"calloc({args[0]}, {args[1]})"
        if func == "realloc" and nums and nums[-1] is not None:
            return nums[-1], f"realloc({args_raw})"
        if func == "malloc" and nums and nums[0] is not None:
            return nums[0], f"malloc({args_raw})"

        expr = f"{func}({','.join(args)})" if args else f"{func}()"
        return DEFAULT_ALLOC_SIZE, expr

    def _target_of(self, rhs: str) -> str:
        rhs = rhs.strip()
        if rhs == "NULL":
            return "NULL"
        if rhs.startswith("&"):
            return rhs
        if rhs.isidentifier():
            return rhs
        return "?"

    # -- API principal -------------------------------------------------------
    def extract_events(self, code: str) -> Tuple[List[dict], List[TraceRecord]]:
        """Devuelve (eventos para MemoryAnimator, registros legibles para el reporte).

        Además puebla ``self.violations`` con hallazgos estáticos de comportamiento
        peligroso: *double-free* y *use-after-free* (incluyendo aliases: si ``q = p``
        y luego ``free(p)``, usar ``q`` también es uso post-liberación).
        """
        clean = strip_c_comments_and_strings(code)
        events: List[dict] = []
        records: List[TraceRecord] = []
        known_ptrs: set = set()
        alias: Dict[str, str] = {}      # puntero -> raíz del bloque al que apunta
        freed: Dict[str, int] = {}      # raíz -> línea donde se liberó
        self.violations: List[TraceRecord] = []

        def raiz(nombre: str) -> str:
            vistos = set()
            while nombre in alias and nombre not in vistos:
                vistos.add(nombre)
                nombre = alias[nombre]
            return nombre

        def colgantes(linea: str) -> List[str]:
            nombres = set(re.findall(r"\b[A-Za-z_]\w*\b", linea))
            return sorted(v for v in nombres if v in known_ptrs and raiz(v) in freed)

        for lineno, raw_line in enumerate(clean.splitlines(), start=1):
            m = self._free_call.search(raw_line)
            if m and ";" in raw_line:
                var = m.group(1)
                if var == "NULL":
                    continue
                r = raiz(var)
                if r in freed:
                    self.violations.append(
                        TraceRecord(lineno, "double-free",
                                    f"free({var}) ya liberado en línea {freed[r]}")
                    )
                    records.append(self.violations[-1])
                    continue
                freed[r] = lineno
                events.append({"op": "free", "tag": var, "line": lineno})
                records.append(TraceRecord(lineno, "free", f"free({var})"))
                continue

            # Declaración de puntero sin inicializar: queda registrado para
            # que asignaciones posteriores se traten como puntero conocido.
            m_decl = self._decl_ptr.match(raw_line)
            if m_decl:
                known_ptrs.add(m_decl.group(1))
                continue

            # Asignación simple sobre un puntero conocido (revive o propaga colgado)
            m_asig = re.match(r"\s*([A-Za-z_]\w*)\s*=(?![=])\s*(.+);?", raw_line.strip() + "\n")
            if m_asig and m_asig.group(1) in known_ptrs and not self._free_call.search(raw_line):
                var, rhs = m_asig.group(1), m_asig.group(2)
                for v in colgantes(rhs):
                    self.violations.append(
                        TraceRecord(lineno, "use-after-free",
                                    f"{var} ← valor de '{v}' (bloque liberado en línea {freed[raiz(v)]})")
                    )
                    records.append(self.violations[-1])
                alloc = self._alloc_call.search(rhs)
                target = self._target_of(rhs)
                if alloc:
                    size, detail = self._parse_size(alloc.group(1), alloc.group(2))
                    events.append({"op": "malloc", "tag": var, "size": size, "line": lineno})
                    records.append(TraceRecord(lineno, "realloc-like", f"{var} ← {detail} ({size} B)"))
                    alias.pop(var, None)
                    if raiz(var) == var:
                        freed.pop(var, None)
                elif target == "NULL" or target.startswith("&") or target not in known_ptrs:
                    alias.pop(var, None)
                    if raiz(var) == var:
                        freed.pop(var, None)
                elif target in known_ptrs:
                    alias[var] = raiz(target)
                continue

            m = self._decl_alloc.match(raw_line)
            if m:
                var, rhs = m.group(1), m.group(2)
                alloc = self._alloc_call.search(rhs)
                if alloc:
                    size, detail = self._parse_size(alloc.group(1), alloc.group(2))
                    events.append({"op": "malloc", "tag": var, "size": size, "line": lineno})
                    records.append(TraceRecord(lineno, "malloc", f"{var} ← {detail} ({size} B)"))
                    freed.pop(var, None)   # renace con memoria fresca
                    alias.pop(var, None)
                else:
                    target = self._target_of(rhs)
                    events.append({"op": "ptr", "var": var, "target": target, "line": lineno})
                    records.append(TraceRecord(lineno, "ptr", f"{var} → {target}"))
                    for v in colgantes(rhs):
                        self.violations.append(
                            TraceRecord(lineno, "use-after-free",
                                        f"{var} ← valor de '{v}' (bloque liberado en línea {freed[raiz(v)]})")
                        )
                        records.append(self.violations[-1])
                    if target in known_ptrs and target != "NULL":
                        alias[var] = raiz(target)
                    else:
                        alias.pop(var, None)
                        if raiz(var) == var:
                            freed.pop(var, None)  # ahora apunta a memoria válida
                known_ptrs.add(var)
                continue

            # Cualquier otra mención a un puntero colgante (printf, condición,
            # desreferencia, retorno...) constituye uso post-liberación.
            for v in colgantes(raw_line):
                self.violations.append(
                    TraceRecord(lineno, "use-after-free",
                                f"uso de '{v}' después de free (línea {freed[raiz(v)]})")
                )
                records.append(self.violations[-1])

        return events, records


# ---------------------------------------------------------------------------
# Plegado de eventos + simulación de heap
# ---------------------------------------------------------------------------
def fold_events(
    events: List[dict],
    capacity: int = 65536,
) -> Tuple[list, List[str], Optional[HeapSimulationReport]]:
    """Pliega eventos en frames (MemoryAnimator) y replays en HeapMemorySimulator."""
    animator = MemoryAnimator()
    warnings: List[str] = []

    try:
        frames = animator.apply(events)
    except AnimationError as exc:
        frames = list(animator.frames)
        warnings.append(f"Plegado interrumpido: {exc}")

    sim = HeapMemorySimulator(capacity=capacity)
    tag_offsets: Dict[str, Optional[int]] = {}
    tags_liberados: set = set()
    for ev in events:
        if ev["op"] == "malloc":
            offset = sim.allocate(ev.get("size", DEFAULT_ALLOC_SIZE), tag=ev["tag"])
            if offset is None:
                warnings.append(
                    f"línea {ev.get('line', '?')}: {ev['tag']} = malloc({ev.get('size')}) "
                    f"excede la capacidad simulada ({capacity} B)"
                )
            tag_offsets[ev["tag"]] = offset
        elif ev["op"] == "free":
            tag = ev["tag"]
            if tag in tags_liberados:
                warnings.append(
                    f"línea {ev.get('line', '?')}: double-free — free({tag}) sobre memoria ya liberada"
                )
                continue
            offset = tag_offsets.get(tag)
            if offset is not None:
                sim.free(offset)
                tags_liberados.add(tag)

    return frames, warnings, sim.get_report()


# ---------------------------------------------------------------------------
# Render HTML
# ---------------------------------------------------------------------------
_CSS = """
body{background:#10141c;color:#e8edf5;font-family:monospace;margin:0;padding:24px}
h1{color:#4fc3f7;font-size:20px} h2{color:#4fc3f7;font-size:15px;margin-top:28px}
.sub{color:#8ea0bd;font-size:12px}
table{border-collapse:collapse;font-size:12px;margin-top:8px}
td,th{border:1px solid #3b4a63;padding:4px 10px;text-align:left}
th{background:#1b2230;color:#4fc3f7}
pre{background:#1b2230;border:1px solid #3b4a63;border-radius:6px;padding:10px;overflow-x:auto}
.warn{background:#3b2f00;border:1px solid #ffb300;color:#ffb300;border-radius:6px;padding:8px 12px;margin-top:12px;font-size:12px}
.info{color:#8ea0bd;font-size:12px}
svg{margin-top:10px}
"""


def generate_trace_html(result: TraceResult) -> str:
    """Compone el HTML autocontenido a partir de un :class:`TraceResult`."""
    esc = html.escape
    parts: List[str] = [
        "<!DOCTYPE html>",
        '<html lang="es">',
        '<meta charset="utf-8">',
        f"<title>ripley trace — {esc(result.source_name)}</title>",
        f"<style>{_CSS}</style>",
        "<h1>Traza de Memoria — spectre</h1>",
        f'<div class="sub">{esc(result.source_name)} · {result.event_count} eventos · '
        f"{len(result.frames)} frames · generado {datetime.now():%Y-%m-%d %H:%M}</div>",
    ]

    for w in result.warnings:
        parts.append(f'<div class="warn">⚠ {esc(w)}</div>')

    # --- Resumen del heap simulado ---
    parts.append("<h2>Resumen del Heap simulado</h2>")
    if result.report is not None:
        rep = result.report
        parts.append("<table>")
        for k, v in (
            ("Capacidad", f"{rep.total_capacity} B"),
            ("Pico ocupado", f"{rep.peak_allocated} B"),
            ("Ocupado actual", f"{rep.current_allocated} B"),
            ("Libre total", f"{rep.total_free} B"),
            ("Mayor bloque libre", f"{rep.largest_free_block} B"),
            ("Fragmentación externa", f"{rep.fragmentation_index * 100:.1f}%"),
        ):
            parts.append(f"<tr><th>{k}</th><td>{v}</td></tr>")
        parts.append("</table>")
        parts.append(f"<pre>{esc(rep.memory_map)}</pre>")

    # --- Animación ---
    parts.append("<h2>Animación paso a paso</h2>")
    if result.frames:
        parts.append(render_animation_svg(result.frames))
        parts.append('<div class="info">Navegación: botones ‹ › ▶ o flechas del teclado.</div>')
    else:
        parts.append('<p class="info">No se detectaron operaciones de memoria dinámica.</p>')

    # --- Topología de structs ---
    if result.structs:
        vis = DynamicMemoryVisualizer()
        parts.append("<h2>Topología de estructuras</h2>")
        parts.append(f'<pre class="mermaid">{esc(vis.to_mermaid(result.structs))}</pre>')
        dot = esc(vis.to_dot(result.structs))
        parts.append(f"<details><summary>Graphviz DOT</summary><pre>{dot}</pre></details>")

    # --- Tabla de eventos ---
    if result.records:
        parts.append("<h2>Eventos detectados</h2><table><tr><th>Línea</th><th>Op</th><th>Detalle</th></tr>")
        for rec in result.records:
            parts.append(f"<tr><td>{rec.line}</td><td>{esc(rec.op)}</td><td>{esc(rec.detail)}</td></tr>")
        parts.append("</table>")

    parts.append('<div class="sub">Generado por ripley trace (mem-trace / spectre).</div>')
    parts.append("</html>")
    return "\n".join(parts)


def save_trace(
    c_file: Path | str,
    output: Path | str,
    capacity: int = 65536,
) -> TraceResult:
    """Pipeline completo: leer C → extraer → plegar → simular → escribir HTML."""
    path = Path(c_file)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    code = path.read_text(encoding="utf-8", errors="replace")
    tracer = MemoryTracer()
    events, records = tracer.extract_events(code)
    frames, warnings, report = fold_events(events, capacity=capacity)
    structs = DynamicMemoryVisualizer().extract_structs(code)

    # Violaciones estáticas (use-after-free, double-free) al frente del reporte
    for v in tracer.violations:
        warnings.insert(0, f"línea {v.line}: {v.op} — {v.detail}")

    result = TraceResult(
        output=Path(output),
        source_name=path.name,
        records=records,
        frames=frames,
        warnings=warnings,
        report=report,
        structs=structs,
    )
    result.output.write_text(generate_trace_html(result), encoding="utf-8")
    return result
