"""Accessible visual glossary of low-level C concepts (pure-Python SVG + self-contained HTML).

Accesibilidad incorporada al formato, no como agregado:
  - Temas de alto contraste y paleta segura para daltonismo (Okabe-Ito).
  - Escala tipográfica ampliada opcional para baja visión.
  - Cada diagrama declara ``role="img"`` con ``<title>`` y ``<desc>`` que los
    lectores de pantalla leen; la descripción larga también se muestra como
    texto visible bajo cada figura.
  - HTML autocontenido sin recursos externos ni JavaScript obligatorio.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple
import html

# ---------------------------------------------------------------------------
# Temas
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GlossaryTheme:
    name: str
    bg: str
    panel: str
    border: str
    text: str
    dim: str
    accent: str
    ok: str
    warn: str
    err: str
    stroke_width: float = 1.4
    font_scale: float = 1.0

    def fs(self, base: float) -> int:
        """Tamaño de fuente escalado, redondeado."""
        return round(base * self.font_scale)


THEMES: Dict[str, GlossaryTheme] = {
    "dark": GlossaryTheme("dark", "#10141c", "#1b2230", "#3b4a63", "#e8edf5",
                          "#8ea0bd", "#4fc3f7", "#66bb6a", "#ffb300", "#ef5350"),
    "light": GlossaryTheme("light", "#ffffff", "#f5f7fa", "#94a3b8", "#0f172a",
                           "#64748b", "#0369a1", "#15803d", "#b45309", "#dc2626"),
    "high-contrast": GlossaryTheme("high-contrast", "#000000", "#000000", "#ffffff",
                                   "#ffffff", "#e0e0e0", "#ffff00", "#00ff00",
                                   "#ffcc00", "#ff5555", stroke_width=2.4),
    "colorblind": GlossaryTheme("colorblind", "#ffffff", "#f2f2f2", "#666666",
                                "#000000", "#444444", "#0072b2", "#009e73",
                                "#e69f00", "#d55e00"),
}


def get_theme(name: str = "light", large_text: bool = False) -> GlossaryTheme:
    if name not in THEMES:
        raise KeyError(f"Tema desconocido: {name!r}. Opciones: {', '.join(THEMES)}")
    base = THEMES[name]
    if large_text:
        return GlossaryTheme(**{**base.__dict__, "font_scale": 1.35})
    return base


# ---------------------------------------------------------------------------
# Primitivas de dibujo
# ---------------------------------------------------------------------------
class _Canvas:
    def __init__(self, theme: GlossaryTheme) -> None:
        self.t = theme
        self.parts: List[str] = []

    def rect(self, x, y, w, h, fill=None, stroke=None, rx=6, dashed=False, sw=None, opacity=None):
        stroke = stroke or self.t.border
        dash = ' stroke-dasharray="6,4"' if dashed else ""
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill or self.t.panel}" stroke="{stroke}" '
            f'stroke-width="{sw or self.t.stroke_width}"{dash}{op}/>'
        )

    def text(self, x, y, s, size=13, fill=None, anchor="start", bold=False):
        weight = ' font-weight="bold"' if bold else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" fill="{fill or self.t.text}" font-size="{self.t.fs(size)}" '
            f'text-anchor="{anchor}"{weight}>{_e(s)}</text>'
        )

    def arrow(self, x1, y1, x2, y2, color=None, dashed=False, label=None):
        color = color or self.t.accent
        dash = ' stroke-dasharray="6,4"' if dashed else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{self.t.stroke_width + 0.6}"{dash} marker-end="url(#garrow)"/>'
        )
        if label:
            self.text((x1 + x2) // 2, min(y1, y2) - 6, label, size=11, fill=color, anchor="middle")

    def cross(self, cx, cy, size=9, color=None):
        color = color or self.t.err
        self.parts.append(
            f'<line x1="{cx-size}" y1="{cy-size}" x2="{cx+size}" y2="{cy+size}" stroke="{color}" stroke-width="2.4"/>'
            f'<line x1="{cx-size}" y1="{cy+size}" x2="{cx+size}" y2="{cy-size}" stroke="{color}" stroke-width="2.4"/>'
        )


def _e(text: str) -> str:
    return html.escape(str(text), quote=True)


def _wrap(concept_id: str, theme: GlossaryTheme, title: str, desc: str,
          inner: List[str], w: int = 640, h: int = 380) -> str:
    uid = _e(concept_id)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" '
        f'role="img" aria-labelledby="t-{uid} d-{uid}" preserveAspectRatio="xMidYMid meet">'
        f'<defs><marker id="garrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{theme.accent}"/></marker></defs>'
        f'<title id="t-{uid}">{_e(title)}</title>'
        f'<desc id="d-{uid}">{_e(desc)}</desc>'
        + "".join(inner) + "</svg>"
    )


def _frame(theme: GlossaryTheme, c: _Canvas, W=640, H=380):
    c.parts.append(f'<rect width="{W}" height="{H}" fill="{theme.bg}"/>')


# ---------------------------------------------------------------------------
# Constructores de diagramas (uno por concepto)
# ---------------------------------------------------------------------------
def _draw_memoria_map(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    segs = [
        (".text  (código)", 60, t.panel),
        (".rodata (literales, solo lectura)", 105, t.warn),
        (".data  (globales inicializadas)", 150, t.panel),
        (".bss   (globales sin valor inicial)", 195, t.panel),
        ("heap ↑ crece hacia arriba", 260, t.ok),
        ("...", 330, None),
        ("stack ↓ crece hacia abajo", 300, t.accent),
    ]
    x, w, hgt = 200, 240, 34
    ys = {"heap": 250}
    c.rect(x, 50, w, 30, fill=t.panel); c.text(x + w / 2, 70, ".text — código", anchor="middle")
    c.rect(x, 90, w, 30, fill=t.panel, dashed=False); c.text(x + w / 2, 110, ".rodata — literales (solo lectura)", anchor="middle", fill=t.warn)
    c.rect(x, 130, w, 30, fill=t.panel); c.text(x + w / 2, 150, ".data — globales inici.", anchor="middle")
    c.rect(x, 170, w, 30, fill=t.panel); c.text(x + w / 2, 190, ".bss — globales sin inicio.", anchor="middle")
    c.rect(x, 230, w, 60, fill=t.ok, opacity=0.18, stroke=t.ok); c.text(x + w / 2, 265, "HEAP (malloc/free)", anchor="middle", fill=t.ok)
    c.arrow(x - 20, 290, x - 20, 235, color=t.ok, label="crece ↓ addr alta")
    c.rect(x, 310, w, 50, fill=t.accent, opacity=0.18, stroke=t.accent); c.text(x + w / 2, 340, "STACK (locales, llamadas)", anchor="middle", fill=t.accent)
    c.arrow(x + w + 20, 315, x + w + 20, 355, color=t.accent, label=None)
    c.text(x + w + 24, 336, "crece", size=11, fill=t.accent)
    return _wrap("memoria-map", t, "Mapa de memoria de un proceso C",
                 "Columna con cinco segmentos apilados: código, literales de solo lectura, "
                 "datos inicializados, datos sin valor inicial, montículo que crece hacia direcciones altas "
                 "y pila que crece hacia direcciones bajas.", c.parts)


def _draw_puntero(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.rect(70, 140, 160, 64); c.text(150, 165, "int *p", anchor="middle", bold=True)
    c.text(150, 188, "valor: 0x7ffd…40", anchor="middle", fill=t.dim)
    c.rect(400, 130, 150, 84, stroke=t.accent); c.text(475, 155, "int x = 42", anchor="middle", bold=True)
    c.text(475, 180, "@ 0x7ffd…40", anchor="middle", fill=t.dim)
    c.arrow(236, 172, 394, 172, label="contiene la DIRECCIÓN de x")
    c.text(320, 320, "*p es lo mismo que x · &x da su dirección", anchor="middle", size=12, fill=t.dim)
    return _wrap("puntero", t, "Puntero: variable que guarda una dirección de memoria",
                 "Caja del puntero p con una dirección adentro; flecha desde esa caja hasta la caja de la "
                 "variable entera x ubicada en esa dirección. Desreferenciar con asterisco equivale a usar x.",
                 c.parts)


def _draw_stack_frames(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.rect(80, 60, 220, 70, stroke=t.accent); c.text(190, 88, "main()", anchor="middle", bold=True)
    c.text(190, 112, "argc, argv", anchor="middle", fill=t.dim)
    c.rect(80, 145, 220, 70, stroke=t.ok); c.text(190, 173, "suma(a,b)", anchor="middle", bold=True)
    c.text(190, 197, "a=2  b=3  retorno 5", anchor="middle", fill=t.dim)
    c.rect(80, 230, 220, 56, fill=t.panel, dashed=True); c.text(190, 262, "(próxima llamada)", anchor="middle", fill=t.dim)
    c.arrow(350, 270, 350, 70, color=t.dim)
    c.text(365, 175, "la pila apila un MARCO", size=13, bold=True)
    c.text(365, 198, "por cada llamada:", size=12, fill=t.dim)
    c.text(365, 222, "· parámetros y locales nuevos", size=12, fill=t.dim)
    c.text(365, 244, "· dirección de retorno", size=12, fill=t.dim)
    c.text(365, 266, "al volver, el marco desaparece", size=12, fill=t.warn)
    return _wrap("stack-frames", t, "Stack: marcos de llamada apilados",
                 "Tres cajas apiladas representan los marcos de main, suma y un espacio libre. Cada llamada "
                 "apila parámetros, variables locales y dirección de retorno; al terminar la función su marco se descarta.",
                 c.parts)


def _draw_heap(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.text(320, 40, "región del heap", anchor="middle", fill=t.ok, bold=True)
    bloques = [(60, 120, "nodo A", True), (200, 80, "libre", False),
               (300, 160, "nodo B", True), (480, 100, "nuevo malloc(96)", True)]
    for x, w, lbl, vivo in bloques:
        color = t.err if lbl == "libre" else t.ok
        c.rect(x, 90, w, 60, stroke=color, dashed=(not vivo), opacity=None if vivo else 0.25)
        c.text(x + w / 2, 125, lbl, anchor="middle", fill=color)
    c.text(240, 205, "free(nodo A) deja un hueco…", anchor="middle", fill=t.err)
    c.arrow(520, 210, 245, 95, color=t.warn, dashed=True, label=None)
    c.text(320, 245, "…el asignador puede reutilizar ese hueco para otro malloc", anchor="middle", fill=t.warn)
    c.text(320, 300, "Si nunca llamás free, el bloque vive hasta que termina el programa: fuga.", anchor="middle", size=12)
    return _wrap("heap", t, "Heap: región de asignación dinámica",
                 "Fila de bloques: dos nodos vivos, un hueco libre marcado en rojo tras un free y un nuevo "
                 "malloc que puede reutilizar ese hueco. Bloques sin free persisten hasta el fin del programa.",
                 c.parts)


def _draw_null(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.rect(80, 150, 150, 60); c.text(155, 185, "int *p = NULL", anchor="middle")
    c.line_parts = getattr(c, "line_parts", [])
    c.arrow(236, 180, 420, 180, color=t.dim, label="no apunta a NADA válido")
    # símbolo de tierra
    for i, wdt in enumerate((70, 46, 22)):
        y = 196 + i * 12
        c.parts.append(f'<line x1="{430 - wdt//2}" y1="{y}" x2="{430 + wdt//2}" y2="{y}" stroke="{t.dim}" stroke-width="3"/>')
    c.text(320, 280, "Desreferenciar NULL (*p) crashea con SIGSEGV.", anchor="middle", fill=t.err, bold=True)
    c.text(320, 308, "Convención: validar `if (p != NULL)` antes de usarlo.", anchor="middle")
    return _wrap("puntero-null", t, "Puntero NULL: ausencia deliberada de destino",
                 "Caja del puntero p con flecha que cae a un símbolo de tierra: no apunta a ningún objeto. "
                 "Desreferenciarlo produce fallo de segmentación; conviene validarlo antes de usar.",
                 c.parts)


def _draw_dangling(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.rect(80, 140, 150, 60); c.text(155, 175, "int *p", anchor="middle")
    c.rect(400, 130, 170, 80, stroke=t.err, dashed=True)
    c.text(485, 158, "bloque liberado", anchor="middle", fill=t.err)
    c.text(485, 182, "(free ya fue llamado)", anchor="middle", fill=t.err, size=11)
    c.arrow(236, 170, 394, 170, color=t.err, dashed=True, label="¡sigue apuntando!")
    c.text(320, 275, "Usar *p después del free es comportamiento INDEFINIDO.", anchor="middle", fill=t.err, bold=True)
    c.text(320, 303, "Solución: p = NULL justo después de free(p).", anchor="middle", fill=t.ok)
    return _wrap("dangling-pointer", t, "Puntero colgante (dangling pointer)",
                 "Caja del puntero p con flecha discontinua roja hacia un bloque tachado ya liberado. "
                 "Leer o escribir a través de él es indefinido; la corrección es anular el puntero tras liberar.",
                 c.parts)


def _draw_leak(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.rect(430, 130, 160, 80, stroke=t.err); c.text(510, 175, "bloque vivo", anchor="middle", fill=t.err)
    c.rect(80, 150, 150, 60); c.text(155, 178, "sin referencias", anchor="middle", fill=t.dim)
    c.cross(305, 180)
    c.text(320, 150, "(se perdió el último puntero)", anchor="middle", fill=t.dim, size=11)
    c.text(320, 285, "El bloque sigue ocupando memoria pero ya nadie puede liberarlo: FUGA.", anchor="middle", fill=t.err, bold=True)
    c.text(320, 313, "Valgrind lo reporta como \"definitely lost\".", anchor="middle", fill=t.dim)
    return _wrap("memory-leak", t, "Fuga de memoria (memory leak)",
                 "Bloque reservado a la derecha sin ninguna flecha entrante porque se perdió el puntero: "
                 "queda inaccesible pero ocupado hasta el fin del programa. Valgrind lo clasifica como definitivamente perdido.",
                 c.parts)


def _draw_double_free(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.rect(430, 130, 170, 80, stroke=t.err, dashed=True); c.text(515, 175, "ya liberado", anchor="middle", fill=t.err)
    c.rect(70, 120, 140, 50); c.text(140, 150, "free(p) 1ª vez", anchor="middle", fill=t.ok)
    c.rect(70, 200, 140, 50); c.text(140, 230, "free(p) 2ª vez", anchor="middle", fill=t.err)
    c.arrow(215, 145, 424, 155, color=t.ok)
    c.arrow(215, 225, 424, 190, color=t.err, dashed=True)
    c.text(320, 300, "Liberar dos veces corrompe las estructuras del asignador: crash o exploits.", anchor="middle", fill=t.err, bold=True)
    return _wrap("double-free", t, "Double free: liberar el mismo bloque dos veces",
                 "Dos cajas de llamada free apuntan al mismo bloque ya liberado. La segunda libera memoria "
                 "que el asignador cree disponible y corrompe sus metadatos.",
                 c.parts)


def _draw_overflow(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.text(320, 45, "int v[4];   índices válidos: 0..3", anchor="middle", bold=True)
    for i in range(4):
        x = 140 + i * 80
        c.rect(x, 80, 76, 54, stroke=t.ok)
        c.text(x + 38, 112, f"v[{i}]", anchor="middle")
    for i in (4, 5):
        x = 140 + i * 80
        c.rect(x, 80, 76, 54, stroke=t.err, dashed=True)
        c.text(x + 38, 112, f"¿v[{i}]?", anchor="middle", fill=t.err)
    c.arrow(560, 200, 545, 140, color=t.err, label="escritura fuera")
    c.rect(500, 210, 120, 40, stroke=t.warn); c.text(560, 235, "memoria ajena", anchor="middle", fill=t.warn)
    c.text(320, 300, "Escribir más allá del arreglo pisa datos de otras variables: undefined behavior.", anchor="middle", fill=t.err)
    return _wrap("buffer-overflow", t, "Buffer overflow: escribir fuera de los límites del arreglo",
                 "Cuatro casillas válidas del arreglo v y dos casillas fantasma fuera de rango resaltadas en rojo; "
                 "una flecha de escritura excedida pisa memoria contigua de otras variables.",
                 c.parts)


def _draw_padding(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.text(320, 45, "struct Ejemplo { char c; int i; };", anchor="middle", bold=True)
    c.rect(120, 90, 60, 60, stroke=t.ok); c.text(150, 125, "c (1B)", anchor="middle")
    c.rect(180, 90, 120, 60, fill=t.warn, opacity=0.25, stroke=t.warn, dashed=True)
    c.text(240, 125, "padding (3B)", anchor="middle", fill=t.warn)
    c.rect(300, 90, 180, 60, stroke=t.ok); c.text(390, 125, "i (4B)", anchor="middle")
    c.text(320, 200, "sizeof(struct Ejemplo) = 8, no 5: el compilador ALINEA campos.", anchor="middle")
    c.text(320, 232, "Al enviar structs a archivos/red, el padding contiene basura → memset antes.", anchor="middle", fill=t.warn)
    c.text(320, 264, "Reordenar campos (mayor a menor alineación) reduce relleno.", anchor="middle", fill=t.dim)
    return _wrap("struct-padding", t, "Padding de estructuras: bytes de relleno por alineación",
                 "Estructura dibujada como tres casillas contiguas: campo char, hueco rayado de tres bytes "
                 "de relleno y campo int. El tamaño total es ocho porque los enteros se alinean a múltiplos de cuatro.",
                 c.parts)


def _draw_endianness(t: GlossaryTheme) -> str:
    c = _Canvas(t)
    _frame(t, c)
    c.text(320, 45, "unsigned int x = 0x12345678;", anchor="middle", bold=True)
    # little endian
    c.text(160, 85, "little-endian (x86_64, ARM64):", fill=t.accent)
    for i, byte in enumerate(("78", "56", "34", "12")):
        c.rect(120 + i * 90, 100, 80, 50, stroke=t.accent)
        c.text(160 + i * 90, 130, byte, anchor="middle")
        c.text(160 + i * 90, 168, f"+{i}", anchor="middle", fill=t.dim)
    c.text(160, 210, "big-endian (MIPS clásico, red):", fill=t.warn)
    for i, byte in enumerate(("12", "34", "56", "78")):
        c.rect(120 + i * 90, 225, 80, 50, stroke=t.warn)
        c.text(160 + i * 90, 255, byte, anchor="middle")
        c.text(160 + i * 90, 293, f"+{i}", anchor="middle", fill=t.dim)
    c.text(320, 335, "El orden de bytes cambia entre arquitecturas: cuidado al volcar binarios o sockets.", anchor="middle", size=12)
    return _wrap("endianness", t, "Endianness: orden de bytes de un número multibyte",
                 "Valor hexadecimal 12345678 mostrado como cuatro bytes. Arriba, little-endian guarda primero "
                 "el byte menos significativo; abajo, big-endian guarda primero el más significativo.",
                 c.parts)


# ---------------------------------------------------------------------------
# Catálogo de conceptos
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GlossaryEntry:
    concept_id: str
    title: str
    summary: str
    long_description: str
    keywords: Tuple[str, ...]
    related: Tuple[str, ...]
    draw: Callable[[GlossaryTheme], str]


ENTRIES: List[GlossaryEntry] = [
    GlossaryEntry("memoria-map", "Mapa de memoria de un proceso",
                  "Un programa C vive en cinco regiones: código, literales, globales, heap y stack.",
                  "Segmentos .text con las instrucciones, .rodata con cadenas constantes de solo lectura, "
                  ".data y .bss con variables globales, el heap que crece hacia direcciones altas donde vive "
                  "todo lo pedido con malloc, y el stack que crece hacia direcciones bajas con los marcos de "
                  "cada función en ejecución.",
                  ("proceso", "segmentos", "heap", "stack"), ("heap", "stack-frames"), _draw_memoria_map),
    GlossaryEntry("puntero", "Puntero", "Variable cuyo valor es la dirección de otra cosa en memoria.",
                  "Un puntero ocupa espacio propio y contiene una dirección. Con *p se accede al objeto "
                  "apuntado y con &x se obtiene la dirección de x. Es la base de arreglos dinámicos, "
                  "estructuras enlazadas y paso por referencia.",
                  ("dirección", "desreferencia", "ampersand"), ("puntero-null", "dangling-pointer"), _draw_puntero),
    GlossaryEntry("stack-frames", "Marcos del Stack", "Cada llamada a función reserva un marco nuevo en la pila.",
                  "El marco guarda parámetros, variables locales y la dirección de retorno. Los marcos se "
                  "apilan en orden de llamada y se descartan al volver: por eso las locales no conservan valor "
                  "entre invocaciones y retornar su dirección es inválido.",
                  ("pila", "llamada", "marco", "retorno"), ("memoria-map", "recursion" ), _draw_stack_frames),
    GlossaryEntry("heap", "Heap y malloc/free", "Memoria pedida en tiempo de ejecución que vive hasta el free.",
                  "malloc reserva un bloque del tamaño pedido y devuelve su dirección; free lo devuelve al "
                  "asignador. El asignador reutiliza huecos dejados por frees previos. Todo malloc debe tener "
                  "exactamente un free correspondiente.",
                  ("malloc", "free", "dinámica", "asignador"), ("memory-leak", "double-free"), _draw_heap),
    GlossaryEntry("puntero-null", "Puntero NULL", "NULL significa explícitamente «esto no apunta a nada».",
                  "Es la dirección cero y sirve para señalar ausencia de dato o fin de estructuras enlazadas. "
                  "Desreferenciarlo lanza SIGSEGV inmediato, así que se valida antes de usar.",
                  ("null", "sigsegv", "validación"), ("puntero", "dangling-pointer"), _draw_null),
    GlossaryEntry("dangling-pointer", "Puntero colgante", "Puntero que sigue apuntando a memoria ya liberada.",
                  "Tras free(p) el bloque puede ser reutilizado por otra parte del programa; usar p entonces lee "
                  "o escribe memoria ajena de forma indefinida. La práctica segura es p = NULL después de cada free.",
                  ("use-after-free", "free", "indefinido"), ("heap", "puntero-null"), _draw_dangling),
    GlossaryEntry("memory-leak", "Fuga de memoria", "Memoria reservada que quedó sin dueño y sin free.",
                  "Ocurre cuando se pierde el último puntero a un bloque vivo. El programa sigue consumiendo "
                  "esa memoria hasta terminar; en procesos largos agota el sistema. Valgrind la detecta como "
                  "\"definitely lost\".",
                  ("fuga", "leak", "valgrind"), ("heap", "dangling-pointer"), _draw_leak),
    GlossaryEntry("double-free", "Double Free", "Llamar free dos veces sobre el mismo bloque.",
                  "La segunda liberación corrompe los metadatos internos del asignador, produciendo crashes "
                  "aleatorios o vulnerabilities explotables. Suele evitarse con el patrón free + NULL.",
                  ("free", "corrupción"), ("heap", "dangling-pointer"), _draw_double_free),
    GlossaryEntry("buffer-overflow", "Desborde de Buffer", "Escribir o leer fuera de los límites de un arreglo.",
                  "Los arreglos en C no controlan índices. Acceder más allá del final pisa memoria contigua "
                  "(otras variables o metadatos del heap): comportamiento indefinido, fuente clásica de bugs "
                  "y vulnerabilidades de seguridad.",
                  ("arreglo", "límites", "seguridad"), ("heap", "puntero"), _draw_overflow),
    GlossaryEntry("struct-padding", "Padding de Estructuras", "Bytes invisibles que el compilador agrega para alinear campos.",
                  "Cada tipo se coloca en direcciones múltiplos de su tamaño: entre un char y un int pueden "
                  "quedar tres bytes de relleno. Afecta sizeof, comparaciones memcmp y volcados a archivos o red.",
                  ("struct", "alineación", "sizeof"), ("endianness", "heap"), _draw_padding),
    GlossaryEntry("endianness", "Endianness", "Orden en que se guardan los bytes de un número de varios bytes.",
                  "Little-endian (x86_64, ARM64) pone primero el byte menos significativo; big-endian (MIPS, "
                  "formatos de red) el más significativo. Volcar structs crudos entre máquinas distintas puede "
                  "intercambiar los valores si no se acuerda el orden.",
                  ("bytes", "orden", "red"), ("struct-padding", "memoria-map"), _draw_endianness),
]

_BY_ID: Dict[str, GlossaryEntry] = {e.concept_id: e for e in ENTRIES}


def list_concepts() -> List[GlossaryEntry]:
    return list(ENTRIES)


def get_entry(concept_id: str) -> GlossaryEntry:
    if concept_id not in _BY_ID:
        raise KeyError(f"Concepto inexistente: {concept_id!r}")
    return _BY_ID[concept_id]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render_entry_svg(entry: GlossaryEntry, theme: GlossaryTheme) -> str:
    return entry.draw(theme)


def render_glossary_html(
    concept_ids: List[str],
    theme: GlossaryTheme,
    title: str = "Glosario Visual de Conceptos de Bajo Nivel — Ripley",
) -> str:
    """Documento único autocontenido: navegación, figuras SVG y descripciones visibles."""
    e = _e

    def css_vars(th: GlossaryTheme) -> str:
        return (
            f"--bg:{th.bg};--panel:{th.panel};--border:{th.border};--text:{th.text};"
            f"--dim:{th.dim};--accent:{th.accent};--ok:{th.ok};--warn:{th.warn};--err:{th.err};"
            f"--sw:{th.stroke_width}px;"
        )

    selected = [get_entry(cid) for cid in concept_ids]
    toc_items = "".join(
        f'<li><a href="#c-{e(entry.concept_id)}">{e(entry.title)}</a></li>'
        for entry in selected
    )

    sections: List[str] = []
    for entry in selected:
        svg = render_entry_svg(entry, theme)
        related = ""
        if entry.related:
            links = []
            for rid in entry.related:
                if rid in _BY_ID:
                    links.append(f'<a href="#c-{e(rid)}">{e(_BY_ID[rid].title)}</a>')
                elif rid == "recursion":
                    links.append('<span class="dim">recursión (ver stack)</span>')
            if links:
                related = (
                    '<p class="related"><strong>Conceptos relacionados:</strong> '
                    + " · ".join(links) + "</p>"
                )
        sections.append(
            f'<section id="c-{e(entry.concept_id)}" aria-labelledby="h-{e(entry.concept_id)}">'
            f'<h2 id="h-{e(entry.concept_id)}">{e(entry.title)}</h2>'
            f'<p class="summary">{e(entry.summary)}</p>'
            f'<figure>{svg}'
            f'<figcaption><strong>Descripción accesible:</strong> {e(entry.long_description)}</figcaption>'
            f'</figure>{related}'
            f'<p class="keywords"><span class="chipset">{"</span> <span class=\"chip\">".join(e(k) for k in entry.keywords)}</span></p>'
            f'</section>'
        )

    th = theme
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<style>
:root {{{css_vars(th)}}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text);
       font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
       font-size: calc(16px * {th.font_scale}); line-height: 1.55; }}
.skip {{ position:absolute; left:-9999px; }}
.skip:focus {{ left: 8px; top: 8px; background: var(--accent); color: var(--bg);
              padding: 8px 14px; z-index: 10; }}
header {{ padding: 24px 32px 8px; }}
header p {{ color: var(--dim); margin-top: 4px; }}
nav[aria-label="Índice"] {{ padding: 8px 32px 24px; }}
nav ul {{ columns: 2; gap: 24px; margin: 8px 0 0; padding-left: 18px; }}
a {{ color: var(--accent); }}
a:focus {{ outline: 3px solid var(--warn); outline-offset: 2px; }}
main {{ max-width: 900px; margin: 0 auto; padding: 0 32px 64px; }}
section {{ background: var(--panel); border: var(--sw) solid var(--border);
          border-radius: 12px; margin: 32px 0; padding: 8px 28px 20px; scroll-margin-top: 16px; }}
figure {{ margin: 12px 0 0; }}
figure svg {{ width: 100%; height: auto; display: block; border-radius: 8px; }}
figcaption {{ color: var(--text); font-style: italic; padding-top: 10px;
             border-top: 1px dashed var(--border); margin-top: 10px; }}
.summary {{ font-size: 1.05em; }}
.related a, .chip {{ background: var(--bg); border: 1px solid var(--border);
                    border-radius: 999px; padding: 2px 10px; text-decoration: none; }}
.chip {{ color: var(--dim); font-size: 0.85em; }}
.keywords {{ margin-top: 14px; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
@media print {{ body {{ background:#fff; }} }}
</style>
</head>
<body>
<a class="skip" href="#contenido">Saltar al contenido</a>
<header>
<h1>{e(title)}</h1>
<p>Tema visual: {e(th.name)} · escala ×{th.font_scale:g} · generado por Ripley. Cada figura incluye
título y descripción accesibles para lectores de pantalla.</p>
</header>
<nav aria-label="Índice"><h2 class="visually-hidden" style="position:absolute;left:-9999px">Índice</h2>
<ul>{toc_items}</ul>
</nav>
<main id="contenido">
{''.join(sections)}
</main>
<footer style="max-width:900px;margin:0 auto;padding:0 32px 48px;color:var(--dim)">
Generado localmente por ripley-check glossary — sin recursos externos ni seguimiento.
</footer>
</body>
</html>"""
