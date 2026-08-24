"""Teacher audit workflow: explicit submission states with an append-only trail.

Máquina de estados por (actividad, alumno):

    ingresada ──▶ evaluada ──▶ en_revision ──▶ calificada ──▶ publicada
                    │              │                            │
                    │              ├──▶ observada               ▼
                    ├──▶ sospechosa◀┘                        apelada
                    │              └────────────▶ en_revision
                    └── observada ──(reentrega)──▶ ingresada

Reglas:
  · Solo se permiten transiciones declaradas (``--force`` las salta pero
    queda registrado como forzado en la bitácora).
  * Cada cambio escribe un evento append-only con actor, nota y timestamp.
  * `publicada` habilita la apelación del estudiante; la apelación reabre
    el ciclo en revisión.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import getpass
from pathlib import Path
from typing import Dict, List, Optional

from ripley.teacher.db import DatabaseManager

ESTADOS = {
    "ingresada": "Entrega incorporada al workspace, pendiente de evaluación automática.",
    "evaluada": "Evaluación automática ejecutada; requiere mirada docente.",
    "en_revision": "Revisión manual docente en curso.",
    "observada": "Con observaciones: espera aclaración o reentrega del estudiante.",
    "sospechosa": "Marcada por detección de plagio u otra irregularidad; requiere veredicto.",
    "calificada": "Nota final asignada por el docente; lista para publicar.",
    "publicada": "Nota visible para el estudiante. Único estado desde donde puede apelar.",
    "apelada": "El estudiante disputó la nota; vuelve al circuito de revisión.",
}

TRANSICIONES: Dict[str, set] = {
    "ingresada": {"evaluada", "en_revision"},
    "evaluada": {"en_revision", "sospechosa", "calificada"},
    "en_revision": {"observada", "calificada", "sospechosa"},
    "observada": {"en_revision", "ingresada"},  # reentrega → re-ingesta
    "sospechosa": {"en_revision"},  # tras veredicto humano
    "calificada": {"publicada", "en_revision"},  # arrepentimiento previo a publicar
    "publicada": {"apelada"},
    "apelada": {"en_revision"},
}


class EstadoInvalido(ValueError):
    pass


class TransicionInvalida(ValueError):
    def __init__(self, actual: str, destino: str, permitidas: set) -> None:
        self.actual = actual
        self.destino = destino
        self.permitidas = sorted(permitidas)
        super().__init__(
            f"Transición inválida: '{actual}' → '{destino}'. "
            f"Destinos permitidos: {', '.join(self.permitidas) or '(ninguno)'} "
            f"(usá --force para forzarla dejando registro)."
        )


@dataclass(frozen=True)
class AuditEvent:
    id: int
    actividad: str
    alumno: str
    estado_anterior: Optional[str]
    estado_nuevo: str
    actor: str
    nota: str
    forzado: bool
    created_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_actor() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "desconocido"


class AuditWorkflow:
    """Fachada del flujo de auditoría sobre las bases por alumno del workspace.

    Respeta la convención existente de Ripley: cada carpeta
    ``<workspace>/entregas/<actividad>/<alumno>/.metadata.db`` contiene su
    propia base; el tablero agrega recorriendo esas carpetas (mismo patrón
    que el exportador).
    """

    def __init__(self, workspace_dir: Path | str = ".", actor: Optional[str] = None) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.default_actor = actor or default_actor()

    def student_db_path(self, actividad: str, alumno: str) -> Path:
        return self.workspace_dir / "entregas" / actividad / alumno / ".metadata.db"

    def _db(self, actividad: str, alumno: str) -> DatabaseManager:
        return DatabaseManager(self.student_db_path(actividad, alumno))

    # ------------------------------------------------------------------
    def estado_actual(self, actividad: str, alumno: str) -> str:
        """Estado vigente; una entrega nunca vista arranca en 'ingresada'."""
        return self._db(actividad, alumno).get_submission_state(actividad, alumno) or "ingresada"

    def validar_destino(self, destino: str) -> None:
        if destino not in ESTADOS:
            raise EstadoInvalido(
                f"Estado desconocido: {destino!r}. Estados válidos: {', '.join(sorted(ESTADOS))}"
            )

    def transicionar(
        self,
        actividad: str,
        alumno: str,
        destino: str,
        nota: str = "",
        actor: Optional[str] = None,
        force: bool = False,
    ) -> AuditEvent:
        self.validar_destino(destino)
        actual = self.estado_actual(actividad, alumno)

        if destino == actual:
            raise EstadoInvalido(f"La entrega ya se encuentra en estado '{actual}'.")
        permitidas = TRANSICIONES.get(actual, set())
        if destino not in permitidas and not force:
            raise TransicionInvalida(actual, destino, permitidas)

        who = actor or self.default_actor
        db = self._db(actividad, alumno)
        db.set_submission_state(actividad, alumno, destino)
        event_id = db.insert_audit_event(
            actividad=actividad,
            alumno=alumno,
            estado_anterior=actual,
            estado_nuevo=destino,
            actor=who,
            nota=nota,
            forzado=force and destino not in permitidas,
        )
        return AuditEvent(
            id=event_id,
            actividad=actividad,
            alumno=alumno,
            estado_anterior=actual,
            estado_nuevo=destino,
            actor=who,
            nota=nota,
            forzado=bool(force and destino not in permitidas),
            created_at=_now_iso(),
        )

    # ------------------------------------------------------------------
    def historia(self, actividad: str, alumno: str) -> List[AuditEvent]:
        rows = self._db(actividad, alumno).get_audit_history(actividad, alumno)
        return [
            AuditEvent(
                id=r["id"],
                actividad=actividad,
                alumno=alumno,
                estado_anterior=r["estado_anterior"],
                estado_nuevo=r["estado_nuevo"],
                actor=r["actor"],
                nota=r["nota"],
                forzado=bool(r["forzado"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def alumnos_de_actividad(self, actividad: str) -> List[str]:
        """Slugs de alumnos con carpeta de entrega para la actividad."""
        base = self.workspace_dir / "entregas" / actividad
        if not base.exists():
            return []
        return sorted(d.name for d in base.iterdir() if d.is_dir() and not d.name.startswith("."))

    def tablero(self, actividad: str) -> Dict[str, List[Dict[str, str]]]:
        """Estados → lista de alumnos con su última actualización.

        Alumnos con carpeta pero sin registro previo figuran como 'ingresada'.
        """
        board: Dict[str, List[Dict[str, str]]] = {estado: [] for estado in ESTADOS}
        for alumno in self.alumnos_de_actividad(actividad):
            estado = self.estado_actual(actividad, alumno)
            updated = ""
            rows = self._db(actividad, alumno).list_activity_states(actividad)
            for r in rows:
                if r["alumno"] == alumno:
                    updated = r["updated_at"]
            board.setdefault(estado, []).append({"alumno": alumno, "updated_at": updated})
        return board

    def publicar_calificadas(self, actividad: str, nota: str = "", actor: Optional[str] = None) -> List[AuditEvent]:
        """Transición masiva calificada → publicada. Devuelve los eventos aplicados."""
        eventos: List[AuditEvent] = []
        for alumno in self.alumnos_de_actividad(actividad):
            if self.estado_actual(actividad, alumno) == "calificada":
                eventos.append(
                    self.transicionar(actividad, alumno, "publicada", nota=nota, actor=actor)
                )
        return eventos
