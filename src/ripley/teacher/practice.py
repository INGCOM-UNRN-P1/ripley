"""Practice and assignment initialization and management module."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
try:
    import tomli_w
except ImportError:
    class _TomliWFallback:
        @staticmethod
        def dumps(d: dict) -> str:
            lines = []
            for section, vals in d.items():
                if isinstance(vals, dict):
                    lines.append(f"[{section}]")
                    for k, v in vals.items():
                        if isinstance(v, bool):
                            lines.append(f"{k} = {'true' if v else 'false'}")
                        elif isinstance(v, (int, float)):
                            lines.append(f"{k} = {v}")
                        elif isinstance(v, str):
                            lines.append(f'{k} = "{v}"')
                        elif isinstance(v, list):
                            items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in v)
                            lines.append(f"{k} = [{items}]")
                    lines.append("")
            return "\n".join(lines)
    tomli_w = _TomliWFallback()

from slugify import slugify

from ripley.config import RipleyConfig, load_config
from ripley.tools.testcases import create_testcase_skeleton


@dataclass
class ExerciseTemplateSpec:
    slug: str
    title: str
    description: str
    cases_count: int = 2
    with_argv: bool = False
    forbidden_calls: List[str] = field(default_factory=list)


@dataclass
class PracticeSpec:
    name: str
    practice_id: str
    description: str
    exercises: List[ExerciseTemplateSpec]
    rubric_compilation: float = 0.25
    rubric_linter: float = 0.25
    rubric_style: float = 0.15
    rubric_tests: float = 0.35

    @property
    def slug(self) -> str:
        base_slug = slugify(self.name)
        return f"{base_slug}_{self.practice_id}" if self.practice_id else base_slug


def generate_enunciado_general(spec: PracticeSpec) -> str:
    lines = [
        f"# {spec.name}",
        f"**Identificador:** `{spec.practice_id or 'Sin ID'}` | **Fecha de Publicación:** {datetime.now().strftime('%d/%m/%Y')}",
        "",
        "## 1. Descripción y Objetivos",
        spec.description or "Implementar los ejercicios requeridos en lenguaje C cumpliendo con las pautas de estilo y robustez.",
        "",
        "## 2. Ejercicios Incluidos",
    ]
    for idx, ex in enumerate(spec.exercises, start=1):
        lines.append(f"{idx}. **[{ex.slug}](./ejercicios/{ex.slug}/enunciado.md):** {ex.title}")

    lines.extend(
        [
            "",
            "## 3. Pautas de Entrega",
            "- Subir los archivos fuente `.c` y encabezados `.h` a la actividad correspondiente de Moodle.",
            "- El código debe compilar con `gcc` empleando `-Wall -Wextra -pedantic -std=c11`.",
            "- No se permiten archivos ejecutables (`.exe`), comprimidos anidados ni documentos PDF.",
            "- Consultar las [Pautas de Evaluación](./pautas_evaluacion.md) para conocer el desglose de calificación.",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_pautas_evaluacion(spec: PracticeSpec) -> str:
    lines = [
        f"# Pautas de Evaluación - {spec.name}",
        "",
        "## 1. Criterios de Corrección y Desglose de Calificación",
        "La evaluación cuantitativa preliminar se calcula en una escala de 0 a 10 con los siguientes pesos:",
        "",
        f"- **Compilación sin errores ni advertencias (gcc -Wall -Wextra):** {int(spec.rubric_compilation * 100)}%",
        f"- **Pruebas de Entrada/Salida y Casos de Borde:** {int(spec.rubric_tests * 100)}%",
        f"- **Análisis Estático y Reglas de Calidad (Cppcheck):** {int(spec.rubric_linter * 100)}%",
        f"- **Cumplimiento de Estilo y Formato de Código:** {int(spec.rubric_style * 100)}%",
        "",
        "## 2. Aspectos Clave a Evaluar",
        "1. **Manejo de Recursos y Memoria:** Todo bloque solicitado con `malloc` debe ser liberado con `free`. No deben registrarse fugas ni lecturas inválidas en Valgrind.",
        "2. **Estilo de Código C:**",
        "   - Estilo de llaves consistente (Allman/K&R).",
        "   - Uso obligatorio de llaves `{}` en todas las estructuras de control.",
        "   - Sangría uniforme (4 espacios) sin tabulaciones mezcladas.",
        "   - Espaciado adecuado en operadores y palabras clave.",
        "3. **Seguridad y Modularidad:**",
        "   - Prohibido el uso de llamadas al sistema no autorizadas (`system()`, `fork()`, `popen()`).",
        "   - Modularización en funciones con responsabilidades acotadas.",
    ]
    return "\n".join(lines) + "\n"


def generate_enunciado_ejercicio(ex: ExerciseTemplateSpec) -> str:
    lines = [
        f"# Ejercicio: {ex.title}",
        f"**Identificador:** `{ex.slug}`",
        "",
        "## 1. Consigna",
        ex.description or "Escribir un programa en C que resuelva el problema especificado.",
        "",
        "## 2. Entrada y Salida",
        "- **Entrada (`stdin` / `argv`):** Leer los datos de entrada según el formato requerido.",
        "- **Salida (`stdout`):** Imprimir la respuesta exacta sin textos superfluos.",
        "",
        "## 3. Restricciones Específicas",
    ]
    if ex.forbidden_calls:
        lines.append(f"- Funciones prohibidas: `{', '.join(ex.forbidden_calls)}`")
    else:
        lines.append("- No se aplican restricciones adicionales más allá de las generales de la materia.")

    lines.extend(
        [
            "",
            "## 4. Ejemplos de Prueba",
            "```text",
            "Entrada:",
            "10 20",
            "Salida:",
            "30",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_solucion_modelo_c(ex: ExerciseTemplateSpec) -> str:
    return f"""/*
 * Solución Modelo de Referencia
 * Ejercicio: {ex.title} ({ex.slug})
 */

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[])
{{
    (void)argc;
    (void)argv;

    int a = 0;
    int b = 0;

    if (scanf("%d %d", &a, &b) == 2)
    {{
        printf("%d\\n", a + b);
    }}

    return 0;
}}
"""


def init_practice(
    spec: PracticeSpec,
    base_dir: str | Path = "practicas",
    force: bool = False,
) -> Path:
    """Inicializa la estructura completa de una práctica en el directorio ./practicas/<slug_practica>/."""

    practicas_root = Path(base_dir)
    practice_dir = practicas_root / spec.slug

    if practice_dir.exists() and not force:
        raise FileExistsError(f"La práctica ya existe en '{practice_dir}'. Usá --force para sobrescribir.")

    practice_dir.mkdir(parents=True, exist_ok=True)

    # 1. Archivo de configuración ripley.toml para la práctica
    practice_cfg = load_config()
    practice_cfg.rubric.peso_compilacion = spec.rubric_compilation
    practice_cfg.rubric.peso_linter = spec.rubric_linter
    practice_cfg.rubric.peso_estilo = spec.rubric_style
    practice_cfg.rubric.peso_pruebas = spec.rubric_tests

    # Serializar ripley.toml en la carpeta de la práctica
    config_dict = {
        "compiler": {
            "executable": practice_cfg.compiler.executable,
            "flags": practice_cfg.compiler.flags,
        },
        "limits": {
            "timeout_segundos": practice_cfg.limits.timeout_segundos,
            "limite_memoria_mb": practice_cfg.limits.limite_memoria_mb,
            "max_tamano_ejecutable_mb": practice_cfg.limits.max_tamano_ejecutable_mb,
        },
        "style": {
            "brace_style": practice_cfg.style.brace_style,
            "require_braces": practice_cfg.style.require_braces,
            "indent_style": practice_cfg.style.indent_style,
            "indent_size": practice_cfg.style.indent_size,
            "spacing_operators": practice_cfg.style.spacing_operators,
            "spacing_keywords": practice_cfg.style.spacing_keywords,
            "no_trailing_whitespace": practice_cfg.style.no_trailing_whitespace,
            "max_blank_lines": practice_cfg.style.max_blank_lines,
        },
        "rubric": {
            "peso_compilacion": spec.rubric_compilation,
            "peso_linter": spec.rubric_linter,
            "peso_estilo": spec.rubric_style,
            "peso_pruebas": spec.rubric_tests,
        },
        "valgrind": {
            "enabled": practice_cfg.valgrind.enabled,
            "flags": practice_cfg.valgrind.flags,
        },
        "cppcheck": {
            "ejecutable": practice_cfg.cppcheck.ejecutable,
            "parametros": practice_cfg.cppcheck.parametros,
            "reglas_python": practice_cfg.cppcheck.reglas_python,
        },
        "security": {
            "forbidden_calls": practice_cfg.security.forbidden_calls,
            "forbidden_headers": practice_cfg.security.forbidden_headers,
        },
    }
    (practice_dir / "ripley.toml").write_text(
        tomli_w.dumps(config_dict),
        encoding="utf-8",
    )

    # 2. Enunciado general y pautas de evaluación
    (practice_dir / "enunciado.md").write_text(generate_enunciado_general(spec), encoding="utf-8")
    (practice_dir / "pautas_evaluacion.md").write_text(generate_pautas_evaluacion(spec), encoding="utf-8")

    # 3. Ejercicios, soluciones modelo y casos de prueba
    ejercicios_dir = practice_dir / "ejercicios"
    ejercicios_dir.mkdir(parents=True, exist_ok=True)

    for ex in spec.exercises:
        ex_dir = ejercicios_dir / ex.slug
        ex_dir.mkdir(parents=True, exist_ok=True)

        (ex_dir / "enunciado.md").write_text(generate_enunciado_ejercicio(ex), encoding="utf-8")
        (ex_dir / "solucion_modelo.c").write_text(generate_solucion_modelo_c(ex), encoding="utf-8")

        # Casos de prueba locales dentro de la práctica
        tests_dir = ex_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        for i in range(1, ex.cases_count + 1):
            in_f = tests_dir / f"caso{i}.in"
            out_f = tests_dir / f"caso{i}.out"
            if not in_f.exists() or force:
                in_f.write_text(f"{i * 10} {i * 20}\n", encoding="utf-8")
            if not out_f.exists() or force:
                out_f.write_text(f"{i * 30}\n", encoding="utf-8")
            if ex.with_argv:
                argv_f = tests_dir / f"caso{i}.argv"
                if not argv_f.exists() or force:
                    argv_f.write_text(f"--test {i}\n", encoding="utf-8")

    return practice_dir


def sync_practice_testcases(practice_dir: Path | str) -> int:
    """Verifica y contabiliza los casos de prueba existentes dentro de practicas/<slug>/ejercicios/*/tests/."""
    p_dir = Path(practice_dir)

    ejercicios_dir = p_dir / "ejercicios"
    if not ejercicios_dir.exists():
        return 0

    valid_cases_count = 0
    for ex_dir in ejercicios_dir.iterdir():
        if not ex_dir.is_dir():
            continue
        ex_tests = ex_dir / "tests"
        if not ex_tests.exists():
            continue

        for file in ex_tests.iterdir():
            if file.is_file() and file.name.startswith("caso") and file.suffix in (".in", ".out", ".argv"):
                valid_cases_count += 1

    return valid_cases_count



def list_practices(base_dir: str | Path = "practicas") -> List[Dict[str, Any]]:
    """Lista las prácticas existentes en el directorio ./practicas/."""
    practicas_root = Path(base_dir)
    if not practicas_root.exists():
        return []

    summaries: List[Dict[str, Any]] = []

    for p_dir in sorted(practicas_root.iterdir()):
        if not p_dir.is_dir() or p_dir.name.startswith("."):
            continue

        has_config = (p_dir / "ripley.toml").exists()
        has_enunciado = (p_dir / "enunciado.md").exists()
        has_pautas = (p_dir / "pautas_evaluacion.md").exists()

        ejercicios_dir = p_dir / "ejercicios"
        exercises: List[str] = []
        if ejercicios_dir.exists():
            exercises = [d.name for d in sorted(ejercicios_dir.iterdir()) if d.is_dir()]

        summaries.append(
            {
                "slug": p_dir.name,
                "path": str(p_dir),
                "has_config": has_config,
                "has_enunciado": has_enunciado,
                "has_pautas": has_pautas,
                "exercises_count": len(exercises),
                "exercises": exercises,
            }
        )

    return summaries
