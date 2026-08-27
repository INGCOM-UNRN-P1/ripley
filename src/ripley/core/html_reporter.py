"""Generador de reportes en HTML interactivo autónomo con badges de calificación de cátedra."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def generate_interactive_html_report(
    eval_data: Dict[str, Any],
    output_path: Path,
    title: str = "Informe de Corrección Pedagógica — Cátedra Programación 1",
) -> Path:
    """Genera un archivo HTML interactivo, autónomo y estilizado con badges de calificación."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    student_name = eval_data.get("student", "Estudiante")
    activity_name = eval_data.get("activity", "Entrega Práctica")
    score = eval_data.get("score", 10.0)
    passed = eval_data.get("passed", True)
    date_str = eval_data.get("date", "2026")
    observations = eval_data.get("observations", [])

    # Contar por severidad
    err_count = sum(1 for o in observations if o.get("severity") in ("ERROR", "FATAL"))
    warn_count = sum(1 for o in observations if o.get("severity") == "ADVERTENCIA")
    style_count = sum(1 for o in observations if o.get("severity") in ("ESTILO", "INFO", "SUGGESTION"))

    # Determinar badge principal
    if passed and err_count == 0 and warn_count == 0:
        badge_class = "badge-approved"
        badge_text = "✓ APROBADO (Sobresaliente)"
        header_color = "#10b981"
    elif passed and err_count == 0:
        badge_class = "badge-observations"
        badge_text = "⚠ APROBADO CON OBSERVACIONES"
        header_color = "#f59e0b"
    else:
        badge_class = "badge-rejected"
        badge_text = "✖ REQUIERE CORRECCIÓN (Desaprobado)"
        header_color = "#ef4444"

    obs_cards = []
    for i, obs in enumerate(observations, start=1):
        sev = obs.get("severity", "INFO").upper()
        sev_badge = "sev-error" if sev in ("ERROR", "FATAL") else ("sev-warn" if sev == "ADVERTENCIA" else "sev-style")
        rule_code = obs.get("rule_code") or obs.get("code") or "OBS"
        obs_title = obs.get("title") or obs.get("message") or "Observación"
        obs_msg = obs.get("message", "")
        obs_sug = obs.get("suggestion", "")
        file_p = obs.get("filename") or obs.get("file", "código")
        line_num = obs.get("line") or obs.get("line_number", "—")
        snippet = obs.get("code_snippet") or obs.get("snippet", "")

        card_html = f"""
        <div class="card obs-card" data-severity="{sev}">
            <div class="card-header">
                <span class="badge {sev_badge}">{html.escape(sev)}</span>
                <span class="rule-code">{html.escape(str(rule_code))}</span>
                <span class="card-title">{html.escape(obs_title)}</span>
                <span class="file-loc">📍 {html.escape(str(file_p))}:{html.escape(str(line_num))}</span>
            </div>
            <div class="card-body">
                <p class="obs-msg">{html.escape(obs_msg)}</p>
                {f'<div class="code-box"><pre><code>{html.escape(snippet)}</code></pre></div>' if snippet else ''}
                {f'<div class="suggestion-box"><strong>💡 Sugerencia:</strong> {html.escape(obs_sug)}</div>' if obs_sug else ''}
            </div>
        </div>
        """
        obs_cards.append(card_html)

    obs_html_block = "\n".join(obs_cards) if obs_cards else '<div class="empty-state">🎉 ¡Excelente trabajo! No se detectaron observaciones ni violaciones de estilo.</div>'

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: #334155;
            --color-error: #ef4444;
            --color-warn: #f59e0b;
            --color-style: #3b82f6;
            --color-ok: #10b981;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background-color: var(--bg-primary); color: var(--text-primary); padding: 2rem 1rem; }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        
        .header {{ background: var(--bg-secondary); border-radius: 12px; padding: 1.75rem; border: 1px solid var(--border-color); margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }}
        .header-info h1 {{ font-size: 1.4rem; color: var(--text-primary); margin-bottom: 0.4rem; }}
        .header-info p {{ color: var(--text-secondary); font-size: 0.95rem; }}
        
        .badge {{ padding: 0.35rem 0.8rem; border-radius: 9999px; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; display: inline-block; }}
        .badge-approved {{ background-color: #064e3b; color: #6ee7b7; border: 1px solid #059669; font-size: 1.05rem; padding: 0.6rem 1.2rem; }}
        .badge-observations {{ background-color: #451a03; color: #fcd34d; border: 1px solid #d97706; font-size: 1.05rem; padding: 0.6rem 1.2rem; }}
        .badge-rejected {{ background-color: #450a0a; color: #fca5a5; border: 1px solid #dc2626; font-size: 1.05rem; padding: 0.6rem 1.2rem; }}

        .sev-error {{ background-color: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid var(--color-error); }}
        .sev-warn {{ background-color: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid var(--color-warn); }}
        .sev-style {{ background-color: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid var(--color-style); }}

        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
        .stat-box {{ background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 1.2rem; text-align: center; }}
        .stat-value {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 0.2rem; }}
        .stat-label {{ color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; }}

        .controls {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
        .filter-btn {{ background: var(--bg-secondary); color: var(--text-secondary); border: 1px solid var(--border-color); padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s; }}
        .filter-btn:hover, .filter-btn.active {{ background: #334155; color: #fff; border-color: #64748b; }}

        .card {{ background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 1rem; overflow: hidden; }}
        .card-header {{ padding: 0.9rem 1.2rem; background: rgba(0,0,0,0.15); display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; border-bottom: 1px solid var(--border-color); }}
        .rule-code {{ font-family: monospace; font-weight: 700; color: #38bdf8; background: #0f172a; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }}
        .card-title {{ font-weight: 600; flex-grow: 1; }}
        .file-loc {{ font-family: monospace; color: var(--text-secondary); font-size: 0.85rem; }}
        .card-body {{ padding: 1.2rem; }}
        .obs-msg {{ color: #e2e8f0; font-size: 0.95rem; margin-bottom: 0.75rem; line-height: 1.5; }}
        .code-box {{ background: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; padding: 0.8rem; overflow-x: auto; margin-bottom: 0.75rem; font-family: monospace; font-size: 0.85rem; color: #f1f5f9; }}
        .suggestion-box {{ background: rgba(16, 185, 129, 0.1); border-left: 4px solid var(--color-ok); padding: 0.75rem 1rem; border-radius: 0 4px 4px 0; color: #d1fae5; font-size: 0.9rem; }}

        .empty-state {{ text-align: center; padding: 3rem; background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color); color: #6ee7b7; font-size: 1.1rem; }}
        .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-top: 2rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-info">
                <h1>{html.escape(student_name)} — {html.escape(activity_name)}</h1>
                <p>Cátedra de Programación 1 · {html.escape(date_str)}</p>
            </div>
            <div>
                <span class="badge {badge_class}">{badge_text}</span>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value" style="color: {header_color};">{score:.1f}/10</div>
                <div class="stat-label">Calificación Global</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: var(--color-error);">{err_count}</div>
                <div class="stat-label">Errores Bloqueantes</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: var(--color-warn);">{warn_count}</div>
                <div class="stat-label">Advertencias</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: var(--color-style);">{style_count}</div>
                <div class="stat-label">Estilo / Didáctico</div>
            </div>
        </div>

        <div class="controls">
            <button class="filter-btn active" onclick="filterObs('ALL')">Todos ({len(observations)})</button>
            <button class="filter-btn" onclick="filterObs('ERROR')">Errores ({err_count})</button>
            <button class="filter-btn" onclick="filterObs('ADVERTENCIA')">Advertencias ({warn_count})</button>
            <button class="filter-btn" onclick="filterObs('ESTILO')">Estilo ({style_count})</button>
        </div>

        <div id="obs-container">
            {obs_html_block}
        </div>

        <div class="footer">
            Generado automáticamente por Ripley · Suite de Corrección y Verificación Pedagógica C
        </div>
    </div>

    <script>
        function filterObs(severity) {{
            const cards = document.querySelectorAll('.obs-card');
            const btns = document.querySelectorAll('.filter-btn');
            
            btns.forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');

            cards.forEach(card => {{
                const s = card.getAttribute('data-severity');
                if (severity === 'ALL') {{
                    card.style.display = 'block';
                }} else if (severity === 'ERROR' && (s === 'ERROR' || s === 'FATAL')) {{
                    card.style.display = 'block';
                }} else if (severity === 'ADVERTENCIA' && s === 'ADVERTENCIA') {{
                    card.style.display = 'block';
                }} else if (severity === 'ESTILO' && (s === 'ESTILO' || s === 'INFO' || s === 'SUGGESTION')) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>"""

    output_path.write_text(html_content, encoding="utf-8")
    return output_path
