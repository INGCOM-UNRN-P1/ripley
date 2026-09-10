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
    """Retorna la ruta raíz de la práctica donde residen los casos de prueba."""
    p_dir = Path(workspace_dir) / "practicas" / activity_slug
    if p_dir.exists():
        return p_dir
    legacy_dir = Path(workspace_dir) / "tests" / activity_slug
    if legacy_dir.exists():
        return legacy_dir
    return p_dir


def create_testcase_skeleton(
    workspace_dir: str | Path,
    activity_slug: str,
    exercise: str,
    cases_count: int = 1,
    with_argv: bool = False,
) -> List[Path]:
    """Genera la estructura de directorios y archivos de prueba (.in, .out, .argv) en practicas/<slug>/ejercicios/<ejercicio>/tests/."""
    ex_dir = Path(workspace_dir) / "practicas" / activity_slug / "ejercicios" / exercise / "tests"
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


def _collect_testcases_from_dir(directory: Path, exercise_name: str) -> List[TestCaseInfo]:
    """Colecciona archivos caso*.in, caso*.out y caso*.argv desde un directorio."""
    cases_map: Dict[str, Dict[str, Optional[Path]]] = {}
    if not directory.exists() or not directory.is_dir():
        return []

    for file in sorted(directory.iterdir()):
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
    return ex_cases


def discover_testcases(
    workspace_dir: str | Path,
    activity_slug: str,
) -> Dict[str, List[TestCaseInfo]]:
    """Descubre los casos de prueba organizados por ejercicio dentro de practicas/<slug>/."""
    ws = Path(workspace_dir)
    practice_dir = ws / "practicas" / activity_slug
    exercises: Dict[str, List[TestCaseInfo]] = {}

    # 1. Esquema estándar: practicas/<activity_slug>/ejercicios/<exercise>/tests/
    ejercicios_dir = practice_dir / "ejercicios"
    if ejercicios_dir.exists() and ejercicios_dir.is_dir():
        for ex_dir in sorted(ejercicios_dir.iterdir()):
            if not ex_dir.is_dir():
                continue
            tests_dir = ex_dir / "tests"
            cases = _collect_testcases_from_dir(tests_dir, ex_dir.name)
            if cases:
                exercises[ex_dir.name] = cases

    # 2. Esquema alternativo: practicas/<activity_slug>/tests/<exercise>/
    practice_tests_dir = practice_dir / "tests"
    if practice_tests_dir.exists() and practice_tests_dir.is_dir():
        for ex_dir in sorted(practice_tests_dir.iterdir()):
            if not ex_dir.is_dir() or ex_dir.name in exercises:
                continue
            cases = _collect_testcases_from_dir(ex_dir, ex_dir.name)
            if cases:
                exercises[ex_dir.name] = cases

    # 3. Fallback retrocompatible para proyectos antiguos: tests/<activity_slug>/<exercise>/
    legacy_dir = ws / "tests" / activity_slug
    if not exercises and legacy_dir.exists() and legacy_dir.is_dir():
        for ex_dir in sorted(legacy_dir.iterdir()):
            if not ex_dir.is_dir():
                continue
            cases = _collect_testcases_from_dir(ex_dir, ex_dir.name)
            if cases:
                exercises[ex_dir.name] = cases

    return exercises


def check_testcases_integrity(
    workspace_dir: str | Path,
    activity_slug: str,
) -> Tuple[bool, List[str]]:
    """Verifica la consistencia e integridad de parejas .in / .out en los testcases dentro de practicas/."""
    exercises = discover_testcases(workspace_dir, activity_slug)
    errors: List[str] = []

    if not exercises:
        errors.append(f"No se encontraron ejercicios con casos de prueba en 'practicas/{activity_slug}'")
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
