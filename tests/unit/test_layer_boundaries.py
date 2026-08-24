"""Layer boundary enforcement for the modularization plan (docs/arquitectura/modularizacion.md).

Reglas de dirección de dependencias:
    models   -> (stdlib only)
    core     -> models
    tools    -> core, models
    pipeline -> core, tools, models        (nunca teacher)
    teacher  -> todo

El CLI estudiantil (ripley.cli.app_student) vive en la zona estudiante:
no puede importar ripley.teacher ni dependencias duras del flujo docente
(jinja2, slugify, tomli_w). Los shims planos en src/ripley/*.py son solo
compatibilidad hacia atrás y se excluyen del escaneo.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "ripley"

STUDENT_ZONES = ["models", "core", "tools", "pipeline"]
FORBIDDEN_IN_STUDENT = ("ripley.teacher",)
FORBIDDEN_TEACHER_DEPS = ("jinja2", "slugify", "tomli_w")

LAYER_RULES = {
    "core": ("ripley.tools", "ripley.teacher", "ripley.pipeline"),
    "tools": ("ripley.teacher", "ripley.pipeline"),
    "pipeline": ("ripley.teacher",),
    "models": ("ripley.core", "ripley.tools", "ripley.pipeline", "ripley.teacher"),
}


def _imports_of(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


@pytest.mark.parametrize("zone", STUDENT_ZONES)
def test_zone_exists_or_is_planned(zone):
    # pipeline se crea en fases posteriores; el test lo exige apenas exista código.
    zone_dir = SRC / zone
    if not zone_dir.exists():
        pytest.skip(f"zona {zone}/ aún no creada")
    assert any(zone_dir.glob("*.py")), f"zona {zone}/ vacía"


@pytest.mark.parametrize("zone", STUDENT_ZONES)
@pytest.mark.skipif(not (SRC / "pipeline").exists() and True, reason="se evalúa por zona")
def test_no_teacher_imports_in_student_zones(zone):
    zone_dir = SRC / zone
    if not zone_dir.exists():
        pytest.skip(f"zona {zone}/ aún no creada")
    violations = []
    for py in zone_dir.rglob("*.py"):
        for imp in _imports_of(py):
            if imp.startswith(FORBIDDEN_IN_STUDENT):
                violations.append(f"{py.relative_to(SRC)} importa {imp}")
    assert not violations, "Frontera violada:\n" + "\n".join(violations)


def test_layer_direction_rules():
    for zone, forbidden in LAYER_RULES.items():
        zone_dir = SRC / zone
        if not zone_dir.exists():
            continue
        violations = []
        for py in zone_dir.rglob("*.py"):
            for imp in _imports_of(py):
                if any(imp == f or imp.startswith(f + ".") for f in forbidden):
                    violations.append(f"{py.relative_to(SRC)} importa {imp}")
        assert not violations, f"Regla de capa violada para {zone}:\n" + "\n".join(violations)


def test_student_cli_has_no_teacher_imports():
    student_cli = SRC / "cli" / "app_student.py"
    if not student_cli.exists():
        pytest.skip("app_student aún no existe (fase F3)")
    for imp in _imports_of(student_cli):
        assert not imp.startswith("ripley.teacher"), f"CLI estudiantil importa {imp}"
        dep = imp.split(".")[0]
        assert dep not in FORBIDDEN_TEACHER_DEPS, f"CLI estudiantil depende de {dep}"


def test_teacher_deps_confined_to_teacher_layer():
    """jinja2/slugify/tomli_w solo pueden importarse desde teacher/ o shims planos."""
    violations = []
    for py in SRC.rglob("*.py"):
        rel = py.relative_to(SRC)
        if rel.parts[0] in ("teacher",) or len(rel.parts) == 1:
            continue  # teacher/ y shims planos están exentos
        for dep in _imports_of(py):
            if dep.split(".")[0] in FORBIDDEN_TEACHER_DEPS:
                violations.append(f"{rel} importa {dep}")
    assert not violations, "Dependencia docente fuera de teacher/:\n" + "\n".join(violations)
