from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from AOA.config import CONFIG_DIR, DATA_DIR
from AOA.core.history import AuditLog, RunStore
from AOA.core.planning import (
    ScenarioComparison,
    ScenarioSpec,
    compare_scenarios,
    dataframe_to_operations,
)
from AOA.core.queue_service import (
    QueueSnapshot,
    build_component_queue_state,
    refresh_component_readiness,
)
from AOA.core.reliability import DiagnosticCheck, DiagnosticReport, RecoveryJournal, run_diagnostics


@dataclass(frozen=True)
class ScenarioPreset:
    key: str
    label: str
    description: str
    scenario: ScenarioSpec


def build_queue_scenario_presets(
    snapshot: QueueSnapshot, *, machine_count: int,
    unavailable_machines: tuple[int, ...] = (),
) -> tuple[ScenarioPreset, ...]:
    planning_active = refresh_component_readiness(snapshot.active, snapshot.path)
    component_queue = build_component_queue_state(planning_active)
    admitted = set(component_queue.admitted)
    operations = dataframe_to_operations(
        planning_active[planning_active["zlecenie_id"].astype(str).isin(admitted)]
    )
    presets = [
        ScenarioPreset("baseline", "Plan bazowy", "Aktualne dane bez zmian.", ScenarioSpec("Bazowy", {}))
    ]
    working_machines = [
        machine_id
        for machine_id in range(1, machine_count + 1)
        if machine_id not in set(unavailable_machines)
    ]
    if working_machines:
        outage_machine = working_machines[-1]
        presets.append(
            ScenarioPreset(
                "machine_outage",
                f"Awaria maszyny {outage_machine}",
                "Sprawdza wynik po wyłączeniu jednej maszyny.",
                ScenarioSpec(f"Awaria M{outage_machine}", {}, (outage_machine,)),
            )
        )
    if operations:
        first = operations[0]
        presets.append(
            ScenarioPreset(
                "component_delay",
                f"Komponenty +4 h ({first.operation_id})",
                "Symuluje opóźnienie dostępności komponentów.",
                ScenarioSpec(
                    "Dostawa +4 h",
                    {first.operation_id: {"components_ready_h": first.components_ready_h + 4.0}},
                ),
            )
        )
        freeze_candidate = next((operation for operation in operations if not operation.predecessors), first)
        presets.append(
            ScenarioPreset(
                "freeze_first",
                f"Zamroź {freeze_candidate.operation_id}",
                "Blokuje wskazaną operację na maszynie 1 od jej najwcześniejszego startu.",
                ScenarioSpec(
                    "Zamrozenie pierwszego kroku",
                    {
                        freeze_candidate.operation_id: {
                            "frozen": True,
                            "fixed_machine_id": 1,
                            "fixed_start_h": freeze_candidate.components_ready_h,
                        }
                    },
                ),
            )
        )
    return tuple(presets)


def compare_queue_scenario(
    snapshot: QueueSnapshot, *, machine_count: int, preset_key: str,
    unavailable_machines: tuple[int, ...] = (),
) -> ScenarioComparison:
    planning_active = refresh_component_readiness(snapshot.active, snapshot.path)
    component_queue = build_component_queue_state(planning_active)
    admitted = set(component_queue.admitted)
    operations = dataframe_to_operations(
        planning_active[planning_active["zlecenie_id"].astype(str).isin(admitted)]
    )
    presets = {
        item.key: item
        for item in build_queue_scenario_presets(
            snapshot,
            machine_count=machine_count,
            unavailable_machines=unavailable_machines,
        )
    }
    if preset_key not in presets:
        raise ValueError(f"Nieznany scenariusz: {preset_key}")
    if preset_key == "baseline":
        return compare_scenarios(
            operations,
            [],
            machine_count=machine_count,
            include_baseline=True,
            baseline_unavailable_machines=unavailable_machines,
        )
    return compare_scenarios(
        operations,
        [presets[preset_key].scenario],
        machine_count=machine_count,
        include_baseline=True,
        baseline_unavailable_machines=unavailable_machines,
    )


def queue_history_summary(path: str | Path, *, limit: int = 20) -> tuple[str, ...]:
    queue_path = Path(path).resolve()
    store = RunStore(queue_path.with_name(f"{queue_path.stem}_runs"), retention=50)
    records = store.list()[: max(1, limit)]
    return tuple(
        f"{record.created_at} | {record.best_method or 'brak wyniku'} | "
        f"{record.objective or 'brak celu'} | {record.run_id}"
        for record in records
    )


def verify_queue_audit(path: str | Path) -> tuple[bool, str]:
    queue_path = Path(path).resolve()
    return AuditLog(queue_path.with_name(f"{queue_path.stem}_audit.jsonl")).verify()


def queue_diagnostics(path: str | Path) -> DiagnosticReport:
    queue_path = Path(path).resolve()
    report = run_diagnostics(data_dir=DATA_DIR, config_dir=CONFIG_DIR, queue_path=queue_path)
    audit_ok, audit_message = verify_queue_audit(queue_path)
    pending = RecoveryJournal(
        queue_path.with_name(f"{queue_path.stem}_recovery")
    ).pending()
    checks = (
        *report.checks,
        DiagnosticCheck("audit_chain", audit_ok, audit_message),
        DiagnosticCheck(
            "pending_recovery",
            not pending,
            "Brak przerwanych zapisow." if not pending else f"Przerwane zapisy: {len(pending)}.",
        ),
    )
    return DiagnosticReport(report.created_at, checks, report.environment)
