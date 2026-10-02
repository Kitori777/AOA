from __future__ import annotations

from pathlib import Path

from .base import StorageProvider
from .local import LocalStorageProvider
from .sharepoint import SharePointStorageProvider, SharePointTransport


def create_storage_provider(
    provider_name: str,
    *,
    local_root: str | Path,
    sharepoint_transport: SharePointTransport | None = None,
) -> StorageProvider:
    normalized = provider_name.strip().lower()
    if normalized == "local":
        return LocalStorageProvider(local_root)
    if normalized == "sharepoint":
        if sharepoint_transport is None:
            raise ValueError("SharePoint wymaga skonfigurowanego transportu i logowania.")
        return SharePointStorageProvider(sharepoint_transport)
    raise ValueError(f"Nieznany storage_provider: {provider_name}")
