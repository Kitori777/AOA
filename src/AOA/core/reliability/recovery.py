from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class RecoveryRecord:
    transaction_id: str
    target: str
    backup: str
    action: str
    created_at: str
    committed: bool = False


class RecoveryJournal:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def begin(self, *, target: str | Path, backup: str | Path, action: str) -> RecoveryRecord:
        record = RecoveryRecord(
            uuid.uuid4().hex,
            str(Path(target).resolve()),
            str(Path(backup).resolve()),
            action,
            datetime.now(UTC).isoformat(),
        )
        self._write(record)
        return record

    def commit(self, transaction_id: str) -> RecoveryRecord:
        record = self.read(transaction_id)
        committed = RecoveryRecord(**{**asdict(record), "committed": True})
        self._write(committed)
        return committed

    def pending(self) -> tuple[RecoveryRecord, ...]:
        records = [self.read(path.stem) for path in self.root.glob("*.json")]
        return tuple(record for record in records if not record.committed)

    def read(self, transaction_id: str) -> RecoveryRecord:
        if not transaction_id.isalnum():
            raise ValueError("Nieprawidlowy transaction_id.")
        path = self.root / f"{transaction_id}.json"
        return RecoveryRecord(**json.loads(path.read_text(encoding="utf-8")))

    def _write(self, record: RecoveryRecord) -> None:
        path = self.root / f"{record.transaction_id}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        temporary.replace(path)
