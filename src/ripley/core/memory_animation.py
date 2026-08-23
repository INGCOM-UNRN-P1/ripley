"""Step-by-step memory animation generator: interactive SVG frames of Stack/Heap/Pointers.

Los frames se construyen plegando una lista de eventos de ejecución
(declaraciones, asignaciones, malloc/free, movimientos de punteros) o a
partir de operaciones de heap en formato compacto. El SVG final es
interactivo (botones prev/next/auto) y degrada al primer frame sin JS.
"""

from dataclasses import dataclass, field
from pathlib import Path
import html
import shutil
import subprocess
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Modelo de estado por frame
# ---------------------------------------------------------------------------
@dataclass
class StackVar:
    name: str
    type_name: str = "int"
    value: str = "?"


@dataclass
class HeapCell:
    tag: str
    size: int
    offset: int = 0
    state: str = "alloc"  # alloc | freed


@dataclass
class PtrArrow:
    name: str
    target: str  # "&<stackvar>" | "#<heaptag>" | "NULL" | "DANGLING"


@dataclass
class MemoryFrame:
    caption: str
    stack: List[StackVar] = field(default_factory=list)
    heap: List[HeapCell] = field(default_factory=list)
    pointers: List[PtrArrow] = field(default_factory=list)


class AnimationError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Plegado de eventos -> frames
# ---------------------------------------------------------------------------
class MemoryAnimator:
    """Construye la secuencia de frames aplicando eventos secuenciales."""

    def __init__(self) -> None:
        self.frames: List[MemoryFrame] = []
        self._stack: Dict[str, StackVar] = {}
        self._heap: Dict[str, HeapCell] = {}
        self._ptrs: Dict[str, PtrArrow] = {}
        self._next_offset = 0x1000
        self._leaked_tags: set = set()

    # -- helpers internos -------------------------------------------------
    def _snapshot(self, caption: str) -> MemoryFrame:
        return MemoryFrame(
            caption=caption,
            stack=[StackVar(v.name, v.type_name, v.value) for v in self._stack.values()],
            heap=[
                HeapCell(c.tag, c.size, c.offset, c.state)
                for c in sorted(self._heap.values(), key=lambda c: c.offset)
            ],
            pointers=[PtrArrow(p.name, p.target) for p in self._ptrs.values()],
        )

    def _resolve_dangling(self, tag: str) -> None:
        """Tras un free, todo puntero que apuntaba a esa celda queda colgante."""
        for p in self._ptrs.values():
            if p.target == f"#{tag}":
                p.target = "DANGLING"

    # -- API principal -----------------------------------------------------
    def apply(self, events: List[dict]) -> List[MemoryFrame]:
        for ev in events:
            op = ev.get("op", "")
            line = ev.get("line")
            suffix = f" (línea {line})" if line else ""
            caption_base = ev.get("caption")

            if op == "decl":
                name = ev["var"]
                self._stack[name] = StackVar(name, ev.get("type", "int"), str(ev.get("value", "?")))
                caption = caption_base or f"{self._stack[name].type_name} {name} = {self._stack[name].value}{suffix}"
            elif op == "assign":
                name = ev["var"]
                if name not in self._stack:
                    raise AnimationError(f"assign sobre variable no declarada: {name}")
                self._stack[name].value = str(ev.get("value", "?"))
                caption = caption_base or f"{name} = {self._stack[name].value}{suffix}"
            elif op == "ptr":
                name = ev["var"]
                target = str(ev.get("target", "NULL"))
                self._ptrs[name] = PtrArrow(name, target)
                caption = caption_base or f"{name} → {target}{suffix}"
            elif op == "malloc":
                tag = ev["tag"]
                size = int(ev.get("size", 1))
                cell = HeapCell(tag=tag, size=size, offset=self._next_offset, state="alloc")
                self._next_offset += size
                self._heap[tag] = cell
                self._leaked_tags.discard(tag)
                caption = caption_base or f"{tag} = malloc({size}){suffix}"
            elif op == "free":
                tag = ev["tag"]
                if tag not in self._heap:
                    raise AnimationError(f"free de celda inexistente: {tag}")
                if self._heap[tag].state == "freed":
                    raise AnimationError(f"double free detectado: {tag}")
                self._heap[tag].state = "freed"
                self._leaked_tags.add(tag)
                self._resolve_dangling(tag)
                caption = caption_base or f"free({tag}){suffix}"
            elif op == "caption":
                caption = caption_base or ev.get("text", "")
                if not caption:
                    raise AnimationError("evento caption sin texto")
            else:
                raise AnimationError(f"operación desconocida: {op!r}")

            self.frames.append(self._snapshot(caption))

        if self.frames:
            vivos = [t for t in self._leaked_tags if self._heap[t].state == "freed"]
            # tags freed siguen en _leaked_tags solo si nunca re-malloc; filtrar liberados-y-reasignados
            realmente_vivos = [
                c.tag for c in self._heap.values()
                if c.state == "alloc"
            ]
            if realmente_vivos:
                self.frames[-1].caption += f" · ⚠ fuga: {', '.join(sorted(realmente_vivos))} sin liberar"
        return self.frames

    def from_heap_ops(self, ops_spec: str) -> List[MemoryFrame]:
        """Atajo: 'malloc:32:nodo1,malloc:64:nodo2,free:nodo1'."""
        events: List[dict] = []
        for raw in ops_spec.split(","):
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split(":")
            if parts[0] == "malloc" and len(parts) >= 2:
                size = int(parts[1])
                tag = parts[2] if len(parts) > 2 else f"blk{len(events)+1}"
                events.append({"op": "malloc", "size": size, "tag": tag})
            elif parts[0] == "free" and len(parts) >= 2:
                events.append({"op": "free", "tag": parts[1]})
            elif parts[0] == "caption":
                events.append({"op": "caption", "text": ":".join(parts[1:])})
            else:
                raise AnimationError(f"op inválida en from_heap_ops: {raw!r}")
        return self.apply(events)


