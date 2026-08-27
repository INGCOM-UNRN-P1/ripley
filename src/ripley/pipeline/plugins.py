"""Lifecycle plugin system: user code in ``plugins/`` hooked into Ripley phases.

Convenciones:
  · Los plugins son archivos ``*.py`` dentro de ``<workspace>/plugins/``
    (o junto a las fuentes verificadas). Se cargan en orden alfabético.
  · Un plugin participa declarando funciones con el nombre exacto del hook;
    las que no declara simplemente no se invocan.
  * El contexto (:class:`PluginContext`) es mutable: los plugins pueden
    agregar observaciones o anotaciones en ``results``.
  · Una excepción en un plugin NO interrumpe el flujo (fail-open): se cuenta
    como error y se continúa con los demás salvo ``strict=True``.
  * Escape hatch universal: variable de entorno ``RIPLEY_DISABLE_PLUGINS=1``.

Hooks disponibles (fases del ciclo de vida):
    session_start   inicio de una corrida completa
    pre_compile     antes de compilar las fuentes
    post_compile    después de compilar (ctx.results["compile"] disponible)
    pre_checks      antes de ejecutar los checks estáticos
    post_checks     después de los checks (ctx.observations poblado)
    pre_report      antes de armar el informe final
    post_report     después del informe
    session_end     cierre de la corrida

Compatibilidad con git hooks: ``ripley-check plugins git-hook install
pre-commit`` instala un shim ejecutable que despacha el hook ``pre_commit_git``
con los fuentes ``.c`` stageados, bloqueando el commit si hay hallazgos ERROR.
"""

from dataclasses import dataclass, field
import importlib.util
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

DISABLE_ENV = "RIPLEY_DISABLE_PLUGINS"

HOOKS = (
    "session_start",
    "pre_compile",
    "post_compile",
    "pre_checks",
    "post_checks",
    "pre_report",
    "post_report",
    "session_end",
    # Hook especial disparado por el shim de git (no forma parte de run_bundle):
    "pre_commit_git",
)


@dataclass
class PluginContext:
    """Estado compartido pasado a cada hook durante una corrida."""

    phase: str
    workspace_dir: Path
    sources: List[Path] = field(default_factory=list)
    activity: Optional[str] = None
    observations: List[dict] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.results[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.results.get(key, default)


@dataclass(frozen=True)
class LoadedPlugin:
    name: str
    path: Path
    hooks: Tuple[str, ...]


class PluginError(RuntimeError):
    pass


def plugins_disabled() -> bool:
    return os.environ.get(DISABLE_ENV, "").strip().lower() in ("1", "true", "yes")


def load_plugin_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"ripley_user_plugin_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise PluginError(f"No se pudo cargar el plugin: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scan_hooks_ast(py_path: Path) -> Tuple[str, ...]:
    """Escanea los hooks definidos en el archivo mediante AST sin ejecutar código de nivel superior."""
    try:
        import ast
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
        hooks = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in HOOKS
        ]
        return tuple(hooks)
    except Exception:
        return HOOKS


def discover_plugins(plugins_dir: Path | str) -> List[LoadedPlugin]:
    """Descubre plugins de forma lazy sin ejecutar sus módulos hasta el despacho."""
    d = Path(plugins_dir)
    if not d.is_dir():
        return []
    loaded: List[LoadedPlugin] = []
    for py in sorted(d.glob("*.py")):
        if py.name.startswith("_"):
            continue
        hooks = _scan_hooks_ast(py)
        loaded.append(LoadedPlugin(name=py.stem, path=py, hooks=hooks))
    return loaded


