from __future__ import annotations

import io
import re
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from AOA.core.component_inventory import (
    READY,
    UNSCHEDULABLE,
    WAITING_COMPONENTS,
    annotate_component_readiness,
)
from AOA.core.history import AuditLog, RunStore
from AOA.core.machine_catalog import MachineSpec
from AOA.core.machine_efficiency import build_machine_efficiency
from AOA.core.mh_models import get_mh_model_names
from AOA.core.monte_carlo import MonteCarloConfig, simulate_schedule_risk
from AOA.core.optimization.objectives import balanced_score, metric_key
from AOA.core.planning import (
    OperationSpec,
    PlanningExplanation,
    PlanningResult,
    WeeklyPlan,
    WeeklyPlanningPolicy,
    apply_weekly_lock,
    dataframe_to_operations,
    explain_plan,
    planning_result_to_dataframe,
    schedule_operations,
)
from AOA.core.queue_machine_config import default_queue_machines
from AOA.core.reliability import BackupManager, RecoveryJournal, RecoveryRecord
from AOA.core.sto_models import (
    OPTIMIZATION_OBJECTIVES,
    dataframe_to_jobs,
    run_selected_sto_models,
)
from AOA.core.storage.base import StorageEntry
from AOA.core.storage.local import LocalStorageProvider
from AOA.settings import load_settings

QUEUE_STATUSES = ("NEW", "PLANNED", "IN_PROGRESS", "DONE", "BLOCKED")
ACTIVE_STATUSES = frozenset({"NEW", "PLANNED", "IN_PROGRESS"})
_ALIASES = {
    "job_id": "zlecenie_id",
    "processing_h": "czas_produkcji_h",
    "due_h": "termin_h",
    "setup_h": "czas_przezbrojenia_h",
    "machine": "dozwolone_maszyny",
}
_REQUIRED_COLUMNS = ("zlecenie_id", "czas_produkcji_h", "termin_h")


@dataclass(frozen=True)
class QueueSnapshot:
    path: Path
    frame: pd.DataFrame
    storage_entry: StorageEntry

    @property
    def active(self) -> pd.DataFrame:
        return self.frame[self.frame["status"].isin(ACTIVE_STATUSES)].copy()

    @property
    def blocked(self) -> pd.DataFrame:
        return self.frame[self.frame["status"] == "BLOCKED"].copy()

    @property
    def done(self) -> pd.DataFrame:
        return self.frame[self.frame["status"] == "DONE"].copy()


@dataclass(frozen=True)
class ComponentQueueState:
    """First queue: component admission before exact operation scheduling."""

    order_frame: pd.DataFrame
    ready_now: tuple[str, ...]
    waiting_components: tuple[str, ...]
    unschedulable: tuple[str, ...]

    @property
    def admitted(self) -> tuple[str, ...]:
        return (*self.ready_now, *self.waiting_components)

    def status_for(self, order_id: object) -> str:
        value = str(order_id)
        if value in self.unschedulable:
            return UNSCHEDULABLE
        if value in self.waiting_components:
            return WAITING_COMPONENTS
        return READY


@dataclass(frozen=True)
class QueueEvaluation:
    snapshot: QueueSnapshot
    results: list[dict]
    selected_methods: tuple[str, ...]
    machine_count: int
    objective: str = "deadline_then_waste"
    unavailable_machines: tuple[int, ...] = ()
    machine_specs: tuple[MachineSpec, ...] = ()
    persistence_warning: str = ""
    component_queue: ComponentQueueState | None = None
    operation_plan: PlanningResult | None = None
    explanation: PlanningExplanation | None = None
    run_id: str = ""
    weekly_plan_id: str = ""
    weekly_plan_version: int = 0
    weekly_status: str = "CONTINUOUS"
    weekly_locked_count: int = 0
    weekly_alerts: tuple[str, ...] = ()
    machine_efficiency: tuple[dict[str, object], ...] = ()
    risk_summary: dict[str, float | int] = dataclass_field(default_factory=dict)

    @property
    def best(self) -> dict | None:
        return self.results[0] if self.results else None


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def _read_frame(data: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Nie mozna odczytac kolejki CSV: {exc}") from exc


def _safe_identifier(value: object, row_number: int) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value).strip()).strip("-")
    return f"Q-{row_number:04d}-{text or 'ORDER'}"


def _clean_text(value: object) -> str:
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return ""
    return str(value).strip()


