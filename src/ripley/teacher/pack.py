"""Teacher-side .ripkg packing: derives the student manifest from practice config."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ripley.config import load_config
from ripley.pipeline import bundle
import ripley.pipeline.checks  # noqa: F401  (pobla el registro del catálogo)
from ripley.pipeline.registry import all_checks


@dataclass
class PackResult:
    output_path: Path
    checks_enabled: int
    payload_files: int
    signed: bool


def _enabled_check_ids(cfg) -> List[str]:
    enabled: List[str] = []
    for spec in all_checks():
        if spec.scope == "teacher" or not spec.config_section:
            continue  # On-demand y exclusivos docentes no viajan en el manifiesto.
        section = getattr(cfg, spec.config_section, None)
        if section is None:
            continue
        if spec.toggle:
            if not getattr(section, spec.toggle, False):
                continue
        elif not getattr(section, "enabled", True):
            continue
        # Master gate del bloque AST.
        if spec.config_section == "ast_auditors" and not cfg.ast_auditors.enabled:
            continue
        enabled.append(spec.check_id)
    return enabled


def pack_practice(
    practice_dir: Path | str,
    config_path: Optional[Path] = None,
    sign_key: Optional[str] = None,
) -> PackResult:
    """Empaqueta una práctica (ripley.toml + testcases públicos) como .ripkg."""
    pdir = Path(practice_dir)
    if not pdir.exists():
        raise FileNotFoundError(f"Directorio de práctica inexistente: {pdir}")

    toml_path = Path(config_path) if config_path else pdir / "ripley.toml"
    if not toml_path.exists():
        raise FileNotFoundError(f"No se encontró {toml_path}: la práctica debe estar configurada.")
    cfg = load_config(toml_path)

    payload: Dict[str, bytes] = {}
    tc_root = pdir / "testcases"
    if tc_root.exists():
        for f in sorted(tc_root.rglob("*")):
            if f.is_file():
                payload[str(f.relative_to(tc_root))] = f.read_bytes()

    manifest = bundle.build_manifest(
        practica_slug=pdir.name,
        enabled_check_ids=_enabled_check_ids(cfg),
        compiler_executable=cfg.compiler.executable,
        compiler_flags=list(cfg.compiler.flags),
        payload_files=payload,
        makefile_cfg={
            "target": cfg.makefile.target,
            "expected_binary": cfg.makefile.expected_binary,
        } if cfg.makefile.enabled else None,
    )
    if sign_key:
        manifest.setdefault("integrity", {})["unsigned"] = False

    out_path = pdir.parent / f"{pdir.name}.ripkg"
    bundle.write_bundle(out_path, manifest, payload, sign_key=sign_key)

    return PackResult(
        output_path=out_path,
        checks_enabled=len(manifest.get("checks", {})),
        payload_files=len(payload),
        signed=bool(sign_key),
    )
