from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Protocol

from .base import StorageEntry


@dataclass(frozen=True)
class SharePointItem:
    key: str
    size_bytes: int
    modified_at: datetime
    version: str


class SharePointTransport(Protocol):
    """Network boundary implemented later by Microsoft Graph/SharePoint auth code."""

    def list_items(self, prefix: str = "") -> list[SharePointItem]: ...

    def download(self, key: str) -> tuple[bytes, SharePointItem]: ...

    def upload(
        self, key: str, data: bytes, *, expected_version: str | None = None
    ) -> SharePointItem: ...

    def delete_item(self, key: str, *, expected_version: str | None = None) -> None: ...


def _safe_key(key: str) -> str:
    normalized = str(PurePosixPath(key.replace("\\", "/"))).lstrip("/")
    if not normalized or normalized == "." or ".." in PurePosixPath(normalized).parts:
        raise ValueError("Nieprawidlowa sciezka SharePoint.")
    return normalized


class SharePointStorageProvider:
    """StorageProvider adapter without embedded credentials or mandatory network access."""

    def __init__(self, transport: SharePointTransport) -> None:
        self.transport = transport

    def list(self, prefix: str = "") -> list[StorageEntry]:
        safe_prefix = _safe_key(prefix) if prefix else ""
        return [
            StorageEntry(item.key, item.size_bytes, item.modified_at, item.version)
            for item in self.transport.list_items(safe_prefix)
        ]

    def read_bytes(self, key: str) -> tuple[bytes, StorageEntry]:
        data, item = self.transport.download(_safe_key(key))
        return data, StorageEntry(item.key, item.size_bytes, item.modified_at, item.version)

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        expected_version: str | None = None,
    ) -> StorageEntry:
        item = self.transport.upload(
            _safe_key(key), data, expected_version=expected_version
        )
        return StorageEntry(item.key, item.size_bytes, item.modified_at, item.version)

    def delete(self, key: str, *, expected_version: str | None = None) -> None:
        self.transport.delete_item(_safe_key(key), expected_version=expected_version)
