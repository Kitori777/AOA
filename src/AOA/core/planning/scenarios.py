from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .explanations import PlanningExplanation, explain_plan
from .models import OperationSpec, PlanningResult
from .scheduler import schedule_operations

_OVERRIDABLE_FIELDS = {
    "processing_time_h",
    "deadline_h",
    "predecessors",
    "eligible_machines",
    "components_ready_h",
    "setup_time_h",
    "waste_kg",
    "energy_kwh",
    "priority",
    "frozen",
    "started",
    "fixed_machine_id",
    "fixed_start_h",
    "station_type",
}


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    operation_overrides: dict[str, dict[str, Any]]
    unavailable_machines: tuple[int, ...] = ()


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    result: PlanningResult
    explanation: PlanningExplanation
    changes: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioComparison:
    scenarios: tuple[ScenarioResult, ...]
    recommended_name: str


def _apply_scenario(
    operations: list[OperationSpec], scenario: ScenarioSpec
) -> tuple[list[OperationSpec], tuple[str, ...]]:
    known = {operation.operation_id for operation in operations}
    unknown = sorted(set(scenario.operation_overrides) - known)
    if unknown:
        raise ValueError("Scenariusz wskazuje nieznane operacje: " + ", ".join(unknown))
    changed: list[OperationSpec] = []
    descriptions: list[str] = []
    for operation in operations:
        overrides = scenario.operation_overrides.get(operation.operation_id, {})
        forbidden = sorted(set(overrides) - _OVERRIDABLE_FIELDS)
        if forbidden:
            raise ValueError("Niedozwolone pola scenariusza: " + ", ".join(forbidden))
        changed.append(replace(operation, **overrides))
        if overrides:
            descriptions.append(
                f"{operation.operation_id}: "
                + ", ".join(f"{key}={value}" for key, value in sorted(overrides.items()))
            )
    if scenario.unavailable_machines:
        descriptions.append(
            "Niedostepne maszyny: " + ", ".join(map(str, scenario.unavailable_machines))
        )
    return changed, tuple(descriptions)


def compare_scenarios(
    operations: list[OperationSpec],
    scenarios: list[ScenarioSpec],
    *,
    machine_count: int,
    include_baseline: bool = True,
    baseline_unavailable_machines: tuple[int, ...] = (),
) -> ScenarioComparison:
    specs = list(scenarios)
    if include_baseline:
        specs.insert(0, ScenarioSpec("Bazowy", {}))
    if not specs:
        raise ValueError("Dodaj przynajmniej jeden scenariusz.")
    results: list[ScenarioResult] = []
    for scenario in specs:
        changed, descriptions = _apply_scenario(operations, scenario)
        result = schedule_operations(
            changed,
            machine_count=machine_count,
            unavailable_machines=tuple(
                sorted(
                    set(baseline_unavailable_machines)
                    | set(scenario.unavailable_machines)
                )
            ),
        )
        results.append(
            ScenarioResult(
                scenario.name,
                result,
                explain_plan(result, changed),
                descriptions,
            )
        )
    recommended = min(
        results,
        key=lambda item: (
            len(item.result.unscheduled),
            len(item.result.violations),
            item.result.total_tardiness_h,
            item.result.total_waste_kg,
            item.result.makespan_h,
            item.name,
        ),
    )
    return ScenarioComparison(tuple(results), recommended.name)
