from __future__ import annotations

import pytest

from AOA.core.storage import LocalStorageProvider, StorageConflictError


def test_local_storage_round_trip_listing_and_atomic_update(tmp_path) -> None:
    storage = LocalStorageProvider(tmp_path)

    created = storage.write_bytes("reports/result.txt", b"first")
    data, loaded = storage.read_bytes("reports/result.txt")
    updated = storage.write_bytes(
        "reports/result.txt",
        b"second",
        expected_version=loaded.version,
    )

    assert data == b"first"
    assert created.version == loaded.version
    assert updated.version != loaded.version
    assert [entry.key for entry in storage.list("reports")] == ["reports/result.txt"]


def test_local_storage_detects_conflict_and_blocks_traversal(tmp_path) -> None:
    storage = LocalStorageProvider(tmp_path)
    entry = storage.write_bytes("model.bin", b"v1")
    storage.write_bytes("model.bin", b"v2")

    with pytest.raises(StorageConflictError):
        storage.write_bytes("model.bin", b"stale", expected_version=entry.version)
    with pytest.raises(ValueError):
        storage.write_bytes("../outside.txt", b"blocked")


def test_local_storage_delete_can_require_current_version(tmp_path) -> None:
    storage = LocalStorageProvider(tmp_path)
    entry = storage.write_bytes("data.csv", b"a\n1\n")

    storage.delete("data.csv", expected_version=entry.version)

    assert storage.list() == []
