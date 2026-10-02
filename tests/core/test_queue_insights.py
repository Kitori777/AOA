from __future__ import annotations

import pandas as pd

from AOA.core.queue_insights import (
    build_queue_scenario_presets,
    compare_queue_scenario,
    queue_diagnostics,
    queue_history_summary,
    verify_queue_audit,
)
from AOA.core.queue_service import evaluate_queue, load_queue_snapshot


def _write_operations(path) -> None:
    pd.DataFrame(
        [
            {"queue_item_id": "Q1", "zlecenie_id": "Z1", "operation_id": "CUT",
             "czas_produkcji_h": 2, "termin_h": 8, "predecessors": "", "status": "NEW"},
            {"queue_item_id": "Q2", "zlecenie_id": "Z1", "operation_id": "SEW",
             "czas_produkcji_h": 3, "termin_h": 8, "predecessors": "CUT", "status": "NEW"},
        ]
    ).to_csv(path, index=False)


def test_scenario_presets_are_exclusive_and_compare_against_baseline(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    _write_operations(path)
    snapshot = load_queue_snapshot(path)
    presets = build_queue_scenario_presets(snapshot, machine_count=4)
    assert {preset.key for preset in presets} == {
        "baseline", "machine_outage", "component_delay", "freeze_first"
    }
    comparison = compare_queue_scenario(snapshot, machine_count=4, preset_key="machine_outage")
    assert [result.name for result in comparison.scenarios] == ["Bazowy", "Awaria M4"]

    with_existing_outage = build_queue_scenario_presets(
        snapshot, machine_count=4, unavailable_machines=(4,)
    )
    outage = next(item for item in with_existing_outage if item.key == "machine_outage")
    assert outage.label == "Awaria maszyny 3"


def test_history_audit_and_diagnostics_are_available_for_queue(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    _write_operations(path)
    evaluate_queue(load_queue_snapshot(path), selected_methods=["MT"], n_machines=2)
    summary = queue_history_summary(path)
    assert len(summary) == 1
    assert "MT" in summary[0]
    ok, message = verify_queue_audit(path)
    assert ok
    assert "Dziennik poprawny" in message
    report = queue_diagnostics(path)
    assert any(check.name == "queue" and check.ok for check in report.checks)
