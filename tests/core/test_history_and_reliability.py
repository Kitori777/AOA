from __future__ import annotations

import json

import pandas as pd
import pytest

from AOA.core.history import AuditLog, RunStore
from AOA.core.reliability import BackupManager, RecoveryJournal, run_diagnostics


def test_run_store_records_and_reloads_reproducible_artifacts(tmp_path) -> None:
    store = RunStore(tmp_path / "runs")
    input_frame = pd.DataFrame([{"job": "A", "time": 2}, {"job": "B", "time": 3}])
    ranking = pd.DataFrame([{"method": "MOPT", "sto": 0.0}])
    schedule = pd.DataFrame([{"job": "A", "start": 0, "end": 2}])

    record = store.record(
        input_frame=input_frame,
        settings={"objective": "deadline_then_waste", "selected_methods": ["MOPT"]},
        ranking=ranking,
        schedule=schedule,
        source_path="schedule.csv",
        events=[{"action": "evaluate"}],
    )
    loaded = store.load(record.run_id)

    assert loaded["manifest"]["best_method"] == "MOPT"
    assert loaded["input"]["job"].tolist() == ["A", "B"]
    assert loaded["settings"]["objective"] == "deadline_then_waste"
    assert loaded["events"] == [{"action": "evaluate"}]


def test_run_store_detects_tampered_input(tmp_path) -> None:
    store = RunStore(tmp_path / "runs")
    record = store.record(
        input_frame=pd.DataFrame([{"job": "A"}]),
        settings={},
        ranking=pd.DataFrame(columns=["method"]),
        schedule=pd.DataFrame(columns=["job"]),
    )
    (record.directory / "input.csv").write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="nie zgadza sie"):
        store.load(record.run_id)


def test_run_store_applies_retention(tmp_path) -> None:
    store = RunStore(tmp_path / "runs", retention=2)
    for index in range(3):
        store.record(
            input_frame=pd.DataFrame([{"job": index}]),
            settings={},
            ranking=pd.DataFrame(columns=["method"]),
            schedule=pd.DataFrame(columns=["job"]),
        )

    assert len(store.list()) == 2


def test_audit_log_builds_and_verifies_hash_chain(tmp_path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    first = audit.append("QUEUE_OPEN", "schedule.csv", {"rows": 4})
    second = audit.append("ORDER_DONE", "Q-1", {"order": "J1"})

    assert second.previous_hash == first.event_hash
    assert audit.verify() == (True, "Dziennik poprawny: 2 zdarzen.")


def test_audit_log_detects_manual_tampering(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(path)
    audit.append("QUEUE_OPEN", "schedule.csv", {"rows": 4})
    payload = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    payload["details"]["rows"] = 999
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    ok, message = audit.verify()

    assert not ok
    assert "hash" in message


def test_backup_restore_and_recovery_journal(tmp_path) -> None:
    source = tmp_path / "schedule.csv"
    source.write_text("old", encoding="utf-8")
    manager = BackupManager(tmp_path / "backups")
    backup = manager.create(source)
    journal = RecoveryJournal(tmp_path / "recovery")
    transaction = journal.begin(target=source, backup=backup.backup, action="replace")
    source.write_text("new", encoding="utf-8")

    manager.restore(backup.backup, source)
    journal.commit(transaction.transaction_id)

    assert source.read_text(encoding="utf-8") == "old"
    assert journal.pending() == ()


def test_diagnostics_checks_directories_and_queue_without_private_payload(tmp_path) -> None:
    queue = tmp_path / "schedule.csv"
    queue.write_text("job,time\nA,2\n", encoding="utf-8")

    report = run_diagnostics(
        data_dir=tmp_path / "data",
        config_dir=tmp_path / "config",
        queue_path=queue,
    )
    saved = report.save(tmp_path / "diagnostics.json")
    text = saved.read_text(encoding="utf-8")

    assert report.ok
    assert "A,2" not in text
    assert "sha256=" in text
