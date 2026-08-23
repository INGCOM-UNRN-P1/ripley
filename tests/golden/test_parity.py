"""Golden parity: registry-driven execution must match direct analyzer invocation.

Garantiza que el estudiante (pipeline/registro) ve exactamente las mismas
observaciones que el flujo docente directo, evitando divergencias futuras
entre ambos caminos.
"""

from pathlib import Path

from ripley.core.ast_auditors import (
    BackwardGotoLinter,
    DeprecatedAPILinter,
    LoopTerminationLinter,
    StringLiteralWriteLinter,
)
from ripley.core.padding_audit import StructPaddingAuditor
import ripley.pipeline.checks  # noqa: F401  (pobla el catálogo)
from ripley.pipeline.registry import get, iter_uniform_static
from ripley.teacher.pack import _enabled_check_ids

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "violaciones.c"

# Analizador directo ↔ check_id del registro (mismo orden de evaluación estable)
DIRECT_PAIRS = {
    "ast.backward_goto": BackwardGotoLinter,
    "ast.deprecated_api": DeprecatedAPILinter,
    "ast.loop_termination": LoopTerminationLinter,
    "ast.string_literal_write": StringLiteralWriteLinter,
    "core.struct_padding": StructPaddingAuditor,
}


def _observations_via_registry(code: str) -> dict:
    """Camino estudiante/docente moderno: catálogo del registro."""
    out: dict = {}
    for spec in iter_uniform_static():
        if spec.check_id not in DIRECT_PAIRS:
            continue
        obs = spec.runner(code, GOLDEN.name)
        out[spec.check_id] = sorted((o.line, o.severity, o.message) for o in obs)
    return out


def _observations_direct(code: str) -> dict:
    """Camino clásico: instancias directas de cada analizador."""
    out: dict = {}
    for check_id, cls in DIRECT_PAIRS.items():
        analyzer = cls()
        obs = analyzer.analyze(code, GOLDEN.name)
        out[check_id] = sorted((o.line, o.severity, o.message) for o in obs)
    return out


def test_golden_file_has_expected_violations():
    code = GOLDEN.read_text(encoding="utf-8")
    reg = _observations_via_registry(code)
    assert any(l for l, _, _ in reg["ast.backward_goto"])
    assert len(reg["ast.deprecated_api"]) >= 1          # gets()
    assert any("rodata" in m for _, _, m in reg["ast.string_literal_write"])
    assert len(reg["ast.loop_termination"]) == 1
    assert len(reg["core.struct_padding"]) == 1


def test_registry_matches_direct_analyzers():
    code = GOLDEN.read_text(encoding="utf-8")
    assert _observations_via_registry(code) == _observations_direct(code)


def test_manifest_enables_exactly_the_golden_checks():
    """Con todos los toggles activos, el manifiesto debe incluir los checks dorados."""
    from dataclasses import replace as dc_replace

    from ripley.config import AstAuditorsConfig, PaddingAuditConfig, RipleyConfig

    cfg = RipleyConfig(
        ast_auditors=AstAuditorsConfig(enabled=True),
        padding=PaddingAuditConfig(enabled=True),
    )
    enabled = set(_enabled_check_ids(cfg))
    for check_id in DIRECT_PAIRS:
        assert check_id in enabled, f"{check_id} falta en el manifiesto"
