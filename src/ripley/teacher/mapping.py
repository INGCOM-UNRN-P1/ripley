"""Interactive and heuristic source-file to testcase exercise mapping module."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

SPECIAL_AUXILIARY = "[AUXILIAR]"
SPECIAL_IGNORE = "[IGNORAR]"


@dataclass
class FileMappingEntry:
    student_slug: str
    filename: str
    file_path: Path
    detected_exercise: Optional[str]
    current_mapping: Optional[str]
    is_ambiguous_or_unmapped: bool


@dataclass
class ActivityMappingConfig:
    activity_slug: str
    global_mappings: Dict[str, str] = field(default_factory=dict)
    student_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)


def heuristic_match(filename: str, available_exercises: List[str]) -> Optional[str]:
    """Infiere el ejercicio correspondiente a partir del nombre del archivo C."""
    if not available_exercises:
        return None

    stem = Path(filename).stem.lower().strip()

    # 1. Coincidencia exacta
    for ex in available_exercises:
        if stem == ex.lower():
            return ex

    # 2. Extracción de dígitos (ej. "ej1", "ej_1", "punto1", "tp1_1" -> coincide con "ejercicio1")
    file_digits = re.findall(r"\d+", stem)
    if file_digits:
        target_num = file_digits[-1]
        matching_exercises = [
            ex for ex in available_exercises if target_num in re.findall(r"\d+", ex)
        ]
        if len(matching_exercises) == 1:
            return matching_exercises[0]

    # 3. Coincidencia de subcadena única
    substring_matches = [
        ex for ex in available_exercises if ex.lower() in stem or stem in ex.lower()
    ]
    if len(substring_matches) == 1:
        return substring_matches[0]

    # Si hay un solo ejercicio disponible en toda la actividad y el archivo es main.c o tp.c
    if len(available_exercises) == 1 and stem in ("main", "tp", "tarea", "entrega", "programa"):
        return available_exercises[0]

    return None


class MappingStore:
    """Administra la persistencia de los mapeos de archivos en mappings.json."""

    def __init__(self, workspace_dir: str | Path, activity_slug: str) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.activity_slug = activity_slug
        self.mapping_file = self.workspace_dir / activity_slug / "mappings.json"
        self.config = self.load()

    def load(self) -> ActivityMappingConfig:
        if not self.mapping_file.exists():
            return ActivityMappingConfig(activity_slug=self.activity_slug)

        try:
            data = json.loads(self.mapping_file.read_text(encoding="utf-8"))
            return ActivityMappingConfig(
                activity_slug=data.get("activity_slug", self.activity_slug),
                global_mappings=data.get("global_mappings", {}),
                student_mappings=data.get("student_mappings", {}),
            )
        except Exception:
            return ActivityMappingConfig(activity_slug=self.activity_slug)

    def save(self) -> None:
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "activity_slug": self.config.activity_slug,
            "global_mappings": self.config.global_mappings,
            "student_mappings": self.config.student_mappings,
        }
        self.mapping_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_effective_mapping(
        self,
        student_slug: str,
        filename: str,
        available_exercises: List[str],
    ) -> Optional[str]:
        # 1. Override específico del estudiante
        if student_slug in self.config.student_mappings:
            if filename in self.config.student_mappings[student_slug]:
                return self.config.student_mappings[student_slug][filename]

        # 2. Regla global por nombre de archivo
        if filename in self.config.global_mappings:
            return self.config.global_mappings[filename]

        # 3. Heurística automática
        return heuristic_match(filename, available_exercises)

    def set_student_mapping(self, student_slug: str, filename: str, target: str) -> None:
        if student_slug not in self.config.student_mappings:
            self.config.student_mappings[student_slug] = {}
        self.config.student_mappings[student_slug][filename] = target

    def set_global_mapping(self, filename: str, target: str) -> None:
        self.config.global_mappings[filename] = target


class InteractiveMapper:
    """Herramienta interactiva para revisar y configurar mapeos entre archivos y testcases."""

    def __init__(
        self,
        workspace_dir: str | Path,
        activity_slug: str,
        console: Optional[Console] = None,
    ) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.activity_slug = activity_slug
        self.console = console or Console()
        self.store = MappingStore(workspace_dir, activity_slug)

    def collect_all_student_files(
        self,
        available_exercises: List[str],
    ) -> List[FileMappingEntry]:
        activity_dir = self.workspace_dir / self.activity_slug
        if not activity_dir.exists():
            return []

        entries: List[FileMappingEntry] = []

        for s_dir in sorted(activity_dir.iterdir()):
            if not s_dir.is_dir() or s_dir.name.startswith("."):
                continue

            # Buscar última revisión rN
            rev_dirs = [d for d in s_dir.iterdir() if d.is_dir() and re.match(r"^r\d+$", d.name)]
            if not rev_dirs:
                continue
            latest_rev = sorted(rev_dirs, key=lambda d: int(d.name[1:]))[-1]

            for c_file in sorted(latest_rev.glob("*.c")):
                effective = self.store.get_effective_mapping(
                    s_dir.name, c_file.name, available_exercises
                )
                detected = heuristic_match(c_file.name, available_exercises)
                is_unmapped = effective is None

                entries.append(
                    FileMappingEntry(
                        student_slug=s_dir.name,
                        filename=c_file.name,
                        file_path=c_file,
                        detected_exercise=detected,
                        current_mapping=effective,
                        is_ambiguous_or_unmapped=is_unmapped,
                    )
                )

        return entries

    def run_interactive_session(
        self,
        available_exercises: List[str],
        unmapped_only: bool = False,
        auto_apply: bool = False,
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> int:
        """Ejecuta la revisión interactiva de mapeos. Retorna la cantidad de mapeos modificados."""
        entries = self.collect_all_student_files(available_exercises)

        if not entries:
            self.console.print("[yellow]No se encontraron archivos .c en las revisiones de los estudiantes.[/yellow]")
            return 0

        # Si auto_apply está activo, asignar los que tienen detección heurística no ambigua
        changes_count = 0
        if auto_apply:
            for entry in entries:
                if entry.current_mapping is None and entry.detected_exercise:
                    self.store.set_global_mapping(entry.filename, entry.detected_exercise)
                    entry.current_mapping = entry.detected_exercise
                    entry.is_ambiguous_or_unmapped = False
                    changes_count += 1

        to_review = [e for e in entries if e.is_ambiguous_or_unmapped] if unmapped_only else entries

        self.console.print(
            Panel(
                f"[bold cyan]Mapeo de Ejercicios a Casos de Prueba[/bold cyan]\n"
                f"Actividad: [green]{self.activity_slug}[/green]\n"
                f"Ejercicios disponibles: [yellow]{', '.join(available_exercises) or 'Ninguno'}[/yellow]\n"
                f"Archivos a revisar: [bold]{len(to_review)}[/bold] ({'Solo sin conectar' if unmapped_only else 'Todos'})",
                title="Ripley Interactive Mapper",
            )
        )

        if not to_review:
            self.console.print("[bold green]✓ Todos los archivos ya están correctamente vinculados.[/bold green]")
            if changes_count > 0:
                self.store.save()
            return changes_count

        options_list = list(available_exercises) + [SPECIAL_AUXILIARY, SPECIAL_IGNORE]

        for idx, entry in enumerate(to_review, start=1):
            self.console.print(
                f"\n[bold magenta]─── Archivo {idx}/{len(to_review)} ──────────────────────────────────────[/bold magenta]"
            )
            self.console.print(f"Estudiante: [cyan]{entry.student_slug}[/cyan]")
            self.console.print(f"Archivo:    [bold yellow]{entry.filename}[/bold yellow]")
            current_status = entry.current_mapping or "[red]Sin vincular[/red]"
            self.console.print(f"Estado:     {current_status}")

            # Mostrar vista previa del archivo
            try:
                code_snippet = entry.file_path.read_text(encoding="utf-8", errors="replace")
                lines = code_snippet.splitlines()[:12]
                preview_text = "\n".join(lines)
                if len(code_snippet.splitlines()) > 12:
                    preview_text += "\n// ... [truncado]"
                self.console.print(
                    Panel(
                        Syntax(preview_text, "c", theme="monokai", line_numbers=True),
                        title=f"Vista previa ({entry.filename})",
                        subtitle=f"{len(code_snippet.splitlines())} líneas totales",
                    )
                )
            except Exception as e:
                self.console.print(f"[dim]No se pudo generar vista previa: {e}[/dim]")

            # Menú de opciones
            self.console.print("\n[bold]Opciones de asignación:[/bold]")
            for opt_idx, opt in enumerate(options_list, start=1):
                self.console.print(f"  [bold cyan]{opt_idx})[/bold cyan] {opt}")
            self.console.print(f"  [bold cyan]{len(options_list) + 1})[/bold cyan] [Crear nuevo ejercicio]")
            self.console.print("  [bold yellow]s)[/bold yellow] Saltar")
            self.console.print("  [bold red]q)[/bold red] Guardar y Salir")

            # Solicitar elección
            prompt_text = "Seleccioná una opción"
            if prompt_fn:
                choice = prompt_fn(prompt_text).strip()
            else:
                choice = Prompt.ask(prompt_text, default="s").strip()

            if choice.lower() == "q":
                self.console.print("[yellow]Guardando cambios y saliendo...[/yellow]")
                break
            elif choice.lower() == "s":
                continue

            selected_target: Optional[str] = None
            if choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(options_list):
                    selected_target = options_list[num - 1]
                elif num == len(options_list) + 1:
                    new_ex_prompt = "Ingresá el nombre del nuevo ejercicio (ej. ejercicio3):"
                    new_ex = (
                        prompt_fn(new_ex_prompt).strip()
                        if prompt_fn
                        else Prompt.ask(new_ex_prompt).strip()
                    )
                    if new_ex:
                        selected_target = new_ex
                        if new_ex not in available_exercises:
                            available_exercises.append(new_ex)
                            options_list.insert(-2, new_ex)

            if selected_target:
                # Preguntar si aplicar globalmente o solo al estudiante
                scope_prompt = f"¿Aplicar regla global para todos los '{entry.filename}'? (s/n)"
                if prompt_fn:
                    apply_global = prompt_fn(scope_prompt).strip().lower() in ("s", "y", "si", "yes")
                else:
                    apply_global = Confirm.ask(scope_prompt, default=True)

                if apply_global:
                    self.store.set_global_mapping(entry.filename, selected_target)
                    self.console.print(
                        f"[green]✓ Regla global configurada:[/green] '{entry.filename}' -> [bold]{selected_target}[/bold]"
                    )
                else:
                    self.store.set_student_mapping(entry.student_slug, entry.filename, selected_target)
                    self.console.print(
                        f"[green]✓ Regla local configurada:[/green] [{entry.student_slug}] '{entry.filename}' -> [bold]{selected_target}[/bold]"
                    )

                entry.current_mapping = selected_target
                entry.is_ambiguous_or_unmapped = False
                changes_count += 1

        self.store.save()
        self.console.print(f"\n[bold green]Mapeos guardados exitosamente en '{self.store.mapping_file}'.[/bold green]\n")
        return changes_count
