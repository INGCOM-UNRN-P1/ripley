"""Mock harness and stub generator for unit testing in C."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from ripley.semantic_diff import CFunctionAST, extract_c_functions


@dataclass
class MockFunctionSpec:
    name: str
    return_type: str
    params: str
    param_list: List[Tuple[str, str]]  # (type, name)


class MockGenerator:
    """Genera arneses de funciones simuladas (mocks) con registro de llamadas y retornos configurables."""

    def parse_header_or_source(self, code: str) -> List[MockFunctionSpec]:
        specs: List[MockFunctionSpec] = []
        # Extraer prototipos o definiciones
        sig_regex = re.compile(
            r"^[ \t]*(?P<ret>[a-zA-Z_][a-zA-Z0-9_* \t]+?)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\((?P<params>[^\)]*)\)\s*(?:;|(?=[{]))",
            re.MULTILINE,
        )

        for match in sig_regex.finditer(code):
            name = match.group("name")
            ret_type = match.group("ret").strip()
            params_str = match.group("params").strip()

            if name in ("if", "for", "while", "switch", "main"):
                continue

            param_list: List[Tuple[str, str]] = []
            if params_str and params_str != "void":
                for p in params_str.split(","):
                    p = p.strip()
                    m = re.match(r"(?P<ptype>.+?)\s+(?P<pname>[a-zA-Z_][a-zA-Z0-9_]*)$", p)
                    if m:
                        param_list.append((m.group("ptype").strip(), m.group("pname").strip()))
                    else:
                        param_list.append((p, f"arg_{len(param_list) + 1}"))

            specs.append(
                MockFunctionSpec(
                    name=name,
                    return_type=ret_type,
                    params=params_str or "void",
                    param_list=param_list,
                )
            )

        return specs

    def generate_mock_header(self, module_name: str, specs: List[MockFunctionSpec]) -> str:
        guard = f"MOCK_{module_name.upper()}_H"
        lines = [
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
            "#include <stddef.h>",
            "#include <stdbool.h>",
            "",
            "// --- Funciones de control de Mocks ---",
            "void reset_all_mocks(void);",
            "",
        ]

        for s in specs:
            lines.append(f"// Mock para: {s.return_type} {s.name}({s.params})")
            lines.append(f"extern int mock_{s.name}_call_count;")
            if s.return_type != "void":
                lines.append(f"extern {s.return_type} mock_{s.name}_return_value;")
                lines.append(f"void mock_{s.name}_set_return({s.return_type} val);")

            lines.append(f"{s.return_type} {s.name}({s.params});")
            lines.append("")

        lines.append(f"#endif // {guard}\n")
        return "\n".join(lines)

    def generate_mock_source(self, module_name: str, specs: List[MockFunctionSpec]) -> str:
        lines = [
            f'#include "mock_{module_name}.h"',
            "#include <string.h>",
            "",
        ]

        # Variables de control
        for s in specs:
            lines.append(f"int mock_{s.name}_call_count = 0;")
            if s.return_type != "void":
                # Inicializador por defecto
                init_val = "0" if "*" not in s.return_type else "NULL"
                lines.append(f"{s.return_type} mock_{s.name}_return_value = {init_val};")
                lines.append(f"void mock_{s.name}_set_return({s.return_type} val) {{ mock_{s.name}_return_value = val; }}")
            lines.append("")

        # Función reset_all_mocks
        lines.extend(
            [
                "void reset_all_mocks(void) {",
            ]
        )
        for s in specs:
            lines.append(f"    mock_{s.name}_call_count = 0;")
        lines.append("}\n")

        # Implementaciones de las funciones mockeadas
        for s in specs:
            lines.append(f"{s.return_type} {s.name}({s.params}) {{")
            lines.append(f"    mock_{s.name}_call_count++;")
            if s.return_type != "void":
                lines.append(f"    return mock_{s.name}_return_value;")
            lines.append("}\n")

        return "\n".join(lines)

    def generate_files(
        self,
        input_file: Path | str,
        output_dir: Path | str,
        module_name: Optional[str] = None,
    ) -> Tuple[Path, Path]:
        in_path = Path(input_file)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        mod_name = module_name or in_path.stem
        code = in_path.read_text(encoding="utf-8", errors="replace")
        specs = self.parse_header_or_source(code)

        h_file = out_dir / f"mock_{mod_name}.h"
        c_file = out_dir / f"mock_{mod_name}.c"

        h_file.write_text(self.generate_mock_header(mod_name, specs), encoding="utf-8")
        c_file.write_text(self.generate_mock_source(mod_name, specs), encoding="utf-8")

        return h_file, c_file