# ---------------------------------------------------------------------------
# Render SVG
# ---------------------------------------------------------------------------
_PALETTE = {
    "bg": "#10141c",
    "panel": "#1b2230",
    "border": "#3b4a63",
    "text": "#e8edf5",
    "dim": "#8ea0bd",
    "accent": "#4fc3f7",
    "heap": "#7e57c2",
    "freed": "#ef5350",
    "dangling": "#ffb300",
    "green": "#66bb6a",
}


def _esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def render_frame_svg(frame: MemoryFrame, width: int = 640, height: int = 420) -> str:
    p = _PALETTE
    out: List[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="monospace">'
    )
    out.append(f'<rect width="{width}" height="{height}" fill="{p["bg"]}"/>')
    out.append(
        f'<rect x="10" y="10" width="{width-20}" height="34" rx="6" fill="{p["panel"]}" stroke="{p["border"]}"/>'
    )
    out.append(
        f'<text x="20" y="32" fill="{p["text"]}" font-size="15">{_esc(frame.caption)}</text>'
    )

    def panel(x, y, w, h, title):
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{p["panel"]}" stroke="{p["border"]}"/>')
        out.append(f'<text x="{x+12}" y="{y+22}" fill="{p["accent"]}" font-size="13">{title}</text>')

    # --- STACK ---
    sx, sy, sw = 20, 60, (width - 60) // 2
    panel(sx, sy, sw, height - sy - 20, "STACK")
    y = sy + 44
    for v in frame.stack:
        out.append(
            f'<text x="{sx+14}" y="{y+14}" fill="{p["text"]}" font-size="13">'
            f'{_esc(v.name)} : {_esc(v.type_name)} = {_esc(v.value)}</text>'
        )
        y += 22

    # --- HEAP ---
    hx = sx + sw + 20
    hw = sw
    panel(hx, sy, hw, height - sy - 20, "HEAP")
    y = sy + 44
    for c in frame.heap:
        color = p["heap"] if c.state == "alloc" else p["freed"]
        label = f'{_esc(c.tag)} [{c.size}B @ {hex(c.offset)}]'
        if c.state == "freed":
            label += " (liberado)"
        out.append(f'<rect x="{hx+12}" y="{y}" width="{hw-24}" height="18" rx="4" fill="{color}" fill-opacity="0.25" stroke="{color}"/>')
        out.append(f'<text x="{hx+18}" y="{y+13}" fill="{p["text"]}" font-size="11">{label}</text>')
        y += 24

    # --- PUNTEROS ---
    py = height - 110
    out.append(f'<text x="20" y="{py}" fill="{p["accent"]}" font-size="13">PUNTEROS</text>')
    x = 20
    for ptr in frame.pointers:
        color = p["dangling"] if ptr.target == "DANGLING" else p["green"]
        out.append(
            f'<text x="{x}" y="{py+20}" fill="{color}" font-size="12">'
            f'{_esc(ptr.name)} → {_esc(ptr.target)}</text>'
        )
        x += max(140, 12 * (len(ptr.name) + len(ptr.target)) + 40)

    out.append("</svg>")
    return "\n".join(out)


