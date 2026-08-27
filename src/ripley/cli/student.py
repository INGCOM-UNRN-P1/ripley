"""Ripley student CLI (ripley-check): self-service verification without teacher tooling.

Este módulo vive en la zona estudiante: NO debe importar ripley.teacher ni
dependencias del flujo docente (ver tests/unit/test_layer_boundaries.py).
"""

import json
import tempfile
from pathlib import Path
from typing import List, Optional

import typer
from rich.table import Table

from ripley.cli._common import console
from ripley.config import load_config


app = typer.Typer(
    name="ripley-check",
    help="Verificación temprana de entregas C desde la computadora del estudiante.",
    no_args_is_help=True,
)

checks_app = typer.Typer(name="checks", help="Catálogo unificado de verificaciones.", no_args_is_help=True)
app.add_typer(checks_app, name="checks")


# ============================================================================
# Registro de checks y diagnóstico del entorno
# ============================================================================


@checks_app.command("list")
def checks_list(
    scope: str = typer.Option("student", "--scope", "-s", help="Filtrar por scope: student | teacher | both | all."),
) -> None:
    """Lista el catálogo unificado de verificaciones disponibles."""
    from ripley.pipeline.availability import available_map
    from ripley.pipeline.registry import all_checks

    tools = available_map()
    table = Table(title="Catálogo de Verificaciones de Ripley")
    table.add_column("Check ID", style="cyan")
    table.add_column("Capa")
    table.add_column("Scope")
    table.add_column("Herramientas", style="dim")
    table.add_column("Estado")
    for spec in all_checks():
        if scope != "all" and spec.scope != scope:
            continue
        missing = [t for t in spec.requires_tools if not tools.get(t)]
        estado = "[green]lista[/green]" if not missing else f"[yellow]omite: falta {', '.join(missing)}[/yellow]"
        table.add_row(spec.check_id, spec.layer, spec.scope, ", ".join(spec.requires_tools) or "-", estado)
    console.print(table)


@app.command("doctor")
def doctor() -> None:
    """Diagnóstico del entorno: herramientas externas presentes y checks afectados."""
    from ripley.pipeline.availability import probe_all
    from ripley.pipeline.registry import all_checks, is_runnable, iter_student

    statuses = probe_all()
    tools = {s.name: s.available for s in statuses}
    table = Table(title="Disponibilidad de Herramientas Externas")
    table.add_column("Herramienta", style="cyan")
    table.add_column("Estado")
    table.add_column("Impacto si falta", style="dim")
    for s in statuses:
        estado = "[green]disponible[/green]" if s.available else "[red]falta[/red]"
        table.add_row(s.name, estado, s.description)
    console.print(table)

    omitidos = [s.check_id for s in iter_student() if not is_runnable(s, tools)]
    if omitidos:
        console.print(f"\n[yellow]Checks estudiantiles que se omitirán: {', '.join(omitidos)}[/yellow]")
    else:
        console.print("\n[green]Todos los checks estudiantiles son ejecutables en este entorno.[/green]")



# ============================================================================
# Verificación temprana contra paquetes de práctica
# ============================================================================


