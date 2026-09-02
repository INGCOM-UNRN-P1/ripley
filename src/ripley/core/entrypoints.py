"""Descubrimiento dinámico y protocolo de adaptadores híbridos (RAM y CLI) para plugins satélites."""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Union

# Catálogo institucional de herramientas satélites delegadas
SATELLITE_CATALOG: Dict[str, Dict[str, Any]] = {
    "compiler": {
        "tool": "daedalus",
        "cli_cmd": "daedalus",
        "cli_subcmd": "compile",
        "description": "Compilación C bajo flags cátedra, AddressSanitizer/UBSan y traducción pedagógica de diagnósticos GCC/Clang/ld.",
    },
    "sandbox": {
        "tool": "nostromo",
        "cli_cmd": "nostromo",
        "cli_subcmd": "check",
        "description": "Ejecución aislada en sandbox Bubblewrap y validación de casos de prueba .in/.out.",
    },
    "style": {
        "tool": "gaff",
        "cli_cmd": "gaff",
        "cli_subcmd": "check",
        "description": "Auditoría de convenciones de estilo (Allman, indentación, espacios, llaves, nombres).",
    },
    "antipatterns": {
        "tool": "spunkmeyer",
        "cli_cmd": "spunkmeyer",
        "cli_subcmd": "detect",
        "description": "Detección de vicios de programación (while(!feof), casts en malloc, etc.).",
    },
    "security": {
        "tool": "kaneda",
        "cli_cmd": "kaneda",
        "cli_subcmd": "audit",
        "description": "Análisis de seguridad de llamadas al sistema, buffer overflows y APIs prohibidas.",
    },
    "headers_audit": {
        "tool": "wierzbowski",
        "cli_cmd": "wierzbowski",
        "cli_subcmd": "check",
        "description": "Auditoría de inclusión de encabezados y dependencias directas (IWYU).",
    },
    "macro_security": {
        "tool": "zhora",
        "cli_cmd": "zhora",
        "cli_subcmd": "check",
        "description": "Auditoría de seguridad y paréntesis en macros y directivas del preprocesador.",
    },
    "padding": {
        "tool": "brett",
        "cli_cmd": "brett",
        "cli_subcmd": "audit",
        "description": "Análisis de alineación, tamaño de structs y bytes de padding desperdiciados.",
    },
    "tda_encapsulation": {
        "tool": "motoko",
        "cli_cmd": "motoko",
        "cli_subcmd": "check",
        "description": "Verificación de opacidad y encapsulamiento de Tipos de Datos Abstractos (TDA).",
    },
    "portability": {
        "tool": "crowe",
        "cli_cmd": "crowe",
        "cli_subcmd": "check",
        "description": "Detección de asunciones de arquitectura y portabilidad (ancho de tipos, endianness).",
    },
    "callgraph": {
        "tool": "giger",
        "cli_cmd": "giger",
        "cli_subcmd": "check",
        "description": "Callgraph, Control Flow Graph (CFG), ciclos de recursión y funciones no invocadas.",
    },
    "formal_contracts": {
        "tool": "callahan",
        "cli_cmd": "callahan",
        "cli_subcmd": "verify",
        "description": "Verificación formal de contratos y pre/postcondiciones ACSL con Frama-C.",
    },
}


