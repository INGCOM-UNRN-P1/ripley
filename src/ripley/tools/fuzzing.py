"""Automated input fuzzing and edge-case testcase generator for C assignments."""

from dataclasses import dataclass
from pathlib import Path
import random
import string
import subprocess
import tempfile
from typing import List, Optional, Tuple

from ripley.tools.compiler import Compiler
from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig


@dataclass
class FuzzTestCase:
    name: str
    input_data: str
    expected_output: str
    cli_args: str = ""
    description: str = ""


class Fuzzer:
    """Genera casos de prueba de borde y mutaciones aleatorias para ejercicios en C."""

    def __init__(self, seed: int = 42) -> None:
        self.random = random.Random(seed)

    def generate_numeric_edge_cases(self) -> List[str]:
        """Genera valores numéricos de borde estándar en arquitectura de 32/64 bits."""
        return [
            "0\n",
            "1\n",
            "-1\n",
            "2147483647\n",  # INT_MAX (32-bit signed)
            "-2147483648\n",  # INT_MIN (32-bit signed)
            "0 0\n",
            "1000000 -1000000\n",
            "2147483647 -2147483647\n",
            "0\n0\n",
            "999999999\n",
        ]

    def generate_string_edge_cases(self) -> List[str]:
        """Genera entradas de texto de borde (cadenas vacías, caracteres especiales, buffers grandes)."""
        return [
            "\n",
            "   \n",
            "a\n",
            "A" * 256 + "\n",  # Buffer boundary común
            "A" * 1024 + "\n",  # Buffer overflow boundary
            "!@#$%^&*()_+~`|}{[]:;?><,./\n",
            "Hello World with spaces and \t tabs\n",
            "Line1\nLine2\nLine3\n",
        ]

    def mutate_input(self, seed: str) -> List[str]:
        """Aplica mutaciones sobre una entrada semilla existente."""
        mutations: List[str] = []
        lines = seed.splitlines()

        # Mutación 1: Duplicar líneas
        mutations.append("\n".join(lines * 2) + "\n")

        # Mutación 2: Invertir líneas
        mutations.append("\n".join(reversed(lines)) + "\n")

        # Mutación 3: Inyectar números extremos
        extreme_numbers = ["0", "-1", "2147483647", "-2147483648"]
        mutated_tokens: List[str] = []
        for line in lines:
            tokens = line.split()
            new_tokens = [
                self.random.choice(extreme_numbers) if t.lstrip("-").isdigit() else t
                for t in tokens
            ]
            mutated_tokens.append(" ".join(new_tokens))
        mutations.append("\n".join(mutated_tokens) + "\n")

        # Mutación 4: Entradas vacías o con espacios excesivos
        mutations.append("   " + seed.replace(" ", "     ") + "   \n")

        return mutations

    def generate_testcases(
        self,
        target_dir: Path | str,
        cases_count: int = 4,
        seed_inputs: Optional[List[str]] = None,
        reference_source_or_binary: Optional[Path | str] = None,
        start_index: int = 1,
    ) -> List[Tuple[Path, Path]]:
        """Genera archivos .in y .out en target_dir ejecutando la solución de referencia si está provista."""
        out_dir = Path(target_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        pool_inputs: List[str] = []

        # Agregar mutaciones de semillas si existen
        if seed_inputs:
            for s in seed_inputs:
                pool_inputs.append(s)
                pool_inputs.extend(self.mutate_input(s))

        # Agregar casos numéricos y de texto
        pool_inputs.extend(self.generate_numeric_edge_cases())
        pool_inputs.extend(self.generate_string_edge_cases())

        # Seleccionar inputs únicos
        unique_inputs: List[str] = []
        seen = set()
        for inp in pool_inputs:
            clean = inp.strip()
            if clean and clean not in seen:
                seen.add(clean)
                unique_inputs.append(inp if inp.endswith("\n") else inp + "\n")
            if len(unique_inputs) >= cases_count:
                break

        # Si aún faltan, generar aleatorios
        while len(unique_inputs) < cases_count:
            r1 = self.random.randint(-10000, 10000)
            r2 = self.random.randint(-10000, 10000)
            unique_inputs.append(f"{r1} {r2}\n")

        # Preparar ejecutable de referencia si existe
        compiled_ref_bin: Optional[Path] = None
        temp_dir_obj = None

        if reference_source_or_binary:
            ref_path = Path(reference_source_or_binary)
            if ref_path.exists():
                if ref_path.suffix == ".c":
                    temp_dir_obj = tempfile.TemporaryDirectory()
                    temp_bin = Path(temp_dir_obj.name) / "ref_solucion.out"
                    comp = Compiler(CompilerConfig(), LimitsConfig(), SandboxConfig())
                    comp_res = comp.compile([ref_path], temp_bin)
                    if comp_res.success:
                        compiled_ref_bin = temp_bin
                else:
                    compiled_ref_bin = ref_path

        generated_pairs: List[Tuple[Path, Path]] = []

        for idx, input_text in enumerate(unique_inputs[:cases_count], start=start_index):
            in_file = out_dir / f"caso{idx}.in"
            out_file = out_dir / f"caso{idx}.out"

            in_file.write_text(input_text, encoding="utf-8")

            expected_output = ""
            if compiled_ref_bin and compiled_ref_bin.exists():
                try:
                    proc = subprocess.run(
                        [str(compiled_ref_bin)],
                        input=input_text,
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    expected_output = proc.stdout
                except Exception:
                    expected_output = "// Error al ejecutar solución de referencia\n"
            else:
                expected_output = f"// Salida esperada para caso {idx} generada por fuzzing\n"

            out_file.write_text(expected_output, encoding="utf-8")
            generated_pairs.append((in_file, out_file))

        if temp_dir_obj:
            temp_dir_obj.cleanup()

        return generated_pairs
