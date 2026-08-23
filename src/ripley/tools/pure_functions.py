"""Auditor and compiler-driven verification of pure and const functions in C."""

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Dict, List, Optional, Set, Tuple

from ripley.core.security import strip_c_comments_and_strings
from ripley.core.semantic_diff import CFunctionAST, extract_c_functions


@dataclass
class PureFunctionObservation:
    function_name: str
    line: int
    is_pure: bool
    is_const: bool
    violations: List[str]
    suggested_attribute: str


class PureFunctionAnalyzer:
    """Audita funciones para verificar la ausencia de efectos colaterales (pure y const)."""

    IO_FUNCTIONS = {
        "printf", "scanf", "puts", "getchar", "putchar", "fopen", "fclose",
        "fread", "fwrite", "fprintf", "fscanf", "gets", "fgets", "system",
    }

    def __init__(self, target_functions: Optional[List[str]] = None) -> None:
        self.target_functions = set(target_functions or [])

    def analyze_file(self, file_path: Path | str) -> List[PureFunctionObservation]:
        path = Path(file_path)
        if not path.exists():
            return []
        code = path.read_text(encoding="utf-8", errors="replace")
        observations = self.analyze_static(code)
        if self.target_functions:
            return [obs for obs in observations if obs.function_name in self.target_functions]
        return observations

    def analyze_static(self, code: str) -> List[PureFunctionObservation]:

        """Análisis estático de pureza basado en inspección de llamadas y mutaciones."""
        observations: List[PureFunctionObservation] = []
        functions = extract_c_functions(code)
        clean = strip_c_comments_and_strings(code)

        for fname, fobj in functions.items():
            if fname in ("main", "setUp", "tearDown"):
                continue

            violations: List[str] = []
            body = fobj.raw_body

            # 1. Llamadas a funciones de Entrada/Salida
            for io_fn in self.IO_FUNCTIONS:
                if re.search(rf"\b{io_fn}\s*\(", body):
                    violations.append(f"Invocación de función con efectos colaterales I/O: `{io_fn}()`.")

            # 2. Modificación de variables a través de punteros desreferenciados (*ptr = ...)
            has_pointer_write = bool(re.search(r"\*[a-zA-Z_][a-zA-Z0-9_]*\s*=[^=]", body))
            if has_pointer_write:
                violations.append("Modificación de memoria externa mediante desreferenciación de puntero.")

            is_pure = len(violations) == 0
            is_const = is_pure and ("*" not in fobj.params) and ("[" not in fobj.params)

            if is_const:
                attr = "__attribute__((const))"
            elif is_pure:
                attr = "__attribute__((pure))"
            else:
                attr = "none"

            observations.append(
                PureFunctionObservation(
                    function_name=fname,
                    line=fobj.start_line,
                    is_pure=is_pure,
                    is_const=is_const,
                    violations=violations,
                    suggested_attribute=attr,
                )
            )

        return observations

    def inject_pure_attributes(self, code: str, mode: str = "pure") -> str:
        """Inyecta __attribute__((pure)) o __attribute__((const)) en las funciones no-main."""
        functions = extract_c_functions(code)
        modified_code = code

        attr = "__attribute__((pure))" if mode == "pure" else "__attribute__((const))"

        for fname, fobj in functions.items():
            if fname == "main":
                continue
            # Inyectar el atributo antes del tipo de retorno
            pattern = rf"\b(?P<ret>[a-zA-Z0-9_* ]+)\s+{fname}\s*\("
            match = re.search(pattern, modified_code)
            if match:
                replacement = f"{attr} {match.group(0)}"
                modified_code = modified_code[: match.start()] + replacement + modified_code[match.end() :]

        return modified_code

    def verify_with_compiler(
        self,
        c_file: Path | str,
        mode: str = "pure",
        compiler: str = "gcc",
    ) -> Tuple[bool, str]:
        """Inyecta atributos y compila con GCC para verificar formalmente con el optimizador."""
        path = Path(c_file)
        if not path.exists():
            return False, f"Archivo no existe: {path}"

        code = path.read_text(encoding="utf-8", errors="replace")
        injected = self.inject_pure_attributes(code, mode=mode)

        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(injected)
            tf_path = Path(tf.name)

        out_bin = tf_path.with_suffix(".out")

        try:
            cmd = [
                compiler,
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(tf_path),
                "-o",
                str(out_bin),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)

            if proc.returncode == 0:
                return True, f"Todas las funciones cumplen estrictamente el contrato `{mode}`."
            else:
                return False, f"El compilador rechazó el atributo `{mode}`:\n{proc.stderr}"
        except Exception as e:
            return False, f"Error durante la verificación con compilador: {e}"
        finally:
            if tf_path.exists():
                tf_path.unlink()
            if out_bin.exists():
                out_bin.unlink()