class PluginManager:
    """Carga los plugins una vez y despacha hooks sobre un contexto compartido."""

    def __init__(
        self,
        plugins_dir: Path | str,
        strict: bool = False,
        force_disabled: Optional[bool] = None,
    ) -> None:
        self.plugins_dir = Path(plugins_dir)
        self.strict = strict
        disabled = plugins_disabled() if force_disabled is None else force_disabled
        self.plugins: List[LoadedPlugin] = [] if disabled else discover_plugins(plugins_dir)
        self.errors: List[str] = []

    @property
    def disabled(self) -> bool:
        return not self.plugins and plugins_disabled()

    def has_subscribers(self, hook: str) -> bool:
        return any(hook in p.hooks for p in self.plugins)

    def summary(self) -> List[tuple]:
        return [(p.name, ", ".join(p.hooks) or "-", str(p.path)) for p in self.plugins]

    # ------------------------------------------------------------------
    def dispatch(self, hook: str, ctx: PluginContext, fail_fast: bool = False) -> int:
        """Invoca a todos los suscriptores del hook. Devuelve cantidad de errores."""
        if hook not in HOOKS:
            raise ValueError(f"Hook desconocido: {hook!r}. Válidos: {', '.join(HOOKS)}")
        errors = 0
        ctx.phase = hook
        # Importación por plugin en cada despacho: permite editar el archivo
        # entre corridas sin reiniciar el proceso.
        for plugin in self.plugins:
            try:
                module = load_plugin_module(plugin.path)
                handler = getattr(module, hook, None)
                if handler is None:
                    continue
                handler(ctx)
            except Exception as e:  # noqa: BLE001 — fail-open deliberado
                msg = f"[plugin:{plugin.name}] error en {hook}: {e}"
                self.errors.append(msg)
                errors += 1
                if self.strict or fail_fast:
                    raise PluginError(msg) from e
        return errors


# ---------------------------------------------------------------------------
# Integración con git: recolección de staged .c y shim de pre-commit
# ---------------------------------------------------------------------------
GIT_SHIM_TEMPLATE = """\
#!/bin/sh
# Instalado por Ripley ({date}) — no editar a mano; usar:
#   ripley-check plugins git-hook uninstall {hook}
if command -v ripley-check >/dev/null 2>&1; then
    exec ripley-check plugins dispatch {dispatch_hook} --git-staged{extra} "$@"
fi
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/ripley-check" ]; then
    exec "$VIRTUAL_ENV/bin/ripley-check" plugins dispatch {dispatch_hook} --git-staged{extra} "$@"
fi
echo "[ripley] ripley-check no disponible: commit permitido sin verificación" >&2
exit 0
"""


def collect_git_staged_c_sources(repo_dir: Path | str = ".") -> List[Path]:
    """Rutas .c stageadas (added/copied/modified/renamed) según git."""
    repo = Path(repo_dir)
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    out = []
    for line in proc.stdout.splitlines():
        p = line.strip()
        if p.endswith(".c"):
            candidate = repo / p
            if candidate.exists():
                out.append(candidate)
    return out


def git_hook_path(repo_dir: Path | str, hook: str) -> Path:
    return Path(repo_dir) / ".git" / "hooks" / hook


def install_git_hook(
    repo_dir: Path | str,
    hook: str,
    dispatch_hook: str = "pre_commit_git",
    strict: bool = False,
) -> Path:
    """Instala el shim ejecutable preservando cualquier hook previo como .bak."""
    target = git_hook_path(repo_dir, hook)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_suffix(target.suffix + ".ripley.bak")
        backup.write_bytes(target.read_bytes())
    extra = " --strict" if strict else ""
    shim = GIT_SHIM_TEMPLATE.format(date=_now_date(), hook=hook, dispatch_hook=dispatch_hook, extra=extra)
    target.write_text(shim, encoding="utf-8")
    target.chmod(0o755)
    return target


def uninstall_git_hook(repo_dir: Path | str, hook: str) -> bool:
    """Elimina el shim de Ripley; restaura el .bak si existe."""
    target = git_hook_path(repo_dir, hook)
    backup = target.with_suffix(target.suffix + ".ripley.bak")
    if not target.exists():
        return False
    content = target.read_text(encoding="utf-8")
    if "Instalado por Ripley" not in content:
        return False  # hook ajeno: no tocar
    if backup.exists():
        target.write_bytes(backup.read_bytes())
        backup.unlink()
    else:
        target.unlink()
    return True


def is_ripley_git_hook(repo_dir: Path | str, hook: str) -> bool:
    target = git_hook_path(repo_dir, hook)
    return target.exists() and "Instalado por Ripley" in target.read_text(encoding="utf-8", errors="replace")


def _now_date() -> str:
    from datetime import date

    return date.today().isoformat()
