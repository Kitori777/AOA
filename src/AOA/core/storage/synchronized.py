from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from .base import StorageEntry, StorageProvider


@dataclass(frozen=True)
class SyncVersion:
    local_version: str | None
    remote_version: str | None


@dataclass(frozen=True)
class SyncAction:
    key: str
    action: str
    status: str
    message: str = ""


@dataclass(frozen=True)
class SyncReport:
    actions: tuple[SyncAction, ...]

    @property
    def conflicts(self) -> tuple[SyncAction, ...]:
        return tuple(action for action in self.actions if action.status == "CONFLICT")

    @property
    def deferred(self) -> tuple[SyncAction, ...]:
        return tuple(action for action in self.actions if action.status == "DEFERRED")


class SynchronizedStorage:
    """Two-way optimistic synchronization with an offline outbox."""

    def __init__(
        self,
        local: StorageProvider,
        remote: StorageProvider,
        state_path: str | Path,
    ) -> None:
        self.local = local
        self.remote = remote
        self.state_path = Path(state_path).resolve()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.outbox_path = self.state_path.with_name(f"{self.state_path.stem}_outbox.json")

    def sync(self, prefix: str = "", *, online: bool = True) -> SyncReport:
        state = self._load_state()
        local = {entry.key: entry for entry in self.local.list(prefix)}
        if not online:
            offline_actions = self._offline_actions(local, state)
            self._write_outbox(offline_actions)
            return SyncReport(tuple(offline_actions))
        try:
            remote = {entry.key: entry for entry in self.remote.list(prefix)}
        except OSError as exc:
            offline_actions = self._offline_actions(local, state, str(exc))
            self._write_outbox(offline_actions)
            return SyncReport(tuple(offline_actions))

        actions: list[SyncAction] = []
        new_state = dict(state)
        for key in sorted(set(local) | set(remote) | set(state)):
            previous = state.get(key, SyncVersion(None, None))
            local_entry = local.get(key)
            remote_entry = remote.get(key)
            local_version = local_entry.version if local_entry else None
            remote_version = remote_entry.version if remote_entry else None
            local_changed = local_version != previous.local_version
            remote_changed = remote_version != previous.remote_version

            if key not in state and local_entry and remote_entry:
                local_data, _ = self.local.read_bytes(key)
                remote_data, _ = self.remote.read_bytes(key)
                if local_data != remote_data:
                    actions.append(
                        SyncAction(key, "none", "CONFLICT", "Rozne pliki bez wspolnej historii.")
                    )
                    continue
                actions.append(SyncAction(key, "none", "UNCHANGED"))
            elif local_changed and remote_changed:
                actions.append(
                    SyncAction(key, "none", "CONFLICT", "Plik zmieniono lokalnie i zdalnie.")
                )
                continue
            elif local_changed:
                if local_entry is None:
                    if remote_entry is not None:
                        self.remote.delete(key, expected_version=previous.remote_version)
                    actions.append(SyncAction(key, "delete_remote", "DONE"))
                    new_state.pop(key, None)
                    continue
                data, _ = self.local.read_bytes(key)
                saved = self.remote.write_bytes(
                    key, data, expected_version=previous.remote_version
                )
                remote_version = saved.version
                actions.append(SyncAction(key, "upload", "DONE"))
            elif remote_changed:
                if remote_entry is None:
                    if local_entry is not None:
                        self.local.delete(key, expected_version=previous.local_version)
                    actions.append(SyncAction(key, "delete_local", "DONE"))
                    new_state.pop(key, None)
                    continue
                data, _ = self.remote.read_bytes(key)
                saved = self.local.write_bytes(
                    key, data, expected_version=previous.local_version
                )
                local_version = saved.version
                actions.append(SyncAction(key, "download", "DONE"))
            else:
                actions.append(SyncAction(key, "none", "UNCHANGED"))
            new_state[key] = SyncVersion(local_version, remote_version)

        self._save_state(new_state)
        self._write_outbox([])
        return SyncReport(tuple(actions))

    def _offline_actions(
        self,
        local: Mapping[str, StorageEntry],
        state: dict[str, SyncVersion],
        message: str = "Tryb offline.",
    ) -> list[SyncAction]:
        actions: list[SyncAction] = []
        for key in sorted(set(local) | set(state)):
            entry = local.get(key)
            version = getattr(entry, "version", None)
            if version != state.get(key, SyncVersion(None, None)).local_version:
                action = "upload" if entry is not None else "delete_remote"
                actions.append(SyncAction(key, action, "DEFERRED", message))
        return actions

    def _load_state(self) -> dict[str, SyncVersion]:
        if not self.state_path.exists():
            return {}
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return {key: SyncVersion(**value) for key, value in payload.items()}

    def _save_state(self, state: dict[str, SyncVersion]) -> None:
        payload = {key: asdict(value) for key, value in sorted(state.items())}
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)

    def _write_outbox(self, actions: list[SyncAction]) -> None:
        temporary = self.outbox_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([asdict(action) for action in actions], indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.outbox_path)
