"""Dynamic memory and data structure visualizer for C structs, linked lists, and trees."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from ripley.security import strip_c_comments_and_strings


@dataclass
class StructField:
    field_type: str
    field_name: str
    is_pointer: bool


@dataclass
class StructDefinition:
    name: str
    fields: List[StructField]


class DynamicMemoryVisualizer:
    """Extrae definiciones de estructuras en C y genera diagramas Graphviz DOT / Mermaid de su topología."""

    def extract_structs(self, code: str) -> Dict[str, StructDefinition]:
        clean = strip_c_comments_and_strings(code)
        struct_regex = re.compile(
            r"struct\s+(?P<name>[a-zA-Z0-9_]+)\s*\{(?P<body>[^}]+)\}",
            re.MULTILINE,
        )

        structs: Dict[str, StructDefinition] = {}

        for m in struct_regex.finditer(clean):
            sname = m.group("name")
            sbody = m.group("body")
            fields: List[StructField] = []

            for raw_field in sbody.split(";"):
                f = raw_field.strip()
                if not f:
                    continue
                is_ptr = "*" in f
                f_parts = f.replace("*", "").split()
                if len(f_parts) >= 2:
                    ftype = f_parts[0]
                    fname = f_parts[-1]
                    fields.append(StructField(field_type=ftype, field_name=fname, is_pointer=is_ptr))

            structs[sname] = StructDefinition(name=sname, fields=fields)

        return structs

    def to_dot(self, structs: Dict[str, StructDefinition]) -> str:
        """Genera diagrama Graphviz DOT con formato de registros estructurados."""
        lines = [
            "digraph DataStructures {",
            '    rankdir=LR;',
            '    node [shape=record, fontname="Arial", fontsize=10];',
            "",
        ]

        for sname, sdef in structs.items():
            # Crear etiqueta record
            field_labels = []
            for f in sdef.fields:
                ptr_str = "*" if f.is_pointer else ""
                field_labels.append(f"<{f.field_name}> {f.field_type}{ptr_str} {f.field_name}")

            record_label = f"{{ <_title> struct {sname} | {' | '.join(field_labels)} }}"
            lines.append(f'    node_{sname} [label="{record_label}"];')

            # Aristas para campos autorreferenciales
            for f in sdef.fields:
                if f.is_pointer and (sname in f.field_type or f.field_type in ("void", "struct")):
                    lines.append(f'    node_{sname}:{f.field_name} -> node_{sname}:_title [label="puntero"];')

        lines.append("}\n")
        return "\n".join(lines)

    def to_mermaid(self, structs: Dict[str, StructDefinition]) -> str:
        """Genera diagrama de clases en Mermaid."""
        lines = ["classDiagram", "    %% Topología de Estructuras Dinámicas en Memoria"]

        for sname, sdef in structs.items():
            lines.append(f"    class {sname} {{")
            for f in sdef.fields:
                ptr_str = "*" if f.is_pointer else ""
                lines.append(f"        +{f.field_type}{ptr_str} {f.field_name}")
            lines.append("    }")

            for f in sdef.fields:
                if f.is_pointer and sname in f.field_type:
                    lines.append(f"    {sname} --> {sname} : {f.field_name}")

        return "\n".join(lines)

    def generate_diagram(
        self,
        c_file: Path | str,
        output_format: str = "mermaid",
    ) -> str:
        path = Path(c_file)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        code = path.read_text(encoding="utf-8", errors="replace")
        structs = self.extract_structs(code)

        if output_format == "mermaid":
            return self.to_mermaid(structs)
        return self.to_dot(structs)
