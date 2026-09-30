"""`ripley checks list` es el catálogo unificado: checks propios y satélites (N-RIPLEY-04).

Mostraba solo 3 checks (los de scope `student`): ocultaba los de scope `both`
y ninguno de los satélites del SATELLITE_CATALOG.
"""

import json

from typer.testing import CliRunner

from ripley.cli.student import app, filas_catalogo
from ripley.core.entrypoints_catalogo import SATELLITE_CATALOG

runner = CliRunner()


def test_el_scope_student_incluye_los_checks_de_ambos_y_los_satelites():
    filas = filas_catalogo("student", {})
    ids = {f["id"] for f in filas}
    assert "ast.backward_goto" in ids  # scope both
    assert all(f["scope"] in ("student", "both") for f in filas)
    # Cada satélite una vez, con el nombre de su función (el catálogo también lo registra
    # por el nombre de la herramienta): 27 herramientas.
    satelites = [f for f in filas if f["origen"] == "satélite"]
    assert len(satelites) == len({f["herramientas"][0] for f in satelites}) == len({id(v) for v in SATELLITE_CATALOG.values()})
    assert "satelite.style" in ids and "satelite.gaff" not in ids
    assert "satelite.bishop" in ids  # sin nombre de función: se lista por el de la herramienta


def test_los_satelites_sin_su_herramienta_figuran_como_omitidos():
    filas = {f["id"]: f for f in filas_catalogo("all", {"gaff": True})}
    assert filas["satelite.style"]["faltan"] == []
    assert filas["satelite.compiler"]["faltan"] == ["daedalus"]
    assert filas["satelite.compiler"]["capa"] == "pipeline"
    assert filas["satelite.semantic_diff"]["requiere"] == ["modelo"]


def test_teacher_no_muestra_los_checks_solo_de_estudiante():
    assert all(f["scope"] in ("teacher", "both") for f in filas_catalogo("teacher", {}))


def test_checks_list_json():
    res = runner.invoke(app, ["checks", "list", "--json"])
    assert res.exit_code == 0, res.output
    datos = json.loads(res.stdout)
    assert datos["schema_version"] == "1.0.0"
    assert any(c["id"] == "satelite.style" for c in datos["checks"])
