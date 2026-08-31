"""Generador de badges SVG de calificación pedagógica para Ripley."""

from __future__ import annotations


def calcular_puntaje_calidad(analisis_resultado: Any) -> float:
    """Calcula un puntaje del 0.0 al 10.0 basado en compilación, pruebas y hallazgos AST."""
    comp = getattr(analisis_resultado, "compilation", {}) or {}
    if not comp.get("success", False):
        return 0.0
        
    findings = getattr(analisis_resultado, "ast_findings", []) or []
    tests = getattr(analisis_resultado, "tests", {}) or {}
    
    score = 10.0
    
    # Penalizaciones por hallazgos AST
    for f in findings:
        sev = str(f.get("severity", "")).upper()
        if "ERROR" in sev:
            score -= 2.5
        elif "WARN" in sev or "ADVERTENCIA" in sev:
            score -= 0.8
        else:
            score -= 0.3
            
    # Penalizaciones por tests fallidos
    total_tests = tests.get("total", 0)
    passed_tests = tests.get("passed", 0)
    if total_tests > 0:
        pct_passed = passed_tests / total_tests
        score = score * (0.4 + 0.6 * pct_passed)
        
    return max(0.0, min(10.0, round(score, 1)))


def generar_badge_svg(puntaje: float, label: str = "ripley") -> str:
    """Genera un SVG flat compatible con Shields.io / GitHub badges."""
    if puntaje >= 9.0:
        color = "#4c1"  # Bright green
        texto_estado = f"{puntaje}/10 PASS"
    elif puntaje >= 7.0:
        color = "#97CA00"  # Green
        texto_estado = f"{puntaje}/10 BUENO"
    elif puntaje >= 5.0:
        color = "#dfb317"  # Yellow
        texto_estado = f"{puntaje}/10 REGULAR"
    else:
        color = "#e05d44"  # Red
        texto_estado = f"{puntaje}/10 REVISAR"
        
    label_width = len(label) * 7 + 12
    value_width = len(texto_estado) * 7 + 14
    total_width = label_width + value_width
    label_center = label_width / 2
    value_center = label_width + (value_width / 2)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h{label_width}v20H0z"/>
    <path fill="{color}" d="M{label_width} 0h{value_width}v20H{label_width}z"/>
    <path fill="url(#b)" d="M0 0h{total_width}v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_center}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_center}" y="14">{label}</text>
    <text x="{value_center}" y="15" fill="#010101" fill-opacity=".3">{texto_estado}</text>
    <text x="{value_center}" y="14">{texto_estado}</text>
  </g>
</svg>"""
    return svg
