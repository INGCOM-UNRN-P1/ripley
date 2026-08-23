"""Cumulative Markdown report generator using Jinja2 templates."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import jinja2

from ripley import __version__
from ripley.teacher.templates import DEFAULT_TEMPLATES_DIR


@dataclass
class VersionReportContext:
    numero_version: int
    fecha_hora: str
    archivos_nuevos: str
    archivos_modificados: str
    archivos_sin_cambios: str
    archivos_ignorados: str
    diff_unificado: str
    resultados_compilacion: List[Dict[str, str]]
    observaciones_estilo: List[Dict[str, Any]]
    logs_detallados_compilacion: str
    resultados_pruebas: List[Dict[str, Any]]
    nota_preliminar: float
    nota_compilacion: float
    nota_estilo: float
    nota_linter: float
    nota_pruebas: float


@dataclass
class StudentReportContext:
    estudiante_nombre: str
    estudiante_id: str
    actividad_nombre: str
    actividad_id: str
    revision_actual: str
    fecha_generacion: str
    origen_configuracion: str = "Valores por defecto del sistema (ripley.toml no encontrado)"
    versiones: List[VersionReportContext] = field(default_factory=list)
    nota_final_preliminar: float = 0.0


class MarkdownReporter:
    """Genera e incrementa informes en Markdown utilizando plantillas Jinja2."""

    def __init__(self, templates_dir: str | Path = "templates") -> None:
        tpl_path = Path(templates_dir)
        if tpl_path.exists():
            self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tpl_path)))
        else:
            self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(DEFAULT_TEMPLATES_DIR)))

    def render_report(self, ctx: StudentReportContext) -> str:
        header_tpl = self.env.get_template("header.jinja2.md")
        version_tpl = self.env.get_template("version_section.jinja2.md")
        footer_tpl = self.env.get_template("footer.jinja2.md")

        parts: List[str] = []

        # 1. Header
        header_rendered = header_tpl.render(
            estudiante_nombre=ctx.estudiante_nombre,
            estudiante_id=ctx.estudiante_id,
            actividad_nombre=ctx.actividad_nombre,
            actividad_id=ctx.actividad_id,
            revision_actual=ctx.revision_actual,
            fecha_generacion=ctx.fecha_generacion,
            origen_configuracion=ctx.origen_configuracion,
        )
        parts.append(header_rendered.strip())


        # 2. Versiones acumuladas (r1, r2, ...)
        for v_ctx in ctx.versiones:
            v_rendered = version_tpl.render(
                numero_version=v_ctx.numero_version,
                fecha_hora=v_ctx.fecha_hora,
                archivos_nuevos=v_ctx.archivos_nuevos,
                archivos_modificados=v_ctx.archivos_modificados,
                archivos_sin_cambios=v_ctx.archivos_sin_cambios,
                archivos_ignorados=v_ctx.archivos_ignorados,
                diff_unificado=v_ctx.diff_unificado,
                resultados_compilacion=v_ctx.resultados_compilacion,
                observaciones_estilo=v_ctx.observaciones_estilo,
                logs_detallados_compilacion=v_ctx.logs_detallados_compilacion,
                resultados_pruebas=v_ctx.resultados_pruebas,
                nota_preliminar=v_ctx.nota_preliminar,
                nota_compilacion=v_ctx.nota_compilacion,
                nota_estilo=v_ctx.nota_estilo,
                nota_linter=v_ctx.nota_linter,
                nota_pruebas=v_ctx.nota_pruebas,
            )
            parts.append(v_rendered.strip())

        # 3. Footer
        footer_rendered = footer_tpl.render(
            ripley_version=__version__,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            nota_final_preliminar=ctx.nota_final_preliminar,
        )
        parts.append(footer_rendered.strip())

        return "\n\n".join(parts) + "\n"

    def write_student_report(
        self,
        output_file: str | Path,
        ctx: StudentReportContext,
    ) -> Path:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.render_report(ctx)
        out_path.write_text(content, encoding="utf-8")
        return out_path
