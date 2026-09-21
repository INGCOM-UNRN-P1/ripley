"""Sistema de plugins y git hooks de ripley-check."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.table import Table

from ripley.cli._common import console

from ripley.cli.student import app


# ============================================================================
# Sistema de plugins y hooks de ciclo de vida
# ============================================================================

plugins_app = typer.Typer(
    name="plugins",
    help="Plugins de usuario en plugins/: hooks de ciclo de vida y git hooks.",
    no_args_is_help=True,
)
app.add_typer(plugins_app, name="plugins")


@plugins_app.command("list")
def cmd_plugins_list(
    workspace: Path = typer.Option(".", "--dir", "-d", help="Directorio que contiene plugins/."),
) -> None:
    """Lista los plugins descubiertos y los hooks que proveen."""
    from ripley.pipeline.plugins import PluginManager, plugins_disabled

    if plugins_disabled():
        console.print("[yellow]Plugins deshabilitados vía RIPLEY_DISABLE_PLUGINS.[/yellow]")
        return
    manager = PluginManager(workspace / "plugins")
    if not manager.plugins:
        console.print(f"[yellow]Sin plugins en {workspace / 'plugins'}[/yellow]")
        return
    table = Table(title=f"Plugins ({len(manager.plugins)})")
    table.add_column("Plugin", style="cyan")
    table.add_column("Hooks")
    table.add_column("Archivo", style="dim")
    for name, hooks, path in manager.summary():
        table.add_row(name, hooks or "-", path)
    console.print(table)


@plugins_app.command("dispatch")
def cmd_plugins_dispatch(
    hook: str = typer.Argument(..., help="Hook a despachar (session_start, pre_compile, pre_commit_git, ...)."),
    sources: Optional[List[Path]] = typer.Option(None, "--source", "-s", help="Fuentes .c del contexto."),
    git_staged: bool = typer.Option(False, "--git-staged", help="Usar fuentes .c stageadas en git."),
    workspace: Path = typer.Option(".", "--dir", "-d", help="Directorio base (busca plugins/ y git)."),
    strict: bool = typer.Option(False, "--strict", help="Cualquier hallazgo bloquea (exit 1), no solo ERROR."),
) -> None:
    """Despacha un hook manualmente. Usado por el shim de git hook (pre-commit)."""
    from ripley.core.gcc_translator import translate_stderr  # noqa: F401
    from ripley.pipeline.plugins import (
        HOOKS,
        PluginContext,
        PluginManager,
        collect_git_staged_c_sources,
    )

    if hook not in HOOKS:
        console.print(f"[bold red]Hook desconocido: {hook}. Válidos: {', '.join(HOOKS)}[/bold red]")
        raise typer.Exit(code=2)

    srcs = list(sources or [])
    if git_staged and not srcs:
        srcs = collect_git_staged_c_sources(workspace)
        console.print(f"[dim]Staged .c detectados: {len(srcs)}[/dim]")

    manager = PluginManager(workspace / "plugins", strict=False)
    ctx = PluginContext(phase=hook, workspace_dir=workspace.resolve(), sources=srcs)

    errores_plugin = manager.dispatch(hook, ctx)
    for err in manager.errors:
        console.print(f"[yellow]{err}[/yellow]")

    # Verificación rápida para el circuito de git: compilar + checks veloces.
    bloqueos = errores_plugin
    if hook == "pre_commit_git" and srcs:
        fallos_compile = 0
        findings_error = 0
        warnings = 0
        import tempfile

        from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig
        from ripley.core.compiler import Compiler

        compiler = Compiler(
            CompilerConfig(executable="gcc", flags=["-std=c11", "-Wall"]),
            LimitsConfig(timeout_segundos=15),
            SandboxConfig(),
        )
        with tempfile.TemporaryDirectory(prefix="ripley_hook_") as td:
            binary = Path(td) / "hook_bin"
            res = compiler.compile(srcs, binary)
            if not res.success:
                fallos_compile = 1
                console.print("[bold red]✗ Compilación falló:[/bold red]")
                from ripley.core.gcc_translator import summarize_for_humans as _sfh
                from ripley.core.gcc_translator import translate_stderr as _ts

                console.print(_sfh(_ts(res.stderr)))
            else:
                console.print("[green]✓ Compila[/green]")

        if not fallos_compile:
            rapidos = ["ast.deprecated_api", "ast.backward_goto", "ast.loop_termination",
                       "ast.string_literal_write", "ast.enum_bitmask"]
            import ripley.pipeline.checks  # noqa: F401
            from ripley.pipeline.registry import get as _get

            for cid in rapidos:
                spec = _get(cid)
                if spec is None or spec.runner is None:
                    continue
                for s in srcs:
                    code = Path(s).read_text(encoding="utf-8", errors="replace")
                    for obs in spec.runner(code, Path(s).name):
                        if obs.severity == "ERROR":
                            findings_error += 1
                            console.print(f"  [red]ERROR[/red] {obs.filename}:{obs.line} {obs.message[:90]}")
                        else:
                            warnings += 1
            console.print(
                f"[dim]checks rápidos: {findings_error} error(es), {warnings} advertencia(s)[/dim]"
            )

        bloqueos += fallos_compile + findings_error
        if strict and warnings:
            bloqueos += warnings

    if bloqueos:
        console.print(f"[bold red]✗ Commit bloqueado ({bloqueos} bloqueo(s)).[/bold red]")
        raise typer.Exit(code=1)
    console.print("[green]✓ Verificación previa al commit superada.[/green]")


@plugins_app.command("git-hook")
def cmd_plugins_git_hook(
    action: str = typer.Argument(..., help="install | uninstall | status"),
    hook: str = typer.Argument("pre-commit", help="Git hook objetivo (pre-commit, pre-push…)."),
    repo: Path = typer.Option(".", "--repo", "-r", help="Repositorio git."),
    strict: bool = typer.Option(False, "--strict", help="Instalar el shim con --strict embebido."),
) -> None:
    """Instala/desinstala/consulta el shim de Ripley dentro de .git/hooks."""
    from ripley.pipeline.plugins import (
        install_git_hook,
        is_ripley_git_hook,
        uninstall_git_hook,
    )

    if action == "install":
        path = install_git_hook(repo, hook, strict=strict)
        console.print(f"[green]✓ Shim instalado:[/green] {path}")
        console.print("[dim]El commit ejecutará la verificación rápida sobre los .c stageados.[/dim]")
    elif action == "uninstall":
        if uninstall_git_hook(repo, hook):
            console.print(f"[green]✓ Shim de Ripley removido de {hook}[/green]")
        else:
            console.print("[yellow]No hay shim de Ripley en ese hook (o es ajeno; no se toca).[/yellow]")
    elif action == "status":
        estado = "de Ripley (activo)" if is_ripley_git_hook(repo, hook) else "no administrado por Ripley"
        existe = (repo / ".git" / "hooks" / hook).exists()
        console.print(f"{hook}: {'existe — ' + estado if existe else 'no instalado'}")
    else:
        console.print(f"[bold red]Acción inválida: {action} (install|uninstall|status)[/bold red]")
        raise typer.Exit(code=2)


# ============================================================================
# Comandos Universales Desacoplados (check y analyze)
# ============================================================================
