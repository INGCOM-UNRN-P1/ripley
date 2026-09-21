"""Comandos `show` y `watch` de ripley-check."""

from pathlib import Path
from typing import List, Optional

import typer

from ripley.cli._common import console

from ripley.cli.student import app


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
    from ripley.core.watcher import WatchSession

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
        from ripley.core.compiler import Compiler

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
            from ripley.core.runner import DynamicTestRunner
            from ripley.core.testcases import TestCaseInfo
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
