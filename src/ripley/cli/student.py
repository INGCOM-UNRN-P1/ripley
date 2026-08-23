"""Ripley student CLI (ripley-check): self-service verification without teacher tooling.

Este módulo vive en la zona estudiante: NO debe importar ripley.teacher ni
dependencias del flujo docente (ver tests/unit/test_layer_boundaries.py).
"""

from pathlib import Path
from typing import List, Optional

import typer
from rich.table import Table

from ripley.cli._common import console
from ripley.config import load_config
from ripley.core.ast_auditors import (
    ConstCorrectnessLinter,
    DeepFreeLinter,
    DanglingStackPointerLinter,
    ShortCircuitLinter,
    StringNullPointerLinter,
    VariableShadowingLinter,
    FloatComparisonLinter,
    IWYULinter,
)
from ripley.core.callgraph import CallGraphGenerator
from ripley.core.doxygen import DoxygenAuditor
from ripley.core.flowchart import FlowchartGenerator
from ripley.core.heap_simulator import HeapMemorySimulator
from ripley.core.linters import (
    DeadCodeLinter,
    InternalCloneLinter,
    LinterObservation,
    MagicNumberLinter,
    NamingConventionLinter,
)
from ripley.core.memory_visualizer import DynamicMemoryVisualizer
from ripley.core.mocks import MockGenerator
from ripley.core.p1_rules import P1RuleChecker
from ripley.core.padding_audit import StructPaddingAuditor
from ripley.tools.benchmark import EnergyBenchmark
from ripley.tools.complexity_profiler import ComplexityProfiler
from ripley.tools.coverage_fuzzing import CoverageGuidedFuzzer
from ripley.tools.cross_arch import CrossArchitectureTester
from ripley.tools.embedded import EmbeddedMemoryRunner
from ripley.tools.formal_contracts import FormalContractAnalyzer
from ripley.tools.property_testing import PropertyTestRunner
from ripley.tools.pure_functions import PureFunctionAnalyzer
from ripley.tools.sandbox import NamespaceSandbox
from ripley.tools.socket_faults import SocketFaultInjector
from ripley.tools.stack_usage import StackUsageAuditor
from ripley.tools.toolchain import capture_snapshot, compare_snapshots, load_snapshot, save_snapshot


app = typer.Typer(
    name="ripley-check",
    help="Verificación temprana de entregas C desde la computadora del estudiante.",
    no_args_is_help=True,
)
mock_app = typer.Typer(name="mock", help="Generador de arneses y mocks en C.", no_args_is_help=True)

checks_app = typer.Typer(name="checks", help="Catálogo unificado de verificaciones.", no_args_is_help=True)

app.add_typer(mock_app, name="mock")
app.add_typer(checks_app, name="checks")


@app.command("flowchart")

