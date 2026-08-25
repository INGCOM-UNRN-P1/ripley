"""Doxygen documentation auditor for C functions and headers."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

from ripley.core.semantic_diff import CFunctionAST, extract_c_functions


@dataclass
class DoxygenObservation:
    filename: str
    function_name: str
    line: int
    missing_items: List[str]  # e.g. ["@brief", "@param a", "@return"]
    message: str


class DoxygenAuditor:
    """Audita la presencia y completitud de comentarios Doxygen en funciones C."""

    def __init__(
        self,
        require_brief: bool = True,
        require_params: bool = True,
        require_return: bool = True,
        require_contracts: bool = True,
    ) -> None:
        self.require_brief = require_brief
        self.require_params = require_params
        self.require_return = require_return
        # doc-auditor (nuevas.md §5.5): primitivas con punteros deben documentar
        # precondiciones (@pre) y la semántica de los punteros de salida.
        self.require_contracts = require_contracts

    def audit_file(self, file_path: Path | str) -> List[DoxygenObservation]:
        path = Path(file_path)
        if not path.exists():
            return []
        code = path.read_text(encoding="utf-8", errors="replace")
        return self.audit_code(code, filename=path.name)

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
            if self.require_brief:
                has_brief = bool(re.search(r"(@brief|\\brief|[a-zA-Z]{3,})", doc_text))
                if not has_brief or not doc_text:
                    missing.append("@brief (descripción de la función)")

            # 2. Verificar parámetros (@param)
            if self.require_params and fobj.params and fobj.params.strip() != "void":
                param_names = self._extract_param_names(fobj.params)
                for p in param_names:
                    if not re.search(rf"(@param|\\param)\s+({re.escape(p)}\b|\[[^\]]+\]\s+{re.escape(p)}\b)", doc_text):
                        missing.append(f"@param {p}")

            # 3. Verificar retorno (@return) para funciones no void
            if self.require_return and fobj.return_type and fobj.return_type.strip() != "void":
                if not re.search(r"(@return|\\return|@returns|\\returns)", doc_text):
                    missing.append("@return")


            # 4. doc-auditor: contratos en primitivas que reciben punteros
            if self.require_contracts and self._es_primitiva_con_punteros(
                fobj.return_type or "", fobj.params or ""
            ):
                if not re.search(r"(@pre|\\pre)", doc_text):
                    missing.append("@pre (precondiciones sobre los punteros)")
                if not re.search(r"(@post|\\post)", doc_text):
                    missing.append("@post (estado esperado al salir)")

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

    @staticmethod
    def _es_primitiva_con_punteros(return_type: str, params: str) -> bool:
        """True si la firma recibe o devuelve punteros (candidata a contratos).

        Se excluyen `main` y las funciones de prueba; el criterio es que al
        menos un parámetro sea puntero, lo que implica precondiciones sobre
        validez/no-NULL que deben quedar documentadas.
        """
        if "main" in params or not params.strip() or params.strip() == "void":
            return False
        return "*" in params

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
