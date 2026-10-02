from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .models import OperationSpec, PlanningResult


@dataclass(frozen=True)
class PlanningExplanation:
    summary: str
    bottlenecks: tuple[str, ...]
    operation_reasons: dict[str, str]
    recommendations: tuple[str, ...]


def explain_plan(
    result: PlanningResult, operations: list[OperationSpec]
) -> PlanningExplanation:
    by_id = {operation.operation_id: operation for operation in operations}
    reasons = {step.operation_id: step.reason for step in result.steps}
    loads: dict[int, float] = defaultdict(float)
    waits: list[tuple[float, str, str]] = []
    for step in result.steps:
        operation = by_id[step.operation_id]
        loads[step.machine_id] += step.end_h - step.start_h
        component_wait = max(0.0, step.components_ready_h - step.predecessor_ready_h)
        if component_wait:
            waits.append((component_wait, step.operation_id, "komponenty"))
        predecessor_wait = max(0.0, step.predecessor_ready_h - step.components_ready_h)
        if predecessor_wait:
            waits.append((predecessor_wait, step.operation_id, "poprzednia operacja"))
        if step.tardiness_h:
            reasons[step.operation_id] += (
                f"; opoznienie {step.tardiness_h:.3f} h wzgledem terminu "
                f"{operation.deadline_h:.3f} h"
            )

    bottlenecks: list[str] = []
    if loads:
        machine_id, load = max(loads.items(), key=lambda item: (item[1], -item[0]))
        bottlenecks.append(f"Maszyna {machine_id}: obciazenie {load:.3f} h.")
    if waits:
        wait, operation_id, cause = max(waits)
        bottlenecks.append(
            f"{operation_id}: najdluzsze oczekiwanie {wait:.3f} h, przyczyna: {cause}."
        )
    if result.unscheduled:
        bottlenecks.append("Niewykonalne operacje: " + ", ".join(result.unscheduled) + ".")
    violations = Counter(message.split(":", 1)[0] for message in result.violations)
    if violations:
        bottlenecks.append(f"Naruszenia planu: {sum(violations.values())}.")

    recommendations: list[str] = []
    tardy = sorted(
        (step for step in result.steps if step.tardiness_h > 0),
        key=lambda step: (-step.tardiness_h, step.operation_id),
    )
    if tardy:
        worst = tardy[0]
        recommendations.append(
            f"Najpierw skroc lub przyspiesz {worst.operation_id}; redukcja o "
            f"{worst.tardiness_h:.3f} h usunie najwieksze opoznienie."
        )
    if any(step.components_ready_h > 0 for step in result.steps):
        recommendations.append(
            "Sprawdz przyspieszenie dostawy komponentow dla operacji oczekujacych na material."
        )
    if result.metadata.get("frozen_count"):
        recommendations.append(
            "Porownaj scenariusz bez wybranych blokad; zamrozone operacje ograniczaja optymalizacje."
        )
    if result.feasible and not tardy:
        recommendations.append("Plan jest wykonalny i nie zawiera opoznionych operacji.")

    summary = (
        f"Zaplanowano {len(result.steps)} operacji na {result.machine_count} maszynach; "
        f"STO operacji {result.total_tardiness_h:.3f} h, koniec {result.makespan_h:.3f} h."
    )
    return PlanningExplanation(summary, tuple(bottlenecks), reasons, tuple(recommendations))
