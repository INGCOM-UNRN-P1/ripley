"""Call graph generator for C source code."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from ripley.core.semantic_diff import extract_c_functions

C_STANDARD_LIBRARY_FUNCS = {
    "printf", "scanf", "puts", "gets", "getchar", "putchar", "fgets", "fputs",
    "malloc", "calloc", "realloc", "free", "exit", "abort", "atoi", "atof",
    "strlen", "strcpy", "strncpy", "strcmp", "strncmp", "strcat", "strncat",
    "strchr", "strstr", "memcpy", "memset", "memcmp", "sizeof", "fopen", "fclose",
    "fread", "fwrite", "fscanf", "fprintf", "feof", "ferror", "system", "qsort"
}


@dataclass
class CallGraphResult:
    defined_functions: List[str]
    calls: List[Tuple[str, str]]  # (caller, callee)
    recursive_functions: List[str]
    external_calls: List[Tuple[str, str]]  # (caller, stdlib_or_unknown)


class CallGraphGenerator:
    """Extrae las relaciones de invocación entre funciones C y genera grafos en Mermaid y DOT."""

    def build_callgraph(self, code: str) -> CallGraphResult:
        functions = extract_c_functions(code)
        defined_names = set(functions.keys())

        calls: Set[Tuple[str, str]] = set()
        external_calls: Set[Tuple[str, str]] = set()
        recursive_funcs: Set[str] = set()

        # Regex para llamadas a funciones: identificador seguido de (
        call_regex = re.compile(r"\b(?P<callee>[a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.MULTILINE)

        for caller_name, f_ast in functions.items():
            # Buscar llamadas en el cuerpo de la función
            for match in call_regex.finditer(f_ast.raw_body):
                callee = match.group("callee")
                if callee in ("if", "for", "while", "switch", "return", "sizeof"):
                    continue

                if callee == caller_name:
                    recursive_funcs.add(caller_name)
                    calls.add((caller_name, callee))
                elif callee in defined_names:
                    calls.add((caller_name, callee))
                elif callee in C_STANDARD_LIBRARY_FUNCS:
                    external_calls.add((caller_name, callee))

        return CallGraphResult(
            defined_functions=sorted(defined_names),
            calls=sorted(calls),
            recursive_functions=sorted(recursive_funcs),
            external_calls=sorted(external_calls),
        )

    def to_mermaid(self, result: CallGraphResult, include_stdlib: bool = False) -> str:
        lines = ["flowchart TD", "    %% Árbol de Llamadas (Call Graph)"]

        # Nodos definidos
        for fname in result.defined_functions:
            if fname in result.recursive_functions:
                lines.append(f'    fn_{fname}["fa:fa-sync {fname}() [Recursiva]"]:::recursive')
            elif fname == "main":
                lines.append(f'    fn_{fname}["fa:fa-play {fname}() [Punto de Entrada]"]:::entrypoint')
            else:
                lines.append(f'    fn_{fname}["{fname}()"]')

        # Aristas internas
        for caller, callee in result.calls:
            lines.append(f"    fn_{caller} --> fn_{callee}")

        # Aristas externas si se solicita
        if include_stdlib:
            for caller, callee in result.external_calls:
                ext_id = f"ext_{callee}"
                lines.append(f'    {ext_id}[/"{callee}() [Librería]"/]:::stdlib')
                lines.append(f"    fn_{caller} -.-> {ext_id}")

        lines.append("    classDef recursive fill:#ffebee,stroke:#c62828,stroke-width:2px;")
        lines.append("    classDef entrypoint fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;")
        lines.append("    classDef stdlib fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray: 5 5;")

        return "\n".join(lines)

    def to_dot(self, result: CallGraphResult, include_stdlib: bool = False) -> str:
        lines = ['digraph CallGraph {', '    rankdir=LR;', '    node [fontname="Arial", fontsize=10];']

        for fname in result.defined_functions:
            if fname in result.recursive_functions:
                lines.append(f'    "{fname}" [shape=box, color=red, style=filled, fillcolor="#ffebee", label="{fname}\\n(recursiva)"];')
            elif fname == "main":
                lines.append(f'    "{fname}" [shape=box, color=green, style=filled, fillcolor="#e8f5e9", label="{fname}\\n(main)"];')
            else:
                lines.append(f'    "{fname}" [shape=box];')

        for caller, callee in result.calls:
            lines.append(f'    "{caller}" -> "{callee}";')

        if include_stdlib:
            for caller, callee in result.external_calls:
                lines.append(f'    "{callee}" [shape=parallelogram, style=dashed];')
                lines.append(f'    "{caller}" -> "{callee}" [style=dashed];')

        lines.append("}")
        return "\n".join(lines)

    def generate_for_file(
        self,
        file_path: Path | str,
        output_format: str = "mermaid",
        include_stdlib: bool = False,
    ) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        code = path.read_text(encoding="utf-8", errors="replace")
        cg = self.build_callgraph(code)

        if output_format == "mermaid":
            return self.to_mermaid(cg, include_stdlib=include_stdlib)
        return self.to_dot(cg, include_stdlib=include_stdlib)

    def find_unreachable_functions(
        self,
        code: str,
        entrypoints: Optional[Set[str]] = None,
    ) -> List[str]:
        """Identifica funciones definidas que no son alcanzables desde los puntos de entrada (código muerto)."""
        cg = self.build_callgraph(code)
        entries = entrypoints or ({"main"} if "main" in cg.defined_functions else set(cg.defined_functions))

        # Grafo de adyacencia
        adj: Dict[str, List[str]] = {fn: [] for fn in cg.defined_functions}
        for caller, callee in cg.calls:
            if caller in adj:
                adj[caller].append(callee)

        # BFS desde entrypoints
        visited: Set[str] = set()
        queue = list(entries)
        for e in queue:
            visited.add(e)

        while queue:
            curr = queue.pop(0)
            for neighbor in adj.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Inalcanzables
        unreachable = [fn for fn in cg.defined_functions if fn not in visited]
        return sorted(unreachable)

