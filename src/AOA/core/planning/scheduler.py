from __future__ import annotations

from collections import defaultdict

from AOA.core.machine_catalog import MachineSpec

from .models import OperationSpec, OperationStep, PlanningResult
from .validation import validate_operation_graph


def _overlaps(start: float, end: float, other_start: float, other_end: float) -> bool:
    return start < other_end and other_start < end


def _earliest_slot(
    bookings: list[tuple[float, float, str]], release: float, duration: float
) -> float:
    start = release
    for other_start, other_end, _other_id in sorted(bookings):
        if start + duration <= other_start:
            return start
        if _overlaps(start, start + duration, other_start, other_end):
            start = other_end
    return start


def schedule_operations(
    operations: list[OperationSpec],
    *,
    machine_count: int,
    unavailable_machines: tuple[int, ...] = (),
    machine_specs: tuple[MachineSpec, ...] | list[MachineSpec] | None = None,
) -> PlanningResult:
    if machine_count < 1 or machine_count > 32:
        raise ValueError("Liczba maszyn musi miescic sie w zakresie 1-32.")
    invalid_unavailable = sorted(
        machine_id
        for machine_id in set(unavailable_machines)
        if machine_id < 1 or machine_id > machine_count
    )
    if invalid_unavailable:
        raise ValueError(
            "Niedostepne maszyny sa poza zakresem: " + ", ".join(map(str, invalid_unavailable))
        )
    normalized_machines = (
        tuple(machine.normalized(index) for index, machine in enumerate(machine_specs, 1))
        if machine_specs is not None
        else ()
    )
    if normalized_machines and len(normalized_machines) != machine_count:
        raise ValueError("Liczba profili maszyn nie zgadza sie z machine_count.")
    machine_by_number = {
        index: machine for index, machine in enumerate(normalized_machines, 1)
    }
    validation = validate_operation_graph(operations)
    if not validation.valid:
        return PlanningResult(
            (),
            validation.errors,
            tuple(operation.operation_id for operation in operations),
            machine_count,
            0.0,
            0.0,
            0.0,
            0.0,
            {"validation": "failed"},
        )

    by_id = {operation.operation_id: operation for operation in operations}
    unavailable = set(unavailable_machines)
    bookings: dict[int, list[tuple[float, float, str]]] = defaultdict(list)
    completion: dict[str, float] = {}
    steps: list[OperationStep] = []
    violations: list[str] = []
    unscheduled: list[str] = []
    last_product: dict[int, str] = {}
    scheduled_machine: dict[str, int] = {}

    for operation in operations:
        if not (operation.frozen or operation.started):
            continue
        if operation.fixed_machine_id is None or operation.fixed_start_h is None:
            continue
        end = operation.fixed_start_h + operation.setup_time_h + operation.processing_time_h
        bookings[operation.fixed_machine_id].append(
            (operation.fixed_start_h, end, operation.operation_id)
        )
    for machine_bookings in bookings.values():
        machine_bookings.sort()

    ranked = sorted(
        validation.topological_order,
        key=lambda operation_id: (
            -by_id[operation_id].priority,
            by_id[operation_id].deadline_h,
            validation.topological_order.index(operation_id),
        ),
    )
    remaining = set(ranked)
    while remaining:
        ready_ids = [
            operation_id
            for operation_id in ranked
            if operation_id in remaining
            and all(predecessor in completion for predecessor in by_id[operation_id].predecessors)
        ]
        if not ready_ids:
            unscheduled.extend(sorted(remaining))
            violations.append("Nie mozna wyznaczyc kolejnych gotowych operacji.")
            break
        operation_id = ready_ids[0]
        operation = by_id[operation_id]
        predecessor_ready = max(
            (completion[predecessor] for predecessor in operation.predecessors),
            default=0.0,
        )
        release = max(predecessor_ready, operation.components_ready_h)
        configured_allowed = operation.eligible_machines or tuple(range(1, machine_count + 1))
        allowed = tuple(
            machine_id
            for machine_id in configured_allowed
            if 1 <= machine_id <= machine_count and machine_id not in unavailable
            and (
                machine_id not in machine_by_number
                or machine_by_number[machine_id].capability.accepts(
                    product=operation.product_id,
                    material=operation.material,
                    operation=operation.station_type or operation.operation_id,
                )
            )
        )
        if operation.frozen or operation.started:
            machine_id = operation.fixed_machine_id or 0
            start = operation.fixed_start_h if operation.fixed_start_h is not None else 0.0
            end = start + operation.setup_time_h + operation.processing_time_h
            if machine_id not in configured_allowed or not 1 <= machine_id <= machine_count:
                violations.append(
                    f"{operation_id}: zamrozona maszyna {machine_id} jest poza dozwolonym zakresem."
                )
                unscheduled.append(operation_id)
                remaining.remove(operation_id)
                continue
            if machine_id in unavailable:
                violations.append(
                    f"{operation_id}: zamrozona maszyna {machine_id} jest niedostepna; "
                    "termin pozostawiono bez zmian."
                )
            if start < release:
                violations.append(
                    f"{operation_id}: zamrozony start {start:.3f} jest przed gotowoscia {release:.3f}."
                )
            for other_start, other_end, other_id in bookings[machine_id]:
                if other_id != operation_id and _overlaps(start, end, other_start, other_end):
                    violations.append(
                        f"{operation_id}: konflikt zamrozonego planu z {other_id} na maszynie {machine_id}."
                    )
            reason = "Zachowano rozpoczecie" if operation.started else "Zachowano zamrozony plan"
        else:
            if not allowed:
                unscheduled.append(operation_id)
                violations.append(f"{operation_id}: brak dostepnej dozwolonej maszyny.")
                remaining.remove(operation_id)
                continue
            candidates = []
            duration_by_machine: dict[int, tuple[float, float]] = {}
            for machine_id in allowed:
                machine = machine_by_number.get(machine_id)
                machine_setup = (
                    machine.setup_time_h
                    if machine is not None
                    and last_product.get(machine_id)
                    and last_product[machine_id] != operation.product_id
                    else 0.0
                )
                speed = machine.speed_factor if machine is not None else 1.0
                duration = operation.setup_time_h + machine_setup + operation.processing_time_h / speed
                start = _earliest_slot(bookings[machine_id], release, duration)
                end = start + duration
                duration_by_machine[machine_id] = (duration, machine_setup)
                candidates.append((end, start, machine_id))
            end, start, machine_id = min(candidates)
            reason_parts = [f"najwczesniejszy koniec na maszynie {machine_id}"]
            if predecessor_ready > 0:
                reason_parts.append(f"poprzedniki gotowe {predecessor_ready:.3f} h")
            if operation.components_ready_h > 0:
                reason_parts.append(f"komponenty gotowe {operation.components_ready_h:.3f} h")
            reason = "; ".join(reason_parts)

        if not (operation.frozen or operation.started):
            bookings[machine_id].append((start, end, operation_id))
            bookings[machine_id].sort()
        completion[operation_id] = end
        scheduled_machine[operation_id] = machine_id
        if operation.product_id:
            last_product[machine_id] = operation.product_id
        steps.append(
            OperationStep(
                operation_id=operation_id,
                order_id=operation.order_id,
                machine_id=machine_id,
                start_h=round(start, 3),
                end_h=round(end, 3),
                deadline_h=operation.deadline_h,
                tardiness_h=round(max(0.0, end - operation.deadline_h), 3),
                components_ready_h=operation.components_ready_h,
                predecessor_ready_h=round(predecessor_ready, 3),
                frozen=operation.frozen,
                started=operation.started,
                reason=reason,
            )
        )
        remaining.remove(operation_id)

    total_tardiness = sum(step.tardiness_h for step in steps)
    makespan = max((step.end_h for step in steps), default=0.0)
    scheduled_ids = {step.operation_id for step in steps}
    return PlanningResult(
        tuple(sorted(steps, key=lambda step: (step.start_h, step.machine_id, step.operation_id))),
        tuple(violations),
        tuple(dict.fromkeys(unscheduled)),
        machine_count,
        round(total_tardiness, 3),
        round(makespan, 3),
        round(
            sum(
                by_id[item].waste_kg
                * machine_by_number.get(
                    scheduled_machine[item],
                    MachineSpec(str(scheduled_machine[item]), "", "QUEUE"),
                ).waste_factor
                for item in scheduled_ids
            ),
            4,
        ),
        round(
            sum(
                (
                    by_id[item].energy_kwh
                    if scheduled_machine[item] not in machine_by_number
                    or machine_by_number[scheduled_machine[item]].energy_kwh_per_hour <= 0
                    else by_id[item].processing_time_h
                    / machine_by_number[scheduled_machine[item]].speed_factor
                    * machine_by_number[scheduled_machine[item]].energy_kwh_per_hour
                )
                for item in scheduled_ids
            ),
            3,
        ),
        {
            "frozen_count": sum(step.frozen for step in steps),
            "unavailable_machines": tuple(sorted(unavailable)),
        },
    )
