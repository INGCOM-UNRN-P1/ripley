"""Genera golden.json: las observaciones de P1RuleChecker sobre los fuentes de caracterización (N-ECO-16).

Se generó antes de partir `P1RuleChecker.analyze` (391 líneas) en una función por regla, para que
test_caracterizacion_p1.py verifique que el refactor no cambió ninguna observación ni su orden.
Regenerarlo solo cuando un cambio de comportamiento sea intencional:
uv run python tests/caracterizacion/generar_golden.py
"""

from __future__ import annotations

import json
from dataclasses import astuple
from pathlib import Path

from ripley.core.p1_rules import P1RuleChecker

RAIZ = Path(__file__).resolve().parents[2]
AQUI = Path(__file__).resolve().parent


def fuentes() -> list[Path]:
    return sorted([*AQUI.glob("*.c"), RAIZ / "tests" / "golden" / "violaciones.c"])


def observaciones(ruta: Path) -> list[list]:
    codigo = ruta.read_text(encoding="utf-8")
    return [list(astuple(o)) for o in P1RuleChecker().analyze(codigo, ruta.name)]


def main() -> None:
    golden = {r.relative_to(RAIZ).as_posix(): observaciones(r) for r in fuentes()}
    (AQUI / "golden.json").write_text(json.dumps(golden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(golden)} fuentes, {sum(len(v) for v in golden.values())} observaciones")


if __name__ == "__main__":
    main()