def normalize_queue_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize legacy/new CSV layouts and isolate malformed rows as BLOCKED."""
    normalized = frame.copy()
    for old, new in _ALIASES.items():
        if new not in normalized.columns and old in normalized.columns:
            normalized = normalized.rename(columns={old: new})

    missing = [column for column in _REQUIRED_COLUMNS if column not in normalized.columns]
    if missing:
        raise ValueError("Brak wymaganych kolumn kolejki: " + ", ".join(missing))

    explicit_operations = "operation_id" in normalized.columns
    if "status" not in normalized.columns:
        normalized["status"] = "NEW"
    if "queue_item_id" not in normalized.columns:
        normalized.insert(0, "queue_item_id", "")
    if "added_at" not in normalized.columns:
        normalized["added_at"] = ""
    if "completed_at" not in normalized.columns:
        normalized["completed_at"] = ""
    if "validation_error" not in normalized.columns:
        normalized["validation_error"] = ""
    if "operation_id" not in normalized.columns:
        normalized["operation_id"] = ""

    normalized = normalized.reset_index(drop=True)
    for index in normalized.index:
        row_number = int(index) + 1
        order_id = _clean_text(normalized.at[index, "zlecenie_id"])
        queue_id = _clean_text(normalized.at[index, "queue_item_id"])
        if not queue_id:
            normalized.at[index, "queue_item_id"] = _safe_identifier(order_id, row_number)
        normalized.at[index, "zlecenie_id"] = order_id
        operation_id = _clean_text(normalized.at[index, "operation_id"])
        if not operation_id:
            normalized.at[index, "operation_id"] = f"{order_id or 'ORDER'}-OP1"
        status = _clean_text(normalized.at[index, "status"]).upper() or "NEW"
        normalized.at[index, "status"] = status

    duplicate_queue_ids = normalized["queue_item_id"].duplicated(keep=False)
    duplicate_order_ids = normalized["zlecenie_id"].duplicated(keep=False)
    duplicate_operation_ids = normalized["operation_id"].duplicated(keep=False)
    for index in normalized.index:
        errors: list[str] = []
        order_id = _clean_text(normalized.at[index, "zlecenie_id"])
        status = str(normalized.at[index, "status"])
        if not order_id:
            errors.append("brak zlecenie_id")
        if status not in QUEUE_STATUSES:
            errors.append(f"nieznany status: {status}")
        for column in ("czas_produkcji_h", "termin_h"):
            try:
                value = float(str(normalized.at[index, column]).replace(",", "."))
            except ValueError:
                errors.append(f"{column} nie jest liczba")
                continue
            if value <= 0:
                errors.append(f"{column} musi byc dodatnie")
            normalized.at[index, column] = value
        if bool(duplicate_queue_ids.at[index]):
            errors.append("powtorzony queue_item_id")
        if bool(duplicate_operation_ids.at[index]):
            errors.append("powtorzony operation_id")
        if not explicit_operations and order_id and bool(duplicate_order_ids.at[index]):
            errors.append("powtorzony zlecenie_id")
        if errors:
            normalized.at[index, "status"] = "BLOCKED"
            normalized.at[index, "validation_error"] = "; ".join(errors)

    return normalized


def load_queue_snapshot(path: str | Path) -> QueueSnapshot:
    queue_path = Path(path).resolve()
    provider = LocalStorageProvider(queue_path.parent)
    data, entry = provider.read_bytes(queue_path.name)
    return QueueSnapshot(queue_path, normalize_queue_frame(_read_frame(data)), entry)


def refresh_component_readiness(active: pd.DataFrame, queue_path: str | Path) -> pd.DataFrame:
    """Recheck sibling BOM/inventory once per order and copy the result to operations."""

    queue_path = Path(queue_path).resolve()
    bom_path = queue_path.with_name("bom.csv")
    inventory_path = queue_path.with_name("inventory.csv")
    if bom_path.exists() != inventory_path.exists():
        raise ValueError("Pierwsza kolejka wymaga obu plikow: bom.csv i inventory.csv.")
    if not bom_path.is_file() or not inventory_path.is_file():
        return active.copy()
    required = {"zlecenie_id", "produkt_id", "ilosc_szt"}
    if not required.issubset(active.columns):
        return active.copy()

    order_rows: list[pd.Series] = []
    for order_id, group in active.groupby("zlecenie_id", sort=False):
        products = {_clean_text(value) for value in group["produkt_id"]}
        quantities = {_clean_text(value).replace(",", ".") for value in group["ilosc_szt"]}
        if len(products) != 1 or len(quantities) != 1:
            raise ValueError(
                f"Zlecenie {order_id} ma niespojne produkt_id lub ilosc_szt miedzy operacjami."
            )
        order_rows.append(group.iloc[0].copy())
    orders = pd.DataFrame(order_rows)
    orders = (
        orders.assign(_due_sort=pd.to_numeric(orders["termin_h"], errors="coerce"))
        .sort_values(["_due_sort", "zlecenie_id"], kind="stable")
        .drop(columns=["_due_sort"])
    )
    provider = LocalStorageProvider(queue_path.parent)
    bom_data, _ = provider.read_bytes(bom_path.name)
    inventory_data, _ = provider.read_bytes(inventory_path.name)
    annotated = annotate_component_readiness(
        orders,
        _read_frame(bom_data),
        _read_frame(inventory_data),
    )
    fields = (
        "components_ready_h",
        "material_wait_h",
        "missing_components",
        "stock_status",
        "stock_reservation",
    )
    values_by_order = {
        str(row["zlecenie_id"]): {field: row[field] for field in fields}
        for _, row in annotated.iterrows()
    }
    out = active.copy()
    for index, row in out.iterrows():
        values = values_by_order[str(row["zlecenie_id"])]
        for field, value in values.items():
            out.at[index, field] = value
    return out


def evaluate_queue(
    snapshot: QueueSnapshot,
    selected_methods: list[str] | tuple[str, ...] | None = None,
    n_machines: int = 1,
    objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
    weekly_policy: WeeklyPlanningPolicy | None = None,
    weekly_plan: WeeklyPlan | None = None,
    now: datetime | None = None,
    machine_specs: tuple[MachineSpec, ...] | list[MachineSpec] | None = None,
) -> QueueEvaluation:
    if n_machines < 1 or n_machines > 8:
        raise ValueError("Liczba maszyn musi miescic sie w zakresie 1-8.")
    if objective not in OPTIMIZATION_OBJECTIVES:
        raise ValueError(f"Nieznany cel optymalizacji: {objective}")
    unavailable = tuple(sorted(set(unavailable_machines)))
    configured_machines = tuple(machine_specs or ())
    if configured_machines and len(configured_machines) != n_machines:
        raise ValueError("Liczba profili maszyn nie zgadza sie z liczba maszyn Auto Queue.")
    invalid_unavailable = [
        machine_id for machine_id in unavailable if machine_id < 1 or machine_id > n_machines
    ]
    if invalid_unavailable:
        raise ValueError(
            "Niedostepne maszyny sa poza zakresem: " + ", ".join(map(str, invalid_unavailable))
        )
    methods = tuple(sorted(get_mh_model_names()) if selected_methods is None else selected_methods)
    weekly_status = "CONTINUOUS"
    weekly_alerts: tuple[str, ...] = ()
    weekly_locked_count = 0
    weekly_plan_id = ""
    weekly_plan_version = 0
    if weekly_policy is not None:
        weekly_status = "MISSING"
        if weekly_plan is None:
            weekly_alerts = (
                "Brak zatwierdzonego planu aktywnego tygodnia; nic nie zostalo zamrozone.",
            )
        else:
            weekly_plan_id = weekly_plan.plan_id
            weekly_plan_version = weekly_plan.version
            weekly_status = weekly_plan.effective_status(now, policy=weekly_policy)
            if weekly_status != "ACTIVE":
                weekly_alerts = (
                    f"Plan {weekly_plan.plan_id} nie jest aktywny; nic nie zostalo zamrozone.",
                )
    active = snapshot.active
    if active.empty:
        evaluation = QueueEvaluation(
            snapshot=snapshot,
            results=[],
            selected_methods=methods,
            machine_count=n_machines,
            objective=objective,
            unavailable_machines=unavailable,
            machine_specs=configured_machines,
            component_queue=ComponentQueueState(pd.DataFrame(), (), (), ()),
            weekly_plan_id=weekly_plan_id,
            weekly_plan_version=weekly_plan_version,
            weekly_status=weekly_status,
            weekly_alerts=weekly_alerts,
        )
        return _persist_evaluation_safely(evaluation)

    planning_active = refresh_component_readiness(active, snapshot.path)
    component_queue = build_component_queue_state(planning_active)
    locked_order_ids: set[str] = set()
    if weekly_policy is not None and weekly_plan is not None and weekly_status == "ACTIVE":
        planning_active, lock_alerts, weekly_locked_count = apply_weekly_lock(
            planning_active,
            weekly_plan,
            weekly_policy,
            unavailable_machines=unavailable,
        )
        weekly_alerts = (*weekly_alerts, *lock_alerts)
        locked_order_ids = {item.order_id for item in weekly_plan.items}
    admitted_ids = set(component_queue.admitted) | locked_order_ids
    admitted_operations = planning_active[
        planning_active["zlecenie_id"].astype(str).isin(admitted_ids)
    ].copy()
    order_frame = component_queue.order_frame[
        component_queue.order_frame["zlecenie_id"].astype(str).isin(admitted_ids)
    ].copy()
    if order_frame.empty:
        operation_plan = schedule_operations(
            [],
            machine_count=n_machines,
            unavailable_machines=unavailable,
            machine_specs=configured_machines or None,
        )
        evaluation = QueueEvaluation(
            snapshot=snapshot,
            results=[],
            selected_methods=methods,
            machine_count=n_machines,
            objective=objective,
            unavailable_machines=unavailable,
            machine_specs=configured_machines,
            component_queue=component_queue,
            operation_plan=operation_plan,
            explanation=explain_plan(operation_plan, []),
            weekly_plan_id=weekly_plan_id,
            weekly_plan_version=weekly_plan_version,
            weekly_status=weekly_status,
            weekly_locked_count=weekly_locked_count,
            weekly_alerts=weekly_alerts,
        )
        return _persist_evaluation_safely(evaluation)

    jobs = dataframe_to_jobs(order_frame, job_id_col="zlecenie_id")
    results = run_selected_sto_models(
        jobs,
        list(methods),
        n_machines=n_machines,
        objective=objective,
        unavailable_machines=unavailable,
        machine_specs=configured_machines or None,
    )
    operations_by_method: dict[str, tuple[list[OperationSpec], PlanningResult]] = {}
    operation_order_by_id = {
        str(row.get("operation_id", "")): str(row.get("zlecenie_id", ""))
        for _, row in admitted_operations.iterrows()
    }
    component_blocked = set(component_queue.unschedulable)
    for result in results:
        priorities = {
            order_id: len(result["order"]) - index for index, order_id in enumerate(result["order"])
        }
        operations = dataframe_to_operations(admitted_operations, order_priorities=priorities)
        plan = schedule_operations(
            operations,
            machine_count=n_machines,
            unavailable_machines=unavailable,
            machine_specs=configured_machines or None,
        )
        machine_blocked = {
            operation_order_by_id.get(operation_id, operation_id)
            for operation_id in plan.unscheduled
        }
        result["sto"] = plan.total_tardiness_h
        result["completion_total"] = plan.makespan_h
        result["makespan_h"] = plan.makespan_h
        result["total_waste_kg"] = plan.total_waste_kg
        result["total_energy_kwh"] = plan.total_energy_kwh
        result["unscheduled_count"] = len(component_blocked | machine_blocked)
        result["component_blocked_count"] = len(component_blocked)
        result["machine_blocked_count"] = len(machine_blocked)
        operations_by_method[str(result["method"])] = (operations, plan)

    results.sort(key=lambda item: (*metric_key(item, jobs, objective), item["method"]))
    if results:
        reference_score = balanced_score(results[0], jobs)
        for index, result in enumerate(results):
            result["optimality_status"] = "BEST_KNOWN" if index == 0 else "CANDIDATE"
            score = balanced_score(result, jobs)
            result["optimality_gap_pct"] = round(
                max(0.0, score - reference_score) / max(abs(reference_score), 1e-9) * 100,
                3,
            )

    best = results[0] if results else None
    if best is None:
        best_operations: list[OperationSpec] = []
        operation_plan = schedule_operations(
            best_operations,
            machine_count=n_machines,
            unavailable_machines=unavailable,
            machine_specs=configured_machines or None,
        )
    else:
        best_operations, operation_plan = operations_by_method[str(best["method"])]
    explanation = explain_plan(operation_plan, best_operations)
    machine_efficiency, risk_summary = _queue_machine_outcomes(
        operation_plan,
        best_operations,
        configured_machines or default_queue_machines(n_machines),
    )
    evaluation = QueueEvaluation(
        snapshot=snapshot,
        results=results,
        selected_methods=methods,
        machine_count=n_machines,
        objective=objective,
        unavailable_machines=unavailable,
        machine_specs=configured_machines,
        component_queue=component_queue,
        operation_plan=operation_plan,
        explanation=explanation,
        weekly_plan_id=weekly_plan_id,
        weekly_plan_version=weekly_plan_version,
        weekly_status=weekly_status,
        weekly_locked_count=weekly_locked_count,
        weekly_alerts=weekly_alerts,
        machine_efficiency=machine_efficiency,
        risk_summary=risk_summary,
    )
    return _persist_evaluation_safely(evaluation)


def _queue_machine_outcomes(
    plan: PlanningResult,
    operations: list[OperationSpec],
    machines: tuple[MachineSpec, ...] | list[MachineSpec],
) -> tuple[tuple[dict[str, object], ...], dict[str, float | int]]:
    if not plan.steps:
        return (), {}
    operation_by_id = {operation.operation_id: operation for operation in operations}
    risk_machines = tuple(
        MachineSpec(
            machine_id=str(index),
            name=machine.name,
            station_id="QUEUE",
            speed_factor=machine.speed_factor,
            waste_factor=machine.waste_factor,
            energy_kwh_per_hour=machine.energy_kwh_per_hour,
            cost_per_hour=machine.cost_per_hour,
            setup_time_h=machine.setup_time_h,
            planned_hours_h=machine.planned_hours_h,
            capability=machine.capability,
            reliability=machine.reliability,
        ).normalized(index)
        for index, machine in enumerate(machines, 1)
    )
    event_rows: list[dict[str, object]] = []
    for step in plan.steps:
        operation = operation_by_id[step.operation_id]
        setup_h = min(operation.setup_time_h, max(0.0, step.end_h - step.start_h))
        productive_h = max(0.0, step.end_h - step.start_h - setup_h)
        machine = risk_machines[step.machine_id - 1]
        event_rows.append(
            {
                "sto_job_id": step.order_id,
                "operation_id": step.operation_id,
                "station_id": operation.station_type or "QUEUE",
                "machine_id": str(step.machine_id),
                "machine_name": machine.name,
                "setup_start": step.start_h,
                "setup_h": setup_h,
                "t_start": step.start_h + setup_h,
                "t_end": step.end_h,
                "czas_produkcji_h": productive_h,
                "base_duration_h": operation.processing_time_h,
                "termin_h": step.deadline_h,
                "lateness_h": step.tardiness_h,
                "quality": 1.0,
                "cost": (productive_h + setup_h) * machine.cost_per_hour,
                "waste": operation.waste_kg * machine.waste_factor,
                "energy_kwh": (
                    operation.energy_kwh
                    if machine.energy_kwh_per_hour <= 0
                    else productive_h * machine.energy_kwh_per_hour
                ),
            }
        )
    events = pd.DataFrame(event_rows)
    risk = simulate_schedule_risk(events, risk_machines, MonteCarloConfig())
    efficiency = build_machine_efficiency(events, risk_machines, risk)
    records = tuple(
        {str(key): value for key, value in record.items()}
        for record in efficiency.to_dict("records")
    )
    return records, risk.summary


def _aggregate_orders_for_heuristics(active: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    sum_columns = (
        "czas_produkcji_h",
        "czas_przezbrojenia_h",
        "odpad_kg",
        "odpad_przezbrojenia_kg",
        "energia_kwh",
    )
    for _order_id, group in active.groupby("zlecenie_id", sort=False):
        row = group.iloc[0].copy()
        for column in sum_columns:
            if column in group.columns:
                row[column] = pd.to_numeric(group[column], errors="coerce").fillna(0).sum()
        row["termin_h"] = pd.to_numeric(group["termin_h"], errors="coerce").min()
        if "components_ready_h" in group.columns:
            row["components_ready_h"] = (
                pd.to_numeric(group["components_ready_h"], errors="coerce").fillna(0).max()
            )
        if "material_wait_h" in group.columns:
            row["material_wait_h"] = (
                pd.to_numeric(group["material_wait_h"], errors="coerce").fillna(0).max()
            )
        statuses = {
            _clean_text(value).upper() or READY
            for value in group.get("stock_status", pd.Series([READY]))
        }
        if "missing_components" in group.columns:
            missing = sorted(
                {_clean_text(value) for value in group["missing_components"] if _clean_text(value)}
            )
            row["missing_components"] = "|".join(missing)
        if UNSCHEDULABLE in statuses or _clean_text(row.get("missing_components", "")):
            row["stock_status"] = UNSCHEDULABLE
        elif WAITING_COMPONENTS in statuses or float(row.get("components_ready_h", 0) or 0) > 0:
            row["stock_status"] = WAITING_COMPONENTS
        else:
            row["stock_status"] = READY
        row["dozwolone_maszyny"] = ""
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def build_component_queue_state(active: pd.DataFrame) -> ComponentQueueState:
    order_frame = _aggregate_orders_for_heuristics(active)
    ready_values = pd.to_numeric(
        order_frame.get("components_ready_h", pd.Series(0, index=order_frame.index)),
        errors="coerce",
    ).fillna(float("inf"))
    status_rank = (
        order_frame.get("stock_status", pd.Series(READY, index=order_frame.index))
        .map({READY: 0, WAITING_COMPONENTS: 1, UNSCHEDULABLE: 2})
        .fillna(2)
    )
    deadline_values = pd.to_numeric(order_frame["termin_h"], errors="coerce")
    order_frame = (
        order_frame.assign(
            _component_status_rank=status_rank,
            _component_ready_sort=ready_values,
            _component_deadline_sort=deadline_values,
        )
        .sort_values(
            [
                "_component_status_rank",
                "_component_ready_sort",
                "_component_deadline_sort",
                "zlecenie_id",
            ],
            kind="stable",
        )
        .drop(
            columns=[
                "_component_status_rank",
                "_component_ready_sort",
                "_component_deadline_sort",
            ]
        )
        .reset_index(drop=True)
    )
    ready_now: list[str] = []
    waiting: list[str] = []
    unschedulable: list[str] = []
    for index, row in order_frame.iterrows():
        order_id = str(row["zlecenie_id"])
        status = _clean_text(row.get("stock_status", READY)).upper() or READY
        ready_h = pd.to_numeric(
            pd.Series([row.get("components_ready_h", 0)]), errors="coerce"
        ).iloc[0]
        if status == UNSCHEDULABLE:
            unschedulable.append(order_id)
        elif status == WAITING_COMPONENTS or (not pd.isna(ready_h) and float(ready_h) > 0):
            waiting.append(order_id)
            order_frame.at[index, "stock_status"] = WAITING_COMPONENTS
        else:
            ready_now.append(order_id)
            order_frame.at[index, "stock_status"] = READY
    return ComponentQueueState(
        order_frame,
        tuple(ready_now),
        tuple(waiting),
        tuple(unschedulable),
    )


def result_cache_paths(path: str | Path) -> tuple[Path, Path]:
    queue_path = Path(path).resolve()
    return (
        queue_path.with_name(f"{queue_path.stem}_model_results_latest.csv"),
        queue_path.with_name(f"{queue_path.stem}_schedule_latest.csv"),
    )


def save_latest_queue_results(evaluation: QueueEvaluation) -> tuple[Path, Path]:
    ranking_path, schedule_path = result_cache_paths(evaluation.snapshot.path)
    provider = LocalStorageProvider(evaluation.snapshot.path.parent)
    updated_at = datetime.now(UTC).isoformat()
    ranking, schedule = _evaluation_frames(evaluation, updated_at)
    provider.write_bytes(ranking_path.name, _csv_bytes(ranking))
    provider.write_bytes(schedule_path.name, _csv_bytes(schedule))
    return ranking_path, schedule_path


def _evaluation_frames(
    evaluation: QueueEvaluation, updated_at: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranking_rows = [
        {
            "method": result["method"],
            "objective": evaluation.objective,
            "optimality_status": result.get("optimality_status", ""),
            "optimality_gap_pct": result.get("optimality_gap_pct", 0.0),
            "sto": result["sto"],
            "makespan_h": result["makespan_h"],
            "total_waste_kg": result["total_waste_kg"],
            "total_energy_kwh": result["total_energy_kwh"],
            "unscheduled_count": result["unscheduled_count"],
            "component_blocked_count": result.get("component_blocked_count", 0),
            "machine_blocked_count": result.get("machine_blocked_count", 0),
            "ready_now_count": (
                len(evaluation.component_queue.ready_now)
                if evaluation.component_queue is not None
                else 0
            ),
            "waiting_components_count": (
                len(evaluation.component_queue.waiting_components)
                if evaluation.component_queue is not None
                else 0
            ),
            "unavailable_machines": "|".join(map(str, evaluation.unavailable_machines)),
            "risk_mean_makespan_h": result.get("risk_summary", {}).get(
                "mean_makespan_h", ""
            ),
            "risk_p90_makespan_h": result.get("risk_summary", {}).get(
                "p90_makespan_h", ""
            ),
            "risk_mean_downtime_h": result.get("risk_summary", {}).get(
                "mean_downtime_h", ""
            ),
            "order": "|".join(result["order"]),
            "updated_at": updated_at,
        }
        for result in evaluation.results
    ]
    ranking_columns = [
        "method",
        "objective",
        "optimality_status",
        "optimality_gap_pct",
        "sto",
        "makespan_h",
        "total_waste_kg",
        "total_energy_kwh",
        "unscheduled_count",
        "component_blocked_count",
        "machine_blocked_count",
        "ready_now_count",
        "waiting_components_count",
        "unavailable_machines",
        "risk_mean_makespan_h",
        "risk_p90_makespan_h",
        "risk_mean_downtime_h",
        "order",
        "updated_at",
    ]
    ranking = pd.DataFrame(ranking_rows, columns=ranking_columns)
    best = evaluation.best
    if evaluation.operation_plan is not None:
        schedule = planning_result_to_dataframe(evaluation.operation_plan)
        if not schedule.empty:
            schedule.insert(0, "model", best["method"] if best else "OPERATIONS")
            schedule.insert(1, "objective", evaluation.objective)
            schedule["optimality_status"] = best.get("optimality_status", "") if best else ""
            schedule["unavailable_machines"] = "|".join(map(str, evaluation.unavailable_machines))
            schedule["updated_at"] = updated_at
        return ranking, schedule
    schedule_columns = [
        "lp",
        "job_id",
        "processing_time",
        "deadline",
        "machine_id",
        "setup_time",
        "start_time",
        "completion_time",
        "lateness",
        "tardiness_positive",
        "waste_kg",
        "energy_kwh",
        "components_ready_h",
        "material_wait_h",
        "missing_components",
        "stock_status",
        "stock_reservation",
        "unscheduled_reason",
        "scheduled",
        "sto_running",
    ]
    schedule = pd.DataFrame(best["steps"] if best else [], columns=schedule_columns)
    if best is not None:
        schedule.insert(0, "model", best["method"])
        schedule.insert(1, "objective", evaluation.objective)
        schedule["optimality_status"] = best.get("optimality_status", "")
        schedule["unavailable_machines"] = "|".join(map(str, evaluation.unavailable_machines))
        schedule["updated_at"] = updated_at
    return ranking, schedule


def load_latest_queue_results(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranking_path, schedule_path = result_cache_paths(path)
    provider = LocalStorageProvider(ranking_path.parent)
    ranking_data, _ = provider.read_bytes(ranking_path.name)
    schedule_data, _ = provider.read_bytes(schedule_path.name)
    return _read_frame(ranking_data), _read_frame(schedule_data)


def _persist_evaluation_safely(evaluation: QueueEvaluation) -> QueueEvaluation:
    try:
        save_latest_queue_results(evaluation)
        updated_at = datetime.now(UTC).isoformat()
        ranking, schedule = _evaluation_frames(evaluation, updated_at)
        store = RunStore(
            evaluation.snapshot.path.with_name(f"{evaluation.snapshot.path.stem}_runs"),
            retention=max(1, load_settings().history_retention),
        )
        record = store.record(
            input_frame=evaluation.snapshot.frame,
            settings={
                "objective": evaluation.objective,
                "selected_methods": list(evaluation.selected_methods),
                "machine_count": evaluation.machine_count,
                "unavailable_machines": list(evaluation.unavailable_machines),
                "weekly_status": evaluation.weekly_status,
                "weekly_plan_id": evaluation.weekly_plan_id,
                "weekly_plan_version": evaluation.weekly_plan_version,
                "weekly_locked_count": evaluation.weekly_locked_count,
                "weekly_alerts": list(evaluation.weekly_alerts),
                "component_ready_now": (
                    len(evaluation.component_queue.ready_now)
                    if evaluation.component_queue is not None
                    else 0
                ),
                "component_waiting": (
                    len(evaluation.component_queue.waiting_components)
                    if evaluation.component_queue is not None
                    else 0
                ),
                "component_blocked": (
                    len(evaluation.component_queue.unschedulable)
                    if evaluation.component_queue is not None
                    else 0
                ),
            },
            ranking=ranking,
            schedule=schedule,
            source_path=evaluation.snapshot.path,
            events=[{"action": "QUEUE_EVALUATED", "at": updated_at}],
        )
        AuditLog(
            evaluation.snapshot.path.with_name(f"{evaluation.snapshot.path.stem}_audit.jsonl")
        ).append(
            "QUEUE_EVALUATED",
            evaluation.snapshot.path.name,
            {
                "run_id": record.run_id,
                "active": len(evaluation.snapshot.active),
                "objective": evaluation.objective,
                "unavailable_machines": list(evaluation.unavailable_machines),
                "weekly_status": evaluation.weekly_status,
                "weekly_plan_id": evaluation.weekly_plan_id,
                "weekly_plan_version": evaluation.weekly_plan_version,
                "weekly_locked_count": evaluation.weekly_locked_count,
                "weekly_alerts": list(evaluation.weekly_alerts),
            },
        )
        return replace(evaluation, run_id=record.run_id)
    except Exception as exc:
        return replace(
            evaluation,
            persistence_warning=f"Nie zapisano pelnej historii wynikow: {exc}",
        )


def mark_queue_item_done(path: str | Path, queue_item_id: str) -> QueueSnapshot:
    snapshot = load_queue_snapshot(path)
    matches = snapshot.frame["queue_item_id"].astype(str) == str(queue_item_id)
    if int(matches.sum()) != 1:
        raise ValueError("Nie znaleziono jednoznacznej pozycji kolejki.")
    frame = snapshot.frame.copy()
    frame.loc[matches, "status"] = "DONE"
    frame.loc[matches, "completed_at"] = datetime.now(UTC).isoformat()
    frame.loc[matches, "validation_error"] = ""
    provider = LocalStorageProvider(snapshot.path.parent)
    backup = BackupManager(
        snapshot.path.with_name(f"{snapshot.path.stem}_backups"),
        retention_per_file=max(1, load_settings().backup_retention),
    ).create(snapshot.path)
    journal, transaction = _begin_recovery(snapshot.path, backup.backup, "QUEUE_ITEM_DONE")
    provider.write_bytes(
        snapshot.path.name,
        _csv_bytes(frame),
        expected_version=snapshot.storage_entry.version,
    )
    journal.commit(transaction.transaction_id)
    AuditLog(snapshot.path.with_name(f"{snapshot.path.stem}_audit.jsonl")).append(
        "QUEUE_ITEM_DONE", queue_item_id, {"path": snapshot.path.name}
    )
    return load_queue_snapshot(snapshot.path)


def archive_completed_orders(path: str | Path, archive_path: str | Path | None = None) -> int:
    """Append DONE rows to an archive, then remove them from the active queue.

    The archive is written first. A retry is safe because queue_item_id is deduplicated.
    """
    snapshot = load_queue_snapshot(path)
    completed = snapshot.done
    if completed.empty:
        return 0

    target = (
        Path(archive_path).resolve()
        if archive_path is not None
        else snapshot.path.with_name(f"{snapshot.path.stem}_archive.csv")
    )
    if target.parent != snapshot.path.parent:
        raise ValueError("Archiwum kolejki musi znajdowac sie w tym samym katalogu.")
    provider = LocalStorageProvider(snapshot.path.parent)
    backup_manager = BackupManager(
        snapshot.path.with_name(f"{snapshot.path.stem}_backups"),
        retention_per_file=max(1, load_settings().backup_retention),
    )
    backup_manager.create(snapshot.path)
    queue_backup = backup_manager.list(snapshot.path.name)[0]
    journal, transaction = _begin_recovery(snapshot.path, queue_backup, "QUEUE_ARCHIVE")
    if target.is_file():
        backup_manager.create(target)
    archive_version: str | None = None
    try:
        archive_data, archive_entry = provider.read_bytes(target.name)
        archive = normalize_queue_frame(_read_frame(archive_data))
        archive_version = archive_entry.version
    except FileNotFoundError:
        archive = pd.DataFrame(columns=snapshot.frame.columns)

    combined = pd.concat([archive, completed], ignore_index=True)
    combined = combined.drop_duplicates(subset=["queue_item_id"], keep="last")
    provider.write_bytes(target.name, _csv_bytes(combined), expected_version=archive_version)
    active = snapshot.frame[snapshot.frame["status"] != "DONE"].copy()
    provider.write_bytes(
        snapshot.path.name,
        _csv_bytes(active),
        expected_version=snapshot.storage_entry.version,
    )
    journal.commit(transaction.transaction_id)
    AuditLog(snapshot.path.with_name(f"{snapshot.path.stem}_audit.jsonl")).append(
        "QUEUE_ARCHIVED", target.name, {"count": len(completed)}
    )
    return len(completed)


def append_queue_orders(path: str | Path, orders: pd.DataFrame) -> QueueSnapshot:
    snapshot = load_queue_snapshot(path)
    combined = pd.concat([snapshot.frame, orders], ignore_index=True)
    normalized = normalize_queue_frame(combined)
    provider = LocalStorageProvider(snapshot.path.parent)
    backup = BackupManager(
        snapshot.path.with_name(f"{snapshot.path.stem}_backups"),
        retention_per_file=max(1, load_settings().backup_retention),
    ).create(snapshot.path)
    journal, transaction = _begin_recovery(snapshot.path, backup.backup, "QUEUE_APPEND")
    provider.write_bytes(
        snapshot.path.name,
        _csv_bytes(normalized),
        expected_version=snapshot.storage_entry.version,
    )
    journal.commit(transaction.transaction_id)
    AuditLog(snapshot.path.with_name(f"{snapshot.path.stem}_audit.jsonl")).append(
        "QUEUE_ORDERS_APPENDED", snapshot.path.name, {"count": len(orders)}
    )
    return load_queue_snapshot(snapshot.path)


def _begin_recovery(
    target: Path, backup: Path, action: str
) -> tuple[RecoveryJournal, RecoveryRecord]:
    journal = RecoveryJournal(target.with_name(f"{target.stem}_recovery"))
    return journal, journal.begin(target=target, backup=backup, action=action)
