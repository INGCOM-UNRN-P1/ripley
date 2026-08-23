"""Check catalog registration: binds every analyzer to the unified registry."""

from ripley.core.ast_auditors import (
    BackwardGotoLinter,
    ConstCorrectnessLinter,
    DanglingStackPointerLinter,
    DeepFreeLinter,
    DeprecatedAPILinter,
    EnumBitmaskLinter,
    EvaluationOrderLinter,
    FloatComparisonLinter,
    IWYULinter,
    LoopTerminationLinter,
    OverengineeringLinter,
    ShortCircuitLinter,
    StringLiteralWriteLinter,
    StringNullPointerLinter,
    VariableShadowingLinter,
)
from ripley.core.doxygen import DoxygenAuditor
from ripley.core.padding_audit import StructPaddingAuditor
from ripley.pipeline.registry import CheckSpec, register

# ---------------------------------------------------------------------------
# Auditores AST estáticos uniformes: runner(code, filename) -> [LinterObservation]
# Los toggles replican 1:1 las claves de [ast_auditors] en ripley.toml.
# ---------------------------------------------------------------------------
_AST_CHECKS = [
    ("ast.const_correctness", "Const-correctness en parámetros puntero", "const_correctness", "const_correctness", "[AST:ConstCorrectness]", ConstCorrectnessLinter),
    ("ast.short_circuit", "Cortocircuitos con efectos colaterales", "short_circuit", "short_circuit", "[AST:ShortCircuit]", ShortCircuitLinter),
    ("ast.deep_free", "Liberación profunda de estructuras anidadas", "deep_free", "deep_free", "[AST:DeepFree]", DeepFreeLinter),
    ("ast.string_null", "Punteros nulos en funciones <string.h>", "string_null", "string_null", "[AST:StringNull]", StringNullPointerLinter),
    ("ast.variable_shadowing", "Sombras de variables (shadowing)", "variable_shadowing", "variable_shadowing", "[AST:Shadowing]", VariableShadowingLinter),
    ("ast.dangling_stack_pointer", "Retorno de direcciones del stack", "dangling_stack_pointer", "dangling_stack_pointer", "[AST:DanglingPtr]", DanglingStackPointerLinter),
    ("ast.overengineering", "Sobre-ingeniería (XOR swap, ternarios anidados)", "overengineering", "overengineering", "[AST:Overengineering]", OverengineeringLinter),
    ("ast.evaluation_order", "Dependencia del orden de evaluación de argumentos", "evaluation_order", "evaluation_order", "[AST:EvaluationOrder]", EvaluationOrderLinter),
    ("ast.string_literal_write", "Escritura sobre literales en .rodata", "string_literal_write", "string_literal_write", "[AST:StringLiteralWrite]", StringLiteralWriteLinter),
    ("ast.backward_goto", "Saltos hacia atrás con goto", "backward_goto", "backward_goto", "[AST:BackwardGoto]", BackwardGotoLinter),
    ("ast.deprecated_api", "API C obsoleta o insegura", "deprecated_api", "deprecated_api", "[AST:DeprecatedAPI]", DeprecatedAPILinter),
    ("ast.enum_bitmask", "Enums usados como máscaras de bits sin potencias de dos", "enum_bitmask", "enum_bitmask", "[AST:EnumBitmask]", EnumBitmaskLinter),
    ("ast.loop_termination", "Heurística de terminación de bucles", "loop_termination", "loop_termination", "[AST:LoopTermination]", LoopTerminationLinter),
]

for check_id, title, toggle, _cfg_key, prefix, cls in _AST_CHECKS:
    register(CheckSpec(
        check_id=check_id,
        title=title,
        layer="static",
        scope="both",
        config_section="ast_auditors",
        toggle=toggle,
        prefix=prefix,
        runner=cls().analyze,
    ))

# Checks estáticos bajo demanda (sin toggle propio en evaluate; disponibles
# vía `ripley-check lint` y listados para el doctor).
register(CheckSpec(
    check_id="core.float_comparison",
    title="Comparaciones de igualdad directa en punto flotante",
    layer="static",
    scope="student",
    prefix="[FloatComparison]",
    runner=FloatComparisonLinter().analyze,
))
register(CheckSpec(
    check_id="core.iwyu",
    title="Inclusiones innecesarias (Include What You Use)",
    layer="static",
    scope="student",
    prefix="[IWYU]",
    runner=IWYULinter().analyze,
))

# Padding de structs (sección TOML propia con master enabled).
register(CheckSpec(
    check_id="core.struct_padding",
    title="Bytes de relleno enviados a I/O sin inicializar",
    layer="static",
    scope="student",
    config_section="padding",
    toggle="enabled",
    prefix="[Padding]",
    runner=StructPaddingAuditor().analyze,
))

# Documentación Doxygen.
register(CheckSpec(
    check_id="core.doxygen",
    title="Bloques @brief/@param/@return en funciones",
    layer="static",
    scope="both",
    prefix="[Doxygen]",
))

# ---------------------------------------------------------------------------
# Construcción: Makefiles estudiantiles y compilación modular (dinámico)
# ---------------------------------------------------------------------------
register(CheckSpec(
    check_id="build.makefile",
    title="Makefile estudiantil: auditoría de calidad y build modular vía make",
    layer="dynamic",
    scope="both",
    config_section="makefile",
    toggle="enabled",
    requires_tools=("make", "gcc"),
))


# ---------------------------------------------------------------------------
# Prácticas gráficas bajo framebuffer virtual (dinámico)
# ---------------------------------------------------------------------------
register(CheckSpec(
    check_id="graphics.xvfb",
    title="Prácticas SDL2/Raylib: ejecución bajo Xvfb y comparación de capturas",
    layer="dynamic",
    scope="both",
    config_section="graphics",
    toggle="enabled",
    requires_tools=("Xvfb", "import", "compare"),
))
