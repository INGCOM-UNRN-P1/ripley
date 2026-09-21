"""Dataclasses de cada sección de ripley.toml."""

from dataclasses import dataclass, field
from typing import List, Optional



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
class GraphicsConfig:
    """Evaluación de prácticas gráficas (SDL2/Raylib) bajo framebuffer virtual."""
    enabled: bool = False
    screen: str = "1280x720x24"
    settle_seconds: float = 1.0
    max_diff_pixels: int = 100
    display_base: int = 90
    capture_executable: str = "import"   # ImageMagick
    compare_executable: str = "compare"  # ImageMagick


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
