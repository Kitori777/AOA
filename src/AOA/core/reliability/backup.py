from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class BackupRecord:
    source: Path
    backup: Path
    created_at: str
    sha256: str


class BackupManager:
    def __init__(self, root: str | Path, *, retention_per_file: int = 10) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.retention_per_file = max(1, retention_per_file)

    def create(self, source: str | Path) -> BackupRecord:
        source_path = Path(source).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = self.root / f"{source_path.name}.{stamp}.{digest[:10]}.bak"
        temporary = backup.with_suffix(backup.suffix + ".tmp")
        shutil.copy2(source_path, temporary)
        temporary.replace(backup)
        self._prune(source_path.name)
        return BackupRecord(source_path, backup, datetime.now(UTC).isoformat(), digest)

    def list(self, source_name: str) -> tuple[Path, ...]:
        return tuple(sorted(self.root.glob(f"{source_name}.*.bak"), reverse=True))

    def restore(self, backup: str | Path, destination: str | Path) -> Path:
        backup_path = Path(backup).resolve()
        if backup_path.parent != self.root or not backup_path.is_file():
            raise ValueError("Kopia nie nalezy do tego magazynu kopii.")
        destination_path = Path(destination).resolve()
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination_path.with_name(f".{destination_path.name}.restore.tmp")
        shutil.copy2(backup_path, temporary)
        temporary.replace(destination_path)
        return destination_path

    def _prune(self, source_name: str) -> None:
        for path in self.list(source_name)[self.retention_per_file :]:
            path.unlink()
