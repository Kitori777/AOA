from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from .base import StorageConflictError, StorageEntry


class LocalStorageProvider:
    """Traversal-safe, atomic storage rooted in one local directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        normalized = str(PurePosixPath(key.replace("\\", "/"))).lstrip("/")
        if not normalized or normalized == "." or ".." in PurePosixPath(normalized).parts:
            raise ValueError("Nieprawidlowa sciezka magazynu danych.")
        resolved = (self.root / Path(normalized)).resolve()
        if self.root != resolved and self.root not in resolved.parents:
            raise ValueError("Sciezka wychodzi poza magazyn danych.")
        return resolved

    @staticmethod
    def _version(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _entry(self, path: Path) -> StorageEntry:
        stat = path.stat()
        return StorageEntry(
            key=path.relative_to(self.root).as_posix(),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            version=self._version(path),
        )

    def list(self, prefix: str = "") -> list[StorageEntry]:
        base = self.root if not prefix else self._resolve(prefix)
        if not base.exists():
            return []
        candidates = [base] if base.is_file() else base.rglob("*")
        entries = [self._entry(path) for path in candidates if path.is_file()]
        return sorted(entries, key=lambda item: item.key.casefold())

    def read_bytes(self, key: str) -> tuple[bytes, StorageEntry]:
        path = self._resolve(key)
        data = path.read_bytes()
        return data, self._entry(path)

    def _check_version(self, path: Path, expected_version: str | None) -> None:
        if expected_version is None:
            return
        if not path.exists() or self._version(path) != expected_version:
            raise StorageConflictError(
                "Plik zostal zmieniony od ostatniego odczytu. Odswiez dane i sprobuj ponownie."
            )

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        expected_version: str | None = None,
    ) -> StorageEntry:
        path = self._resolve(key)
        self._check_version(path, expected_version)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return self._entry(path)

    def delete(self, key: str, *, expected_version: str | None = None) -> None:
        path = self._resolve(key)
        self._check_version(path, expected_version)
        path.unlink()
