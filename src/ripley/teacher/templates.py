"""Template manager for Ripley Jinja2 Markdown templates."""

import os
from pathlib import Path
from typing import Dict, List, Tuple
import jinja2
from jinja2 import meta

REQUIRED_TEMPLATES = [
    "header.jinja2.md",
    "version_section.jinja2.md",
    "footer.jinja2.md",
]

CRITICAL_VARIABLES: Dict[str, List[str]] = {
    "header.jinja2.md": [
        "estudiante_nombre",
        "estudiante_id",
        "actividad_nombre",
        "actividad_id",
    ],
    "version_section.jinja2.md": [
        "numero_version",
        "resultados_compilacion",
        "nota_preliminar",
    ],
    "footer.jinja2.md": [
        "ripley_version",
        "timestamp",
        "nota_final_preliminar",
    ],
}

DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "default_templates"


def init_templates(target_dir: str | Path = "templates", force: bool = False) -> List[Path]:
    """Genera o restaura las plantillas Jinja2 por defecto en el directorio especificado."""
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []

    for name in REQUIRED_TEMPLATES:
        src = DEFAULT_TEMPLATES_DIR / name
        dst = target_path / name
        if dst.exists() and not force:
            continue
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            created.append(dst)

    return created


def list_templates(target_dir: str | Path = "templates") -> Dict[str, bool]:
    """Lista las plantillas requeridas e indica si están presentes en la carpeta."""
    target_path = Path(target_dir)
    status: Dict[str, bool] = {}
    for name in REQUIRED_TEMPLATES:
        dst = target_path / name
        status[name] = dst.exists()
    return status


def check_templates(target_dir: str | Path = "templates") -> Tuple[bool, List[str]]:
    """Valida la presencia, sintaxis y variables críticas en snake_case de las plantillas."""
    target_path = Path(target_dir)
    errors: List[str] = []
    env = jinja2.Environment()

    for name in REQUIRED_TEMPLATES:
        template_file = target_path / name
        if not template_file.exists():
            errors.append(f"Falta la plantilla requerida: '{name}' en {target_path}")
            continue

        try:
            content = template_file.read_text(encoding="utf-8")
            ast = env.parse(content)
            undeclared = meta.find_undeclared_variables(ast)
        except jinja2.TemplateSyntaxError as e:
            errors.append(f"Error de sintaxis en '{name}' (línea {e.lineno}): {e.message}")
            continue
        except Exception as e:
            errors.append(f"Error al leer '{name}': {str(e)}")
            continue

        # Verificar variables críticas
        required_vars = CRITICAL_VARIABLES.get(name, [])
        for var in required_vars:
            if var not in undeclared:
                errors.append(f"Plantilla '{name}' no referencia la variable obligatoria '{var}'")

        # Verificar convención snake_case en todas las variables
        for var in undeclared:
            if not var.islower() and not var.replace("_", "").isalnum():
                errors.append(f"Variable '{var}' en '{name}' no sigue la convención snake_case")

    is_valid = len(errors) == 0
    return is_valid, errors