@app.command("run")
def cmd_run(
    sources: List[Path] = typer.Argument(..., help="Archivos .c del estudiante a verificar."),
    practica: str = typer.Option(..., "--practica", "-p", help="Ruta al paquete .ripkg de la práctica."),
    strict: bool = typer.Option(False, "--strict", help="Salir con código 1 si hay hallazgos, no solo errores."),
    verify_signature: bool = typer.Option(False, "--verify-signature", help="Exigir firma GPG válida del paquete."),
) -> None:
    """Verificación temprana completa: compila, corre testcases públicos y aplica los checks del manifiesto."""
    from ripley.pipeline.bundle import BundleError
    from ripley.pipeline.student_runner import run_bundle

    for s in sources:
        if not Path(s).exists():
            console.print(f"[bold red]Fuente no encontrada: {s}[/bold red]")
            raise typer.Exit(code=1)

    try:
        report = run_bundle(Path(practica), [Path(s) for s in sources], verify_signature=verify_signature)
    except BundleError as e:
        console.print(f"[bold red]Paquete inválido: {e}[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Verificación temprana — {report.practica}[/bold]")
    estado = "[green]OK[/green]" if report.compiled_ok else "[red]FALLÓ[/red]"
    console.print(f"  Compilación      : {estado}")
    if not report.compiled_ok:
        console.print(f"  [dim]{report.compile_errors[:600]}[/dim]")
    if report.tests_total:
        color = "green" if report.tests_passed == report.tests_total else "red"
        console.print(f"  Testcases públicos: [{color}]{report.tests_passed}/{report.tests_total}[/{color}]")
    else:
        console.print("  Testcases públicos: ninguno incluido en el paquete")

    for check_id, obs in report.findings.items():
        if not obs:
            console.print(f"  {check_id}: [green]sin hallazgos[/green]")
            continue
        errores = sum(1 for o in obs if o["severidad"] == "ERROR")
        color = "red" if errores else "yellow"
        console.print(f"  {check_id}: [{color}]{len(obs)} hallazgos ({errores} ERROR)[/{color}]")
        for o in obs[:5]:
            console.print(f"    · {o['archivo']}:{o['linea']} {o['mensaje'][:100]}")

    if report.omitted:
        console.print(f"  [dim]Omitidos por falta de herramientas: {', '.join(report.omitted)}[/dim]")
    if report.signature_verified:
        console.print("  Firma GPG verificada.")

    exito = report.success and (not strict or report.total_findings == 0)
    if exito:
        console.print("\n[bold green]✓ Listo para entregar.[/bold green]\n")
    else:
        console.print("\n[bold yellow]⚠ Revisá los puntos anteriores antes de entregar.[/bold yellow]\n")
        raise typer.Exit(code=1)


