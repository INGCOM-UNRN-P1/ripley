"""Doxygen documentation auditor for C functions and headers."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

from ripley.semantic_diff import CFunctionAST, extract_c_functions


@dataclass
class DoxygenObservation:
    filename: str
    function_name: str
    line: int
    missing_items: List[str]  # e.g. ["@brief", "@param a", "@return"]
    message: str


class DoxygenAuditor:
    """Audita la presencia y completitud de comentarios Doxygen en funciones C."""

    def audit_code(self, code: str, filename: str = "archivo.c") -> List[DoxygenObservation]:
        observations: List[DoxygenObservation] = []
        functions = extract_c_functions(code)
        lines = code.splitlines()

        for fname, fobj in functions.items():
            if fname in ("main", "setUp", "tearDown"):
                continue

            # Buscar bloque de comentarios inmediatamente previo a la función
            start_idx = fobj.start_line - 1
            comment_lines: List[str] = []

            curr = start_idx - 1
            while curr >= 0 and not lines[curr].strip():
                curr -= 1

            # Recolectar líneas de comentario hacia arriba
            if curr >= 0 and (lines[curr].strip().endswith("*/") or lines[curr].strip().startswith("//")):
                while curr >= 0:
                    l = lines[curr].strip()
                    comment_lines.insert(0, l)
                    if l.startswith("/*") or l.startswith("/**") or not l.startswith("//") and not l.startswith("*"):
                        break
                    curr -= 1

            doc_text = "\n".join(comment_lines)
            missing: List[str] = []

            # 1. Verificar descripción / @brief
            has_brief = bool(re.search(r"(@brief|\\brief|[a-zA-Z]{3,})", doc_text))
            if not has_brief or not doc_text:
                missing.append("@brief (descripción de la función)")

            # 2. Verificar parámetros (@param)
            if fobj.params and fobj.params.strip() != "void":
                param_names = self._extract_param_names(fobj.params)
                for p in param_names:
                    if not re.search(rf"(@param|\\param)\s+({re.escape(p)}\b|\[[^\]]+\]\s+{re.escape(p)}\b)", doc_text):
                        missing.append(f"@param {p}")

            # 3. Verificar retorno (@return) para funciones no void
            if fobj.return_type and fobj.return_type.strip() != "void":
                if not re.search(r"(@return|\\return|@returns|\\returns)", doc_text):
                    missing.append("@return")

            if missing:
                observations.append(
                    DoxygenObservation(
                        filename=filename,
                        function_name=fname,
                        line=fobj.start_line,
                        missing_items=missing,
                        message=f"Función `{fname}()` incompleta en Doxygen. Falta documentar: {', '.join(missing)}.",
                    )
                )

        return observations

    def _extract_param_names(self, params_str: str) -> List[str]:
        names: List[str] = []
        for p in params_str.split(","):
            p_clean = p.strip()
            if not p_clean or p_clean == "void":
                continue
            # Obtener el último identificador
            m = re.search(r"(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)(?:\[\])?$", p_clean)
            if m:
                names.append(m.group("name"))
        return names
