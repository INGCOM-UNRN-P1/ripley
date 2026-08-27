"""External tool availability matrix powering doctor reports and check skipping."""

from dataclasses import dataclass
import shutil
from typing import Dict, List

# Ejecutable -> descripción funcional (qué checks se degradan sin él)
TOOL_CATALOG: Dict[str, str] = {
    "gcc": "Compilación, sanitizadores, stack-usage, fuzzing con cobertura",
    "valgrind": "Auditoría de memoria, conteo de instrucciones (Callgrind)",
    "cppcheck": "Análisis estático externo",
    "gcov": "Cobertura para fuzzing guiado",
    "frama-c": "Demostración WP de contratos ACSL",
    "bwrap": "Sandbox por namespaces (bubblewrap)",
    "unshare": "Sandbox user-ns alternativo",
    "qemu-aarch64": "Ejecución cruzada ARM64",
    "qemu-riscv64": "Ejecución cruzada RISC-V",
    "gpg": "Firma/verificación criptográfica de paquetes .ripkg",
    # Subherramientas desacopladas del ecosistema
    "daedalus": "Compilador pedagógico y traductor de diagnósticos GCC/Clang",
    "nostromo": "Sandbox de ejecución aislada y runner de testcases .in/.out",
    "gaff": "Linter pedagógico de convenciones de cátedra con autofix",
    "hal": "Asistente forense de core dumps y segfaults post-mortem",
    "brett": "Auditor de padding y alineación de structs",
    "kaneda": "Auditor de seguridad y llamadas a sistema prohibidas",
    "spunkmeyer": "Detector de antipatrones didácticos en C",
    "holden": "Generador de mocks e inyección de fallos",
    "callahan": "Verificador formal de contratos ACSL",
    "drake": "Fuzzer pedagógico guiado por límites",
    "giger": "Generador de callgraphs y grafos de flujo",
    "weyl": "Diffing semántico y comparación estructural",
    "bishop": "Visualizador pedagógico de memoria Stack & Heap",
    "sebastian": "Analizador de recursión y stack frame",
    "rachel": "Desensamblador y visualizador de jump tables",
}


@dataclass
class ToolStatus:
    name: str
    available: bool
    path: str = ""
    description: str = ""


def probe_all() -> List[ToolStatus]:
    statuses = []
    for name, description in TOOL_CATALOG.items():
        path = shutil.which(name) or ""
        statuses.append(ToolStatus(name=name, available=bool(path), path=path, description=description))
    return statuses


def available_map() -> Dict[str, bool]:
    return {name: bool(shutil.which(name)) for name in TOOL_CATALOG}