@app.command("show")
def cmd_show_ripkg(
    paquete: str = typer.Argument(..., help="Ruta al archivo .ripkg (o slug de la práctica)."),
    enunciado: bool = typer.Option(False, "--enunciado", "-e", help="Mostrar el enunciado / consigna Markdown."),
    pistas: bool = typer.Option(False, "--pistas", "-p", help="Mostrar las pistas progresivas / pautas."),
    tests: bool = typer.Option(False, "--tests", "-t", help="Mostrar casos de prueba públicos del payload."),
    checks: bool = typer.Option(False, "--checks", "-c", help="Mostrar checks y reglas habilitadas en el manifiesto."),
    archivos: bool = typer.Option(False, "--archivos", "-f", help="Mostrar listado de archivos del payload e integridad SHA-256."),
    meta: bool = typer.Option(False, "--meta", "-m", help="Mostrar metadatos del paquete (flags de compilador, versión, firma)."),
    todos: bool = typer.Option(False, "--todos", "-a", help="Mostrar todas las secciones."),
    verify_signature: bool = typer.Option(False, "--verify-signature", help="Verificar criptográficamente la firma GPG del paquete."),
    raw: bool = typer.Option(False, "--raw", help="Salida en texto plano sin formato Rich."),
) -> None:
    """Inspecciona y muestra el contenido, metadatos, enunciado y testcases de un paquete .ripkg."""
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from ripley.pipeline.bundle import BundleError, load_bundle, payload_of

    p = Path(paquete)
    if not p.is_file():
        candidatos = [
            Path(f"{paquete}.ripkg"),
            Path("practicas") / paquete / f"{paquete}.ripkg",
            Path("practicas") / f"{paquete}.ripkg",
            Path("dist") / f"{paquete}.ripkg",
            Path("dist") / paquete / f"{paquete}.ripkg",
            Path("banco") / paquete / f"{paquete}.ripkg",
        ]
        for c in candidatos:
            if c.is_file():
                p = c
                break

    if not p.is_file():
        console.print(f"[bold red]No se encontró el paquete .ripkg: '{paquete}'[/bold red]")
        raise typer.Exit(code=1)

    try:
        bundle = load_bundle(p, verify_signature=verify_signature)
    except BundleError as e:
        console.print(f"[bold red]Error al abrir el paquete '{p}': {e}[/bold red]")
        raise typer.Exit(code=1)

    if todos:
        enunciado = pistas = tests = checks = archivos = meta = True
    elif not any([enunciado, pistas, tests, checks, archivos, meta]):
        # Default: enunciado, pistas y casos de prueba
        enunciado = True
        pistas = True
        tests = True
        meta = False
        checks = False
        archivos = False

    manifest = bundle.manifest
    meta_info = manifest.get("meta", {})
    practica_slug = meta_info.get("practica", p.stem)
    created_at = meta_info.get("created_at", "—")
    format_ver = meta_info.get("format_version", 1)

    compiler_cfg = manifest.get("compiler", {})
    compiler_exec = compiler_cfg.get("executable", "gcc")
    compiler_flags = compiler_cfg.get("flags", [])

    checks_dict = manifest.get("checks", {})
    enabled_checks = [cid for cid, v in sorted(checks_dict.items()) if v]

    integrity_cfg = manifest.get("integrity", {})
    sha256_map = integrity_cfg.get("sha256", {})

    payload = payload_of(bundle)

    # Extraer enunciado
    enunciado_text: Optional[str] = None
    for cand in ["enunciado.md", "README.md", "consigna.md", "consigna.txt"]:
        if cand in payload:
            enunciado_text = payload[cand].decode("utf-8", errors="replace")
            break
    if not enunciado_text:
        for name, data in sorted(payload.items()):
            if name.endswith(".md"):
                enunciado_text = data.decode("utf-8", errors="replace")
                break

    # Extraer pistas
    pistas_text: Optional[str] = None
    for cand in ["pistas.txt", "pistas.md", "hints.txt", "pautas.md", "pautas.txt"]:
        if cand in payload:
            pistas_text = payload[cand].decode("utf-8", errors="replace")
            break

    # Extraer testcases estructurados
    casos: dict[str, dict[str, str]] = {}
    for name, data in payload.items():
        if name.endswith(".in"):
            c_name = name[:-3]
            casos.setdefault(c_name, {})["in"] = data.decode("utf-8", errors="replace")
        elif name.endswith(".out"):
            c_name = name[:-4]
            casos.setdefault(c_name, {})["out"] = data.decode("utf-8", errors="replace")
        elif name.endswith(".argv"):
            c_name = name[:-5]
            casos.setdefault(c_name, {})["argv"] = data.decode("utf-8", errors="replace")

    if raw:
        if meta:
            print(f"Paquete: {p.resolve()}")
            print(f"Practica: {practica_slug}")
            print(f"Version: {format_ver}")
            print(f"Creado: {created_at}")
            print(f"Compilador: {compiler_exec} {' '.join(compiler_flags)}")
            print(f"Firmado: {'si' if bundle.signed else 'no'}")
            print(f"Archivos payload: {len(payload)}")
        if checks:
            print("\n--- CHECKS HABILITADOS ---")
            for cid in enabled_checks:
                print(f"- {cid}")
        if enunciado and enunciado_text:
            print(f"\n--- ENUNCIADO ---\n{enunciado_text.strip()}")
        if pistas and pistas_text:
            print(f"\n--- PISTAS / PAUTAS ---\n{pistas_text.strip()}")
        if tests and casos:
            print("\n--- TESTCASES ---")
            for c_name, c_data in sorted(casos.items()):
                print(f"[{c_name}]")
                if "argv" in c_data:
                    print(f"ARGV: {c_data['argv'].strip()}")
                print(f"IN:\n{c_data.get('in', '').strip()}")
                print(f"OUT:\n{c_data.get('out', '').strip()}\n")
        if archivos:
            print("\n--- ARCHIVOS PAYLOAD ---")
            for f_name, f_data in sorted(payload.items()):
                hash_val = sha256_map.get(f_name, "—")
                print(f"{f_name} ({len(f_data)} B) [sha256: {hash_val}]")
        return

    if meta:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold")
        grid.add_column()
        grid.add_row("Práctica / Slug:", practica_slug)
        grid.add_row("Archivo paquete:", str(p.resolve()))
        grid.add_row("Versión formato:", f"v{format_ver}")
        grid.add_row("Fecha creación:", created_at)
        grid.add_row("Compilador:", f"[cyan]{compiler_exec}[/cyan] {' '.join(compiler_flags)}")
        grid.add_row(
            "Firma criptográfica:",
            "[green]✓ Firmado (GPG)[/green]" if bundle.signed else "[dim]— No firmado (unsigned=true)[/dim]"
        )
        grid.add_row("Payload:", f"{len(payload)} archivos · {len(casos)} casos de prueba públicos")
        if "makefile" in manifest:
            mf = manifest["makefile"]
            grid.add_row("Makefile:", f"target: [bold]{mf.get('target', 'all')}[/bold], bin: [bold]{mf.get('expected_binary', '')}[/bold]")

        console.print(Panel(grid, title=f"[bold cyan]📦 Paquete Ripley (.ripkg)[/bold cyan] — {practica_slug}", border_style="blue"))

    if checks:
        tabla_c = Table(title=f"✓ Checks y Reglas Pedagógicas ({len(enabled_checks)} activas)")
        tabla_c.add_column("Check ID", style="cyan")
        tabla_c.add_column("Estado", justify="center")
        for cid in enabled_checks:
            tabla_c.add_row(cid, "[green]habilitado[/green]")
        console.print(tabla_c)

    if enunciado:
        if enunciado_text:
            console.print(Markdown(enunciado_text))
        else:
            console.print("[dim]No se encontró enunciado Markdown en el payload del paquete.[/dim]")

    if pistas:
        if pistas_text:
            console.print(Panel(pistas_text.strip(), title="💡 Pistas y Pautas de Trabajo", border_style="yellow"))

    if tests:
        if casos:
            tabla_t = Table(title=f"🧪 Casos de Prueba Públicos ({len(casos)} casos)")
            tabla_t.add_column("Caso", style="cyan")
            tabla_t.add_column("Argumentos CLI (argv)", style="dim")
            tabla_t.add_column("Entrada (.in)")
            tabla_t.add_column("Salida Esperada (.out)")
            for c_name, c_data in sorted(casos.items()):
                tabla_t.add_row(
                    c_name,
                    c_data.get("argv", "").strip() or "—",
                    c_data.get("in", "").strip() or "(vacío)",
                    c_data.get("out", "").strip() or "(vacío)",
                )
            console.print(tabla_t)
        else:
            console.print("[dim]No se encontraron casos de prueba (.in/.out) en el payload del paquete.[/dim]")

    if archivos:
        tabla_f = Table(title=f"📂 Contenido del Payload ({len(payload)} archivos)")
        tabla_f.add_column("Ruta en Payload", style="cyan")
        tabla_f.add_column("Tamaño", justify="right")
        tabla_f.add_column("SHA-256 (Integridad)", style="dim")
        for f_name, f_data in sorted(payload.items()):
            h = sha256_map.get(f_name, "")
            h_str = f"{h[:12]}...{h[-8:]}" if len(h) >= 20 else (h or "—")
            tabla_f.add_row(f_name, f"{len(f_data)} B", h_str)
        console.print(tabla_f)



