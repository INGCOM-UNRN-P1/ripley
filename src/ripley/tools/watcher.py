"""Live TDD watch session: poll-based change detection for student sources."""

from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Callable, Iterator, List, Optional, Set


def collect_source_files(paths: List[Path], pattern: str = "*.c") -> List[Path]:
    """Expande archivos y directorios a la lista plana de fuentes vigiladas."""
    files: List[Path] = []
    seen: Set[str] = set()
    for p in paths:
        if p.is_dir():
            candidates = sorted(p.rglob(pattern))
        elif p.suffix == ".c" and p.exists():
            candidates = [p]
        else:
            continue
        for c in candidates:
            key = str(c.resolve())
            if key not in seen:
                seen.add(key)
                files.append(c)
    return files


def snapshot_mtimes(files: List[Path]) -> dict:
    state = {}
    for f in files:
        try:
            state[str(f)] = f.stat().st_mtime_ns
        except OSError:
            continue  # archivo eliminado: ausente del snapshot → ChangeSet.deleted
    return state


@dataclass
class ChangeSet:
    changed: List[Path] = field(default_factory=list)
    deleted: List[Path] = field(default_factory=list)

    @property
    def any(self) -> bool:
        return bool(self.changed or self.deleted)


class WatchSession:
    """Sesión de vigilancia por polling: sin dependencias externas.

    Uso:
        session = WatchSession(["src/"])
        for changes in session.iter_changes():
            ... recompilar y verificar ...
    """

    def __init__(self, paths: List[Path], interval_sec: float = 1.0, pattern: str = "*.c") -> None:
        if interval_sec <= 0:
            raise ValueError("interval_sec debe ser > 0")
        self.paths = [Path(p) for p in paths]
        self.interval_sec = interval_sec
        self.pattern = pattern
        self.files = collect_source_files(self.paths, pattern)
        self._state = snapshot_mtimes(self.files)

    def refresh_file_list(self) -> None:
        """Re-escanea archivos nuevos sin resetear los mtimes ya conocidos."""
        self.files = collect_source_files(self.paths, self.pattern)
        current = snapshot_mtimes(self.files)
        for key, mtime in current.items():
            self._state.setdefault(key, mtime)

    def iter_changes(self, on_tick: Optional[Callable[[int], None]] = None) -> Iterator[ChangeSet]:
        """Generador infinito: rinde un ChangeSet solo cuando algo cambió."""
        tick = 0
        while True:
            time.sleep(self.interval_sec)
            tick += 1
            self.refresh_file_list()
            current = snapshot_mtimes(self.files)

            changed: List[Path] = []
            deleted: List[Path] = []
            for path_str, old_mtime in self._state.items():
                new_mtime = current.get(path_str, -1)
                if path_str not in current:
                    deleted.append(Path(path_str))
                elif new_mtime != old_mtime:
                    changed.append(Path(path_str))

            if changed or deleted:
                yield ChangeSet(changed=changed, deleted=deleted)

            self._state = current
            if on_tick is not None:
                on_tick(tick)
