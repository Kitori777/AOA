from __future__ import annotations

from AOA.core.planning import (
    OperationSpec,
    ScenarioSpec,
    compare_scenarios,
    explain_plan,
    schedule_operations,
    validate_operation_graph,
)


def test_operation_graph_rejects_missing_predecessor_and_cycle() -> None:
    missing = [OperationSpec("CUT", "O1", 2, 10, predecessors=("MISSING",))]
    cyclic = [
        OperationSpec("A", "O1", 1, 10, predecessors=("B",)),
        OperationSpec("B", "O1", 1, 10, predecessors=("A",)),
    ]

    assert not validate_operation_graph(missing).valid
    assert "brak poprzednika" in " ".join(validate_operation_graph(missing).errors)
    assert "Cykl zaleznosci" in " ".join(validate_operation_graph(cyclic).errors)


def test_scheduler_respects_predecessors_components_and_multiple_machines() -> None:
    operations = [
        OperationSpec("CUT", "O1", 2, 12, eligible_machines=(1,)),
        OperationSpec(
            "SEW",
            "O1",
            3,
            12,
            predecessors=("CUT",),
            eligible_machines=(2,),
            components_ready_h=4,
        ),
        OperationSpec("PACK", "O2", 1, 8, eligible_machines=(1, 2), priority=2),
    ]

    result = schedule_operations(operations, machine_count=2)
    by_id = {step.operation_id: step for step in result.steps}

    assert result.feasible
    assert by_id["SEW"].start_h == 4
    assert by_id["SEW"].start_h >= by_id["CUT"].end_h
    assert {step.machine_id for step in result.steps} == {1, 2}


def test_frozen_operation_keeps_slot_and_regular_work_uses_available_gap() -> None:
    operations = [
        OperationSpec(
            "LOCKED",
            "O1",
            3,
            20,
            eligible_machines=(1,),
            frozen=True,
            fixed_machine_id=1,
            fixed_start_h=4,
        ),
        OperationSpec("EARLY", "O2", 2, 10, eligible_machines=(1,)),
        OperationSpec("LATE", "O3", 3, 20, eligible_machines=(1,)),
    ]

    result = schedule_operations(operations, machine_count=1)
    by_id = {step.operation_id: step for step in result.steps}

    assert by_id["LOCKED"].start_h == 4
    assert by_id["EARLY"].end_h <= 4
    assert by_id["LATE"].start_h >= by_id["LOCKED"].end_h


def test_invalid_frozen_start_is_reported_without_moving_the_operation() -> None:
    operations = [
        OperationSpec("FIRST", "O1", 4, 10, eligible_machines=(1,)),
        OperationSpec(
            "LOCKED",
            "O1",
            2,
            12,
            predecessors=("FIRST",),
            eligible_machines=(1,),
            frozen=True,
            fixed_machine_id=1,
            fixed_start_h=1,
        ),
    ]

    result = schedule_operations(operations, machine_count=1)
    locked = next(step for step in result.steps if step.operation_id == "LOCKED")

    assert locked.start_h == 1
    assert any("przed gotowoscia" in violation for violation in result.violations)


def test_scenario_comparison_selects_lower_tardiness_variant() -> None:
    operations = [
        OperationSpec("A", "O1", 5, 4, eligible_machines=(1,)),
        OperationSpec("B", "O2", 2, 10, eligible_machines=(1,)),
    ]
    scenarios = [
        ScenarioSpec("Przyspieszenie", {"A": {"processing_time_h": 3}}),
        ScenarioSpec("Awaria", {}, unavailable_machines=(1,)),
    ]

    comparison = compare_scenarios(operations, scenarios, machine_count=1)

    assert comparison.recommended_name == "Przyspieszenie"
    assert {item.name for item in comparison.scenarios} == {"Bazowy", "Przyspieszenie", "Awaria"}


def test_plan_explanation_names_bottleneck_and_recommendation() -> None:
    operations = [OperationSpec("A", "O1", 5, 2, eligible_machines=(1,))]
    result = schedule_operations(operations, machine_count=1)

    explanation = explain_plan(result, operations)

    assert "Zaplanowano 1" in explanation.summary
    assert any("Maszyna 1" in item for item in explanation.bottlenecks)
    assert any("Najpierw" in item for item in explanation.recommendations)


def test_scheduler_never_assigns_an_unavailable_machine() -> None:
    operations = [
        OperationSpec("A", "O1", 2, 8, eligible_machines=(1, 2)),
        OperationSpec("B", "O2", 2, 8, eligible_machines=(2,)),
    ]

    result = schedule_operations(operations, machine_count=2, unavailable_machines=(2,))

    assert {step.machine_id for step in result.steps} == {1}
    assert result.unscheduled == ("B",)
    assert result.metadata["unavailable_machines"] == (2,)


def test_unavailable_machine_does_not_move_a_frozen_operation() -> None:
    operations = [
        OperationSpec(
            "LOCKED",
            "O1",
            2,
            8,
            eligible_machines=(2,),
            frozen=True,
            fixed_machine_id=2,
            fixed_start_h=5,
        )
    ]

    result = schedule_operations(operations, machine_count=2, unavailable_machines=(2,))

    assert result.steps[0].machine_id == 2
    assert result.steps[0].start_h == 5
    assert any("termin pozostawiono" in item for item in result.violations)
