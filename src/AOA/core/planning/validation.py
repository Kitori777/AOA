from __future__ import annotations

from collections import defaultdict

from .models import OperationSpec, ValidationResult


def validate_operation_graph(operations: list[OperationSpec]) -> ValidationResult:
    errors: list[str] = []
    by_id: dict[str, OperationSpec] = {}
    for operation in operations:
        operation_id = operation.operation_id.strip()
        if not operation_id:
            errors.append("Operacja bez operation_id.")
            continue
        if operation_id in by_id:
            errors.append(f"Powtorzony operation_id: {operation_id}.")
        by_id[operation_id] = operation
        if operation.processing_time_h <= 0:
            errors.append(f"{operation_id}: czas operacji musi byc dodatni.")
        if operation.deadline_h <= 0:
            errors.append(f"{operation_id}: termin musi byc dodatni.")
        if operation.components_ready_h < 0:
            errors.append(f"{operation_id}: gotowosc komponentow nie moze byc ujemna.")
        if operation.frozen or operation.started:
            if operation.fixed_machine_id is None or operation.fixed_start_h is None:
                errors.append(
                    f"{operation_id}: operacja zamrozona wymaga fixed_machine_id i fixed_start_h."
                )
        if operation.fixed_start_h is not None and operation.fixed_start_h < 0:
            errors.append(f"{operation_id}: fixed_start_h nie moze byc ujemny.")

    successors: dict[str, list[str]] = defaultdict(list)
    indegree = {operation_id: 0 for operation_id in by_id}
    for operation in operations:
        if operation.operation_id not in by_id:
            continue
        for predecessor in operation.predecessors:
            if predecessor == operation.operation_id:
                errors.append(f"{operation.operation_id}: operacja nie moze zalezec od siebie.")
                continue
            if predecessor not in by_id:
                errors.append(
                    f"{operation.operation_id}: brak poprzednika {predecessor}."
                )
                continue
            successors[predecessor].append(operation.operation_id)
            indegree[operation.operation_id] += 1

    ready = sorted(operation_id for operation_id, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while ready:
        operation_id = ready.pop(0)
        ordered.append(operation_id)
        for successor in sorted(successors[operation_id]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort()
    if len(ordered) != len(by_id):
        cycle_nodes = sorted(set(by_id) - set(ordered))
        errors.append("Cykl zaleznosci operacji: " + ", ".join(cycle_nodes) + ".")

    return ValidationResult(not errors, tuple(errors), tuple(ordered))
