"""Hermetic toolchain snapshots for 100% reproducible evaluations over time."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional


@dataclass
class ToolchainSnapshot:
    created_at: str
    machine: str
    kernel: str
    compiler_path: str
    compiler_version: str
    compiler_target: str
    libc_version: str
    flags_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class SnapshotComparison:
    reproducible: bool
    differences: List[str] = field(default_factory=list)
    message: str = ""


def _run(cmd: List[str], timeout: int = 15) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return (proc.stdout or proc.stderr).strip()


def capture_snapshot(
    compiler_executable: str = "gcc",
    compile_flags: Optional[List[str]] = None,
) -> ToolchainSnapshot:
    """Captura el estado completo del toolchain activo: versiones, target,
    biblioteca C y hash de los flags de compilación."""
    compiler_bin = shutil.which(compiler_executable) or compiler_executable

    try:
        version = _run([compiler_bin, "--version"]).splitlines()[0]
    except Exception:
        version = "desconocida"
    try:
        target = _run([compiler_bin, "-dumpmachine"])
    except Exception:
        target = "desconocido"

    libc = "desconocida"
    ldd = shutil.which("ldd")
    if ldd:
        try:
            libc = _run([ldd, "--version"]).splitlines()[0]
        except Exception:
            pass
    else:
        getconf = shutil.which("getconf")
        if getconf:
            try:
                libc = _run([getconf, "GNU_LIBC_VERSION"])
            except Exception:
                pass

    flags_hash = None
    if compile_flags:
        normalized = " ".join(sorted(compile_flags))
        flags_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    return ToolchainSnapshot(
        created_at=datetime.now().isoformat(timespec="seconds"),
        machine=platform.machine(),
        kernel=platform.release(),
        compiler_path=compiler_bin,
        compiler_version=version,
        compiler_target=target,
        libc_version=libc,
        flags_hash=flags_hash,
    )


def save_snapshot(snapshot: ToolchainSnapshot, output_path: Path | str) -> Path:
    """Persiste la instantánea como JSON para verificación futura."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def load_snapshot(path: Path | str) -> Optional[ToolchainSnapshot]:
    snap_file = Path(path)
    if not snap_file.exists():
        return None
    data = json.loads(snap_file.read_text(encoding="utf-8"))
    return ToolchainSnapshot(**data)


def compare_snapshots(baseline: ToolchainSnapshot, current: ToolchainSnapshot) -> SnapshotComparison:
    """Compara dos instantáneas campo por campo ignorando la marca temporal."""
    ignored_fields = {"created_at"}
    differences: List[str] = []
    for key, baseline_value in baseline.to_dict().items():
        if key in ignored_fields:
            continue
        current_value = getattr(current, key)
        if baseline_value != current_value:
            differences.append(f"{key}: '{baseline_value}' → '{current_value}'")

    reproducible = not differences
    message = (
        "Toolchain idéntico al de referencia: evaluaciones reproducibles."
        if reproducible
        else f"Toolchain divergió en {len(differences)} campos: las evaluaciones pueden no ser comparables."
    )
    return SnapshotComparison(reproducible=reproducible, differences=differences, message=message)