# ============================================================================
# Modo Live TDD / Watch
# ============================================================================


@app.command("watch")
def cmd_watch(
    paths: Optional[List[Path]] = typer.Argument(None, help="Archivos o directorios .c a vigilar (por defecto: .)."),
    practica: Optional[str] = typer.Option(None, "--practica", "-p", help="Paquete .ripkg para flags oficiales y testcases públicos."),
    interval: float = typer.Option(1.0, "--interval", "-i", help="Segundos entre sondeos de cambios."),
) -> None:
    """Modo Live TDD: recompila y verifica automáticamente al guardar (Ctrl+C para salir)."""
    from ripley.core.gcc_translator import summarize_for_humans, translate_stderr
    from ripley.tools.watcher import WatchSession

    effective_paths = paths if paths else [Path(".")]
    session = WatchSession(effective_paths, interval_sec=interval)

    # Cargar manifiesto una sola vez si hay práctica.
    manifest = None
    bundle_payload = {}
    if practica:
        from ripley.pipeline import bundle as bundle_mod

        try:
            loaded = bundle_mod.load_bundle(Path(practica))
            manifest = loaded.manifest
            bundle_payload = bundle_mod.payload_of(loaded)
        except Exception as e:  # BundleError u otros
            console.print(f"[bold red]Paquete inválido: {e}[/bold red]")
            raise typer.Exit(code=1)

    def quick_verify() -> bool:
        """Ciclo rápido de verificación; devuelve True si todo está verde."""
        sources = session.files
        if not sources:
            console.print("[yellow]Sin fuentes .c vigiladas todavía…[/yellow]")
            return True

        compiler_cfg = (manifest or {}).get("compiler", {})
        from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig
        from ripley.tools.compiler import Compiler

        binary = Path(".ripley_watch_bin")
        compiler = Compiler(
            CompilerConfig(
                executable=compiler_cfg.get("executable", "gcc"),
                flags=list(compiler_cfg.get("flags", ["-std=c11", "-Wall"])),
            ),
            LimitsConfig(timeout_segundos=15),
            SandboxConfig(),
        )
        res = compiler.compile(sources, binary)
        if not res.success:
            console.print(f"[bold red]✗ Compilación falló[/bold red]")
            translated = translate_stderr(res.stderr)
            if translated:
                console.print(summarize_for_humans(translated))
            else:
                console.print(f"[dim]{res.stderr[:500]}[/dim]")
            return False

        fallos = 0
        if bundle_payload:
            from ripley.config import LimitsConfig as _L
            from ripley.tools.runner import DynamicTestRunner
            from ripley.tools.testcases import TestCaseInfo
            import tempfile

            runner = DynamicTestRunner(_L(timeout_segundos=5))
            outs = {Path(n).stem for n in bundle_payload if n.endswith(".out")}
            with tempfile.TemporaryDirectory() as td:
                for in_name in sorted(n for n in bundle_payload if n.endswith(".in")):
                    stem = Path(in_name).stem
                    if stem not in outs:
                        continue
                    in_path = Path(td) / f"{stem}.in"
                    out_path = Path(td) / f"{stem}.out"
                    in_path.write_text(bundle_payload[in_name], encoding="utf-8")
                    out_path.write_text(bundle_payload[[n for n in bundle_payload if Path(n).stem == stem and n.endswith('.out')][0]], encoding="utf-8")
                    detail = runner.run_case(binary, TestCaseInfo(
                        exercise="watch", case_name=stem,
                        in_file=in_path, out_file=out_path, argv_file=None))
                    marca = "[green]✓[/green]" if detail.resultado == "PASSED" else "[red]✗[/red]"
                    console.print(f"  {marca} testcase {stem}")
                    if detail.resultado != "PASSED":
                        fallos += 1

        if not fallos:
            console.print("[bold green]✓ Compila y pasa los testcases públicos.[/bold green]")
        return fallos == 0

    console.print(f"[bold]ripley watch[/bold] · vigilando {len(session.files)} fuentes · intervalo {interval}s · Ctrl+C para salir\n")

    try:
        primera = True
        for changes in session.iter_changes():
            if not primera and not changes.any:
                continue
            if changes.any:
                nombres = ", ".join(c.name for c in changes.changed[:3])
                console.print(f"\n[cyan]⟳ Cambio detectado:[/cyan] {nombres}{' …' if len(changes.changed) > 3 else ''}")
                import datetime

                hora = datetime.datetime.now().strftime("%H:%M:%S")
                console.print(f"[dim]{hora}[/dim]")
            quick_verify()
            primera = False
    except KeyboardInterrupt:
        console.print("\n[bold]Watch finalizado.[/bold]")



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
        from ripley.tools.compiler import Compiler

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


