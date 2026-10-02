from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from AOA.core.storage import (
    LocalStorageProvider,
    SharePointItem,
    SharePointStorageProvider,
    SynchronizedStorage,
    create_storage_provider,
)


class FakeSharePointTransport:
    def __init__(self) -> None:
        self.items: dict[str, tuple[bytes, int]] = {}
        self.list_calls = 0

    def _item(self, key: str) -> SharePointItem:
        data, version = self.items[key]
        return SharePointItem(key, len(data), datetime.now(UTC), str(version))

    def list_items(self, prefix: str = "") -> list[SharePointItem]:
        self.list_calls += 1
        return [self._item(key) for key in sorted(self.items) if key.startswith(prefix)]

    def download(self, key: str):
        data, _version = self.items[key]
        return data, self._item(key)

    def upload(self, key: str, data: bytes, *, expected_version: str | None = None):
        current = self.items.get(key)
        if expected_version is not None and (
            current is None or str(current[1]) != expected_version
        ):
            raise RuntimeError("remote conflict")
        version = (current[1] + 1) if current else 1
        self.items[key] = (data, version)
        return self._item(key)

    def delete_item(self, key: str, *, expected_version: str | None = None) -> None:
        current = self.items[key]
        if expected_version is not None and str(current[1]) != expected_version:
            raise RuntimeError("remote conflict")
        del self.items[key]


def test_sharepoint_provider_delegates_versioned_operations() -> None:
    transport = FakeSharePointTransport()
    provider = SharePointStorageProvider(transport)

    first = provider.write_bytes("queues/schedule.csv", b"one")
    data, read = provider.read_bytes("queues/schedule.csv")
    second = provider.write_bytes(
        "queues/schedule.csv", b"two", expected_version=first.version
    )

    assert data == b"one"
    assert read.version == "1"
    assert second.version == "2"
    assert provider.list("queues")[0].key == "queues/schedule.csv"


def test_storage_factory_keeps_sharepoint_optional(tmp_path) -> None:
    local = create_storage_provider("local", local_root=tmp_path)
    transport = FakeSharePointTransport()
    remote = create_storage_provider(
        "sharepoint", local_root=tmp_path, sharepoint_transport=transport
    )

    assert isinstance(local, LocalStorageProvider)
    assert isinstance(remote, SharePointStorageProvider)


def test_first_sync_uploads_local_file_and_next_sync_downloads_remote_change(tmp_path) -> None:
    local = LocalStorageProvider(tmp_path / "local")
    remote = LocalStorageProvider(tmp_path / "remote")
    local.write_bytes("schedule.csv", b"local")
    sync = SynchronizedStorage(local, remote, tmp_path / "state" / "sync.json")

    first = sync.sync()
    remote_data, remote_entry = remote.read_bytes("schedule.csv")
    remote.write_bytes("schedule.csv", b"remote-new", expected_version=remote_entry.version)
    second = sync.sync()

    assert remote_data == b"local"
    assert first.actions[0].action == "upload"
    assert second.actions[0].action == "download"
    assert local.read_bytes("schedule.csv")[0] == b"remote-new"


def test_sync_reports_conflict_without_overwriting_either_side(tmp_path) -> None:
    local = LocalStorageProvider(tmp_path / "local")
    remote = LocalStorageProvider(tmp_path / "remote")
    local.write_bytes("schedule.csv", b"base")
    sync = SynchronizedStorage(local, remote, tmp_path / "state" / "sync.json")
    sync.sync()
    local_entry = local.read_bytes("schedule.csv")[1]
    remote_entry = remote.read_bytes("schedule.csv")[1]
    local.write_bytes("schedule.csv", b"local-change", expected_version=local_entry.version)
    remote.write_bytes("schedule.csv", b"remote-change", expected_version=remote_entry.version)

    report = sync.sync()

    assert len(report.conflicts) == 1
    assert local.read_bytes("schedule.csv")[0] == b"local-change"
    assert remote.read_bytes("schedule.csv")[0] == b"remote-change"


def test_offline_sync_never_touches_remote_and_records_outbox(tmp_path) -> None:
    local = LocalStorageProvider(tmp_path / "local")
    transport = FakeSharePointTransport()
    remote = SharePointStorageProvider(transport)
    local.write_bytes("schedule.csv", b"offline-change")
    state_path = tmp_path / "state" / "sync.json"
    sync = SynchronizedStorage(local, remote, state_path)

    report = sync.sync(online=False)

    assert transport.list_calls == 0
    assert len(report.deferred) == 1
    assert state_path.with_name("sync_outbox.json").is_file()
    assert hashlib.sha256(local.read_bytes("schedule.csv")[0]).hexdigest()
