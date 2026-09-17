"""Regresión del racimo D0901: los satélites catalogados deben ser alcanzables.

El motor filtraba los plugins descubiertos contra un conjunto `static_plugins`
escrito a mano que omitía 15 de los 28 satélites del catálogo (mocks,
semantic_diff, mcdc_coverage, binary_io, documentation, dataset_generator,
mutation_testing...). Quedaban declarados en su pyproject, descubiertos por
entry-point y jamás ejecutados.
"""

import pytest

from ripley.core.entrypoints import (
    SATELLITE_CATALOG,
    discover_entrypoint_plugins,
    plugins_de_fase,
)

FASES_VALIDAS = {"estatico", "dinamico", "orquestado"}


def test_toda_entrada_del_catalogo_declara_su_fase():
    """Sin fase, un satélite nuevo no entraría en ninguna pasada."""
    sin_fase = [k for k, v in SATELLITE_CATALOG.items() if v.get("fase") not in FASES_VALIDAS]
    assert sin_fase == [], f"entradas sin fase válida: {sin_fase}"


def test_ningun_satelite_estatico_queda_fuera_de_la_pasada():
    """La lista de ejecución se deriva del catálogo, no de una copia paralela."""
    habilitados = plugins_de_fase("estatico")
    catalogados = {k for k, v in SATELLITE_CATALOG.items() if v.get("fase") == "estatico"}
    assert catalogados <= habilitados


def test_las_fases_son_disjuntas_por_clave():
    claves = [set(), set(), set()]
    for i, fase in enumerate(("estatico", "dinamico", "orquestado")):
        claves[i] = {k for k, v in SATELLITE_CATALOG.items() if v.get("fase") == fase}
    assert not (claves[0] & claves[1])
    assert not (claves[0] & claves[2])
    assert not (claves[1] & claves[2])


def test_los_dinamicos_no_corren_en_el_analisis_estatico():
    """Fuzzing, mutación o perfilado no deben dispararse en un lint."""
    estaticos = plugins_de_fase("estatico")
    for clave in ("fuzzing", "mutation_testing", "fault_injection", "hardware_profiler", "mocks"):
        assert clave not in estaticos


@pytest.mark.parametrize("clave", sorted(SATELLITE_CATALOG))
def test_el_plugin_resuelve_el_binario_real_y_no_su_nombre(clave):
    """`mocks` debe resolver a `holden`, no a `shutil.which("mocks")`."""
    info = SATELLITE_CATALOG[clave]
    adaptadores = {p.name: p for p in discover_entrypoint_plugins()}
    plugin = adaptadores.get(clave)
    if plugin is None:
        pytest.skip(f"{clave} no está instalado en este entorno")
    assert plugin.cli_command == info["cli_cmd"]
    assert plugin.tool_name == info["tool"]


def test_los_satelites_que_precisan_configuracion_la_declaran():
    """kane necesita un binario y weyl un modelo; sin eso se saltean, no fallan."""
    assert SATELLITE_CATALOG["binary_io"]["requiere_config"] == ("binario",)
    assert SATELLITE_CATALOG["semantic_diff"]["requiere_config"] == ("modelo",)
