"""Ripkg practice bundles: shared container format for teacher packing and student consumption.

Un ``.ripkg`` es un ZIP con:
    manifest.toml      metadatos, checks habilitados y flags de compilación
    manifest.sig       firma GPG desasociada (opcional)
    payload/<archivo>  testcases públicos y recursos visibles al estudiante

La integridad del payload se valida con SHA-256 registrado en el manifiesto;
la autenticidad de origen queda cubierta por la firma cuando existe.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import io
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import zipfile

MANIFEST_NAME = "manifest.toml"
SIGNATURE_NAME = "manifest.sig"
PAYLOAD_PREFIX = "payload/"
FORMAT_VERSION = 1


@dataclass
class RipkgBundle:
    manifest: Dict
    files: Dict[str, bytes] = field(default_factory=dict)

    @property
    def practica(self) -> str:
        return self.manifest.get("meta", {}).get("practica", "")

    @property
    def signed(self) -> bool:
        return SIGNATURE_NAME in self.files


class BundleError(Exception):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(
    practica_slug: str,
    enabled_check_ids: List[str],
    compiler_executable: str,
    compiler_flags: List[str],
    payload_files: Dict[str, bytes],
    makefile_cfg: Optional[Dict] = None,
) -> Dict:
    """Construye el diccionario de manifiesto con hashes de integridad."""
    manifest = {
        "meta": {
            "format_version": FORMAT_VERSION,
            "practica": practica_slug,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "checks": {cid: True for cid in sorted(enabled_check_ids)},
        "compiler": {
            "executable": compiler_executable,
            "flags": list(compiler_flags),
        },
        "integrity": {
            "unsigned": True,
            "sha256": {name: _sha256(payload_files[name]) for name in sorted(payload_files)},
        },
    }
    if makefile_cfg:
        manifest["makefile"] = dict(makefile_cfg)
    return manifest


def serialize_manifest(manifest: Dict) -> bytes:
    """Serializa a TOML mínimo (strings, ints, bools, listas, tablas).

    Todas las claves se emiten entrecomilladas para preservar puntos y
    barras de los check-ids y nombres de archivo.
    """

    def fmt(v) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list):
            inner = ", ".join(fmt(x) for x in v)
            return f"[{inner}]"
        if isinstance(v, dict):
            inline = ", ".join(f'{_q(k)} = {fmt(x)}' for k, x in sorted(v.items()))
            return "{ " + inline + " }"
        s = str(v).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'

    def _q(k: str) -> str:
        return '"' + str(k).replace("\\", "\\\\").replace('"', '\\"') + '"'

    out: List[str] = []

    def emit(table: Dict, prefix_parts: List[str]) -> None:
        for key, value in table.items():
            parts = [*prefix_parts, str(key)]
            if isinstance(value, dict):
                emit(value, parts)
            else:
                dotted = ".".join(_q(p) for p in parts)
                out.append(f"{dotted} = {fmt(value)}")

    emit(manifest, [])
    out.append("")
    return "\n".join(out).encode("utf-8")


def parse_manifest(data: bytes) -> Dict:
    return tomllib.loads(data.decode("utf-8"))


def write_bundle(
    output_path: Path,
    manifest: Dict,
    payload_files: Dict[str, bytes],
    sign_key: Optional[str] = None,
) -> Path:
    """Escribe el .ripkg; si se indica clave GPG disponible, firma el manifiesto."""
    manifest_bytes = serialize_manifest(manifest)
    signature_bytes: Optional[bytes] = None

    if sign_key:
        gpg = shutil.which("gpg")
        if not gpg:
            raise BundleError("gpg no está disponible para firmar el paquete.")
        with tempfile.TemporaryDirectory() as td:
            m_path = Path(td) / MANIFEST_NAME
            s_path = Path(td) / SIGNATURE_NAME
            m_path.write_bytes(manifest_bytes)
            proc = subprocess.run(
                [gpg, "--batch", "--yes", "--detach-sign", "--local-user", sign_key,
                 "--output", str(s_path), str(m_path)],
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                raise BundleError(f"Firma GPG fallida: {proc.stderr.decode(errors='replace')[:200]}")
            signature_bytes = s_path.read_bytes()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, manifest_bytes)
        if signature_bytes is not None:
            zf.writestr(SIGNATURE_NAME, signature_bytes)
        for name, data in payload_files.items():
            safe = f"{PAYLOAD_PREFIX}{name}"
            if safe.startswith("/") or ".." in Path(safe).parts:
                raise BundleError(f"Nombre de archivo inseguro en payload: {name}")
            zf.writestr(safe, data)
    return out


def load_bundle(path: Path | str, verify_signature: bool = False) -> RipkgBundle:
    """Lee y valida un .ripkg: rutas seguras, hashes SHA-256 y firma opcional."""
    bundle_file = Path(path)
    if not bundle_file.exists():
        raise BundleError(f"Paquete no encontrado: {bundle_file}")

    try:
        with zipfile.ZipFile(bundle_file) as zf:
            names = zf.namelist()
            for n in names:
                if n.startswith("/") or ".." in Path(n).parts:
                    raise BundleError(f"Entrada insegura dentro del paquete: {n}")
            if MANIFEST_NAME not in names:
                raise BundleError("El paquete no contiene manifest.toml.")
            manifest_bytes = zf.read(MANIFEST_NAME)
            manifest = parse_manifest(manifest_bytes)
            files: Dict[str, bytes] = {}
            for n in names:
                if n == MANIFEST_NAME:
                    continue
                files[n] = zf.read(n)
    except zipfile.BadZipFile as e:
        raise BundleError(f"ZIP inválido: {e}") from e

    expected = manifest.get("integrity", {}).get("sha256", {})
    # Los hashes se registran con nombres sin prefijo payload/.
    stripped = {
        name[len(PAYLOAD_PREFIX):]: data
        for name, data in files.items()
        if name.startswith(PAYLOAD_PREFIX)
    }
    mismatches = [
        name for name, digest in expected.items()
        if name not in stripped or _sha256(stripped[name]) != digest
    ]
    if mismatches:
        raise BundleError(f"Integridad comprometida en: {', '.join(mismatches)}")

    bundle = RipkgBundle(manifest=manifest, files=files)

    if verify_signature:
        if not bundle.signed:
            raise BundleError("El paquete no está firmado y se exigió verificación.")
        gpg = shutil.which("gpg")
        if not gpg:
            raise BundleError("gpg no está disponible para verificar la firma.")
        with tempfile.TemporaryDirectory() as td:
            m_path = Path(td) / MANIFEST_NAME
            s_path = Path(td) / SIGNATURE_NAME
            m_path.write_bytes(manifest_bytes)
            s_path.write_bytes(files[SIGNATURE_NAME])
            proc = subprocess.run(
                [gpg, "--verify", str(s_path), str(m_path)],
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                raise BundleError("Firma GPG inválida: el paquete no proviene del origen declarado.")

    return bundle


def payload_of(bundle: RipkgBundle) -> Dict[str, bytes]:
    """Archivos de payload sin prefijo, ignorando la firma."""
    result: Dict[str, bytes] = {}
    for name, data in bundle.files.items():
        if name == SIGNATURE_NAME:
            continue
        if name.startswith(PAYLOAD_PREFIX):
            result[name[len(PAYLOAD_PREFIX):]] = data
    return result
