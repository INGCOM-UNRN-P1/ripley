"""Etapa de ejecución dinámica de casos de prueba de la evaluación de un estudiante."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def ejecutar_casos_de_prueba(
    compiled: bool,
    compiled_binaries: Dict[str, Optional[Path]],
    testcases_by_exercise: Dict[str, list],
    test_runner,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Corre los casos de cada ejercicio contra su binario y devuelve (resultados, aprobados, total)."""
    test_results: List[Dict[str, Any]] = []
    tests_passed_count = 0
    total_tests_count = 0

    if compiled:
        for ex_name, cases in testcases_by_exercise.items():
            # Obtener el binario correspondiente al ejercicio
            bin_for_ex = compiled_binaries.get(ex_name)
            if not bin_for_ex:
                # Fallback si un binario coincide en dígitos
                for k, b in compiled_binaries.items():
                    if re.findall(r"\d+", k) == re.findall(r"\d+", ex_name):
                        bin_for_ex = b
                        break

            if not bin_for_ex:
                for tc in cases:
                    total_tests_count += 1
                    test_results.append(
                        {
                            "ejercicio": tc.exercise,
                            "nombre_caso": tc.case_name,
                            "argumentos_cli": "-",
                            "resultado": "NO_SOURCE",
                            "tiempo_ms": 0.0,
                        }
                    )
                continue

            for tc in cases:
                total_tests_count += 1
                r_detail = test_runner.run_case(bin_for_ex, tc)
                if r_detail.resultado == "PASSED":
                    tests_passed_count += 1
                test_results.append(
                    {
                        "ejercicio": r_detail.ejercicio,
                        "nombre_caso": r_detail.nombre_caso,
                        "argumentos_cli": r_detail.argumentos_cli or "-",
                        "resultado": r_detail.resultado,
                        "tiempo_ms": r_detail.tiempo_ms,
                    }
                )
    return test_results, tests_passed_count, total_tests_count
