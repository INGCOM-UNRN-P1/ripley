"""Student-side verification runner: executes a .ripkg manifest against local sources.

Compila con los flags de la práctica, corre los testcases públicos y aplica
exactamente el subconjunto de checks declarado en el manifiesto. Los checks
cuyas herramientas externas faltan se reportan como OMITIDOS, nunca como
aprobados.
"""

from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from typing import Dict, List, Optional

from ripley.pipeline import bundle as bundle_mod
from ripley.pipeline.availability import available_map
from ripley.pipeline.bundle import BundleError, RipkgBundle
from ripley.core.gcc_translator import summarize_for_humans, translate_stderr
import ripley.pipeline.checks  # noqa: F401  (pobla el registro)
from ripley.pipeline.plugins import HOOKS, PluginContext, PluginManager
from ripley.pipeline.registry import all_checks, get, is_runnable, iter_uniform_static
from ripley.tools.compiler import Compiler
from ripley.tools.makefile import make_build
from ripley.tools.runner import DynamicTestRunner
from ripley.tools.testcases import TestCaseInfo


@dataclass
class StudentRunReport:
    practica: str = ""
    compiled_ok: bool = False
    compile_errors: str = ""
    tests_total: int = 0
    tests_passed: int = 0
    findings: Dict[str, List[dict]] = field(default_factory=dict)
    omitted: List[str] = field(default_factory=list)
    executed_checks: List[str] = field(default_factory=list)
    signature_verified: bool = False
    human_diagnostics: str = ""
    plugins_ran: List[str] = field(default_factory=list)

    @property
    def total_findings(self) -> int:
        return sum(len(v) for v in self.findings.values())

    @property
    def success(self) -> bool:
        """True si compila, pasa todos los testcases públicos y no hay hallazgos ERROR."""
        if not self.compiled_ok or (self.tests_total and self.tests_passed < self.tests_total):
            return False
        for obs in self.findings.values():
            if any(o.get("severity") == "ERROR" for o in obs):
                return False
        return True


