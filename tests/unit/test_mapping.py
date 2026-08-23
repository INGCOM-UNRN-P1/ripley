"""Unit tests for heuristic and interactive mapping module."""

import json
from pathlib import Path

from ripley.teacher.mapping import (
    InteractiveMapper,
    MappingStore,
    SPECIAL_AUXILIARY,
    SPECIAL_IGNORE,
    heuristic_match,
)


def test_heuristic_match():
    exercises = ["ejercicio1", "ejercicio2", "ejercicio3"]

    # Exacto
    assert heuristic_match("ejercicio1.c", exercises) == "ejercicio1"
    assert heuristic_match("ejercicio2.C", exercises) == "ejercicio2"

    # Con números
    assert heuristic_match("ej1.c", exercises) == "ejercicio1"
    assert heuristic_match("ej_2.c", exercises) == "ejercicio2"
    assert heuristic_match("punto3.c", exercises) == "ejercicio3"
    assert heuristic_match("tp_ej1_final.c", exercises) == "ejercicio1"

    # Ambiguo o desconocido
    assert heuristic_match("auxiliar.c", exercises) is None
    assert heuristic_match("codigo_raro.c", exercises) is None


def test_mapping_store_load_save_and_priority(tmp_path):
    ws = tmp_path
    act_slug = "entrega-1_1228009"

    store = MappingStore(ws, act_slug)
    exercises = ["ejercicio1", "ejercicio2"]

    # Sin reglas previas -> Heurística
    assert store.get_effective_mapping("student1", "ej1.c", exercises) == "ejercicio1"
    assert store.get_effective_mapping("student1", "main.c", exercises) is None

    # Configurar regla global
    store.set_global_mapping("main.c", "ejercicio1")
    assert store.get_effective_mapping("student1", "main.c", exercises) == "ejercicio1"
    assert store.get_effective_mapping("student2", "main.c", exercises) == "ejercicio1"

    # Override específico para un estudiante
    store.set_student_mapping("student2", "main.c", "ejercicio2")
    assert store.get_effective_mapping("student1", "main.c", exercises) == "ejercicio1"
    assert store.get_effective_mapping("student2", "main.c", exercises) == "ejercicio2"

    # Guardar y recargar
    store.save()
    assert (ws / act_slug / "mappings.json").exists()

    reloaded_store = MappingStore(ws, act_slug)
    assert reloaded_store.get_effective_mapping("student2", "main.c", exercises) == "ejercicio2"


def test_interactive_mapper_unmapped_and_all_modes(tmp_path):
    ws = tmp_path
    act_slug = "entrega-1_1228009"
    student1_dir = ws / act_slug / "alumno-uno_111" / "r1"
    student2_dir = ws / act_slug / "alumno-dos_222" / "r1"
    student1_dir.mkdir(parents=True, exist_ok=True)
    student2_dir.mkdir(parents=True, exist_ok=True)

    (student1_dir / "ejercicio1.c").write_text("int main() { return 0; }", encoding="utf-8")
    (student1_dir / "misterioso.c").write_text("void foo() {}", encoding="utf-8")
    (student2_dir / "main.c").write_text("int main() { return 0; }", encoding="utf-8")

    mapper = InteractiveMapper(ws, act_slug)
    exercises = ["ejercicio1", "ejercicio2"]

    # alumno-dos_222 viene antes que alumno-uno_111 por orden alfabético
    # Para main.c (alumno-dos) -> asignar a ejercicio1 (opción 1), global (s)
    # Para misterioso.c (alumno-uno) -> asignar a SPECIAL_AUXILIARY (opción 3), local (n)
    simulated_inputs = ["1", "s", "3", "n"]
    input_iter = iter(simulated_inputs)

    def mock_prompt(_prompt_text: str) -> str:
        return next(input_iter)

    changes = mapper.run_interactive_session(
        available_exercises=exercises,
        unmapped_only=True,
        prompt_fn=mock_prompt,
    )
    assert changes == 2

    # Verificar que se guardó correctamente
    store = MappingStore(ws, act_slug)
    assert store.get_effective_mapping("alumno-dos_222", "main.c", exercises) == "ejercicio1"
    assert store.get_effective_mapping("alumno-uno_111", "misterioso.c", exercises) == SPECIAL_AUXILIARY

