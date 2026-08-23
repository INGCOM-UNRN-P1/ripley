"""Static auditor for struct padding bytes sent to files or sockets without zero-initialization."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from ripley.core.linters import LinterObservation
from ripley.core.security import strip_c_comments_and_strings

# Tamaños y alineamientos LP64 (x86_64 / aarch64 Linux)
_TYPE_LAYOUT: Dict[str, Tuple[int, int]] = {
    "char": (1, 1),
    "signed char": (1, 1),
    "unsigned char": (1, 1),
    "short": (2, 2),
    "unsigned short": (2, 2),
    "int": (4, 4),
    "unsigned int": (4, 4),
    "long": (8, 8),
    "unsigned long": (8, 8),
    "long long": (8, 8),
    "unsigned long long": (8, 8),
    "float": (4, 4),
    "double": (8, 8),
}

_POINTER_SIZE = 8
_IO_FUNCTIONS = ("fwrite", "write", "send", "sendto")


@dataclass
class StructLayout:
    name: str
    total_size: int
    padding_bytes: int
    holes: List[Tuple[str, int]] = field(default_factory=list)  # (descripción, bytes)

    @property
    def has_padding(self) -> bool:
        return self.padding_bytes > 0


class StructPaddingAuditor:
    """Detecta estructuras con bytes de relleno (*padding*) que se envían a archivos,
    sockets o pipes sin haber sido inicializadas con memset/zero-init previo."""

    def _parse_field(self, raw: str) -> Optional[Tuple[str, str]]:
        """Devuelve (tipo_base, declarador) de un campo o None si no es computable."""
        raw = raw.strip()
        if not raw:
            return None
        m = re.match(
            r"^(?P<type>(?:const\s+|volatile\s+|unsigned\s+|signed\s+|long\s+)*[a-zA-Z_][a-zA-Z0-9_ \t]*?)"
            r"[\s*]+(?P<decl>[a-zA-Z_][a-zA-Z0-9_\[\]]*)$",
            raw.replace("\n", " "),
        )
        if not m:
            return None
        base_type = re.sub(r"\s+", " ", m.group("type")).strip()
        return base_type, m.group("decl")

    def _field_layout(self, base_type: str, decl: str) -> Optional[Tuple[int, int]]:
        """Tamaño y alineamiento del campo según tipo base y arreglo opcional."""
        array_match = re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\[(\d+)\])?$", decl)
        if not array_match:
            return None
        count = int(array_match.group(1)) if array_match.group(1) else 1
        if decl.endswith("*") or "*" in decl:
            return _POINTER_SIZE * count, _POINTER_SIZE
        layout = _TYPE_LAYOUT.get(base_type)
        if layout is None:
            return None
        size, align = layout
        return size * count, align

    def compute_struct_layout(self, struct_name: str, body: str) -> Optional[StructLayout]:
        """Calcula el layout C estándar (offsets, huecos y tamaño total) de un struct."""
        offset = 0
        max_align = 1
        padding = 0
        holes: List[Tuple[str, int]] = []

        for raw_field in body.split(";"):
            parsed = self._parse_field(raw_field)
            if parsed is None:
                continue
            base_type, decl = parsed
            field_layout = self._field_layout(base_type, decl)
            if field_layout is None:
                return None  # Tipo desconocido (typedef anidado): layout no confiable.
            size, align = field_layout
            aligned_offset = (offset + align - 1) // align * align
            gap = aligned_offset - offset
            if gap > 0:
                padding += gap
                holes.append((f"hueco antes de `{decl.strip()}`", gap))
            offset = aligned_offset + size
            max_align = max(max_align, align)

        final_pad = (max_align - offset % max_align) % max_align
        if final_pad > 0:
            padding += final_pad
            holes.append(("relleno final de la estructura", final_pad))

        return StructLayout(
            name=struct_name,
            total_size=offset + final_pad,
            padding_bytes=padding,
            holes=holes,
        )

    def _extract_struct_layouts(self, clean: str) -> Dict[str, StructLayout]:
        layouts: Dict[str, StructLayout] = {}
        struct_regex = re.compile(r"\bstruct\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\{(?P<body>[^}]*)\}\s*;", re.DOTALL)
        for m in struct_regex.finditer(clean):
            layout = self.compute_struct_layout(m.group("name"), m.group("body"))
            if layout is not None:
                layouts[m.group("name")] = layout
        return layouts

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        layouts = self._extract_struct_layouts(clean)

        padded_structs = {name for name, lay in layouts.items() if lay.has_padding}
        if not padded_structs:
            return observations

        # Variables locales instanciadas de structs con padding.
        instance_types: Dict[str, str] = {}
        for name in sorted(padded_structs):
            for m in re.finditer(rf"\bstruct\s+{name}\s+(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<init>[^;]*);", clean):
                var = m.group("var")
                init = m.group("init")
                is_zero_init = bool(re.search(r"=\s*\{\s*(0|\.\w+\s*=)", init)) or "= {}" in init
                if not is_zero_init:
                    instance_types[var] = name

        if not instance_types:
            return observations

        lines = clean.splitlines()
        io_regex = re.compile(rf"\b(?P<fn>{'|'.join(_IO_FUNCTIONS)})\s*\(")

        zero_initialized: set = set()
        for line_idx, line in enumerate(lines):
            # Registrar memset/zero-init explícito sobre cualquier instancia conocida.
            for var in instance_types:
                if re.search(rf"\bmemset\s*\(\s*&\s*{var}\b[^;]*,\s*0\s*,", line) or re.search(
                    rf"\b{var}\s*=\s*\(", line
                ):
                    zero_initialized.add(var)

            match = io_regex.search(line)
            if not match:
                continue
            call_args = line[match.end() :].split(";")[0]
            for var, struct_name in instance_types.items():
                if not re.search(rf"&?\b{var}\b", call_args):
                    continue
                if var in zero_initialized or line[: match.start()].count("memset"):
                    continue
                layout = layouts[struct_name]
                observations.append(
                    LinterObservation(
                        linter_name="struct_padding_leak",
                        filename=filename,
                        line=line_idx + 1,
                        severity="ADVERTENCIA",
                        message=(
                            f"`{struct_name} {var}` ({layout.total_size} B, {layout.padding_bytes} B de padding) "
                            f"se envía vía `{match.group('fn')}()` sin inicialización previa garantizada."
                        ),
                        suggestion=(
                            "Los bytes de relleno contienen datos indeterminados que pueden filtrar "
                            "información o romper la reproducibilidad. Usá `memset(&"
                            + var
                            + ", 0, sizeof("
                            + var
                            + "))` antes de poblar los campos, o reordená los campos para minimizar el padding."
                        ),
                    )
                )

        return observations
