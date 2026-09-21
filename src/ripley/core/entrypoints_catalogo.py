"""Catálogo institucional de herramientas satélites delegadas."""

from __future__ import annotations

from typing import Any, Dict



# Catálogo institucional de herramientas satélites delegadas
SATELLITE_CATALOG: Dict[str, Dict[str, Any]] = {
    "compiler": {
        "fase": "orquestado",
        "tool": "daedalus",
        "cli_cmd": "daedalus",
        "cli_subcmd": "compile",
        "description": "Compilación C bajo flags cátedra, AddressSanitizer/UBSan y traducción pedagógica de diagnósticos GCC/Clang/ld.",
    },
    "sandbox": {
        "fase": "orquestado",
        "tool": "nostromo",
        "cli_cmd": "nostromo",
        "cli_subcmd": "check",
        "description": "Ejecución aislada en sandbox Bubblewrap y validación de casos de prueba .in/.out.",
    },
    "style": {
        "fase": "estatico",
        "tool": "gaff",
        "cli_cmd": "gaff",
        "cli_subcmd": "check",
        "description": "Auditoría de convenciones de estilo (Allman, indentación, espacios, llaves, nombres).",
    },
    "antipatterns": {
        "fase": "estatico",
        "tool": "spunkmeyer",
        "cli_cmd": "spunkmeyer",
        "cli_subcmd": "detect",
        "description": "Detección de vicios de programación (while(!feof), casts en malloc, etc.).",
    },
    "security": {
        "fase": "estatico",
        "tool": "kaneda",
        "cli_cmd": "kaneda",
        "cli_subcmd": "audit",
        "description": "Análisis de seguridad de llamadas al sistema, buffer overflows y APIs prohibidas.",
    },
    "headers_audit": {
        "fase": "estatico",
        "tool": "wierzbowski",
        "cli_cmd": "wierzbowski",
        "cli_subcmd": "check",
        "description": "Auditoría de inclusión de encabezados y dependencias directas (IWYU).",
    },
    "macro_security": {
        "fase": "estatico",
        "tool": "zhora",
        "cli_cmd": "zhora",
        "cli_subcmd": "check",
        "description": "Auditoría de seguridad y paréntesis en macros y directivas del preprocesador.",
    },
    "padding": {
        "fase": "estatico",
        "tool": "brett",
        "cli_cmd": "brett",
        "cli_subcmd": "audit",
        "description": "Análisis de alineación, tamaño de structs y bytes de padding desperdiciados.",
    },
    "tda_encapsulation": {
        "fase": "estatico",
        "tool": "motoko",
        "cli_cmd": "motoko",
        "cli_subcmd": "check",
        "description": "Verificación de opacidad y encapsulamiento de Tipos de Datos Abstractos (TDA).",
    },
    "portability": {
        "fase": "estatico",
        "tool": "crowe",
        "cli_cmd": "crowe",
        "cli_subcmd": "check",
        "description": "Detección de asunciones de arquitectura y portabilidad (ancho de tipos, endianness).",
    },
    "callgraph": {
        "fase": "estatico",
        "entrada": "archivo",
        "tool": "giger",
        "cli_cmd": "giger",
        "cli_subcmd": "check",
        "description": "Callgraph, Control Flow Graph (CFG), ciclos de recursión y funciones no invocadas.",
    },
    "formal_contracts": {
        "fase": "estatico",
        "entrada": "archivo",
        "tool": "callahan",
        "cli_cmd": "callahan",
        "cli_subcmd": "verify",
        "description": "Verificación formal de contratos y pre/postcondiciones ACSL con Frama-C.",
    },
    "fuzzing": {
        "fase": "dinamico",
        # `drake check` recibe UN archivo con `main` (lo compila y lo fuzza): se lo
        # invoca por archivo, y solo con los que son programas completos.
        "entrada": "archivo",
        "requiere_main": True,
        "tool": "drake",
        "cli_cmd": "drake",
        "cli_subcmd": "check",
        "description": "Fuzzing guiado por límites y pruebas de robustez contra payloads extremos.",
    },
    "sanitizer_translator": {
        "fase": "dinamico",
        "entrada": "archivo",
        "requiere_main": True,
        "tool": "tetsuo",
        "cli_cmd": "tetsuo",
        "cli_subcmd": "check",
        "description": "Compilación y ejecución bajo sanitizers (ASan/UBSan) con traducción de reportes.",
    },
    "mocks": {
        "fase": "dinamico",
        "tool": "holden",
        "cli_cmd": "holden",
        "cli_subcmd": "list",
        "description": "Generación de mocks en C e inyección de fallos de asignación y archivos.",
    },
    "fault_injection": {
        "fase": "dinamico",
        "tool": "vasquez",
        "cli_cmd": "vasquez",
        "cli_subcmd": "check",
        "description": "Inyección determinista de fallos de memoria, archivos y condiciones de carrera.",
    },
    "mutation_testing": {
        "fase": "dinamico",
        "tool": "vassili",
        "cli_cmd": "vassili",
        "cli_subcmd": "check",
        "description": "Análisis de mutación y cálculo de mutation score sobre suites de pruebas.",
    },
    "dataset_generator": {
        "fase": "dinamico",
        "tool": "tyrell",
        "cli_cmd": "tyrell",
        "cli_subcmd": "generate",
        "description": "Generador determinista de casos de prueba y datasets sintéticos (.in/.out).",
    },
    "hardware_profiler": {
        "fase": "dinamico",
        # Perfilar ejecuta el programa con N creciente bajo Cachegrind: puede tardar
        # y exige que el programa lea N por stdin. Solo corre si el manifiesto indica
        # cuál (`target`), en vez de perfilar a ciegas cada archivo.
        "requiere_config": ("target",),
        "argumento_config": "target",
        "tool": "ferro",
        "cli_cmd": "ferro",
        "cli_subcmd": "check",
        "description": "Perfilado de rendimiento, regresión asintótica O(n) y auditoría de throughput.",
    },
    "abi_audit": {
        "fase": "estatico",
        "tool": "parker",
        "cli_cmd": "parker",
        "cli_subcmd": "check",
        "description": "Auditoría de ABI, símbolos exportados y visibilidad en bibliotecas compartidas.",
    },
    "mcdc_coverage": {
        "fase": "estatico",
        "entrada": "archivo",
        "tool": "dietrich",
        "cli_cmd": "dietrich",
        "cli_subcmd": "check",
        "description": "Medición y reporte de cobertura de código estructural (MCDC, ramas, sentencias).",
    },
    "binary_io": {
        "fase": "estatico",
        # `kane check` recibe un binario (.bin/.dat), no fuentes C: sin binario
        # configurado no hay nada que inspeccionar.
        "requiere_config": ("binario",),
        "tool": "kane",
        "cli_cmd": "kane",
        "cli_subcmd": "check",
        "description": "Inspección y decodificación estructurada de archivos binarios y endianness.",
    },
    "documentation": {
        "fase": "estatico",
        "entrada": "archivo",
        "tool": "corbel",
        "cli_cmd": "corbel",
        "cli_subcmd": "check",
        "description": "Verificación y scaffolding de documentación técnica Doxygen y contratos C.",
    },
    "gcc_explainer": {
        "fase": "orquestado",
        # `esper catalog` solo lista el catálogo y no recibe rutas: lo que explica
        # los diagnósticos del código es `esper compile`, sin dejar un ejecutable.
        "entrada": "archivo",
        "tool": "esper",
        "cli_cmd": "esper",
        "cli_subcmd": "compile",
        "args_extra": ("-Wall", "-Wextra", "-o", "/dev/null"),
        "description": "Catálogo y explicación pedagógica de warnings y optimizaciones de GCC.",
    },
    "semantic_diff": {
        "fase": "estatico",
        # `weyl check` compara la entrega contra un modelo: sin la referencia
        # canónica no hay nada que comparar y no debe invocarse.
        "requiere_config": ("modelo",),
        "tool": "weyl",
        "cli_cmd": "weyl",
        "cli_subcmd": "check",
        "description": "Diffing semántico y comparación estructural AST entre entregas y modelos.",
    },
    "bishop": {
        "fase": "dinamico",
        "tool": "bishop",
        "cli_cmd": "bishop",
        "cli_subcmd": "audit",
        "description": "Visualización e inspección dinámica y estática de memoria en Stack y Heap.",
    },
    "rachel": {
        "fase": "estatico",
        "entrada": "archivo",
        "tool": "rachel",
        "cli_cmd": "rachel",
        "cli_subcmd": "check",
        "description": "Desensamblado e inspección de control de flujo bifurcado y Jump Tables.",
    },
    "sebastian": {
        "fase": "estatico",
        "entrada": "archivo",
        "tool": "sebastian",
        "cli_cmd": "sebastian",
        "cli_subcmd": "check",
        "description": "Auditoría de funciones recursivas, profundidad de pila y riesgos de stack overflow.",
    },
}
