from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from AOA.core.planning import (
    OperationSpec,
    WeeklyPlan,
    WeeklyPlanItem,
    WeeklyPlanningPolicy,
    WeeklyPlanStatus,
    WeeklyPlanStore,
    apply_weekly_lock,
    schedule_operations,
)
from AOA.core.queue_service import evaluate_queue, load_queue_snapshot

WARSAW = ZoneInfo("Europe/Warsaw")


def _result(*, moved: bool = False):
    return schedule_operations(
        [
            OperationSpec(
                "CUT",
                "O1",
                2,
                20,
                eligible_machines=(1, 2),
                priority=2,
            ),
            OperationSpec(
                "SEW",
                "O1",
                3,
                30,
                predecessors=("CUT",),
                eligible_machines=(2,) if moved else (1, 2),
            ),
        ],
        machine_count=2,
    )


def test_policy_keeps_monday_0600_across_dst_and_year_boundaries() -> None:
    policy = WeeklyPlanningPolicy()

    after_dst = policy.next_week_start(datetime(2026, 10, 23, 12, tzinfo=WARSAW))
    new_year = policy.next_week_start(datetime(2026, 12, 31, 12, tzinfo=WARSAW))

    assert after_dst.isoformat() == "2026-10-26T06:00:00+01:00"
    assert new_year.isoformat() == "2027-01-04T06:00:00+01:00"
    assert policy.horizon_hours == 40
    assert policy.elapsed_work_hours(datetime(2026, 10, 6, 7, tzinfo=WARSAW)) == 9


def test_draft_approval_is_idempotent_and_survives_store_restart(tmp_path) -> None:
    policy = WeeklyPlanningPolicy()
    now = datetime(2026, 10, 2, 12, tzinfo=WARSAW)
    queue_path = tmp_path / "schedule.csv"
    store = WeeklyPlanStore(tmp_path / "plans", queue_path)

    draft = store.create_draft(
        target_week_start=policy.next_week_start(now),
        policy=policy,
        result=_result(),
        source_queue_hash="abc",
        source_run_id="run-1",
        now=now,
    )
    approved = store.approve(draft.plan_id, policy=policy, now=now)
    second = store.approve(draft.plan_id, policy=policy, now=now)
    reloaded = WeeklyPlanStore(tmp_path / "plans", queue_path).latest(draft.plan_id)

    assert draft.status == WeeklyPlanStatus.DRAFT
    assert approved.status == WeeklyPlanStatus.APPROVED
    assert second == approved
    assert reloaded == approved
    assert len(store.list_versions(draft.plan_id)) == 2


def test_active_plan_resolution_and_week_rollover(tmp_path) -> None:
    policy = WeeklyPlanningPolicy()
    week_start = datetime(2026, 10, 5, 6, tzinfo=WARSAW)
    queue_path = tmp_path / "schedule.csv"
    store = WeeklyPlanStore(tmp_path / "plans", queue_path)
    draft = store.create_draft(
        target_week_start=week_start,
        policy=policy,
        result=_result(),
        source_queue_hash="abc",
        now=datetime(2026, 10, 2, 12, tzinfo=WARSAW),
    )
    approved = store.approve(draft.plan_id, policy=policy)

    assert store.current_plan(policy, datetime(2026, 10, 5, 7, tzinfo=WARSAW)) == approved
    assert store.current_plan(policy, datetime(2026, 10, 12, 7, tzinfo=WARSAW)) is None
    assert (
        approved.effective_status(datetime(2026, 10, 12, 7, tzinfo=WARSAW), policy=policy)
        == "CLOSED"
    )


def test_apply_weekly_lock_freezes_known_items_and_releases_new_work_after_horizon() -> None:
    policy = WeeklyPlanningPolicy()
    plan = WeeklyPlan(
        plan_id="2026-W41",
        version=2,
        status=WeeklyPlanStatus.APPROVED,
        target_week_start="2026-10-05T06:00:00+02:00",
        target_week_end="2026-10-12T06:00:00+02:00",
        created_at="2026-10-02T12:00:00+02:00",
        approved_at="2026-10-02T12:05:00+02:00",
        source_run_id="run",
        source_queue_hash="hash",
        emergency_reason="",
        items=(WeeklyPlanItem("LOCKED", "O1", 2, 4, 6),),
    )
    frame = pd.DataFrame(
        [
            {"operation_id": "LOCKED", "components_ready_h": 0, "stock_status": "READY"},
            {"operation_id": "NEW", "components_ready_h": 3, "stock_status": "READY"},
        ]
    )

    updated, alerts, locked = apply_weekly_lock(frame, plan, policy, unavailable_machines=(2,))

    locked_row = updated[updated["operation_id"] == "LOCKED"].iloc[0]
    new_row = updated[updated["operation_id"] == "NEW"].iloc[0]
    assert locked_row["frozen"]
    assert locked_row["fixed_machine_id"] == 2
    assert locked_row["fixed_start_h"] == 4
    assert new_row["components_ready_h"] == 40
    assert locked == 1
    assert any("M2" in alert for alert in alerts)