def cmd_flowchart(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    function: Optional[str] = typer.Option(
        None,
        "--function",
        help="Nombre específico de la función a graficar (por defecto todas las funciones).",
    ),
    output_format: str = typer.Option(
        "mermaid",
        "--format",
        help="Formato de salida del diagrama ('mermaid' o 'dot').",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Ruta donde guardar el archivo generado (ej. flujo.md o flujo.dot).",
    ),
) -> None:
    """Genera diagramas de flujo con la notación tradicional (ISO/ANSI) a partir de código C."""
    generator = FlowchartGenerator()
    try:
        diagrams = generator.generate_for_file(
            c_file_path=file_path,
            target_function=function,
            output_format=output_format,
        )

        if not diagrams:
            console.print(f"[yellow]No se detectaron funciones en '{file_path}'.[/yellow]")
            return

        combined_output = []
        for fname, chart in diagrams.items():
            if output_format == "mermaid":
                combined_output.append(f"### Diagrama de Flujo: `{fname}()`\n\n```mermaid\n{chart}\n```\n")
            else:
                combined_output.append(f"// --- Función {fname} ---\n{chart}\n")

        full_text = "\n".join(combined_output)

        if output:
            out_p = Path(output)
            out_p.write_text(full_text, encoding="utf-8")
            console.print(f"\n[bold green]✓ Diagrama(s) de flujo guardado(s) exitosamente en:[/bold green] [cyan]{out_p}[/cyan]\n")
        else:
            console.print(f"\n[bold green]Diagramas de Flujo Tradicionales ({file_path}):[/bold green]\n")
            for fname, chart in diagrams.items():
                console.print(f"[bold cyan]Función {fname}():[/bold cyan]")
                console.print(f"```{output_format}\n{chart}\n```\n")
    except Exception as e:
        console.print(f"[bold red]Error al generar diagrama de flujo:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("callgraph")
def cmd_callgraph(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    format_type: str = typer.Option("mermaid", "--format", help="Formato de salida ('mermaid' o 'dot')."),
    stdlib: bool = typer.Option(False, "--stdlib", help="Incluir llamadas a funciones de biblioteca estándar."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Archivo donde guardar el callgraph."),
) -> None:
    """Genera el árbol de llamadas (Call Graph) entre funciones C en formato Mermaid o DOT."""
    cg_gen = CallGraphGenerator()
    try:
        graph_text = cg_gen.generate_for_file(
            file_path=file_path,
            output_format=format_type,
            include_stdlib=stdlib,
        )

        if output:
            out_p = Path(output)
            out_p.write_text(graph_text, encoding="utf-8")
            console.print(f"\n[bold green]✓ Árbol de llamadas guardado en:[/bold green] [cyan]{out_p}[/cyan]\n")
        else:
            console.print(f"\n[bold green]Árbol de Llamadas ({file_path}):[/bold green]\n")
            console.print(f"```{format_type}\n{graph_text}\n```\n")
    except Exception as e:
        console.print(f"[bold red]Error al generar callgraph:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("lint")
def cmd_lint(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    magic_numbers: bool = typer.Option(True, "--magic-numbers/--no-magic-numbers", help="Auditar números mágicos."),
    clones: bool = typer.Option(True, "--clones/--no-clones", help="Auditar código duplicado (copy-paste)."),
    naming: bool = typer.Option(True, "--naming/--no-naming", help="Auditar convenciones de nombres."),
    dead_code: bool = typer.Option(True, "--dead-code/--no-dead-code", help="Auditar funciones/código inalcanzable."),
    doxygen: bool = typer.Option(False, "--doxygen/--no-doxygen", help="Auditar completitud de Doxygen."),
    advanced: bool = typer.Option(True, "--advanced/--no-advanced", help="Auditar reglas avanzadas de AST (float, const, short-circuit, deep-free, shadowing, dangling)."),
    p1_rules: bool = typer.Option(True, "--p1-rules/--no-p1-rules", help="Auditar reglas de estilo oficiales de Programación I (0xXXXXh)."),
) -> None:
    """Ejecuta análisis de números mágicos, código duplicado, convenciones, código muerto y reglas de estilo P1 (0xXXXXh)."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Archivo no encontrado: {path}[/bold red]")
        raise typer.Exit(code=1)

    code = path.read_text(encoding="utf-8", errors="replace")
    all_obs = []

    if p1_rules:
        p1_obs = P1RuleChecker().analyze(code, filename=path.name)
        for p in p1_obs:
            all_obs.append(
                LinterObservation(
                    linter_name=f"{p.rule_code} ({p.title})",
                    filename=path.name,
                    line=p.line,
                    severity=p.severity,
                    message=p.message,
                    suggestion=p.suggestion,
                )
            )

    if magic_numbers:
        all_obs.extend(MagicNumberLinter().analyze(code, filename=path.name))


    if naming:
        all_obs.extend(NamingConventionLinter().analyze(code, filename=path.name))

    if dead_code:
        all_obs.extend(DeadCodeLinter().analyze(code, filename=path.name))

    if clones:
        dup_matches = InternalCloneLinter().analyze(code, filename=path.name)
        for d in dup_matches:
            all_obs.append(
                LinterObservation(
                    linter_name="copy_paste_detector",
                    filename=path.name,
                    line=d.line_a,
                    severity="ADVERTENCIA",
                    message=d.description,
                    suggestion="Extraé la lógica común en una función auxiliar parametrizada.",
                )
            )

    if doxygen:
        dox_obs = DoxygenAuditor().audit_code(code, filename=path.name)
        for dox in dox_obs:
            all_obs.append(
                LinterObservation(
                    linter_name="doxygen",
                    filename=path.name,
                    line=dox.line,
                    severity="ESTILO",
                    message=dox.message,
                    suggestion="Agregá @brief, @param y @return en el bloque de documentación.",
                )
            )

    if advanced:
        all_obs.extend(FloatComparisonLinter().analyze(code, filename=path.name))
        all_obs.extend(IWYULinter().analyze(code, filename=path.name))
        all_obs.extend(ConstCorrectnessLinter().analyze(code, filename=path.name))
        all_obs.extend(ShortCircuitLinter().analyze(code, filename=path.name))
        all_obs.extend(DeepFreeLinter().analyze(code, filename=path.name))
        all_obs.extend(StringNullPointerLinter().analyze(code, filename=path.name))
        all_obs.extend(VariableShadowingLinter().analyze(code, filename=path.name))
        all_obs.extend(DanglingStackPointerLinter().analyze(code, filename=path.name))
        all_obs.extend(OverengineeringLinter().analyze(code, filename=path.name))
        all_obs.extend(EvaluationOrderLinter().analyze(code, filename=path.name))
        all_obs.extend(StringLiteralWriteLinter().analyze(code, filename=path.name))
        all_obs.extend(BackwardGotoLinter().analyze(code, filename=path.name))

    if not all_obs:
        console.print(f"\n[bold green]✓ No se detectaron desvíos en '{path.name}'. Código limpio y modular.[/bold green]\n")
        return

    table = Table(title=f"Observaciones de Calidad y Estilo - {path.name}")
    table.add_column("Línea", justify="right", style="bold")
    table.add_column("Regla", style="cyan")
    table.add_column("Severidad", justify="center")
    table.add_column("Mensaje")
    table.add_column("Sugerencia Pedagógica", style="dim")

    for obs in all_obs:
        if obs.severity == "ERROR":
            sev_style = "[bold red]ERROR[/bold red]"
        elif obs.severity == "ADVERTENCIA":
            sev_style = "[bold yellow]ADVERTENCIA[/bold yellow]"
        else:
            sev_style = "[cyan]ESTILO[/cyan]"

        table.add_row(
            str(obs.line),
            obs.linter_name,
            sev_style,
            obs.message,
            obs.suggestion,
        )

    console.print(table)


@app.command("heap-simulate")
def cmd_heap_simulate(
    capacity: int = typer.Option(1024, "--capacity", "-c", help="Capacidad del heap simulado en bytes."),
    allocations: str = typer.Option("128,256,64,512", "--allocations", "-a", help="Tamaños de asignación separados por coma."),
    frees: str = typer.Option("1,3", "--frees", "-f", help="Índices 1-based de asignaciones a liberar separados por coma."),
) -> None:
    """Simula un montículo (Heap) para analizar patrones de fragmentación externa e interna."""
    sim = HeapMemorySimulator(capacity=capacity)
    sizes = [int(s.strip()) for s in allocations.split(",") if s.strip()]
    free_indices = [int(idx.strip()) for idx in frees.split(",") if idx.strip()]

    allocated_offsets = []
    for i, sz in enumerate(sizes):
        offset = sim.allocate(sz, tag=f"alloc_{i+1}")
        allocated_offsets.append(offset)

    for f_idx in free_indices:
        if 1 <= f_idx <= len(allocated_offsets):
            off = allocated_offsets[f_idx - 1]
            if off is not None:
                sim.free(off)

    rep = sim.get_report()

    console.print(f"\n[bold green]Reporte de Fragmentación de Memoria Heap ({capacity} B):[/bold green]")
    console.print(f" - [cyan]Memoria Ocupada Actual:[/cyan] {rep.current_allocated} B / {rep.total_capacity} B (Pico: {rep.peak_allocated} B)")
    console.print(f" - [cyan]Memoria Libre Total:[/cyan] {rep.total_free} B")
    console.print(f" - [cyan]Bloque Libre Contiguo Mayor:[/cyan] {rep.largest_free_block} B")
    console.print(f" - [cyan]Índice de Fragmentación Externa:[/cyan] [bold yellow]{rep.fragmentation_index * 100:.1f}%[/bold yellow]")
    console.print(f" - [cyan]Mapa de Memoria:[/cyan] {rep.memory_map}\n")


@app.command("pure-audit")
def cmd_pure_audit(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c)."),
    mode: str = typer.Option("pure", "--mode", "-m", help="Modo de auditoría ('pure' o 'const')."),
    verify_compiler: bool = typer.Option(True, "--verify-compiler/--no-verify-compiler", help="Verificar inyectando atributos con GCC."),
) -> None:
    """Audita la pureza y ausencia de efectos colaterales en funciones C (__attribute__((pure|const)))."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Archivo no encontrado: {path}[/bold red]")
        raise typer.Exit(code=1)

    code = path.read_text(encoding="utf-8", errors="replace")
    analyzer = PureFunctionAnalyzer()
    obs_list = analyzer.analyze_static(code)

    table = Table(title=f"Auditoría de Funciones Puras - {path.name}")
    table.add_column("Línea", justify="right", style="bold")
    table.add_column("Función", style="cyan")
    table.add_column("Pureza", justify="center")
    table.add_column("Atributo Sugerido", justify="center")
    table.add_column("Violaciones Detectadas", style="dim")

    for obs in obs_list:
        p_str = "[bold green]PURA[/bold green]" if obs.is_pure else "[bold red]IMPURA[/bold red]"
        viol_str = ", ".join(obs.violations) if obs.violations else "Sin efectos secundarios"
        table.add_row(
            str(obs.line),
            obs.function_name,
            p_str,
            obs.suggested_attribute,
            viol_str,
        )

    console.print(table)

    if verify_compiler:
        ok, msg = analyzer.verify_with_compiler(path, mode=mode)
        if ok:
            console.print(f"\n[bold green]✓ Verificación con compilador exitosa:[/bold green] {msg}\n")
        else:
            console.print(f"\n[bold yellow]! Advertencia del compilador:[/bold yellow] {msg}\n")


@app.command("memory-visualize")
def cmd_memory_visualize(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C con estructuras (.c o .h)."),
    format_type: str = typer.Option("mermaid", "--format", help="Formato de salida ('mermaid' o 'dot')."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Archivo de salida."),
) -> None:
    """Genera diagramas visuales de la topología de estructuras dinámicas de datos en memoria."""
    vis = DynamicMemoryVisualizer()
    try:
        diagram = vis.generate_diagram(c_file=file_path, output_format=format_type)
        if output:
            out_p = Path(output)
            out_p.write_text(diagram, encoding="utf-8")
            console.print(f"\n[bold green]✓ Diagrama de memoria guardado en:[/bold green] [cyan]{out_p}[/cyan]\n")
        else:
            console.print(f"\n[bold green]Topología de Estructuras Dinámicas ({file_path}):[/bold green]\n")
            console.print(f"```{format_type}\n{diagram}\n```\n")
    except Exception as e:
        console.print(f"[bold red]Error al visualizar memoria:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("embedded-test")
def cmd_embedded_test(
    binary: str = typer.Option(..., "--binary", "-b", help="Ruta al binario compilado."),
    limit_kb: int = typer.Option(64, "--limit-kb", "-l", help="Límite máximo de memoria en KB."),
    stdin_data: str = typer.Option("", "--stdin", help="Entrada estándar."),
) -> None:
    """Ejecuta un binario bajo límites estrictos de memoria de sistemas embebidos."""
    runner = EmbeddedMemoryRunner(memory_limit_kb=limit_kb)
    res = runner.run(binary_path=binary, stdin_data=stdin_data)

    if res.success:
        console.print(f"\n[bold green]✓ {res.message}[/bold green]\n")
    else:
        console.print(f"\n[bold red]✗ {res.message}[/bold red]")
        if res.stderr:
            console.print(f"[yellow]Stderr:[/yellow] {res.stderr}\n")
        raise typer.Exit(code=1)




@mock_app.command("generate")
def cmd_mock_generate(
    header: str = typer.Option(..., "--header", "-h", help="Ruta al archivo de cabecera (.h) o fuente (.c)."),
    output_dir: str = typer.Option(".", "--output-dir", "-o", help="Directorio de destino."),
) -> None:
    """Genera automáticamente arneses mock (.h y .c) para pruebas unitarias en C."""
    generator = MockGenerator()
    try:
        h_file, c_file = generator.generate_files(input_file=header, output_dir=output_dir)
        console.print(f"\n[bold green]✓ Arneses Mock generados exitosamente:[/bold green]\n")
        console.print(f" - [cyan]{h_file}[/cyan]")
        console.print(f" - [cyan]{c_file}[/cyan]\n")
    except Exception as e:
        console.print(f"[bold red]Error al generar mocks:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("doxygen")
def cmd_doxygen(
    file_path: str = typer.Option(..., "--file", "-f", help="Ruta al archivo fuente C (.c o .h)."),
) -> None:
    """Audita la presencia y completitud de comentarios Doxygen (@brief, @param, @return)."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Archivo no encontrado: {path}[/bold red]")
        raise typer.Exit(code=1)

    code = path.read_text(encoding="utf-8", errors="replace")
    auditor = DoxygenAuditor()
    obs = auditor.audit_code(code, filename=path.name)

    if not obs:
        console.print(f"\n[bold green]✓ Todas las funciones en '{path.name}' están correctamente documentadas en Doxygen.[/bold green]\n")
        return

    table = Table(title=f"Auditoría Doxygen - {path.name}")
    table.add_column("Línea", justify="right", style="bold")
    table.add_column("Función", style="cyan")
    table.add_column("Faltantes", style="yellow")

    for o in obs:
        table.add_row(str(o.line), f"{o.function_name}()", ", ".join(o.missing_items))

    console.print(table)


@app.command("property-test")
def cmd_property_test(
    source: str = typer.Option(..., "--source", "-s", help="Ruta al archivo C del estudiante."),
    function: str = typer.Option(..., "--function", "-f", help="Nombre de la función a evaluar."),
    property_type: str = typer.Option(
        "IDEMPOTENCE",
        "--property",
        "-p",
        help="Tipo de invariante a verificar ('IDEMPOTENCE', 'COMMUTATIVITY', 'SORT_INVARIANT').",
    ),
    iterations: int = typer.Option(100, "--iterations", "-i", help="Cantidad de iteraciones aleatorias a ejecutar."),
) -> None:
    """Ejecuta pruebas basadas en propiedades (Property-Based Testing) sobre funciones en C."""
    runner = PropertyTestRunner()
    console.print(
        f"\n[bold green]Iniciando Property-Based Testing:[/bold green] [cyan]{function}()[/cyan] | Propiedad: [bold]{property_type}[/bold] ({iterations} iteraciones)\n"
    )

    res = runner.run_property_test(
        student_source=source,
        property_type=property_type,
        target_function=function,
        iterations=iterations,
    )

    if res.passed:
        console.print(f"[bold green]✓ {res.message}[/bold green]\n")
    else:
        console.print(f"[bold red]✗ {res.message}[/bold red]")
        if res.counterexample_output:
            console.print(f"[yellow]Contraejemplo hallado:[/yellow] {res.counterexample_output}\n")
        raise typer.Exit(code=1)


# ============================================================================
# Módulo 1: Compilación, Aislamiento y Entornos Seguros
# ============================================================================


@app.command("cross-test")
def cmd_cross_test(
    file_path: str = typer.Argument(..., help="Ruta al archivo fuente C (.c)."),
    stdin_file: Optional[str] = typer.Option(None, "--stdin", "-i", help="Archivo con la entrada estándar."),
) -> None:
    """Compila y ejecuta la fuente en múltiples arquitecturas vía QEMU (x86_64, ARM64, RISC-V, MIPS-BE)."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Fuente no encontrada: {path}[/bold red]")
        raise typer.Exit(code=1)
    stdin_data = Path(stdin_file).read_text(encoding="utf-8") if stdin_file else ""

    tester = CrossArchitectureTester()
    report = tester.test(path, stdin_data=stdin_data)

    console.print(f"\n[bold green]Matriz de Compilación Cruzada:[/bold green] {path.name}")
    table = Table()
    table.add_column("Arquitectura", style="cyan")
    table.add_column("Toolchain")
    table.add_column("Emulador")
    table.add_column("Estado")
    for t in report.targets:
        status = (
            "[green]OK - salida consistente[/green]"
            if t.compiled and t.output_matched
            else "[red]Salida divergente[/red]"
            if t.compiled and t.ran and not t.output_matched
            else "[yellow]" + (t.message[:60] or "compilado sin ejecutar") + "[/yellow]"
            if t.compiled
            else "[dim]" + t.message[:70] + "[/dim]"
        )
        table.add_row(t.architecture, "sí" if t.compiler_used else "no", t.emulator_used or "-", status)
    console.print(table)


@app.command("sandbox-test")
def cmd_sandbox_test(
    binary_path: str = typer.Argument(..., help="Binario a ejecutar aislado."),
    stdin_file: Optional[str] = typer.Option(None, "--stdin", "-i", help="Archivo con la entrada estándar."),
) -> None:
    """Ejecuta el binario dentro de namespaces Linux (bubblewrap/unshare) sin root."""
    binp = Path(binary_path)
    if not binp.exists():
        console.print(f"[bold red]Binario no encontrado: {binp}[/bold red]")
        raise typer.Exit(code=1)
    stdin_data = Path(stdin_file).read_text(encoding="utf-8") if stdin_file else ""

    sandbox = NamespaceSandbox()
    self_test = sandbox.self_test()
    strategy = sandbox.detect_strategy()
    style_map = {"bubblewrap": "[green]bubblewrap[/green]", "unshare": "[yellow]unshare (user-ns)[/yellow]", "none": "[red]sin aislamiento[/red]"}
    console.print(f"\n[bold]Estrategia detectada:[/bold] {style_map.get(strategy, strategy)}")
    console.print(f"  Self-test: {'[green]OK[/green]' if self_test.success else '[red]FALLÓ[/red]'} — {self_test.message}")

    res = sandbox.run(binp, stdin_data=stdin_data)
    console.print(f"  rc={res.returncode} | stdout: {len(res.stdout)} bytes | stderr: {len(res.stderr)} bytes")
    console.print(f"  {res.message}")
    if not res.success:
        raise typer.Exit(code=1)


@app.command("toolchain-snapshot")
def cmd_toolchain_snapshot(
    output: str = typer.Option(".ripley/toolchain_snapshot.json", "--output", "-o", help="Ruta del JSON de instantánea."),
    verify: bool = typer.Option(False, "--verify", help="Compara contra la instantánea guardada en lugar de crearla nueva."),
) -> None:
    """Captura o verifica una instantánea hermética del toolchain para reproducibilidad."""
    current = capture_snapshot(compile_flags=load_config().compiler.flags)
    snapshot_path = Path(output)

    if verify:
        baseline = load_snapshot(snapshot_path)
        if baseline is None:
            console.print(f"[bold red]No existe instantánea previa en {snapshot_path}.[/bold red]")
            raise typer.Exit(code=1)
        comparison = compare_snapshots(baseline, current)
        if comparison.reproducible:
            console.print(f"[bold green]✓ {comparison.message}[/bold green]")
        else:
            console.print(f"[bold yellow]⚠ {comparison.message}[/bold yellow]")
            for diff in comparison.differences:
                console.print(f"   • {diff}")
            raise typer.Exit(code=1)
    else:
        save_snapshot(current, snapshot_path)
        console.print(f"\n[bold green]Instantánea de toolchain guardada en {snapshot_path}[/bold green]")
        console.print(f"  Compilador : {current.compiler_version} ({current.compiler_target})")
        console.print(f"  libc       : {current.libc_version}")
        console.print(f"  Kernel/Maq : {current.kernel} / {current.machine}")


# ============================================================================
# Módulo 2: Testing Dinámico, Rendimiento y Fuzzing Avanzado
# ============================================================================


@app.command("coverage-fuzz")
def cmd_coverage_fuzz(
    file_path: str = typer.Argument(..., help="Fuente C del alumno (.c)."),
    iterations: int = typer.Option(200, "--iterations", "-n", help="Máximo de iteraciones de fuzzing."),
    seed: int = typer.Option(42, "--seed", help="Semilla aleatoria reproducible."),
) -> None:
    """Fuzzing guiado por cobertura (gcov): prioriza entradas que descubren líneas nuevas."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Fuente no encontrada: {path}[/bold red]")
        raise typer.Exit(code=1)

    fuzzer = CoverageGuidedFuzzer(seed=seed)
    with console.status("[bold cyan]Fuzzing guiado por cobertura en curso..."):
        report = fuzzer.fuzz(path, max_iterations=iterations)

    if not report.available:
        console.print(f"[bold red]{report.message}[/bold red]")
        raise typer.Exit(code=1)
    console.print(f"\n[bold green]Reporte de Fuzzing Guiado por Cobertura:[/bold green] {report.summary()}")
    for crash in report.crashes[:5]:
        console.print(f"  [bold red]CRASH rc={crash.returncode}[/bold red] input: {crash.input_data!r:.80}")
        console.print(f"    {crash.stderr_excerpt[:160]}")
    if report.crashes:
        raise typer.Exit(code=1)


@app.command("complexity-profile")
def cmd_complexity_profile(
    binary_path: str = typer.Argument(..., help="Binario ya compilado a perfilar."),
    pattern: str = typer.Option("{n}\\n", "--pattern", help="Plantilla de entrada; '{n}' se reemplaza por el tamaño N."),
    sizes: str = typer.Option("10,100,1000,10000", "--sizes", help="Tamaños N separados por coma."),
    repeats: int = typer.Option(3, "--repeats", help="Repeticiones por tamaño."),
) -> None:
    """Analiza la complejidad asintótica empírica O(N) vs O(N^2) ajustando regresiones log-log."""
    binp = Path(binary_path)
    if not binp.exists():
        console.print(f"[bold red]Binario no encontrado: {binp}[/bold red]")
        raise typer.Exit(code=1)

    size_list = [int(s.strip()) for s in sizes.split(",") if s.strip()]
    profiler = ComplexityProfiler(sizes=size_list, repeats_per_size=repeats)
    report = profiler.profile(binp, input_pattern=pattern.replace("\\n", "\n"))

    console.print(f"\n[bold green]Perfil de Complejidad Empírica:[/bold green] {binp.name}")
    if not report.available:
        console.print(f"[bold red]{report.message}[/bold red]")
        raise typer.Exit(code=1)
    table = Table()
    table.add_column("N", justify="right", style="cyan")
    table.add_column("Tiempo promedio (ms)", justify="right")
    for m in report.measurements:
        table.add_row(str(m.n), f"{m.time_ms:.2f}")
    console.print(table)
    console.print(f"  Pendiente log-log: [bold]{report.slope:.2f}[/bold] (R²={report.r_squared:.4f})")
    console.print(f"  Clasificación estimada: [bold magenta]{report.classification}[/bold magenta]")


@app.command("stack-audit")
def cmd_stack_audit(
    files: list[str] = typer.Argument(..., help="Archivos fuente C a auditar."),
    threshold: int = typer.Option(1024, "--threshold", "-t", help="Umbral de bytes de stack por función."),
) -> None:
    """Audita el consumo máximo de stack por función con -fstack-usage."""
    sources = [Path(f) for f in files]
    missing = [s for s in sources if not s.exists()]
    if missing:
        console.print(f"[bold red]Archivos no encontrados: {[str(m) for m in missing]}[/bold red]")
        raise typer.Exit(code=1)

    auditor = StackUsageAuditor(threshold_bytes=threshold)
    report = auditor.audit(sources)
    if not report.available:
        console.print(f"[bold red]{report.message}[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold green]Auditoría de Consumo de Stack[/bold green] (umbral: {threshold} B)")
    offenders = report.offenders
    dynamic = report.dynamic_entries
    if not offenders and not dynamic:
        console.print("[green]✓ Ninguna función supera el umbral ni usa asignaciones dinámicas.[/green]")
        return
    table = Table()
    table.add_column("Función", style="cyan")
    table.add_column("Ubicación", dim=True)
    table.add_column("Bytes", justify="right")
    table.add_column("Tipo")
    for e in offenders:
        kind = "[red]dinámico (VLA/alloca)[/red]" if e.is_dynamic else "[yellow]estático grande[/yellow]"
        table.add_row(e.function, f"{e.source_file}:{e.line}", str(e.size_bytes), kind)
    console.print(table)


@app.command("socket-fault")
def cmd_socket_fault(
    binary_path: str = typer.Argument(..., help="Binario que utiliza sockets."),
    rounds: int = typer.Option(5, "--rounds", help="Cantidad de rondas de inyección de fallas."),
) -> None:
    """Inyecta fallas de red (connect/send/recv) vía LD_PRELOAD y audita fugas de descriptores."""
    binp = Path(binary_path)
    if not binp.exists():
        console.print(f"[bold red]Binario no encontrado: {binp}[/bold red]")
        raise typer.Exit(code=1)

    injector = SocketFaultInjector()
    try:
        audit = injector.audit(binp, max_fault_rounds=rounds)
    finally:
        injector.close()

    if not audit.available:
        console.print(f"[bold red]{audit.message}[/bold red]")
        raise typer.Exit(code=1)
    if audit.baseline:
        b = audit.baseline
        console.print(f"\n[bold green]Línea base:[/bold green] sockets={b.sockets_created} cerrados={b.sockets_closed} fugas={b.leaked_fds}")
    for r in audit.fault_rounds:
        console.print(
            f"  falla tras op #{r.fail_after}: creados={r.sockets_created} cerrados={r.sockets_closed} "
            f"fugas=[{'red' if r.leaked_fds > 0 else 'green'}]{r.leaked_fds}[/] fallas_inyectadas={r.injected_failures}"
        )
    console.print(f"\n  Veredicto: {'[bold red]' + audit.message + '[/bold red]' if audit.leaks_under_faults else '[green]' + audit.message + '[/green]'}")
    if audit.leaks_under_faults:
        raise typer.Exit(code=1)


@app.command("benchmark")
def cmd_benchmark(
    binary_path: str = typer.Argument(..., help="Binario a medir."),
    repeats: int = typer.Option(5, "--repeats", "-r", help="Repeticiones para el tiempo de pared."),
    stdin_file: Optional[str] = typer.Option(None, "--stdin", "-i", help="Entrada estándar opcional."),
) -> None:
    """Benchmark de ciclos de instrucción y consumo energético estimado."""
    binp = Path(binary_path)
    if not binp.exists():
        console.print(f"[bold red]Binario no encontrado: {binp}[/bold red]")
        raise typer.Exit(code=1)
    stdin_data = Path(stdin_file).read_text(encoding="utf-8") if stdin_file else ""

    bench = EnergyBenchmark(repeats=repeats)
    result = bench.run(binp, stdin_data=stdin_data)

    console.print(f"\n[bold green]Benchmark Energético y de Ciclos:[/bold green] {result.binary}")
    console.print(f"  Tiempo medio : {result.mean_time_ms:.2f} ms (±{result.stddev_time_ms:.2f}, min {result.min_time_ms:.2f})")
    console.print(f"  Instrucciones: {result.instruction_count:,} {'(Callgrind)' if result.counters_available else '(valgrind no disponible: valor aproximado)'}")
    console.print(f"  Ciclos est.  : {result.estimated_cycles:,}")
    console.print(f"  Energía est. : {result.estimated_energy_joules * 1e6:.2f} µJ")
    console.print(f"  Score        : {result.throughput_score:,.0f} instrucciones/ms")


# ============================================================================
# Módulo 3: Análisis Semántico y Verificación Formal
# ============================================================================


@app.command("contract-check")
def cmd_contract_check(
    file_path: str = typer.Argument(..., help="Fuente C con contratos ACSL /*@ ... */."),
    run_prover: bool = typer.Option(True, "--prover/--no-prover", help="Ejecutar Frama-C WP si está instalado."),
) -> None:
    """Verifica contratos ACSL (requires/ensures): inventario estático + demostración Frama-C."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Fuente no encontrada: {path}[/bold red]")
        raise typer.Exit(code=1)

    code = path.read_text(encoding="utf-8", errors="replace")
    analyzer = FormalContractAnalyzer()
    coverage = analyzer.audit_contract_coverage(code, path.name)

    console.print(f"\n[bold green]Cobertura de Contratos ACSL:[/bold green] {coverage['coverage_pct']}% ({coverage['documented']}/{coverage['total_functions']} funciones)")
    if coverage["incomplete_contracts"]:
        console.print(f"  [yellow]Contratos incompletos (faltan requires/ensures): {coverage['incomplete_contracts']}[/yellow]")
    if coverage["undocumented_functions"]:
        console.print(f"  [dim]Sin contrato: {coverage['undocumented_functions'][:8]}[/dim]")

    if not run_prover:
        return
    prover = analyzer.run_frama_c(path)
    if not prover.available:
        console.print(f"  [dim]{prover.message}[/dim]")
        return
    verdict = "[green]✓ todas las metas probadas[/green]" if prover.all_proved else f"[yellow]{prover.unproved_goals} metas sin probar[/yellow]"
    console.print(f"  Frama-C WP: {prover.proved_goals} probadas, {verdict}")


@app.command("padding-audit")
def cmd_padding_audit(
    files: list[str] = typer.Argument(..., help="Archivos fuente C a auditar."),
) -> None:
    """Detecta structs con padding enviados a archivos/sockets sin inicializar (memset)."""
    findings = 0
    for f in files:
        path = Path(f)
        if not path.exists():
            console.print(f"[bold red]Archivo no encontrado: {path}[/bold red]")
            raise typer.Exit(code=1)
        code = path.read_text(encoding="utf-8", errors="replace")
        obs = StructPaddingAuditor().analyze(code, path.name)
        for o in obs:
            findings += 1
            console.print(f"[bold red]ADVERTENCIA[/bold red] {o.filename}:{o.line} — {o.message}")
            console.print(f"  [dim]→ {o.suggestion}[/dim]")
    if findings == 0:
        console.print("[green]✓ Sin riesgos de filtración de bytes de relleno detectados.[/green]")
    else:
        raise typer.Exit(code=1)




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
