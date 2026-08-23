"""AST-based semantic diffing module for C source files."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from ripley.plagiarism import tokenize_c_code
from ripley.core.security import strip_c_comments_and_strings


@dataclass
class CFunctionAST:
    name: str
    return_type: str
    params: str
    start_line: int
    end_line: int
    raw_body: str
    normalized_tokens: List[str]


@dataclass
class SemanticChange:
    category: str  # "AGREGADO", "ELIMINADO", "MODIFICADO_LOGICA", "COSMETICO"
    symbol_name: str
    description: str
    line_number: int = 1


@dataclass
class FileSemanticDiff:
    filename: str
    has_semantic_changes: bool
    changes: List[SemanticChange] = field(default_factory=list)


def extract_c_functions(code: str) -> Dict[str, CFunctionAST]:
    """Extrae las funciones y su representación normalizada en código C."""
    functions: Dict[str, CFunctionAST] = {}

    # Regex para prototipo e inicio de función en C (debe estar seguido por { en la misma o siguiente línea)
    func_sig_regex = re.compile(
        r"^[ \t]*(?P<ret>[a-zA-Z_][a-zA-Z0-9_* \t]+?)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\((?P<params>[^\)]*)\)\s*(?=[{]|\n[ \t]*[{])",
        re.MULTILINE,
    )



    for match in func_sig_regex.finditer(code):
        name = match.group("name")
        ret_type = match.group("ret").strip()
        params = match.group("params").strip()

        if name in ("if", "for", "while", "switch"):
            continue

        # Encontrar el bloque correspondiente emparejando llaves
        start_pos = match.end()
        # Buscar la primera llave abierta {
        open_brace = code.find("{", match.start())
        if open_brace == -1:
            continue

        start_line = code[:match.start()].count("\n") + 1

        brace_depth = 1
        curr = open_brace + 1
        while curr < len(code) and brace_depth > 0:
            if code[curr] == "{":
                brace_depth += 1
            elif code[curr] == "}":
                brace_depth -= 1
            curr += 1

        if brace_depth == 0:
            raw_body = code[open_brace:curr]
            end_line = code[:curr].count("\n") + 1
            tokens = [t[0] for t in tokenize_c_code(raw_body)]
            functions[name] = CFunctionAST(
                name=name,
                return_type=ret_type,
                params=params,
                start_line=start_line,
                end_line=end_line,
                raw_body=raw_body,
                normalized_tokens=tokens,
            )

    return functions


class SemanticDiffer:
    """Compara dos versiones de archivos C a nivel sintáctico y semántico."""

    def compare_c_codes(
        self,
        filename: str,
        old_code: str,
        new_code: str,
    ) -> FileSemanticDiff:
        old_funcs = extract_c_functions(old_code)
        new_funcs = extract_c_functions(new_code)

        changes: List[SemanticChange] = []
        has_semantic = False

        all_func_names = sorted(set(old_funcs.keys()) | set(new_funcs.keys()))

        for name in all_func_names:
            old_f = old_funcs.get(name)
            new_f = new_funcs.get(name)

            if not old_f and new_f:
                changes.append(
                    SemanticChange(
                        category="AGREGADO",
                        symbol_name=name,
                        description=f"Nueva función `{name}({new_f.params})` implementada.",
                        line_number=new_f.start_line,
                    )
                )
                has_semantic = True
            elif old_f and not new_f:
                changes.append(
                    SemanticChange(
                        category="ELIMINADO",
                        symbol_name=name,
                        description=f"Función `{name}` eliminada en la nueva versión.",
                        line_number=old_f.start_line,
                    )
                )
                has_semantic = True
            elif old_f and new_f:
                # Verificar si cambiaron tokens estructurales
                if old_f.normalized_tokens != new_f.normalized_tokens:
                    changes.append(
                        SemanticChange(
                            category="MODIFICADO_LOGICA",
                            symbol_name=name,
                            description=f"Función `{name}`: Modificación en la lógica algorítmica interna o flujo de control.",
                            line_number=new_f.start_line,
                        )
                    )
                    has_semantic = True
                elif old_f.raw_body != new_f.raw_body:
                    changes.append(
                        SemanticChange(
                            category="COSMETICO",
                            symbol_name=name,
                            description=f"Función `{name}`: Cambios cosméticos (formato, nombres de variables o comentarios) sin alteración de la estructura lógica.",
                            line_number=new_f.start_line,
                        )
                    )

        # Si no hubo funciones extraídas pero el código cambió
        if not all_func_names and old_code != new_code:
            tokens_old = [t[0] for t in tokenize_c_code(old_code)]
            tokens_new = [t[0] for t in tokenize_c_code(new_code)]
            if tokens_old != tokens_new:
                changes.append(
                    SemanticChange(
                        category="MODIFICADO_LOGICA",
                        symbol_name="global",
                        description="Modificación en el código global a nivel de flujo y operaciones.",
                    )
                )
                has_semantic = True
            else:
                changes.append(
                    SemanticChange(
                        category="COSMETICO",
                        symbol_name="global",
                        description="Cambios menores de formato sin impacto semántico.",
                    )
                )

        return FileSemanticDiff(
            filename=filename,
            has_semantic_changes=has_semantic,
            changes=changes,
        )

    def compare_folders(
        self,
        old_folder: Optional[Path | str],
        new_folder: Path | str,
    ) -> List[FileSemanticDiff]:
        new_path = Path(new_folder)
        if not new_path.exists():
            return []

        diffs: List[FileSemanticDiff] = []

        if old_folder is None or not Path(old_folder).exists():
            for f in sorted(new_path.glob("*.[ch]")):
                code = f.read_text(encoding="utf-8", errors="replace")
                funcs = extract_c_functions(code)
                changes = [
                    SemanticChange(
                        category="AGREGADO",
                        symbol_name=fname,
                        description=f"Función `{fname}` creada en la versión inicial.",
                        line_number=fobj.start_line,
                    )
                    for fname, fobj in funcs.items()
                ]
                diffs.append(
                    FileSemanticDiff(
                        filename=f.name,
                        has_semantic_changes=True,
                        changes=changes,
                    )
                )
            return diffs

        old_path = Path(old_folder)
        old_files = {f.name: f for f in old_path.glob("*.[ch]")}
        new_files = {f.name: f for f in new_path.glob("*.[ch]")}

        all_names = sorted(set(old_files.keys()) | set(new_files.keys()))

        for fname in all_names:
            old_f = old_files.get(fname)
            new_f = new_files.get(fname)

            old_text = old_f.read_text(encoding="utf-8", errors="replace") if old_f else ""
            new_text = new_f.read_text(encoding="utf-8", errors="replace") if new_f else ""

            diff = self.compare_c_codes(fname, old_text, new_text)
            diffs.append(diff)

        return diffs