def test_emergency_replan_requires_reason_and_writes_audited_version(tmp_path) -> None:
    policy = WeeklyPlanningPolicy()
    active_at = datetime(2026, 10, 5, 7, tzinfo=WARSAW)
    store = WeeklyPlanStore(tmp_path / "plans", tmp_path / "schedule.csv")
    draft = store.create_draft(
        target_week_start=policy.week_start(active_at),
        policy=policy,
        result=_result(),
        source_queue_hash="v1",
        now=datetime(2026, 10, 2, 12, tzinfo=WARSAW),
    )
    approved = store.approve(draft.plan_id, policy=policy)

    with pytest.raises(ValueError, match="powodu"):
        store.emergency_replan(
            approved.plan_id,
            policy=policy,
            result=_result(moved=True),
            reason="",
            source_queue_hash="v2",
            now=active_at,
        )

    replacement = store.emergency_replan(
        approved.plan_id,
        policy=policy,
        result=_result(moved=True),
        reason="Awaria maszyny M1",
        source_queue_hash="v2",
        now=active_at,
    )

    valid, message = store.audit.verify()
    assert replacement.version == approved.version + 1
    assert replacement.emergency_reason == "Awaria maszyny M1"
    assert valid, message
    assert store.audit.read()[-1].action == "WEEKLY_PLAN_EMERGENCY_REPLAN"


def test_weekly_queue_keeps_active_slots_and_pushes_new_orders_to_future(tmp_path) -> None:
    queue_path = tmp_path / "schedule.csv"
    pd.DataFrame(
        [
            {
                "zlecenie_id": "LOCKED-ORDER",
                "operation_id": "LOCKED",
                "czas_produkcji_h": 2,
                "termin_h": 10,
                "dozwolone_maszyny": "1",
                "status": "NEW",
            },
            {
                "zlecenie_id": "NEW-ORDER",
                "operation_id": "NEW",
                "czas_produkcji_h": 2,
                "termin_h": 15,
                "dozwolone_maszyny": "2",
                "status": "NEW",
            },
        ]
    ).to_csv(queue_path, index=False)
    policy = WeeklyPlanningPolicy()
    active_at = datetime(2026, 10, 5, 8, tzinfo=WARSAW)
    plan = WeeklyPlan(
        plan_id=policy.week_id(policy.week_start(active_at)),
        version=2,
        status=WeeklyPlanStatus.APPROVED,
        target_week_start=policy.week_start(active_at).isoformat(),
        target_week_end=policy.week_end(policy.week_start(active_at)).isoformat(),
        created_at=active_at.isoformat(),
        approved_at=active_at.isoformat(),
        source_run_id="run",
        source_queue_hash="hash",
        emergency_reason="",
        items=(WeeklyPlanItem("LOCKED", "LOCKED-ORDER", 1, 6, 8),),
    )

    evaluation = evaluate_queue(
        load_queue_snapshot(queue_path),
        selected_methods=["MT"],
        n_machines=2,
        unavailable_machines=(1,),
        weekly_policy=policy,
        weekly_plan=plan,
        now=active_at,
    )
    assert evaluation.operation_plan is not None
    by_id = {step.operation_id: step for step in evaluation.operation_plan.steps}

    assert evaluation.weekly_status == "ACTIVE"
    assert evaluation.weekly_locked_count == 1
    assert by_id["LOCKED"].start_h == 6
    assert by_id["LOCKED"].machine_id == 1
    assert by_id["NEW"].start_h >= 40
    assert any("M1" in alert for alert in evaluation.weekly_alerts)
    assert any("termin pozostawiono" in item for item in evaluation.operation_plan.violations)


def test_weekly_queue_without_approved_plan_warns_and_does_not_freeze(tmp_path) -> None:
    queue_path = tmp_path / "schedule.csv"
    pd.DataFrame(
        [
            {
                "zlecenie_id": "O1",
                "czas_produkcji_h": 2,
                "termin_h": 10,
                "status": "NEW",
            }
        ]
    ).to_csv(queue_path, index=False)

    evaluation = evaluate_queue(
        load_queue_snapshot(queue_path),
        selected_methods=["MT"],
        weekly_policy=WeeklyPlanningPolicy(),
    )

    assert evaluation.operation_plan is not None
    assert evaluation.weekly_status == "MISSING"
    assert evaluation.weekly_locked_count == 0
    assert "Brak zatwierdzonego" in evaluation.weekly_alerts[0]
    assert all(not step.frozen for step in evaluation.operation_plan.steps)