def render_animation_svg(frames: List[MemoryFrame], width: int = 640, height: int = 420, delay_ms: int = 1200) -> str:
    """SVG interactivo: un grupo por frame + navegación embebida.

    Sin JS se muestra el primer frame; con JS habilitado funcionan los
    botones ‹ › ▶ (auto-avance cada delay_ms).
    """
    p = _PALETTE
    n = len(frames)
    total_h = height + 46

    out: List[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}" '
        f'viewBox="0 0 {width} {total_h}" font-family="monospace">'
    )
    out.append(f"<title>Animación de memoria ({n} frames)</title>")
    out.append(f'<rect width="{width}" height="{total_h}" fill="{p["bg"]}"/>')

    for i, fr in enumerate(frames):
        display = "inline" if i == 0 else "none"
        inner = render_frame_svg(fr, width, height)
        # incrustar el frame como grupo interno quitando el wrapper <svg>
        body = inner.split(">", 1)[1].rsplit("</svg>", 1)[0]
        out.append(f'<g id="fr{i}" style="display:{display}">{body}</g>')

    # --- barra de controles ---
    bar_y = height + 8
    out.append(f'<rect x="10" y="{bar_y}" width="{width-20}" height="30" rx="6" fill="{p["panel"]}" stroke="{p["border"]}"/>')
    btn = lambda x, w, label, act: (
        f'<g style="cursor:pointer" onclick="{act}">'
        f'<rect x="{x}" y="{bar_y+4}" width="{w}" height="22" rx="4" fill="{p["border"]}"/>'
        f'<text x="{x+w//2}" y="{bar_y+19}" text-anchor="middle" fill="{p["text"]}" font-size="12">{label}</text></g>'
    )
    out.append(btn(18, 36, "‹", "show(frame_idx-1)"))
    out.append(btn(58, 36, "›", "show(frame_idx+1)"))
    out.append(btn(width - 118, 100, "▶ auto", "toggle_auto()"))
    out.append(
        f'<text id="counter" x="{width//2 - 20}" y="{bar_y+19}" text-anchor="middle" '
        f'fill="{p["dim"]}" font-size="12">1/{n}</text>'
    )

    out.append(f"""<script><![CDATA[
var frame_idx = 0;
var FRAMES = {n};
var DELAY = {delay_ms};
var timer = null;
function show(i) {{
  if (FRAMES === 0) return;
  frame_idx = Math.max(0, Math.min(FRAMES - 1, i));
  for (var k = 0; k < FRAMES; k++) {{
    document.getElementById('fr' + k).style.display = (k === frame_idx) ? 'inline' : 'none';
  }}
  document.getElementById('counter').textContent = (frame_idx + 1) + '/' + FRAMES;
}}
function toggle_auto() {{
  if (timer) {{ clearInterval(timer); timer = null; return; }}
  timer = setInterval(function () {{ show((frame_idx + 1) % FRAMES); }}, DELAY);
}}
document.addEventListener('keydown', function (e) {{
  if (e.key === 'ArrowRight') show(frame_idx + 1);
  if (e.key === 'ArrowLeft') show(frame_idx - 1);
}});
]]></script>""")

    out.append("</svg>")
    return "\n".join(out)


def export_gif(svg_paths: List[Path], output: Path, delay_cs: int = 120) -> tuple:
    """Convierte frames SVG a GIF usando ImageMagick `convert` (opcional).

    Devuelve (ok: bool, mensaje). Sin convert instalado, sugiere abrir el SVG.
    """
    convert_bin = shutil.which("convert")
    if not convert_bin:
        return False, "ImageMagick `convert` no disponible; el GIF requiere ImageMagick. El SVG interactivo no lo necesita."
    existing = [s for s in svg_paths if s.exists()]
    if not existing:
        return False, "No hay frames para convertir."
    try:
        proc = subprocess.run(
            [convert_bin, "-delay", str(delay_cs), "-loop", "0",
             *[str(s) for s in existing], str(output)],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"Fallo convirtiendo GIF: {e}"
    if proc.returncode != 0 or not output.exists():
        return False, f"convert falló: {proc.stderr[:200]}"
    return True, f"GIF generado: {output}"
