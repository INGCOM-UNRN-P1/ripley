"""Configuration loader and validator for ripley.toml."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional
import tomllib


@dataclass
class CompilerConfig:
    enabled: bool = True
    executable: str = "gcc"
    flags: List[str] = field(
        default_factory=lambda: [
            "-Wall",
            "-Wextra",
            "-pedantic",
            "-std=c11",
            "-fsanitize=address,undefined",
        ]
    )


@dataclass
class LimitsConfig:
    timeout_segundos: int = 5
    limite_memoria_mb: int = 128
    max_tamano_ejecutable_mb: int = 10


@dataclass
class TemplatesConfig:
    ruta_plantillas: str = "templates/"


@dataclass
class CppcheckConfig:
    enabled: bool = True
    ejecutable: str = "cppcheck"
    parametros: List[str] = field(
        default_factory=lambda: [
            "--enable=all",
            "--inline-suppr",
            "--suppress=missingIncludeSystem",
            "--suppress=staticFunction",
        ]
    )
    reglas_python: List[str] = field(default_factory=list)


@dataclass
class StyleConfig:
    enabled: bool = True
    brace_style: str = "allman"  # "allman" | "bsd" | "break" | "k&r" | "attach"
    require_braces: bool = True
    indent_style: str = "spaces"  # "spaces" | "tabs"
    indent_size: int = 4
    spacing_operators: bool = True
    spacing_keywords: bool = True
    no_trailing_whitespace: bool = True
    max_blank_lines: int = 2


@dataclass
class P1RulesConfig:
    enabled: bool = True


@dataclass
class LintersConfig:
    enabled: bool = False
    dead_code: bool = True
    magic_numbers: bool = True
    internal_clones: bool = True
    naming: bool = True
    doxygen: bool = False


@dataclass
class ValgrindConfig:
    enabled: bool = True
    tolerar_fugas_en_error: bool = True
    flags: List[str] = field(
        default_factory=lambda: [
            "--leak-check=full",
            "--show-leak-kinds=all",
            "--track-origins=yes",
            "--error-exitcode=1",
        ]
    )


@dataclass
class RubricConfig:
    peso_compilacion: float = 0.25
    peso_linter: float = 0.25
    peso_estilo: float = 0.15
    peso_pruebas: float = 0.35

    def validate(self) -> None:
        total = self.peso_compilacion + self.peso_linter + self.peso_estilo + self.peso_pruebas
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"La suma de los pesos de la rúbrica debe ser 1.0 (actual: {total:.2f})")


@dataclass
class SecurityConfig:
    enabled: bool = True
    forbidden_calls: List[str] = field(
        default_factory=lambda: [
            "system",
            "fork",
            "execv",
            "execvp",
            "execl",
            "execlp",
            "execle",
            "execve",
            "popen",
            "kill",
            "raise",
            "clone",
            "ptrace",
            "socket",
            "connect",
            "bind",
            "listen",
            "accept",
        ]
    )
    forbidden_headers: List[str] = field(
        default_factory=lambda: [
            "unistd.h",
            "sys/socket.h",
            "netinet/in.h",
            "arpa/inet.h",
            "sys/wait.h",
            "signal.h",
            "sys/ptrace.h",
        ]
    )


@dataclass
class SandboxConfig:
    enabled: bool = False
    provider: str = "bubblewrap"


@dataclass
class FlowchartConfig:
    enabled: bool = False
    format: str = "mermaid"  # "mermaid" | "dot"


@dataclass
class MemoryVisualizerConfig:
    enabled: bool = False
    format: str = "mermaid"  # "mermaid" | "dot"


@dataclass
class CallgraphConfig:
    enabled: bool = False
    format: str = "mermaid"  # "mermaid" | "dot"
    include_stdlib: bool = False


@dataclass
class PropertyTestingConfig:
    enabled: bool = False
    properties: List[str] = field(
        default_factory=lambda: ["idempotence", "commutativity", "sort_invariant"]
    )


@dataclass
class AstAuditorsConfig:
    enabled: bool = False
    const_correctness: bool = True
    short_circuit: bool = True
    deep_free: bool = True
    string_null: bool = True
    variable_shadowing: bool = True
    dangling_stack_pointer: bool = True
    overengineering: bool = True
    evaluation_order: bool = True
    string_literal_write: bool = True
    backward_goto: bool = True
    deprecated_api: bool = True
    enum_bitmask: bool = True
    loop_termination: bool = True


@dataclass
class PureFunctionsConfig:
    enabled: bool = False
    functions: List[str] = field(default_factory=list)


@dataclass
class MakefileConfig:
    """Soporte para Makefiles estudiantiles y compilación modular."""
    enabled: bool = False
    prefer_makefile: bool = True
    executable: str = "make"
    target: str = "all"
    timeout_segundos: int = 30
    expected_binary: str = ""  # nombre del binario producido; vacío = autodetección


@dataclass
class PaddingAuditConfig:
    """Auditoría de bytes de relleno de structs enviados a I/O sin inicializar."""
    enabled: bool = False


@dataclass
class RestrictionsConfig:
    enabled: bool = False
    forbidden_constructs: List[str] = field(default_factory=list)
    required_constructs: List[str] = field(default_factory=list)


@dataclass
class DoxygenConfig:
    enabled: bool = False
    require_brief: bool = True
    require_params: bool = True
    require_return: bool = True


@dataclass
class CustomToolConfig:
    name: str
    command: str
    enabled: bool = True
    stage: str = "source"  # "source" | "binary" | "folder"
    fail_on_error: bool = False
    timeout_segundos: Optional[int] = None


@dataclass
class RipleyConfig:
    compiler: CompilerConfig = field(default_factory=CompilerConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    templates: TemplatesConfig = field(default_factory=TemplatesConfig)
    cppcheck: CppcheckConfig = field(default_factory=CppcheckConfig)
    style: StyleConfig = field(default_factory=StyleConfig)
    p1_rules: P1RulesConfig = field(default_factory=P1RulesConfig)
    linters: LintersConfig = field(default_factory=LintersConfig)
    ast_auditors: AstAuditorsConfig = field(default_factory=AstAuditorsConfig)
    flowchart: FlowchartConfig = field(default_factory=FlowchartConfig)
    memory_visualizer: MemoryVisualizerConfig = field(default_factory=MemoryVisualizerConfig)
    callgraph: CallgraphConfig = field(default_factory=CallgraphConfig)
    property_testing: PropertyTestingConfig = field(default_factory=PropertyTestingConfig)
    pure_functions: PureFunctionsConfig = field(default_factory=PureFunctionsConfig)
    padding: PaddingAuditConfig = field(default_factory=PaddingAuditConfig)
    makefile: MakefileConfig = field(default_factory=MakefileConfig)
    restrictions: RestrictionsConfig = field(default_factory=RestrictionsConfig)
    doxygen: DoxygenConfig = field(default_factory=DoxygenConfig)
    valgrind: ValgrindConfig = field(default_factory=ValgrindConfig)
    rubric: RubricConfig = field(default_factory=RubricConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    custom_tools: List[CustomToolConfig] = field(default_factory=list)
    origen_configuracion: str = "Valores por defecto del sistema (ripley.toml no encontrado)"


    def validate(self) -> None:
        self.rubric.validate()
        if self.limits.timeout_segundos <= 0:
            raise ValueError("timeout_segundos debe ser mayor a 0")
        if self.limits.limite_memoria_mb <= 0:
            raise ValueError("limite_memoria_mb debe ser mayor a 0")
        if self.limits.max_tamano_ejecutable_mb <= 0:
            raise ValueError("max_tamano_ejecutable_mb debe ser mayor a 0")
        valid_braces = {"allman", "bsd", "break", "k&r", "attach"}
        if self.style.brace_style.lower() not in valid_braces:
            raise ValueError(f"brace_style inválido: '{self.style.brace_style}'. Opciones: {valid_braces}")
        valid_indents = {"spaces", "tabs"}
        if self.style.indent_style.lower() not in valid_indents:
            raise ValueError(f"indent_style inválido: '{self.style.indent_style}'. Opciones: {valid_indents}")


def load_config(config_path: str | Path = "ripley.toml") -> RipleyConfig:
    """Carga y valida ripley.toml. Si no existe, retorna configuración por defecto."""
    path = Path(config_path)
    if not path.exists():
        cfg = RipleyConfig(origen_configuracion="Valores por defecto del sistema (ripley.toml no encontrado)")
        cfg.validate()
        return cfg

    with open(path, "rb") as f:
        data: dict[str, Any] = tomllib.load(f)

    compiler_data = data.get("compiler", {})
    limits_data = data.get("limits", {})
    templates_data = data.get("templates", {})
    cppcheck_data = data.get("cppcheck", {})
    style_data = data.get("style", {})
    p1_rules_data = data.get("p1_rules", {})
    linters_data = data.get("linters", {})
    ast_auditors_data = data.get("ast_auditors", {})
    flowchart_data = data.get("flowchart", {})
    memory_vis_data = data.get("memory_visualizer", {})
    callgraph_data = data.get("callgraph", {})
    prop_testing_data = data.get("property_testing", {})
    pure_funcs_data = data.get("pure_functions", {})
    restrictions_data = data.get("restrictions", {})
    doxygen_data = data.get("doxygen", {})
    valgrind_data = data.get("valgrind", {})
    rubric_data = data.get("rubric", {})
    security_data = data.get("security", {})
    sandbox_data = data.get("sandbox", {})
    makefile_data = data.get("makefile", {})

    cfg = RipleyConfig(
        compiler=CompilerConfig(
            enabled=compiler_data.get("enabled", True),
            executable=compiler_data.get("executable", "gcc"),
            flags=compiler_data.get(
                "flags",
                ["-Wall", "-Wextra", "-pedantic", "-std=c11", "-fsanitize=address,undefined"],
            ),
        ),
        limits=LimitsConfig(
            timeout_segundos=limits_data.get("timeout_segundos", 5),
            limite_memoria_mb=limits_data.get("limite_memoria_mb", 128),
            max_tamano_ejecutable_mb=limits_data.get("max_tamano_ejecutable_mb", 10),
        ),
        templates=TemplatesConfig(
            ruta_plantillas=templates_data.get("ruta_plantillas", "templates/"),
        ),
        cppcheck=CppcheckConfig(
            enabled=cppcheck_data.get("enabled", True),
            ejecutable=cppcheck_data.get("ejecutable", "cppcheck"),
            parametros=cppcheck_data.get(
                "parametros",
                [
                    "--enable=all",
                    "--inline-suppr",
                    "--suppress=missingIncludeSystem",
                    "--suppress=staticFunction",
                ],
            ),
            reglas_python=cppcheck_data.get("reglas_python", []),
        ),
        style=StyleConfig(
            enabled=style_data.get("enabled", True),
            brace_style=style_data.get("brace_style", "allman"),
            require_braces=style_data.get("require_braces", True),
            indent_style=style_data.get("indent_style", "spaces"),
            indent_size=style_data.get("indent_size", 4),
            spacing_operators=style_data.get("spacing_operators", True),
            spacing_keywords=style_data.get("spacing_keywords", True),
            no_trailing_whitespace=style_data.get("no_trailing_whitespace", True),
            max_blank_lines=style_data.get("max_blank_lines", 2),
        ),
        p1_rules=P1RulesConfig(
            enabled=p1_rules_data.get("enabled", True),
        ),
        linters=LintersConfig(
            enabled=linters_data.get("enabled", False),
            dead_code=linters_data.get("dead_code", True),
            magic_numbers=linters_data.get("magic_numbers", True),
            internal_clones=linters_data.get("internal_clones", True),
            naming=linters_data.get("naming", True),
            doxygen=linters_data.get("doxygen", False),
        ),
        ast_auditors=AstAuditorsConfig(
            enabled=ast_auditors_data.get("enabled", False),
            const_correctness=ast_auditors_data.get("const_correctness", True),
            short_circuit=ast_auditors_data.get("short_circuit", True),
            deep_free=ast_auditors_data.get("deep_free", True),
            string_null=ast_auditors_data.get("string_null", True),
            variable_shadowing=ast_auditors_data.get("variable_shadowing", True),
            dangling_stack_pointer=ast_auditors_data.get("dangling_stack_pointer", True),
            overengineering=ast_auditors_data.get("overengineering", True),
            evaluation_order=ast_auditors_data.get("evaluation_order", True),
            string_literal_write=ast_auditors_data.get("string_literal_write", True),
            backward_goto=ast_auditors_data.get("backward_goto", True),
            deprecated_api=ast_auditors_data.get("deprecated_api", True),
            enum_bitmask=ast_auditors_data.get("enum_bitmask", True),
            loop_termination=ast_auditors_data.get("loop_termination", True),
        ),
        flowchart=FlowchartConfig(
            enabled=flowchart_data.get("enabled", False),
            format=flowchart_data.get("format", "mermaid"),
        ),
        memory_visualizer=MemoryVisualizerConfig(
            enabled=memory_vis_data.get("enabled", False),
            format=memory_vis_data.get("format", "mermaid"),
        ),
        callgraph=CallgraphConfig(
            enabled=callgraph_data.get("enabled", False),
            format=callgraph_data.get("format", "mermaid"),
            include_stdlib=callgraph_data.get("include_stdlib", False),
        ),
        property_testing=PropertyTestingConfig(
            enabled=prop_testing_data.get("enabled", False),
            properties=prop_testing_data.get(
                "properties", ["idempotence", "commutativity", "sort_invariant"]
            ),
        ),
        pure_functions=PureFunctionsConfig(
            enabled=pure_funcs_data.get("enabled", False),
            functions=pure_funcs_data.get("functions", []),
        ),
        padding=PaddingAuditConfig(
            enabled=data.get("padding", data.get("padding_audit", {})).get("enabled", False)
            if isinstance(data.get("padding", data.get("padding_audit")), dict)
            else False,
        ),
        makefile=MakefileConfig(
            enabled=makefile_data.get("enabled", False),
            prefer_makefile=makefile_data.get("prefer_makefile", True),
            executable=makefile_data.get("executable", "make"),
            target=makefile_data.get("target", "all"),
            timeout_segundos=makefile_data.get("timeout_segundos", 30),
            expected_binary=makefile_data.get("expected_binary", ""),
        ),
        restrictions=RestrictionsConfig(
            enabled=restrictions_data.get("enabled", False),
            forbidden_constructs=restrictions_data.get("forbidden_constructs", []),
            required_constructs=restrictions_data.get("required_constructs", []),
        ),
        doxygen=DoxygenConfig(
            enabled=doxygen_data.get("enabled", False),
            require_brief=doxygen_data.get("require_brief", True),
            require_params=doxygen_data.get("require_params", True),
            require_return=doxygen_data.get("require_return", True),
        ),
        valgrind=ValgrindConfig(
            enabled=valgrind_data.get("enabled", True),
            flags=valgrind_data.get(
                "flags",
                [
                    "--leak-check=full",
                    "--show-leak-kinds=all",
                    "--track-origins=yes",
                    "--error-exitcode=1",
                ],
            ),
        ),
        rubric=RubricConfig(
            peso_compilacion=rubric_data.get("peso_compilacion", 0.25),
            peso_linter=rubric_data.get("peso_linter", 0.25),
            peso_estilo=rubric_data.get("peso_estilo", 0.15),
            peso_pruebas=rubric_data.get("peso_pruebas", 0.35),
        ),
        security=SecurityConfig(
            enabled=security_data.get("enabled", True),
            forbidden_calls=security_data.get(
                "forbidden_calls",
                [
                    "system",
                    "fork",
                    "execv",
                    "execvp",
                    "execl",
                    "execlp",
                    "execle",
                    "execve",
                    "popen",
                    "kill",
                    "raise",
                    "clone",
                    "ptrace",
                    "socket",
                    "connect",
                    "bind",
                    "listen",
                    "accept",
                ],
            ),
            forbidden_headers=security_data.get(
                "forbidden_headers",
                [
                    "unistd.h",
                    "sys/socket.h",
                    "netinet/in.h",
                    "arpa/inet.h",
                    "sys/wait.h",
                    "signal.h",
                    "sys/ptrace.h",
                ],
            ),
        ),
        sandbox=SandboxConfig(
            enabled=sandbox_data.get("enabled", False),
            provider=sandbox_data.get("provider", "bubblewrap"),
        ),
        custom_tools=[
            CustomToolConfig(
                name=item.get("name", "custom_tool"),
                command=item.get("command", ""),
                enabled=item.get("enabled", True),
                stage=item.get("stage", "source"),
                fail_on_error=item.get("fail_on_error", False),
                timeout_segundos=item.get("timeout_segundos", None),
            )
            for item in data.get("custom_tools", [])
            if isinstance(item, dict) and "command" in item
        ],
        origen_configuracion=f"Archivo de configuración: '{path}'",
    )

    cfg.validate()
    return cfg


