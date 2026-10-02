from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class StorageConflictError(RuntimeError):
    """Raised when a remote or local item changed since it was read."""


@dataclass(frozen=True)
class StorageEntry:
    key: str
    size_bytes: int
    modified_at: datetime
    version: str


class StorageProvider(Protocol):
    """Storage boundary shared by local files and a future SharePoint adapter."""

    def list(self, prefix: str = "") -> list[StorageEntry]: ...

    def read_bytes(self, key: str) -> tuple[bytes, StorageEntry]: ...

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        expected_version: str | None = None,
    ) -> StorageEntry: ...

    def delete(self, key: str, *, expected_version: str | None = None) -> None: ...
