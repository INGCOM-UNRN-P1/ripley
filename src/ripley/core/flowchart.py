"""Traditional flowchart generator from C code using standard ANSI/ISO shapes."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from ripley.core.security import strip_c_comments_and_strings
from ripley.core.semantic_diff import CFunctionAST, extract_c_functions


class FlowNodeType(str, Enum):
    TERMINAL = "TERMINAL"  # Óvalo / Píldora: Inicio, Fin
    INPUT = "INPUT"  # Paralelogramo: Lectura de datos (scanf, getchar, fgets)
    OUTPUT = "OUTPUT"  # Paralelogramo invertido: Salida de datos (printf, puts, putchar)
    PROCESS = "PROCESS"  # Rectángulo: Asignación, cálculo, declaración
    DECISION = "DECISION"  # Rombo: if, while, for


@dataclass
class FlowNode:
    node_id: str
    node_type: FlowNodeType
    label: str
    edges: List[Tuple[str, Optional[str]]] = field(default_factory=list)  # (target_id, label)


class FlowchartBuilder:
    """Construye un grafo de flujo estructurado a partir del código de una función C."""

    def __init__(self, func_name: str) -> None:
        self.func_name = func_name
        self.nodes: Dict[str, FlowNode] = {}
        self._node_counter = 0

    def _next_id(self, prefix: str = "node") -> str:
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def add_node(self, node_type: FlowNodeType, label: str, prefix: str = "node") -> str:
        nid = self._next_id(prefix)
        # Sanitizar label para Mermaid
        clean_label = label.replace('"', "'").replace("\n", " ").strip()
        self.nodes[nid] = FlowNode(node_id=nid, node_type=node_type, label=clean_label)
        return nid

    def add_edge(self, from_id: str, to_id: str, label: Optional[str] = None) -> None:
        if from_id in self.nodes:
            self.nodes[from_id].edges.append((to_id, label))

    def build_from_function(self, func_ast: CFunctionAST) -> str:
        """Parsea el cuerpo de la función C y genera el diagrama de flujo tradicional."""
        start_id = self.add_node(FlowNodeType.TERMINAL, f"Inicio: {self.func_name}()", prefix="start")
        end_id = self.add_node(FlowNodeType.TERMINAL, "Fin", prefix="end")

        body = func_ast.raw_body.strip()
        # Remover llaves exteriores { ... }
        if body.startswith("{") and body.endswith("}"):
            body = body[1:-1].strip()

        clean_body = strip_c_comments_and_strings(body)
        last_node = self._parse_structured_block(clean_body, entry_node=start_id, exit_node=end_id)

        if last_node and last_node != end_id and last_node in self.nodes:
            self.add_edge(last_node, end_id)

        return self.to_mermaid()

    def _parse_structured_block(self, code: str, entry_node: str, exit_node: str) -> str:
        """Parsea sentencias secuenciales y estructuras de control (if, while, for)."""
        current_node = entry_node
        remaining = code.strip()

        while remaining:
            remaining = remaining.strip()
            if not remaining:
                break

            # 1. Estructura IF-ELSE
            if remaining.startswith("if"):
                m = re.match(r"^if\s*\((?P<cond>[^\)]+)\)\s*\{?", remaining)
                if m:
                    cond = m.group("cond").strip()
                    dec_node = self.add_node(FlowNodeType.DECISION, f"¿{cond}?", prefix="if_dec")
                    self.add_edge(current_node, dec_node)

                    # Encontrar el bloque then
                    after_if = remaining[m.end() :]
                    open_b = remaining.find("{", m.start())
                    then_block, rest = self._extract_block_content(remaining, open_b)

                    # Verificar si sigue un else
                    else_block = ""
                    rest_trimmed = rest.strip()
                    if rest_trimmed.startswith("else"):
                        m_else = re.match(r"^else\s*\{?", rest_trimmed)
                        if m_else:
                            open_b_else = rest_trimmed.find("{", m_else.start())
                            else_block, rest = self._extract_block_content(rest_trimmed, open_b_else)

                    # Parsear bloque Then
                    join_node = self.add_node(FlowNodeType.PROCESS, "Continuar", prefix="join")
                    then_end = self._parse_structured_block(then_block, entry_node=dec_node, exit_node=exit_node)
                    # El edge desde dec_node hacia then_start lleva "Sí"
                    if dec_node in self.nodes and self.nodes[dec_node].edges:
                        # Asignar label 'Sí' a la primera arista creada desde dec_node
                        first_edge = self.nodes[dec_node].edges[-1]
                        self.nodes[dec_node].edges[-1] = (first_edge[0], "Sí")

                    if then_end and then_end != exit_node:
                        self.add_edge(then_end, join_node)

                    # Parsear bloque Else si existe
                    if else_block:
                        else_end = self._parse_structured_block(else_block, entry_node=dec_node, exit_node=exit_node)
                        if dec_node in self.nodes and len(self.nodes[dec_node].edges) > 1:
                            second_edge = self.nodes[dec_node].edges[-1]
                            self.nodes[dec_node].edges[-1] = (second_edge[0], "No")
                        if else_end and else_end != exit_node:
                            self.add_edge(else_end, join_node)
                    else:
                        self.add_edge(dec_node, join_node, label="No")

                    current_node = join_node
                    remaining = rest
                    continue

            # 2. Estructura WHILE
            if remaining.startswith("while"):
                m = re.match(r"^while\s*\((?P<cond>[^\)]+)\)\s*\{?", remaining)
                if m:
                    cond = m.group("cond").strip()
                    while_dec = self.add_node(FlowNodeType.DECISION, f"¿{cond}?", prefix="while_dec")
                    self.add_edge(current_node, while_dec)

                    open_b = remaining.find("{", m.start())
                    body_block, rest = self._extract_block_content(remaining, open_b)

                    body_end = self._parse_structured_block(body_block, entry_node=while_dec, exit_node=exit_node)
                    if while_dec in self.nodes and self.nodes[while_dec].edges:
                        first_edge = self.nodes[while_dec].edges[-1]
                        self.nodes[while_dec].edges[-1] = (first_edge[0], "Sí")

                    # Conexión de retorno del bucle
                    if body_end and body_end != exit_node:
                        self.add_edge(body_end, while_dec)

                    exit_loop = self.add_node(FlowNodeType.PROCESS, "Continuar", prefix="while_exit")
                    self.add_edge(while_dec, exit_loop, label="No")

                    current_node = exit_loop
                    remaining = rest
                    continue

            # 3. Estructura FOR
            if remaining.startswith("for"):
                m = re.match(r"^for\s*\((?P<init>[^;]+);(?P<cond>[^;]+);(?P<inc>[^\)]+)\)\s*\{?", remaining)
                if m:
                    init_stmt = m.group("init").strip()
                    cond_stmt = m.group("cond").strip()
                    inc_stmt = m.group("inc").strip()

                    init_node = self.add_node(FlowNodeType.PROCESS, init_stmt, prefix="for_init")
                    self.add_edge(current_node, init_node)

                    for_dec = self.add_node(FlowNodeType.DECISION, f"¿{cond_stmt}?", prefix="for_dec")
                    self.add_edge(init_node, for_dec)

                    open_b = remaining.find("{", m.start())
                    body_block, rest = self._extract_block_content(remaining, open_b)

                    inc_node = self.add_node(FlowNodeType.PROCESS, inc_stmt, prefix="for_inc")
                    self.add_edge(inc_node, for_dec)

                    body_end = self._parse_structured_block(body_block, entry_node=for_dec, exit_node=exit_node)
                    if for_dec in self.nodes and self.nodes[for_dec].edges:
                        first_edge = self.nodes[for_dec].edges[-1]
                        self.nodes[for_dec].edges[-1] = (first_edge[0], "Sí")

                    if body_end and body_end != exit_node:
                        self.add_edge(body_end, inc_node)

                    exit_loop = self.add_node(FlowNodeType.PROCESS, "Continuar", prefix="for_exit")
                    self.add_edge(for_dec, exit_loop, label="No")

                    current_node = exit_loop
                    remaining = rest
                    continue

            # 4. Sentencias simples terminadas en ';'
            semicolon_idx = remaining.find(";")
            if semicolon_idx == -1:
                stmt = remaining.strip()
                remaining = ""
            else:
                stmt = remaining[:semicolon_idx].strip()
                remaining = remaining[semicolon_idx + 1 :]

            if not stmt:
                continue

            # Lectura stdin
            if re.search(r"\b(scanf|getchar|fgets|gets)\s*\(", stmt):
                in_node = self.add_node(FlowNodeType.INPUT, f"Leer: {stmt}", prefix="input")
                self.add_edge(current_node, in_node)
                current_node = in_node
            # Escritura stdout
            elif re.search(r"\b(printf|puts|putchar|perror)\s*\(", stmt):
                out_node = self.add_node(FlowNodeType.OUTPUT, f"Mostrar: {stmt}", prefix="output")
                self.add_edge(current_node, out_node)
                current_node = out_node
            # Retorno
            elif stmt.startswith("return"):
                ret_node = self.add_node(FlowNodeType.PROCESS, stmt, prefix="ret")
                self.add_edge(current_node, ret_node)
                self.add_edge(ret_node, exit_node)
                current_node = ret_node
            # Asignación / proceso
            else:
                proc_node = self.add_node(FlowNodeType.PROCESS, stmt, prefix="proc")
                self.add_edge(current_node, proc_node)
                current_node = proc_node

        return current_node

    def _extract_block_content(self, code: str, open_brace_idx: int) -> Tuple[str, str]:
        """Extrae el contenido entre { y } emparejando llaves anidadas."""
        if open_brace_idx == -1 or open_brace_idx >= len(code):
            return "", ""

        depth = 1
        curr = open_brace_idx + 1
        while curr < len(code) and depth > 0:
            if code[curr] == "{":
                depth += 1
            elif code[curr] == "}":
                depth -= 1
            curr += 1

        block = code[open_brace_idx + 1 : curr - 1].strip()
        rest = code[curr:].strip()
        return block, rest

    def to_mermaid(self) -> str:
        """Genera la representación en sintaxis Mermaid Flowchart con notación tradicional."""
        lines = ["flowchart TD", f'    %% Diagrama de Flujo Tradicional: {self.func_name}()']

        # Definir nodos con sus formas estándar ANSI/ISO
        for nid, node in self.nodes.items():
            if node.node_type == FlowNodeType.TERMINAL:
                # Óvalo / Píldora: ([ Inicio / Fin ])
                lines.append(f'    {nid}(["{node.label}"])')
            elif node.node_type == FlowNodeType.INPUT:
                # Paralelogramo de entrada: [/ Leer ... /]
                lines.append(f'    {nid}[/"{node.label}"/]')
            elif node.node_type == FlowNodeType.OUTPUT:
                # Paralelogramo de salida: [\ Mostrar ... \]
                lines.append(f'    {nid}[\\"{node.label}"\\]')
            elif node.node_type == FlowNodeType.DECISION:
                # Rombo de decisión: { ¿Condición? }
                lines.append(f'    {nid}{{"{node.label}"}}')
            else:
                # Rectángulo de proceso: [ Acción ]
                lines.append(f'    {nid}["{node.label}"]')

        # Definir conexiones y etiquetas
        for nid, node in self.nodes.items():
            for target_id, edge_label in node.edges:
                if edge_label:
                    lines.append(f'    {nid} -->|{edge_label}| {target_id}')
                else:
                    lines.append(f'    {nid} --> {target_id}')

        return "\n".join(lines)

    def to_dot(self) -> str:
        """Genera la representación en formato Graphviz (DOT)."""
        lines = [f'digraph "{self.func_name}" {{', '    rankdir=TB;', '    node [fontname="Arial", fontsize=10];']

        for nid, node in self.nodes.items():
            if node.node_type == FlowNodeType.TERMINAL:
                shape = "oval"
            elif node.node_type == FlowNodeType.INPUT:
                shape = "parallelogram"
            elif node.node_type == FlowNodeType.OUTPUT:
                shape = "parallelogram"
            elif node.node_type == FlowNodeType.DECISION:
                shape = "diamond"
            else:
                shape = "box"

            lbl = node.label.replace('"', '\\"')
            lines.append(f'    {nid} [label="{lbl}", shape={shape}];')

        for nid, node in self.nodes.items():
            for target_id, edge_label in node.edges:
                if edge_label:
                    lines.append(f'    {nid} -> {target_id} [label="{edge_label}"];')
                else:
                    lines.append(f'    {nid} -> {target_id};')

        lines.append("}")
        return "\n".join(lines)


class FlowchartGenerator:
    """Genera diagramas de flujo para todas las funciones de un archivo fuente en C."""

    def generate_for_file(
        self,
        c_file_path: Path | str,
        target_function: Optional[str] = None,
        output_format: str = "mermaid",
    ) -> Dict[str, str]:
        path = Path(c_file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        code = path.read_text(encoding="utf-8", errors="replace")
        functions = extract_c_functions(code)

        result: Dict[str, str] = {}

        if target_function:
            if target_function not in functions:
                raise ValueError(f"La función '{target_function}' no fue encontrada en '{path.name}'.")
            f_ast = functions[target_function]
            builder = FlowchartBuilder(target_function)
            builder.build_from_function(f_ast)
            result[target_function] = builder.to_mermaid() if output_format == "mermaid" else builder.to_dot()
        else:
            for fname, f_ast in functions.items():
                builder = FlowchartBuilder(fname)
                builder.build_from_function(f_ast)
                result[fname] = builder.to_mermaid() if output_format == "mermaid" else builder.to_dot()

        return result
