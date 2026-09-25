"""`ripley doctor` debe describir cada satélite con la descripción del catálogo (N-RIPLEY-01).

pipeline/availability.py tenía su propia copia de las descripciones y había
derivado: tetsuo figuraba como «análisis de mutación», vassili como
«benchmarking», corbel como «validación de layouts binarios», entre otros.
"""

from ripley.core.entrypoints_catalogo import SATELLITE_CATALOG
from ripley.pipeline.availability import TOOL_CATALOG, probe_all


def test_cada_satelite_usa_la_descripcion_del_catalogo():
    for entrada in SATELLITE_CATALOG.values():
        assert TOOL_CATALOG[entrada["cli_cmd"]] == entrada["description"], entrada["cli_cmd"]


def test_descripciones_que_habian_derivado():
    assert "sanitizer" in TOOL_CATALOG["tetsuo"].lower()
    assert "mutation" in TOOL_CATALOG["vassili"].lower() or "mutación" in TOOL_CATALOG["vassili"].lower()
    assert "documentación" in TOOL_CATALOG["corbel"].lower()
    assert "cobertura" in TOOL_CATALOG["dietrich"].lower()
    assert "abi" in TOOL_CATALOG["parker"].lower()


def test_probe_all_informa_la_misma_descripcion():
    descripciones = {s.name: s.description for s in probe_all()}
    assert descripciones["tetsuo"] == TOOL_CATALOG["tetsuo"]