def normalize_finding(raw_obs: Dict[str, Any], source_plugin: str) -> Dict[str, Any]:
    """Adapta cualquier observación devuelta por plugins (RAM o CLI) al esquema canónico de Ripley."""
    rule_code = str(
        raw_obs.get("rule_code")
        or raw_obs.get("codigo")
        or raw_obs.get("code")
        or raw_obs.get("rule_id")
        or source_plugin
    )
    rule_name = str(
        raw_obs.get("rule_name")
        or raw_obs.get("titulo")
        or raw_obs.get("title")
        or (f"Violación de Encapsulamiento TDA: {raw_obs['tda']}" if "tda" in raw_obs else None)
        or (f"Violación de Encapsulamiento TDA: {raw_obs['tda_name']}" if "tda_name" in raw_obs else None)
        or raw_obs.get("symbol")
        or rule_code
    )

    raw_sev = str(raw_obs.get("severity") or raw_obs.get("severidad") or "ADVERTENCIA").upper()
    if raw_sev in ("WARN", "WARNING"):
        severity = "ADVERTENCIA"
    elif raw_sev in ("CRITICO", "ALTO", "ERROR", "FATAL"):
        severity = "ERROR"
    elif raw_sev in ("ESTILO", "STYLE"):
        severity = "ESTILO"
    elif raw_sev in ("INFO", "INFORMACION", "INFORMATIVO"):
        severity = "INFO"
    else:
        severity = raw_sev

    raw_file = str(raw_obs.get("file") or raw_obs.get("archivo") or raw_obs.get("location") or "")
    f_name = Path(raw_file).name if raw_file else ""
    line = int(raw_obs.get("line") or raw_obs.get("linea") or 0)
    col = int(raw_obs.get("column") or raw_obs.get("columna") or 0)
    msg = str(raw_obs.get("message") or raw_obs.get("mensaje") or "")
    sug = str(raw_obs.get("suggestion") or raw_obs.get("sugerencia") or "")

    return {
        "rule_code": rule_code,
        "rule_name": rule_name,
        "severity": severity,
        "file": f_name,
        "line": line,
        "column": col,
        "message": msg,
        "suggestion": sug,
        "source_plugin": source_plugin,
        # Claves de compatibilidad institucional
        "rule_id": rule_code,
        "codigo": rule_code,
        "titulo": rule_name,
        "severidad": severity,
        "archivo": f_name,
        "linea": line,
        "columna": col,
        "mensaje": msg,
        "sugerencia": sug,
    }


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

        raw_obs = (
            res.get("observaciones")
            or res.get("issues")
            or res.get("diagnosticos")
            or res.get("violations")
            or []
        )
        norm_obs = [normalize_finding(o, self.name) for o in raw_obs]
        res["observaciones"] = norm_obs
        res["issues"] = norm_obs

        if "passed" in res and "ok" not in res:
            res["ok"] = res["passed"]
        elif "ok" in res and "passed" not in res:
            res["passed"] = res["ok"]

        return res

    def _execute_cli(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la herramienta secundaria como subproceso CLI solicitando salida JSON."""
        cmd = self.cli_command or self.tool_name or self.name
        timeout = float(manifest_config.get("timeout", 20.0))

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
        elif self.name in ("callgraph", "formal_contracts") and workspace.is_dir():
            c_files = manifest_config.get("c_files")
            if not c_files:
                c_files = list(workspace.glob("*.c")) + list(workspace.glob("src/*.c"))
            if not c_files:
                return {"ok": True, "observaciones": [], "issues": []}

            cat = SATELLITE_CATALOG.get(self.name, {})
            subcmd = cat.get("cli_subcmd", "check")
            all_obs = []
            all_ok = True
            for cf in c_files:
                proc = subprocess.run(
                    [cmd, subcmd, str(cf), "--json"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if proc.stdout:
                    try:
                        data = json.loads(proc.stdout.strip())
                        raw_obs = (
                            data.get("observaciones")
                            or data.get("issues")
                            or data.get("diagnosticos")
                            or []
                        )
                        all_obs.extend([normalize_finding(o, self.name) for o in raw_obs])
                        if not data.get("ok", data.get("exito", True)):
                            all_ok = False
                    except Exception:
                        pass
            return {
                "ok": all_ok,
                "passed": all_ok,
                "observaciones": all_obs,
                "issues": all_obs,
            }
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
        raw_obs = (
            data.get("observaciones")
            or data.get("issues")
            or data.get("diagnosticos")
            or data.get("violations")
            or []
        )
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


def discover_entrypoint_plugins() -> List[SatellitePluginAdapter]:
    """Descubre todos los plugins registrados en 'ripley.plugins' y las herramientas del catálogo."""
    plugins_by_name: Dict[str, SatellitePluginAdapter] = {}

    # 1. Entrypoints registrados en el entorno Python
    try:
        eps = importlib.metadata.entry_points(group="ripley.plugins")
        for ep in eps:
            adapter = SatellitePluginAdapter(
                name=ep.name,
                group="ripley.plugins",
                entry_point=ep,
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

