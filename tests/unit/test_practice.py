"""Unit tests for practice initialization and management module."""

from pathlib import Path
import pytest

from ripley.practice import (
    ExerciseTemplateSpec,
    PracticeSpec,
    init_practice,
    list_practices,
    sync_practice_testcases,
)


def test_init_practice_creates_full_structure(tmp_path):
    base_practicas = tmp_path / "practicas"
    ws = tmp_path

    spec = PracticeSpec(
        name="Práctica 1 - Punteros y Memoria",
        practice_id="1228009",
        description="Aprender punteros simples y dobles.",
        exercises=[
            ExerciseTemplateSpec(
                slug="ejercicio1",
                title="Punteros Simples",
                description="Invertir un arreglo usando aritmética de punteros.",
                cases_count=2,
                with_argv=True,
            ),
            ExerciseTemplateSpec(
                slug="ejercicio2",
                title="Matrices Dinámicas",
                description="Reserva dinámica de matriz.",
                cases_count=3,
                with_argv=False,
            ),
        ],
    )

    p_dir = init_practice(
        spec=spec,
        base_dir=base_practicas,
        force=False,
    )

    expected_slug = "practica-1-punteros-y-memoria_1228009"
    assert p_dir.name == expected_slug
    assert (p_dir / "ripley.toml").exists()
    assert (p_dir / "enunciado.md").exists()
    assert (p_dir / "pautas_evaluacion.md").exists()

    # Verificar ejercicios
    ej1_dir = p_dir / "ejercicios" / "ejercicio1"
    assert (ej1_dir / "enunciado.md").exists()
    assert (ej1_dir / "solucion_modelo.c").exists()
    assert (ej1_dir / "tests" / "caso1.in").exists()
    assert (ej1_dir / "tests" / "caso1.out").exists()
    assert (ej1_dir / "tests" / "caso1.argv").exists()

    ej2_dir = p_dir / "ejercicios" / "ejercicio2"
    assert (ej2_dir / "tests" / "caso3.in").exists()
    assert not (ej2_dir / "tests" / "caso3.argv").exists()

    # Verificar sincronización y conteo dentro de practicas/
    count = sync_practice_testcases(p_dir)
    assert count >= 5


    # Re-init sin force debe fallar
    with pytest.raises(FileExistsError):
        init_practice(spec=spec, base_dir=base_practicas, force=False)


    # Re-init con force debe sobrescribir
    re_dir = init_practice(spec=spec, base_dir=base_practicas, force=True)
    assert re_dir.exists()


def test_list_practices(tmp_path):
    base_practicas = tmp_path / "practicas"

    spec1 = PracticeSpec(
        name="TP1",
        practice_id="101",
        description="",
        exercises=[ExerciseTemplateSpec(slug="ej1", title="Ej 1", description="")],
    )
    spec2 = PracticeSpec(
        name="TP2",
        practice_id="102",
        description="",
        exercises=[ExerciseTemplateSpec(slug="ej1", title="Ej 1", description="")],
    )

    init_practice(spec1, base_dir=base_practicas)
    init_practice(spec2, base_dir=base_practicas)

    practices = list_practices(base_dir=base_practicas)
    assert len(practices) == 2
    slugs = [p["slug"] for p in practices]
    assert "tp1_101" in slugs
    assert "tp2_102" in slugs
