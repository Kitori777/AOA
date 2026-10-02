from __future__ import annotations

import pandas as pd
import pytest

from AOA.core.mh_models import get_mh_model_names
from AOA.core.queue_service import (
    append_queue_orders,
    archive_completed_orders,
    build_component_queue_state,
    evaluate_queue,
    load_latest_queue_results,
    load_queue_snapshot,
    mark_queue_item_done,
    refresh_component_readiness,
)
from AOA.core.sto_models import Job, sequence_genetic, sequence_neh, sequence_random_restart


def _write_queue(path) -> None:
    path.write_text(
        "job_id,processing_h,due_h,setup_h,machine,status\n"
        "J1,4,8,0.5,1|2,NEW\n"
        "J2,2,3,0.2,1|2,NEW\n"
        "J3,8,16,0.8,1|2,NEW\n"
        "J4,3,9,0.3,1|2,NEW\n",
        encoding="utf-8",
    )


def test_legacy_queue_runs_every_registered_heuristic_for_four_orders(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    _write_queue(path)

    evaluation = evaluate_queue(load_queue_snapshot(path), n_machines=2)

    assert {result["method"] for result in evaluation.results} == get_mh_model_names()
    assert all(len(result["order"]) == 4 for result in evaluation.results)
    assert all(result["machine_count"] == 2 for result in evaluation.results)

    ranking, schedule = load_latest_queue_results(path)
    assert len(ranking) == len(evaluation.results)
    assert ranking.iloc[0]["objective"] == "deadline_then_waste"
    assert len(schedule) == 4


def test_queue_persists_selected_exclusive_objective(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    _write_queue(path)

    evaluation = evaluate_queue(
        load_queue_snapshot(path),
        selected_methods=["MT", "ECO_WASTE"],
        n_machines=2,
        objective="waste_then_deadline",
    )
    ranking, _ = load_latest_queue_results(path)

    assert evaluation.objective == "waste_then_deadline"
    assert set(ranking["objective"]) == {"waste_then_deadline"}


def test_malformed_and_duplicate_rows_are_blocked_without_stopping_valid_orders(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    path.write_text(
        "zlecenie_id,czas_produkcji_h,termin_h,status\n"
        "OK,2,8,NEW\nDUP,3,9,NEW\nDUP,4,10,NEW\nBAD,nope,11,NEW\n",
        encoding="utf-8",
    )

    snapshot = load_queue_snapshot(path)
    evaluation = evaluate_queue(snapshot, selected_methods=["MT"])

    assert len(snapshot.active) == 1
    assert len(snapshot.blocked) == 3
    assert evaluation.results[0]["order"] == ["OK"]


def test_done_order_is_archived_and_removed_idempotently(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    _write_queue(path)
    snapshot = load_queue_snapshot(path)
    queue_id = str(snapshot.frame.iloc[0]["queue_item_id"])

    mark_queue_item_done(path, queue_id)
    assert archive_completed_orders(path) == 1
    assert archive_completed_orders(path) == 0

    active = load_queue_snapshot(path)
    archive = load_queue_snapshot(tmp_path / "schedule_archive.csv")
    assert len(active.frame) == 3
    assert archive.frame["queue_item_id"].tolist() == [queue_id]


def test_append_orders_preserves_existing_queue_and_validates_new_rows(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    _write_queue(path)

    snapshot = append_queue_orders(
        path,
        pd.DataFrame(
            [{"zlecenie_id": "J5", "czas_produkcji_h": 1.5, "termin_h": 7, "status": "NEW"}]
        ),
    )

    assert len(snapshot.active) == 5
    assert snapshot.active.iloc[-1]["zlecenie_id"] == "J5"
    assert snapshot.active.iloc[-1]["queue_item_id"].startswith("Q-0005-J5")


def test_queue_requires_canonical_or_legacy_required_columns(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    path.write_text("id,value\nA,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Brak wymaganych kolumn"):
        load_queue_snapshot(path)


@pytest.mark.parametrize("algorithm", [sequence_neh, sequence_random_restart, sequence_genetic])
def test_expensive_heuristics_keep_large_queue_complete(algorithm) -> None:
    jobs = [Job(f"J{index:03d}", 1 + index % 7, 10 + index) for index in range(75)]

    result = algorithm(jobs, n_machines=4)

    assert len(result) == len(jobs)
    assert {job.job_id for job in result} == {job.job_id for job in jobs}


def test_double_queue_gates_components_before_exact_machine_plan(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    pd.DataFrame(
        [
            {
                "queue_item_id": "Q1",
                "zlecenie_id": "READY",
                "operation_id": "READY-OP",
                "czas_produkcji_h": 2,
                "termin_h": 10,
                "dozwolone_maszyny": "1|2",
                "components_ready_h": 0,
                "stock_status": "READY",
                "status": "NEW",
            },
            {
                "queue_item_id": "Q2",
                "zlecenie_id": "FUTURE",
                "operation_id": "FUTURE-OP",
                "czas_produkcji_h": 1,
                "termin_h": 12,
                "dozwolone_maszyny": "2",
                "components_ready_h": 5,
                "stock_status": "WAITING_COMPONENTS",
                "status": "NEW",
            },
            {
                "queue_item_id": "Q3",
                "zlecenie_id": "MISSING",
                "operation_id": "MISSING-OP",
                "czas_produkcji_h": 1,
                "termin_h": 9,
                "dozwolone_maszyny": "1",
                "components_ready_h": "",
                "missing_components": "SKU-X:1",
                "stock_status": "UNSCHEDULABLE",
                "status": "NEW",
            },
        ]
    ).to_csv(path, index=False)
    snapshot = load_queue_snapshot(path)

    component_queue = build_component_queue_state(snapshot.active)
    evaluation = evaluate_queue(
        snapshot,
        selected_methods=["ECO_WASTE", "COMPONENT_READY_EDD"],
        n_machines=2,
        unavailable_machines=(2,),
    )

    assert evaluation.best is not None
    assert evaluation.operation_plan is not None
    assert component_queue.ready_now == ("READY",)
    assert component_queue.waiting_components == ("FUTURE",)
    assert component_queue.unschedulable == ("MISSING",)
    assert set(evaluation.best["order"]) == {"READY", "FUTURE"}
    assert evaluation.best["component_blocked_count"] == 1
    assert evaluation.best["machine_blocked_count"] == 1
    assert evaluation.best["unscheduled_count"] == 2
    assert [step.operation_id for step in evaluation.operation_plan.steps] == ["READY-OP"]
    assert evaluation.operation_plan.unscheduled == ("FUTURE-OP",)


def test_confirmed_future_components_start_no_earlier_than_ready_time(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    pd.DataFrame(
        [
            {
                "zlecenie_id": "FUTURE",
                "czas_produkcji_h": 2,
                "termin_h": 12,
                "dozwolone_maszyny": "1|2",
                "components_ready_h": 5,
                "stock_status": "WAITING_COMPONENTS",
                "status": "NEW",
            }
        ]
    ).to_csv(path, index=False)

    evaluation = evaluate_queue(
        load_queue_snapshot(path),
        selected_methods=["COMPONENT_READY_EDD"],
        n_machines=2,
    )

    assert evaluation.component_queue is not None
    assert evaluation.operation_plan is not None
    assert evaluation.best is not None
    assert evaluation.component_queue.waiting_components == ("FUTURE",)
    assert evaluation.operation_plan.steps[0].start_h >= 5
    assert evaluation.best["unscheduled_count"] == 0


def test_double_queue_rechecks_sibling_inventory_once_per_order(tmp_path) -> None:
    path = tmp_path / "schedule.csv"
    pd.DataFrame(
        [
            {
                "queue_item_id": "Q1",
                "zlecenie_id": "EARLY",
                "operation_id": "EARLY-CUT",
                "produkt_id": "P1",
                "ilosc_szt": 2,
                "czas_produkcji_h": 1,
                "termin_h": 5,
                "status": "NEW",
            },
            {
                "queue_item_id": "Q2",
                "zlecenie_id": "EARLY",
                "operation_id": "EARLY-SEW",
                "produkt_id": "P1",
                "ilosc_szt": 2,
                "czas_produkcji_h": 1,
                "termin_h": 5,
                "status": "NEW",
            },
            {
                "queue_item_id": "Q3",
                "zlecenie_id": "LATE",
                "operation_id": "LATE-CUT",
                "produkt_id": "P1",
                "ilosc_szt": 2,
                "czas_produkcji_h": 1,
                "termin_h": 10,
                "status": "NEW",
            },
        ]
    ).to_csv(path, index=False)
    pd.DataFrame(
        [{"produkt_id": "P1", "component_sku": "A", "quantity_per_unit": 2}]
    ).to_csv(tmp_path / "bom.csv", index=False)
    pd.DataFrame(
        [
            {
                "lot_id": "A0",
                "component_sku": "A",
                "quantity": 4,
                "available_at_h": 0,
            }
        ]
    ).to_csv(tmp_path / "inventory.csv", index=False)
    snapshot = load_queue_snapshot(path)

    refreshed = refresh_component_readiness(snapshot.active, path)
    evaluation = evaluate_queue(
        snapshot,
        selected_methods=["COMPONENT_READY_EDD"],
        n_machines=2,
    )

    assert evaluation.component_queue is not None
    assert evaluation.operation_plan is not None
    early_rows = refreshed[refreshed["zlecenie_id"] == "EARLY"]
    assert set(early_rows["stock_status"]) == {"READY"}
    assert evaluation.component_queue.ready_now == ("EARLY",)
    assert evaluation.component_queue.unschedulable == ("LATE",)
    assert {step.order_id for step in evaluation.operation_plan.steps} == {"EARLY"}
