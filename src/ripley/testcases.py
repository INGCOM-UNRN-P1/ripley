"""Testcase management, skeleton generation, listing and integrity validation."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple


@dataclass
class TestCaseInfo:
    __test__ = False
    exercise: str
    case_name: str
    in_file: Optional[Path]
    out_file: Optional[Path]
    argv_file: Optional[Path]


    @property
    def is_complete(self) -> bool:
        return self.in_file is not None and self.out_file is not None and self.in_file.exists() and self.out_file.exists()


def get_tests_root(workspace_dir: str | Path, activity_slug: str) -> Path:
    return Path(workspace_dir) / "tests" / activity_slug


def create_testcase_skeleton(
    workspace_dir: str | Path,
    activity_slug: str,
    exercise: str,
    cases_count: int = 1,
    with_argv: bool = False,
) -> List[Path]:
    """Genera la estructura de directorios y archivos de prueba (.in, .out, .argv)."""
    ex_dir = get_tests_root(workspace_dir, activity_slug) / exercise
    ex_dir.mkdir(parents=True, exist_ok=True)

    created_files: List[Path] = []

    for i in range(1, cases_count + 1):
        in_path = ex_dir / f"caso{i}.in"
        out_path = ex_dir / f"caso{i}.out"

        if not in_path.exists():
            in_path.write_text(f"// Entrada de prueba para caso {i}\n", encoding="utf-8")
            created_files.append(in_path)

        if not out_path.exists():
            out_path.write_text(f"// Salida esperada para caso {i}\n", encoding="utf-8")
            created_files.append(out_path)

        if with_argv:
            argv_path = ex_dir / f"caso{i}.argv"
            if not argv_path.exists():
                argv_path.write_text(f"--param{i} valor{i}\n", encoding="utf-8")
                created_files.append(argv_path)

    return created_files


def discover_testcases(
    workspace_dir: str | Path,
    activity_slug: str,
) -> Dict[str, List[TestCaseInfo]]:
    """Descubre los casos de prueba organizados por ejercicio para una actividad."""
    activity_tests_dir = get_tests_root(workspace_dir, activity_slug)
    if not activity_tests_dir.exists():
        return {}

    exercises: Dict[str, List[TestCaseInfo]] = {}

    for ex_dir in sorted(activity_tests_dir.iterdir()):
        if not ex_dir.is_dir():
            continue
        exercise_name = ex_dir.name
        cases_map: Dict[str, Dict[str, Optional[Path]]] = {}

        for file in sorted(ex_dir.iterdir()):
            if not file.is_file():
                continue
            case_match = re.match(r"^(caso\d+)\.(in|out|argv)$", file.name, re.IGNORECASE)
            if case_match:
                case_base = case_match.group(1).lower()
                ext = case_match.group(2).lower()
                if case_base not in cases_map:
                    cases_map[case_base] = {"in": None, "out": None, "argv": None}
                cases_map[case_base][ext] = file

        ex_cases: List[TestCaseInfo] = []
        for case_base, files in sorted(cases_map.items()):
            ex_cases.append(
                TestCaseInfo(
                    exercise=exercise_name,
                    case_name=case_base,
                    in_file=files["in"],
                    out_file=files["out"],
                    argv_file=files["argv"],
                )
            )

        exercises[exercise_name] = ex_cases

    return exercises


def check_testcases_integrity(
    workspace_dir: str | Path,
    activity_slug: str,
) -> Tuple[bool, List[str]]:
    """Verifica la consistencia e integridad de parejas .in / .out en los testcases."""
    activity_tests_dir = get_tests_root(workspace_dir, activity_slug)
    if not activity_tests_dir.exists():
        return False, [f"No existe el directorio de pruebas para la actividad: {activity_tests_dir}"]

    errors: List[str] = []
    exercises = discover_testcases(workspace_dir, activity_slug)

    if not exercises:
        errors.append(f"No se encontraron ejercicios con casos de prueba en '{activity_tests_dir}'")
        return False, errors

    for ex_name, cases in exercises.items():
        if not cases:
            errors.append(f"El ejercicio '{ex_name}' no contiene casos de prueba.")
            continue

        for tc in cases:
            if tc.in_file is None:
                errors.append(f"[{ex_name}] Falta archivo de entrada '.in' para el caso '{tc.case_name}'")
            if tc.out_file is None:
                errors.append(f"[{ex_name}] Falta archivo de salida esperada '.out' para el caso '{tc.case_name}'")

    is_valid = len(errors) == 0
    return is_valid, errors
