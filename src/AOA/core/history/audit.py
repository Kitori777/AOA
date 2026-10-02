from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from AOA.core.storage.local import LocalStorageProvider


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    occurred_at: str
    actor: str
    action: str
    entity_id: str
    details: dict[str, Any]
    previous_hash: str
    event_hash: str


def _event_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditLog:
    """Append-only JSONL audit log with a verifiable hash chain."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.provider = LocalStorageProvider(self.path.parent)
        self._lock = threading.Lock()

    def read(self) -> tuple[AuditEvent, ...]:
        try:
            data, _entry = self.provider.read_bytes(self.path.name)
        except FileNotFoundError:
            return ()
        events: list[AuditEvent] = []
        for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                events.append(AuditEvent(**json.loads(line)))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Uszkodzony dziennik audytu, wiersz {line_number}.") from exc
        return tuple(events)

    def append(
        self,
        action: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
        *,
        actor: str = "local-user",
    ) -> AuditEvent:
        with self._lock:
            try:
                current, entry = self.provider.read_bytes(self.path.name)
                expected_version = entry.version
                existing = self.read()
            except FileNotFoundError:
                current = b""
                expected_version = None
                existing = ()
            previous_hash = existing[-1].event_hash if existing else ""
            occurred_at = datetime.now(UTC).isoformat()
            event_details = details or {}
            seed: dict[str, Any] = {
                "occurred_at": occurred_at,
                "actor": actor,
                "action": action,
                "entity_id": entity_id,
                "details": event_details,
                "previous_hash": previous_hash,
            }
            digest = _event_hash(seed)
            event = AuditEvent(
                event_id=digest[:16],
                occurred_at=occurred_at,
                actor=actor,
                action=action,
                entity_id=entity_id,
                details=event_details,
                previous_hash=previous_hash,
                event_hash=digest,
            )
            line = json.dumps(asdict(event), ensure_ascii=False, sort_keys=True) + "\n"
            self.provider.write_bytes(
                self.path.name,
                current + line.encode("utf-8"),
                expected_version=expected_version,
            )
            return event

    def verify(self) -> tuple[bool, str]:
        previous_hash = ""
        for index, event in enumerate(self.read(), start=1):
            seed = {
                "occurred_at": event.occurred_at,
                "actor": event.actor,
                "action": event.action,
                "entity_id": event.entity_id,
                "details": event.details,
                "previous_hash": event.previous_hash,
            }
            if event.previous_hash != previous_hash:
                return False, f"Przerwany lancuch audytu przy zdarzeniu {index}."
            if _event_hash(seed) != event.event_hash:
                return False, f"Nieprawidlowy hash zdarzenia {index}."
            previous_hash = event.event_hash
        return True, f"Dziennik poprawny: {len(self.read())} zdarzen."