@app.command("check")
def cmd_check(
    target: Path = typer.Argument(Path("."), help="Ruta al archivo .c o directorio del proyecto a verificar."),
    strict: bool = typer.Option(False, "--strict", help="Salir con código de error si se detectan advertencias."),
    output_format: str = typer.Option("rich", "--format", help="Formato de salida: 'rich' (consola interactiva) o 'json'."),
    bench: Optional[str] = typer.Option(None, "--bench", help="complexity-bench: cota esperada (O(1), O(n), O(n log n), O(n^2))."),
    bench_pattern: str = typer.Option("{n}\\n", "--bench-pattern", help="Entrada por tamaño; '{n}' se reemplaza por N."),
    strict_ub: bool = typer.Option(False, "--strict-ub", help="ub-sentinel: auditoría de comportamiento indefinido tras compilar."),
    ub_level: int = typer.Option(2, "--ub-level", min=1, max=4, help="Nivel máximo del pipeline ub-sentinel (1=sanitizers, 2=+clang-analyzer, 3=+Frama-C, 4=+TSan)."),
    ub_timeout: int = typer.Option(30, "--ub-timeout", help="Timeout en segundos por testcase del ub-sentinel."),
) -> None:
    """Verificación unificada y pedagógica de código C: AST, reglas P1, compilación y AddressSanitizer."""
    from ripley.core.engine import analyze_target

    if not target.exists():
        console.print(f"[bold red]Ruta inexistente: {target}[/bold red]")
        raise typer.Exit(code=1)

    result = analyze_target(target)

    if output_format.lower() == "json":
        print(result.to_json())
        if not result.compilation.get("success", False) or (strict and result.metrics.get("ast_findings_count", 0) > 0):
            raise typer.Exit(code=1)
        return

    # Visualización Rich
    console.print(f"\n[bold cyan]─── Verificación Ripley: {target.name} ───[/bold cyan]\n")

    # 1. Compilación
    comp = result.compilation
    if comp.get("success"):
        console.print("  [bold green]✓ Compilación GCC / Clang:[/bold green] Exitosa sin errores bloqueantes.")
    else:
        console.print("  [bold red]✗ Fallo de Compilación:[/bold red]")
        if comp.get("human_summary"):
            console.print(f"    [yellow]{comp['human_summary']}[/yellow]")
        for d in comp.get("translated_diagnostics", []):
            console.print(f"    · [bold]{d.get('file')}:{d.get('line')}[/bold] [{d.get('severity')}] {d.get('translated_message')}")
            if d.get("suggestion"):
                console.print(f"      [dim]💡 {d.get('suggestion')}[/dim]")
        if comp.get("raw_stderr") and not comp.get("translated_diagnostics"):
            console.print(f"    [dim]{comp['raw_stderr'][:400]}[/dim]")

    # 2. Reglas AST y Calidad
    findings = result.ast_findings
    if findings:
        table = Table(title="Hallazgos de Calidad, Reglas P1 y AST")
        table.add_column("Archivo:Línea", style="cyan", justify="left")
        table.add_column("Regla", style="bold")
        table.add_column("Severidad", justify="center")
        table.add_column("Diagnóstico y Sugerencia Pedagógica")

        for f in findings:
            sev = f.get("severity", "ADVERTENCIA")
            color = "red" if sev == "ERROR" else ("yellow" if "WARN" in sev or "ADV" in sev else "blue")
            msg = f"{f.get('message')}\n[dim]💡 {f.get('suggestion')}[/dim]" if f.get("suggestion") else f.get("message")
            table.add_row(
                f"{f.get('file')}:{f.get('line')}",
                f.get("rule_id"),
                f"[{color}]{sev}[/{color}]",
                msg,
            )
        console.print("\n")
        console.print(table)
    else:
        console.print("  [bold green]✓ Reglas de Estilo y AST:[/bold green] Sin observaciones.")

    # 3. Pruebas y Memoria
    tests = result.tests
    if tests.get("total", 0) > 0:
        passed = tests.get("passed", 0)
        total = tests.get("total", 0)
        color = "green" if passed == total else "red"
        console.print(f"\n  [bold]Pruebas Funcionales:[/bold] [{color}]{passed}/{total} aprobadas[/{color}]")
        for tc in tests.get("cases", []):
            status = "[green]PASÓ[/green]" if tc.get("passed") else "[red]FALLÓ[/red]"
            leak = " [bold red][Fuga de Memoria][/bold red]" if tc.get("memory_leak") else ""
            console.print(f"    · {tc.get('name')}: {status}{leak}")
            if not tc.get("passed") and tc.get("sanitizer_error"):
                console.print(f"      [dim red]{tc.get('sanitizer_error')[:300]}[/dim red]")

    # 3.b ub-sentinel: comportamiento indefinido (opcional)
    if strict_ub:
        from ripley.tools.ub_sentinel import auditar_ub

        base_ub = target if target.is_dir() else target.parent
        fuentes_ub = [base_ub / rel for rel in result.c_files]
        casos = sorted((base_ub / "tests").glob("caso_*.in")) if (base_ub / "tests").is_dir() else []
        reporte_ub = auditar_ub(fuentes_ub, casos, nivel_maximo=ub_level, timeout=ub_timeout)
        console.print(f"\n[bold]ub-sentinel[/bold] — {reporte_ub.resumen()}")
        for h in reporte_ub.hallazgos:
            sev_color = "red" if h.severidad == "ERROR" else "yellow"
            donde = f"{h.archivo}:{h.linea}" if h.linea else str(h.archivo)
            console.print(f"  [{sev_color}]N{h.nivel}·{h.categoria}[/{sev_color}] {donde}: {h.mensaje}")
            if h.sugerencia:
                console.print(f"    [dim]💡 {h.sugerencia}[/dim]")
        if not reporte_ub.hallazgos and not reporte_ub.omitidos:
            console.print("  [green]✓ Sin comportamiento indefinido detectado.[/green]")
        if reporte_ub.hay_errores:
            result.metrics["ast_errors_count"] = result.metrics.get("ast_errors_count", 0) + len(reporte_ub.errores)

    # 4. complexity-bench: verificar cota asintótica exigida (opcional)
    if bench:
        if not comp.get("success"):
            console.print("[yellow]--bench omitido: el proyecto no compila.[/yellow]")
        else:
            from ripley.core.bench import compilar_optimizado, normalizar_cota, verificar_cota

            base = target if target.is_dir() else target.parent
            fuentes = [base / rel for rel in result.c_files]
            bin_bench = Path(tempfile.mkdtemp(prefix="ripley_bench_")) / "bench.bin"
            ok_compile, err = compilar_optimizado(fuentes, bin_bench, include_dirs=[base])
            if not ok_compile:
                console.print(f"[red]complexity-bench: no se pudo compilar optimizado:[/red] {err}")
                raise typer.Exit(code=1)
            ok_cota, resumen = verificar_cota(bin_bench, bench, patron_entrada=bench_pattern)
            console.print(f"\n[bold]complexity-bench[/bold] ({normalizar_cota(bench)}): {resumen}")
            if ok_cota is False:
                console.print("[bold red]✗ El algoritmo excede la cota exigida por la consigna.[/bold red]")
                raise typer.Exit(code=1)
            if ok_cota is None:
                console.print("[yellow]⚠ Medición inconclusa: no se penaliza esta vez.[/yellow]")
            else:
                console.print("[green]✓ La complejidad empírica respeta la cota exigida.[/green]")

    # Veredicto final
    has_errors = not comp.get("success", False) or result.metrics.get("ast_errors_count", 0) > 0 or tests.get("failed", 0) > 0
    if has_errors:
        console.print("\n[bold red]✗ Se encontraron errores o violaciones que impiden la entrega.[/bold red]\n")
        raise typer.Exit(code=1)
    elif strict and result.metrics.get("ast_findings_count", 0) > 0:
        console.print("\n[bold yellow]⚠ Modo estricto: Existen advertencias pendientes de corrección.[/bold yellow]\n")
        raise typer.Exit(code=1)
    else:
        console.print("\n[bold green]✓ Proyecto verificado con éxito y listo para entregar.[/bold green]\n")


@app.command("analyze")
def cmd_analyze(
    target: Path = typer.Argument(Path("."), help="Ruta al archivo .c o directorio del proyecto a analizar."),
    format: str = typer.Option("json", "--format", help="Formato de salida ('json')."),
) -> None:
    """Análisis programático sin estado para orquestadores (dredd, CI/CD, scripts)."""
    from ripley.core.engine import analyze_target

    if not target.exists():
        error_res = {
            "version": "2.0.0",
            "error": f"Target not found: {target}",
            "compilation": {"success": False},
        }
        print(json.dumps(error_res, indent=2))
        raise typer.Exit(code=1)

    result = analyze_target(target)
    print(result.to_json())
    if not result.compilation.get("success", False):
        raise typer.Exit(code=1)


