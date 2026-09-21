"""Supresión de observaciones P1 por comentario (archivo, línea o bloque)."""

import re
from typing import Dict, List, Set, Tuple


from ripley.core.p1_rules import P1RuleObservation


def extract_suppressions(code: str) -> Tuple[Set[str], Dict[int, Set[str]], List[Tuple[int, int, Set[str]]]]:
    """Extrae reglas suprimidas a nivel de archivo, línea o bloque.
    
    Formatos soportados:
      // ripley:disable=0x1001h,0x1002h
      // ripley:disable-line=0x1001h
      // ripley:disable-next-line=0x1001h
      /* ripley:disable=0x1001h */ ... /* ripley:enable=0x1001h */
    """
    file_suppressions: Set[str] = set()
    line_suppressions: Dict[int, Set[str]] = {}
    range_suppressions: List[Tuple[int, int, Set[str]]] = []

    active_ranges: Dict[str, int] = {}
    lines = code.splitlines()

    for idx, line in enumerate(lines, start=1):
        # Directiva de línea o archivo: ripley:disable(=|:)([0-9a-zA-Zx, ]+)
        m_disable = re.findall(r"ripley:disable(?:-line)?\s*[=:]\s*([0-9a-zA-Zx_,\s]+)", line, re.IGNORECASE)
        for group in m_disable:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            if idx <= 5 and re.match(r"^\s*(?://|/\*)\s*ripley:disable", line, re.IGNORECASE):
                file_suppressions.update(codes)
            line_suppressions.setdefault(idx, set()).update(codes)

        m_next = re.findall(r"ripley:disable-next-line\s*[=:]\s*([0-9a-zA-Zx_,\s]+)", line, re.IGNORECASE)
        for group in m_next:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            line_suppressions.setdefault(idx + 1, set()).update(codes)

        m_range_start = re.findall(r"/\*\s*ripley:disable\s*[=:]\s*([0-9a-zA-Zx_,\s]+)\s*\*/", line, re.IGNORECASE)
        for group in m_range_start:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            for c in codes:
                active_ranges[c] = idx

        m_range_end = re.findall(r"/\*\s*ripley:enable\s*[=:]\s*([0-9a-zA-Zx_,\s]+)\s*\*/", line, re.IGNORECASE)
        for group in m_range_end:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            for c in codes:
                if c in active_ranges:
                    range_suppressions.append((active_ranges[c], idx, {c}))
                    del active_ranges[c]

    for c, start_line in active_ranges.items():
        range_suppressions.append((start_line, len(lines) + 1, {c}))

    return file_suppressions, line_suppressions, range_suppressions


def filter_suppressed_observations(
    observations: List[P1RuleObservation],
    code: str,
) -> List[P1RuleObservation]:
    """Filtra observaciones anuladas mediante comentarios de supresión directos."""
    if not observations:
        return []

    file_sup, line_sup, range_sup = extract_suppressions(code)
    filtered = []

    for obs in observations:
        code_norm = obs.rule_code.lower()
        if "all" in file_sup or code_norm in file_sup:
            continue
        if obs.line in line_sup and ("all" in line_sup[obs.line] or code_norm in line_sup[obs.line]):
            continue
        in_range = False
        for start_l, end_l, codes in range_sup:
            if start_l <= obs.line <= end_l and ("all" in codes or code_norm in codes):
                in_range = True
                break
        if in_range:
            continue

        filtered.append(obs)

    return filtered
