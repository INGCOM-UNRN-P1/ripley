"""Tests for the teacher audit workflow state machine."""

from pathlib import Path

import pytest

from ripley.teacher.audit import (
    ESTADOS,
    AuditWorkflow,
    EstadoInvalido,
    TransicionInvalida,
)


@pytest.fixture()
def workspace(tmp_path):
    """Carpeta de entregas con dos alumnos para la actividad demo."""
    for alumno in ("gonzalo_123", "maria_456"):
        (tmp_path / "entregas" / "entrega-1" / alumno).mkdir(parents=True)
    return tmp_path


def test_estado_inicial_es_ingresada(workspace):
    wf = AuditWorkflow(workspace_dir=workspace)
    assert wf.estado_actual("entrega-1", "gonzalo_123") == "ingresada"


def test_camino_feliz_hasta_publicada(workspace):
    wf = AuditWorkflow(workspace_dir=workspace, actor="profe")
    camino = ["evaluada", "en_revision", "calificada", "publicada"]
    for destino in camino:
        ev = wf.transicionar("entrega-1", "gonzalo_123", destino)
        assert ev.estado_anterior is not None
    historia = wf.historia("entrega-1", "gonzalo_123")
    assert [e.estado_nuevo for e in historia] == camino
    assert historia[0].actor == "profe"
    assert all(not e.forzado for e in historia)


def test_salto_invalido_lista_permitidos(workspace):
    wf = AuditWorkflow(workspace_dir=workspace)
    with pytest.raises(TransicionInvalida) as exc:
        wf.transicionar("entrega-1", "gonzalo_123", "publicada")
    assert "evaluada" in exc.value.permitidas
    assert "en_revision" in exc.value.permitidas
    assert "publicada" not in exc.value.permitidas


def test_force_registra_transicion_forzada(workspace):
    wf = AuditWorkflow(workspace_dir=workspace)
    ev = wf.transicionar("entrega-1", "gonzalo_123", "publicada", force=True, nota="urgencia")
    assert ev.forzado is True
    assert ev.nota == "urgencia"
    assert wf.estado_actual("entrega-1", "gonzalo_123") == "publicada"


def test_mismo_estado_rechazado_con_error_claro(workspace):
    wf = AuditWorkflow(workspace_dir=workspace)
    with pytest.raises(EstadoInvalido, match="ya se encuentra"):
        wf.transicionar("entrega-1", "gonzalo_123", "ingresada")


def test_estado_desconocido_rechazado(workspace):
    wf = AuditWorkflow(workspace_dir=workspace)
    with pytest.raises(EstadoInvalido, match="desconocido"):
        wf.transicionar("entrega-1", "gonzalo_123", "aprobada")


def test_circuito_apelacion_y_observada(workspace):
    wf = AuditWorkflow(workspace_dir=workspace)
    for d in ("evaluada", "en_revision", "calificada", "publicada"):
        wf.transicionar("entrega-1", "gonzalo_123", d)
    wf.transicionar("entrega-1", "gonzalo_123", "apelada")
    assert wf.estado_actual("entrega-1", "gonzalo_123") == "apelada"
    wf.transicionar("entrega-1", "gonzalo_123", "en_revision")

    # observada → reentrega re-ingresa
    wf2 = AuditWorkflow(workspace_dir=workspace)
    for d in ("observada",):
        # desde en_revision actual
        pass
    wf.transicionar("entrega-1", "gonzalo_123", "observada")
    wf.transicionar("entrega-1", "gonzalo_123", "ingresada")
    assert wf.estado_actual("entrega-1", "gonzalo_123") == "ingresada"


def test_tablero_agrega_por_alumno(workspace):
    wf = AuditWorkflow(workspace_dir=workspace, actor="docente2")
    wf.transicionar("entrega-1", "gonzalo_123", "evaluada")
    for d in ("evaluada", "calificada"):
        wf.transicionar("entrega-1", "maria_456", d)
    board = wf.tablero("entrega-1")
    assert len(board["evaluada"]) == 1
    assert len(board["calificada"]) == 1


def test_publicar_masivo_solo_calificadas(workspace):
    wf = AuditWorkflow(workspace_dir=workspace)
    wf.transicionar("entrega-1", "gonzalo_123", "evaluada")
    wf.transicionar("entrega-1", "gonzalo_123", "calificada")
    # maria queda en ingresada
    publicados = wf.publicar_calificadas("entrega-1")
    assert len(publicados) == 1
    assert publicados[0].alumno == "gonzalo_123"
    assert wf.estado_actual("entrega-1", "maria_456") == "ingresada"


def test_todos_los_estados_documentados():
    assert set(TRANSICIONES_KEYS()) == set(ESTADOS.keys())


def TRANSICIONES_KEYS():
    from ripley.teacher.audit import TRANSICIONES

    return TRANSICIONES.keys()


def test_bitacora_sobrevive_reapertura(tmp_path):
    wf = AuditWorkflow(workspace_dir=tmp_path)
    wf.transicionar("act", "alumno_x", "evaluada", nota="auto")
    wf2 = AuditWorkflow(workspace_dir=tmp_path, actor="otro")
    wf2.transicionar("act", "alumno_x", "calificada")
    historia = wf2.historia("act", "alumno_x")
    assert [e.actor for e in historia] == [wf.default_actor, "otro"]
