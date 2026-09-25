"""External tool availability matrix powering doctor reports and check skipping."""

from dataclasses import dataclass
import shutil
from typing import Dict, List

from ripley.core.entrypoints_catalogo import SATELLITE_CATALOG

# Binarios del sistema -> qué checks se degradan sin ellos.
_BINARIOS_DEL_SISTEMA: Dict[str, str] = {
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
}

# Herramientas del ecosistema que no son satélites de ripley, pero cuya
# presencia informa `doctor`.
_HERRAMIENTAS_EXTRA: Dict[str, str] = {
    "hal": "Forense de core dumps y análisis pedagógico post-mortem de segfaults",
}


def _descripciones_satelites() -> Dict[str, str]:
    """Comando -> descripción, tomadas de SATELLITE_CATALOG (fuente única).

    Antes este módulo mantenía su propia copia de las descripciones, que había
    derivado: `ripley doctor` describía mal a diez satélites (N-RIPLEY-01).
    """
    descripciones: Dict[str, str] = {}
    for entrada in SATELLITE_CATALOG.values():
        descripciones.setdefault(entrada["cli_cmd"], entrada["description"])
    return descripciones


# Ejecutable -> descripción funcional (qué checks se degradan sin él)
TOOL_CATALOG: Dict[str, str] = {
    **_BINARIOS_DEL_SISTEMA,
    **_descripciones_satelites(),
    **_HERRAMIENTAS_EXTRA,
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
