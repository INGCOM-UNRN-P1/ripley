"""Property-Based Testing framework and harness generator for C assignments."""

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import tempfile
from typing import List, Optional, Tuple

from ripley.tools.compiler import Compiler
from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig


@dataclass
class PropertyTestResult:
    passed: bool
    iterations_run: int
    property_name: str
    counterexample_input: Optional[str] = None
    counterexample_output: Optional[str] = None
    message: str = ""


class PropertyTestRunner:
    """Genera arneses de pruebas basados en propiedades e invariantes formales en C."""

    def __init__(self) -> None:
        self.compiler = Compiler(
            compiler_cfg=CompilerConfig(executable="gcc", flags=["-std=c11", "-Wall", "-Wextra"]),
            limits_cfg=LimitsConfig(timeout_segundos=10),
            sandbox_cfg=SandboxConfig(),
        )

    def generate_harness_c(
        self,
        student_source: Path | str,
        property_type: str,
        target_function: str,
        iterations: int = 100,
    ) -> str:
        """Genera el código C del arnés de prueba de propiedades."""
        prop = property_type.upper()

        if prop == "IDEMPOTENCE":
            # f(f(x)) == f(x)
            test_logic = f"""
            int x = rand() % 1000 - 500;
            int r1 = {target_function}(x);
            int r2 = {target_function}(r1);
            if (r1 != r2) {{
                printf("FAIL: Input=%d, f(x)=%d, f(f(x))=%d\\n", x, r1, r2);
                return 1;
            }}
            """
        elif prop == "COMMUTATIVITY":
            # f(a, b) == f(b, a)
            test_logic = f"""
            int a = rand() % 1000 - 500;
            int b = rand() % 1000 - 500;
            int r1 = {target_function}(a, b);
            int r2 = {target_function}(b, a);
            if (r1 != r2) {{
                printf("FAIL: a=%d, b=%d, f(a,b)=%d != f(b,a)=%d\\n", a, b, r1, r2);
                return 1;
            }}
            """
        elif prop == "SORT_INVARIANT":
            # Valida que el arreglo quede no-decreciente y conserve longitud
            test_logic = f"""
            int n = (rand() % 20) + 1;
            int arr[20];
            for (int j = 0; j < n; j++) arr[j] = rand() % 200 - 100;
            {target_function}(arr, n);
            for (int j = 0; j < n - 1; j++) {{
                if (arr[j] > arr[j + 1]) {{
                    printf("FAIL: Arreglo no ordenado en indice %d: %d > %d\\n", j, arr[j], arr[j + 1]);
                    return 1;
                }}
            }}
            """
        else:
            # Invariante general de positividad o no-nulo
            test_logic = f"""
            int x = rand() % 100;
            int r = {target_function}(x);
            if (r < 0) {{
                printf("FAIL: Input=%d produjo resultado negativo=%d\\n", x, r);
                return 1;
            }}
            """

        harness_code = f"""
        #include <stdio.h>
        #include <stdlib.h>
        #include <stdbool.h>
        #include <time.h>

        // Inclusión de la fuente del estudiante
        #include "{Path(student_source).resolve()}"

        int main(void) {{
            srand(42);
            for (int i = 1; i <= {iterations}; i++) {{
                {test_logic}
            }}
            printf("PASSED: {iterations} iteraciones exitosas.\\n");
            return 0;
        }}
        """
        return harness_code

    def run_property_test(
        self,
        student_source: Path | str,
        property_type: str,
        target_function: str,
        iterations: int = 100,
    ) -> PropertyTestResult:
        src_path = Path(student_source)
        if not src_path.exists():
            return PropertyTestResult(
                passed=False,
                iterations_run=0,
                property_name=property_type,
                message=f"Archivo no encontrado: {src_path}",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            harness_c = Path(temp_dir) / "harness.c"
            harness_bin = Path(temp_dir) / "harness.out"

            code = self.generate_harness_c(
                student_source=src_path,
                property_type=property_type,
                target_function=target_function,
                iterations=iterations,
            )
            harness_c.write_text(code, encoding="utf-8")

            comp_res = self.compiler.compile([harness_c], harness_bin)
            if not comp_res.success:
                return PropertyTestResult(
                    passed=False,
                    iterations_run=0,
                    property_name=property_type,
                    message=f"Error al compilar el arnés de propiedades: {comp_res.stderr}",
                )

            try:
                proc = subprocess.run(
                    [str(harness_bin)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    return PropertyTestResult(
                        passed=True,
                        iterations_run=iterations,
                        property_name=property_type,
                        message=f"Invariante '{property_type}' cumplida exitosamente tras {iterations} pruebas aleatorias.",
                    )
                else:
                    return PropertyTestResult(
                        passed=False,
                        iterations_run=iterations,
                        property_name=property_type,
                        counterexample_output=proc.stdout.strip(),
                        message=f"Violación de invariante '{property_type}': {proc.stdout.strip()}",
                    )
            except subprocess.TimeoutExpired:
                return PropertyTestResult(
                    passed=False,
                    iterations_run=0,
                    property_name=property_type,
                    message="Timeout durante la ejecución de las pruebas de propiedades.",
                )
