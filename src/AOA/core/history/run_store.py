from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    created_at: str
    input_hash: str
    source_path: str
    objective: str
    selected_methods: tuple[str, ...]
    best_method: str
    directory: Path


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


class RunStore:
    """Immutable, reproducible planning runs stored as self-contained directories."""

    SCHEMA_VERSION = 1

    def __init__(self, root: str | Path, *, retention: int = 50) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.retention = max(1, retention)

    def record(
        self,
        *,
        input_frame: pd.DataFrame,
        settings: dict[str, Any],
        ranking: pd.DataFrame,
        schedule: pd.DataFrame,
        source_path: str | Path = "",
        events: list[dict[str, Any]] | None = None,
    ) -> RunRecord:
        input_data = _csv_bytes(input_frame)
        input_hash = hashlib.sha256(input_data).hexdigest()
        now = datetime.now(UTC)
        run_id = f"{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
        temporary = self.root / f".{run_id}.tmp"
        destination = self.root / run_id
        temporary.mkdir(parents=False, exist_ok=False)
        objective = str(settings.get("objective", ""))
        methods = tuple(str(item) for item in settings.get("selected_methods", []))
        best_method = str(ranking.iloc[0].get("method", "")) if not ranking.empty else ""
        manifest = {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": run_id,
            "created_at": now.isoformat(),
            "input_hash": input_hash,
            "source_path": str(source_path),
            "objective": objective,
            "selected_methods": list(methods),
            "best_method": best_method,
            "files": {
                "input": "input.csv",
                "settings": "settings.json",
                "ranking": "ranking.csv",
                "schedule": "schedule.csv",
                "events": "events.jsonl",
            },
        }
        try:
            (temporary / "input.csv").write_bytes(input_data)
            (temporary / "settings.json").write_text(
                json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            (temporary / "ranking.csv").write_bytes(_csv_bytes(ranking))
            (temporary / "schedule.csv").write_bytes(_csv_bytes(schedule))
            event_text = "".join(
                json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
                for event in (events or [])
            )
            (temporary / "events.jsonl").write_text(event_text, encoding="utf-8")
            (temporary / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temporary.replace(destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        self._prune()
        return RunRecord(
            run_id,
            str(manifest["created_at"]),
            input_hash,
            str(source_path),
            objective,
            methods,
            best_method,
            destination,
        )

    def list(self) -> tuple[RunRecord, ...]:
        records: list[RunRecord] = []
        for directory in sorted(self.root.iterdir(), reverse=True):
            manifest_path = directory / "manifest.json"
            if not directory.is_dir() or not manifest_path.is_file():
                continue
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if int(payload.get("schema_version", 0)) > self.SCHEMA_VERSION:
                continue
            records.append(
                RunRecord(
                    str(payload["run_id"]),
                    str(payload["created_at"]),
                    str(payload["input_hash"]),
                    str(payload.get("source_path", "")),
                    str(payload.get("objective", "")),
                    tuple(payload.get("selected_methods", [])),
                    str(payload.get("best_method", "")),
                    directory,
                )
            )
        return tuple(records)

    def load(self, run_id: str) -> dict[str, Any]:
        if not run_id or any(character not in "0123456789TZ-abcdef" for character in run_id):
            raise ValueError("Nieprawidlowy identyfikator przebiegu.")
        directory = (self.root / run_id).resolve()
        if directory.parent != self.root or not directory.is_dir():
            raise FileNotFoundError(run_id)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        input_data = (directory / "input.csv").read_bytes()
        if hashlib.sha256(input_data).hexdigest() != manifest["input_hash"]:
            raise ValueError("Plik wejsciowy przebiegu nie zgadza sie z manifestem.")
        return {
            "manifest": manifest,
            "input": pd.read_csv(directory / "input.csv", encoding="utf-8-sig"),
            "settings": json.loads((directory / "settings.json").read_text(encoding="utf-8")),
            "ranking": pd.read_csv(directory / "ranking.csv", encoding="utf-8-sig"),
            "schedule": pd.read_csv(directory / "schedule.csv", encoding="utf-8-sig"),
            "events": [
                json.loads(line)
                for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ],
        }

    def _prune(self) -> None:
        records = self.list()
        for record in records[self.retention :]:
            shutil.rmtree(record.directory)
