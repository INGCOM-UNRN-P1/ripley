"""Descubrimiento dinámico y protocolo de adaptadores híbridos (RAM y CLI) para plugins satélites."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import json
import re
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Set, Union




_MAIN = re.compile(r"\bint\s+main\s*\(|\bmain\s*\(\s*(?:void|int)")


def _define_main(archivo: Path) -> bool:
    """¿El archivo C define `main`? Heurística textual, suficiente para elegir programas completos."""
    try:
        texto = archivo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(_MAIN.search(texto))


@dataclass
class SatellitePluginAdapter:
    """Adaptador híbrido de ejecución (In-Memory / CLI Fallback) y resiliencia para plugins satélites."""

    name: str
    group: str = "ripley.plugins"
    entry_point: Any = None
    instance: Any = None
    cli_command: Optional[str] = None
    tool_name: Optional[str] = None
    is_available: bool = True
    execution_mode: str = "memory"  # "memory", "cli", "unavailable"

    def __post_init__(self) -> None:
        cat_info = SATELLITE_CATALOG.get(self.name, {})
        if not cat_info:
            # Buscar si self.name es el nombre del binario o herramienta en el catálogo
            for k, v in SATELLITE_CATALOG.items():
                if v.get("tool") == self.name or v.get("cli_cmd") == self.name:
                    cat_info = v
                    break
        if not cat_info and self.entry_point is not None:
            # Inferir paquete del entrypoint (ej. 'drake.ripley_plugin:DrakePlugin' -> 'drake')
            mod = getattr(self.entry_point, "module", "") or str(getattr(self.entry_point, "value", ""))
            pkg = mod.split(".")[0] if mod else ""
            if pkg:
                cat_info = SATELLITE_CATALOG.get(pkg, {})
                if not cat_info:
                    for k, v in SATELLITE_CATALOG.items():
                        if v.get("tool") == pkg or v.get("cli_cmd") == pkg:
                            cat_info = v
                            break

        if not self.tool_name:
            self.tool_name = cat_info.get("tool", self.name)
        if not self.cli_command:
            self.cli_command = cat_info.get("cli_cmd", self.tool_name)

        if not self.is_available or self.execution_mode == "unavailable":
            self.is_available = False
            self.execution_mode = "unavailable"
            return

        self._resolve_availability()

    def _resolve_availability(self) -> None:
        """Aplica el algoritmo de 3 niveles: Prioridad 1 (RAM) -> Prioridad 2 (CLI) -> Prioridad 3 (Ausente)."""
        # 1. Si ya se proporcionó una instancia en RAM
        if self.instance is not None:
            avail = self.instance.is_available() if hasattr(self.instance, "is_available") else True
            if avail:
                self.is_available = True
                self.execution_mode = "memory"
                return

        # 2. Si hay un entrypoint registrado, intentar cargarlo
        if self.entry_point is not None:
            try:
                cls = self.entry_point.load()
                self.instance = cls()
                avail = self.instance.is_available() if hasattr(self.instance, "is_available") else True
                if avail:
                    self.is_available = True
                    self.execution_mode = "memory"
                    return
            except Exception:
                self.instance = None

        # 3. Fallback a subproceso CLI
        target_cmd = self.cli_command or self.tool_name or self.name
        if target_cmd and shutil.which(target_cmd):
            self.is_available = True
            self.execution_mode = "cli"
            return

        # 4. Herramienta Ausente
        self.is_available = False
        self.execution_mode = "unavailable"

    def execute(
        self,
        workspace: Union[Path, str],
        manifest_config: Optional[Dict[str, Any]] = None,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """Ejecuta el plugin adaptando el modo según disponibilidad y garantizando aislamiento de fallos."""
        ws_path = Path(workspace).resolve()
        cfg = manifest_config or {}

        # Prioridad 3: Herramienta Ausente
        if not self.is_available or self.execution_mode == "unavailable":
            return self._handle_missing_tool(ws_path, strict=strict)

        # Prioridad 1: Carga en RAM
        if self.execution_mode == "memory" and self.instance is not None:
            try:
                return self._execute_in_memory(ws_path, cfg)
            except Exception as e:
                return self._handle_plugin_error(ws_path, e)

        # Prioridad 2: Fallback a Subproceso CLI
        if self.execution_mode == "cli":
            try:
                return self._execute_cli(ws_path, cfg)
            except Exception as e:
                return self._handle_plugin_error(ws_path, e)

        return self._handle_missing_tool(ws_path, strict=strict)

    def _execute_in_memory(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la instancia cargada en memoria invocando .execute() o .run()."""
        if hasattr(self.instance, "execute"):
            res = self.instance.execute(workspace, manifest_config)
        elif hasattr(self.instance, "run"):
            source_dir = workspace if workspace.is_dir() else workspace.parent
            context = {
                "source_dir": str(source_dir),
                "workspace": workspace,
                "manifest_config": manifest_config,
            }
            res = self.instance.run(context)
        else:
            res = {"ok": True, "observaciones": []}

        if not isinstance(res, dict):
            res = {"ok": True, "observaciones": []}

        raw_obs = extract_raw_observations(res)
        norm_obs = [normalize_finding(o, self.name) for o in raw_obs]
        res["observaciones"] = norm_obs
        res["issues"] = norm_obs

        if "passed" in res and "ok" not in res:
            res["ok"] = res["passed"]
        elif "ok" in res and "passed" not in res:
            res["passed"] = res["ok"]
        elif "ok" not in res and "passed" not in res:
            res["ok"] = not any(str(o.get("severity", "")).upper() == "ERROR" for o in norm_obs)
            res["passed"] = res["ok"]

        return res

    def _execute_cli(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la herramienta secundaria como subproceso CLI solicitando salida JSON."""
        cmd = self.cli_command or self.tool_name or self.name
        timeout = float(manifest_config.get("timeout", 20.0))

        # Un satélite que necesita configuración que no recibió se saltea. Si se
        # lo invocara igual, su error de uso ("Missing argument 'modelo'")
        # terminaría como un hallazgo de severidad ERROR contra el código del
        # estudiante, que no tiene nada que ver con el problema.
        requeridas = SATELLITE_CATALOG.get(self.name, {}).get("requiere_config", ())
        faltantes = [k for k in requeridas if not manifest_config.get(k)]
        if faltantes:
            return {
                "ok": True,
                "passed": True,
                "observaciones": [],
                "issues": [],
                "omitido": True,
                "motivo": (
                    f"'{self.tool_name or self.name}' requiere "
                    f"{', '.join(faltantes)} en la configuración del manifiesto."
                ),
            }

        if self.name == "compiler":
            args = [cmd, "compile"]
            c_files = manifest_config.get("c_files")
            if c_files:
                args.extend([str(f) for f in c_files])
            elif workspace.is_file():
                args.append(str(workspace))
            else:
                c_candidates = list(workspace.glob("*.c")) + list(workspace.glob("src/*.c"))
                args.extend([str(f) for f in c_candidates])
            if manifest_config.get("output_bin"):
                args.extend(["-o", str(manifest_config["output_bin"])])
            args.append("--json")
        elif self.name == "sandbox":
            bin_path = manifest_config.get("binary_path") or str(workspace)
            test_dir = manifest_config.get("test_dir") or (
                str(workspace / "tests") if (workspace / "tests").is_dir() else str(workspace)
            )
            args = [cmd, "check", str(bin_path), str(test_dir), "--json"]
        elif SATELLITE_CATALOG.get(self.name, {}).get("entrada") == "archivo" and workspace.is_dir():
            c_files = manifest_config.get("c_files")
            if not c_files:
                c_files = list(workspace.glob("*.c")) + list(workspace.glob("src/*.c"))
            cat = SATELLITE_CATALOG.get(self.name, {})
            if cat.get("requiere_main"):
                # Fuzzear o correr bajo sanitizers exige un programa completo: un
                # módulo sin `main` no enlaza y su error de compilación llegaba
                # como hallazgo contra el estudiante.
                c_files = [f for f in c_files if _define_main(Path(f))]
            if not c_files:
                return {"ok": True, "observaciones": [], "issues": []}

            subcmd = cat.get("cli_subcmd", "check")
            all_obs = []
            all_ok = True
            for cf in c_files:
                proc = subprocess.run(
                    [cmd, subcmd, str(cf), *cat.get("args_extra", ()), "--json"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if proc.stdout:
                    try:
                        data = json.loads(proc.stdout.strip())
                        if isinstance(data, list):
                            data = {"ok": proc.returncode == 0, "observaciones": data}
                        raw_obs = extract_raw_observations(data)
                        all_obs.extend([normalize_finding(o, self.name) for o in raw_obs])
                        if data.get("instrumented") is False:
                            # tetsuo no pudo instrumentar (p. ej. falta libasan): no se
                            # verificó nada, y eso no es un hallazgo sobre el código.
                            continue
                        if not data.get("ok", data.get("exito", data.get("passed", proc.returncode == 0))):
                            all_ok = False
                    except Exception:
                        pass
            return {
                "ok": all_ok,
                "passed": all_ok,
                "observaciones": all_obs,
                "issues": all_obs,
            }
        elif self.name in ("abi_audit", "parker"):
            header = manifest_config.get("header")
            binary = manifest_config.get("binary")
            if not header or not binary:
                return {"ok": True, "observaciones": [], "issues": []}
            args = [cmd, "audit", str(header), "--binary", str(binary), "--json"]
        elif SATELLITE_CATALOG.get(self.name, {}).get("argumento_config"):
            cat = SATELLITE_CATALOG[self.name]
            # `requiere_config` ya garantizó que el valor está presente.
            args = [cmd, cat.get("cli_subcmd", "check"), str(manifest_config[cat["argumento_config"]]), "--json"]
        else:
            cat = SATELLITE_CATALOG.get(self.name, {})
            subcmd = cat.get("cli_subcmd", "check")
            args = [cmd, subcmd, str(workspace), "--json"]

        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = proc.stdout.strip() if proc.stdout else ""
        if not stdout:
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or f"Código de retorno CLI: {proc.returncode}")
            return {"ok": True, "observaciones": [], "issues": []}

        data = json.loads(stdout)
        if isinstance(data, list):
            data = {"ok": proc.returncode == 0, "observaciones": data}
        elif not isinstance(data, dict):
            data = {"ok": proc.returncode == 0, "observaciones": []}

        raw_obs = extract_raw_observations(data)
        norm_obs = [normalize_finding(o, self.name) for o in raw_obs]

        ok_val = bool(data.get("ok", data.get("exito", data.get("passed", proc.returncode == 0))))
        return {
            "ok": ok_val,
            "passed": ok_val,
            "observaciones": norm_obs,
            "issues": norm_obs,
            "raw_stdout": stdout,
            "raw_stderr": proc.stderr,
            "return_code": proc.returncode,
            **{k: v for k, v in data.items() if k not in ("observaciones", "issues", "diagnosticos", "violations")},
        }

    def _handle_missing_tool(self, workspace: Path, strict: bool = False) -> Dict[str, Any]:
        """Genera el diagnóstico informativo canónico ante una herramienta secundaria ausente."""
        tool_label = self.tool_name or (SATELLITE_CATALOG.get(self.name, {}).get("tool", self.name))
        sev = "ERROR" if strict else "ADVERTENCIA"
        code = f"MISSING_TOOL_{tool_label.upper()}"
        msg = f"La herramienta secundaria '{tool_label}' no está disponible en el entorno ni en PATH. Se omitieron sus verificaciones."
        sug = f"Instalá la herramienta mediante 'uv tool install {tool_label}'."

        finding = {
            "rule_code": code,
            "rule_name": f"Herramienta Ausente: {tool_label}",
            "severity": sev,
            "file": workspace.name,
            "line": 0,
            "column": 0,
            "message": msg,
            "suggestion": sug,
            "source_plugin": self.name,
            # Compatibilidad
            "rule_id": code,
            "codigo": code,
            "titulo": f"Herramienta Ausente: {tool_label}",
            "severidad": sev,
            "archivo": workspace.name,
            "linea": 0,
            "columna": 0,
            "mensaje": msg,
            "sugerencia": sug,
        }

        return {
            "ok": not strict,
            "passed": not strict,
            "missing_tool": True,
            "tool_name": tool_label,
            "observaciones": [finding],
            "issues": [finding],
        }

    def _handle_plugin_error(self, workspace: Path, error: Exception) -> Dict[str, Any]:
        """Aislamiento de fallo (Fail-Open): registra PLUGIN_ERROR_<NOMBRE> y permite continuar la evaluación."""
        tool_label = self.tool_name or self.name
        code = f"PLUGIN_ERROR_{tool_label.upper()}"
        msg = f"Fallo durante la ejecución del plugin '{tool_label}': {error}"
        sug = f"Verificá el funcionamiento o dependencias de '{tool_label}'."

        finding = {
            "rule_code": code,
            "rule_name": f"Fallo en Plugin: {tool_label}",
            "severity": "ERROR",
            "file": workspace.name,
            "line": 0,
            "column": 0,
            "message": msg,
            "suggestion": sug,
            "source_plugin": self.name,
            # Compatibilidad
            "rule_id": code,
            "codigo": code,
            "titulo": f"Fallo en Plugin: {tool_label}",
            "severidad": "ERROR",
            "archivo": workspace.name,
            "linea": 0,
            "columna": 0,
            "mensaje": msg,
            "sugerencia": sug,
        }

        return {
            "ok": False,
            "passed": False,
            "error": str(error),
            "observaciones": [finding],
            "issues": [finding],
        }


# Alias para compatibilidad hacia atrás
DiscoveredPlugin = SatellitePluginAdapter


def plugins_de_fase(fase: str) -> Set[str]:
    """Nombres de plugin (y de herramienta) catalogados en una fase dada.

    El lazo de plugins del motor se construye a partir de esto en vez de una
    lista escrita a mano: un satélite nuevo en el catálogo queda habilitado
    solo por estar catalogado, sin depender de que alguien recuerde agregarlo
    a una segunda lista paralela.
    """
    nombres: Set[str] = set()
    for clave, info in SATELLITE_CATALOG.items():
        if info.get("fase") == fase:
            nombres.add(clave)
            herramienta = info.get("tool")
            if herramienta:
                nombres.add(herramienta)
    return nombres


def discover_entrypoint_plugins() -> List[SatellitePluginAdapter]:
    """Descubre todos los plugins registrados en 'ripley.plugins' y las herramientas del catálogo."""
    plugins_by_name: Dict[str, SatellitePluginAdapter] = {}

    # 1. Entrypoints registrados en el entorno Python
    try:
        eps = importlib.metadata.entry_points(group="ripley.plugins")
        for ep in eps:
            # El entry-point solo aporta el nombre del plugin; sin los datos del
            # catálogo el fallback CLI buscaría `shutil.which("mocks")` en vez
            # del binario real (`holden`) y el satélite quedaría "no disponible".
            info = SATELLITE_CATALOG.get(ep.name, {})
            adapter = SatellitePluginAdapter(
                name=ep.name,
                group="ripley.plugins",
                entry_point=ep,
                tool_name=info.get("tool"),
                cli_command=info.get("cli_cmd"),
            )
            plugins_by_name[ep.name] = adapter
    except Exception:
        pass

    # 2. Herramientas del catálogo institucional que no estén en entrypoints
    for plugin_key, info in SATELLITE_CATALOG.items():
        if plugin_key not in plugins_by_name:
            adapter = SatellitePluginAdapter(
                name=plugin_key,
                group="ripley.plugins",
                tool_name=info.get("tool", plugin_key),
                cli_command=info.get("cli_cmd", plugin_key),
            )
            plugins_by_name[plugin_key] = adapter

    return list(plugins_by_name.values())


def get_satellite_plugin(name: str) -> SatellitePluginAdapter:
    """Obtiene un adaptador satélite por nombre garantizando resolución de disponibilidad."""
    for p in discover_entrypoint_plugins():
        if p.name == name:
            return p

    cat = SATELLITE_CATALOG.get(name, {})
    return SatellitePluginAdapter(
        name=name,
        group="ripley.plugins",
        tool_name=cat.get("tool", name),
        cli_command=cat.get("cli_cmd", name),
    )


# Registro de comandos y re-exports (deben ir tras definir los objetos compartidos)
from ripley.core.entrypoints_catalogo import SATELLITE_CATALOG  # noqa: E402,F401
from ripley.core.entrypoints_contrato import extract_raw_observations, normalize_finding  # noqa: E402,F401