def run_bundle(
    bundle_path: Path | str,
    source_files: List[Path],
    strict: bool = False,
    verify_signature: bool = False,
) -> StudentRunReport:
    """Ejecuta la verificación temprana completa sobre fuentes locales."""
    plugins_dir = Path(source_files[0]).resolve().parent / "plugins"
    if not plugins_dir.is_dir():
        plugins_dir = Path.cwd() / "plugins"
    manager = PluginManager(plugins_dir)
    ctx = PluginContext(phase="session_start", workspace_dir=Path.cwd(),
                        sources=[Path(s).resolve() for s in source_files],
                        activity=Path(bundle_path).stem)
    manager.dispatch("session_start", ctx)

    try:
        loaded: RipkgBundle = bundle_mod.load_bundle(bundle_path, verify_signature=verify_signature)
    except BundleError:
        raise
    finally:
        if manager.errors:
            ctx.set("plugin_errors", list(manager.errors))
    report = StudentRunReport(
        practica=loaded.practica,
        signature_verified=verify_signature and loaded.signed,
    )
    manifest = loaded.manifest
    enabled_ids = {k for k, v in manifest.get("checks", {}).items() if v}
    compiler_cfg = manifest.get("compiler", {})

    tools = available_map()
    payload = bundle_mod.payload_of(loaded)

    with tempfile.TemporaryDirectory(prefix="ripley_check_") as td:
        tmp = Path(td)

        # 1. Compilación con los flags declarados por la práctica.
        sources = [Path(s).resolve() for s in source_files]
        missing = [str(s) for s in sources if not s.exists()]
        if missing:
            raise FileNotFoundError(f"Fuentes inexistentes: {', '.join(missing)}")

        # 1bis. Build modular vía Makefile si la práctica lo habilita.
        make_cfg = manifest.get("makefile", {})
        src_dir = sources[0].parent
        use_make = (
            "build.makefile" in enabled_ids
            and (src_dir / "Makefile").exists()
            and tools.get("make")
        )

        from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig
        binary = tmp / "student_bin"
        compiler = Compiler(
            CompilerConfig(
                executable=compiler_cfg.get("executable", "gcc"),
                flags=list(compiler_cfg.get("flags", ["-std=c11", "-Wall"])),
            ),
            LimitsConfig(timeout_segundos=15),
            SandboxConfig(),
        )
        if use_make:
            build = make_build(
                src_dir,
                target=make_cfg.get("target", "all"),
                expected_binary=make_cfg.get("expected_binary", ""),
            )
            report.compiled_ok = build.success
            report.compile_errors = (build.stderr or build.stdout).strip()[:4000]
            report.human_diagnostics = build.human_errors
            if not build.success or build.binary_path is None:
                if build.success and build.binary_path is None:
                    # Sin binario detectable: caer a compilación directa con flags oficiales.
                    pass
                else:
                    return report
            else:
                binary = build.binary_path

        manager.dispatch("pre_compile", ctx)
        result = compiler.compile(sources, binary)
        ctx.set("compile", {"success": result.success})
        manager.dispatch("post_compile", ctx)
        report.compiled_ok = result.success
        if not result.success:
            report.compile_errors = result.stderr.strip()[:4000]
            translated = translate_stderr(result.stderr)
            if translated:
                report.human_diagnostics = summarize_for_humans(translated)
            manager.dispatch("session_end", ctx)
            return report

        # 2. Testcases públicos: se materializan en disco para reutilizar
        #    exactamente el mismo DynamicTestRunner que usa el docente.
        tc_dir = tmp / "testcases"
        ins = sorted(n for n in payload if n.endswith(".in"))
        outs = {Path(n).stem: n for n in payload if n.endswith(".out")}
        from ripley.config import LimitsConfig
        runner = DynamicTestRunner(LimitsConfig(timeout_segundos=5))
        for in_name in ins:
            stem = Path(in_name).stem
            if stem not in outs:
                continue  # Sin salida esperada no es verificable por el estudiante.
            in_path = tc_dir / f"{stem}.in"
            out_path = tc_dir / f"{stem}.out"
            in_path.parent.mkdir(parents=True, exist_ok=True)
            in_path.write_bytes(payload[in_name])
            out_path.write_bytes(payload[outs[stem]])
            detail = runner.run_case(binary, TestCaseInfo(
                exercise="practica",
                case_name=stem,
                in_file=in_path,
                out_file=out_path,
                argv_file=None,
            ))
            report.tests_total += 1
            if detail.resultado == "PASSED":
                report.tests_passed += 1

    # 3. Checks estáticos habilitados en el manifiesto.
    for spec in iter_uniform_static():
        if spec.check_id not in enabled_ids:
            continue
        if not is_runnable(spec, tools):
            report.omitted.append(spec.check_id)
            continue
        findings: List[dict] = []
        for src in source_files:
            code = Path(src).read_text(encoding="utf-8", errors="replace")
            for obs in spec.runner(code, Path(src).name):
                findings.append({
                    "archivo": obs.filename,
                    "linea": obs.line,
                    "severidad": obs.severity,
                    "mensaje": obs.message,
                    "sugerencia": obs.suggestion,
                })
        report.findings[spec.check_id] = findings
        report.executed_checks.append(spec.check_id)

    ctx.observations = [
        {**obs, "check": cid}
        for cid, obs_list in report.findings.items()
        for obs in obs_list
    ]
    manager.dispatch("post_checks", ctx)
    for plugin_name in (p.name for p in manager.plugins):
        report.plugins_ran.append(plugin_name)

    manager.dispatch("pre_report", ctx)
    manager.dispatch("post_report", ctx)
    manager.dispatch("session_end", ctx)

    # Checks del manifiesto que no son uniform-static: listados como omitidos
    # cuando sus herramientas no están; los dinámicos avanzados quedan para CLIs.
    static_ids = {s.check_id for s in iter_uniform_static()}
    for cid in sorted(enabled_ids - static_ids):
        spec = get(cid)
        if spec is None:
            continue
        if not is_runnable(spec, tools):
            report.omitted.append(cid)

    return report
