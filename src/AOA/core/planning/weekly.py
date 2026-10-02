from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

from AOA.core.history import AuditLog
from AOA.core.storage.local import LocalStorageProvider

from .models import PlanningResult

WEEKLY_PLAN_SCHEMA_VERSION = 1


class WeeklyPlanStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


@dataclass(frozen=True)
class WeeklyPlanningPolicy:
    timezone: str = "Europe/Warsaw"
    week_start_weekday: int = 0
    week_start_hour: int = 6
    workdays: int = 5
    workday_hours: float = 8.0

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Nieznana strefa czasowa: {self.timezone}") from exc
        if self.week_start_weekday < 0 or self.week_start_weekday > 6:
            raise ValueError("Dzien rozpoczecia tygodnia musi miescic sie w zakresie 0-6.")
        if self.week_start_hour < 0 or self.week_start_hour > 23:
            raise ValueError("Godzina rozpoczecia tygodnia musi miescic sie w zakresie 0-23.")
        if self.workdays < 1 or self.workdays > 7:
            raise ValueError("Liczba dni roboczych musi miescic sie w zakresie 1-7.")
        if self.workday_hours <= 0 or self.workday_hours > 24:
            raise ValueError("Dzien roboczy musi miec od 0 do 24 godzin.")

    @property
    def horizon_hours(self) -> float:
        return round(self.workdays * self.workday_hours, 3)

    def localize(self, moment: datetime | None = None) -> datetime:
        zone = ZoneInfo(self.timezone)
        value = moment or datetime.now(UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=zone)
        return value.astimezone(zone)

    def week_start(self, moment: datetime | None = None) -> datetime:
        local = self.localize(moment)
        days_back = (local.weekday() - self.week_start_weekday) % 7
        candidate_date = (local - timedelta(days=days_back)).date()
        candidate = datetime(
            candidate_date.year,
            candidate_date.month,
            candidate_date.day,
            self.week_start_hour,
            tzinfo=ZoneInfo(self.timezone),
        )
        if local < candidate:
            candidate_date -= timedelta(days=7)
            candidate = datetime(
                candidate_date.year,
                candidate_date.month,
                candidate_date.day,
                self.week_start_hour,
                tzinfo=ZoneInfo(self.timezone),
            )
        return candidate

    def next_week_start(self, moment: datetime | None = None) -> datetime:
        start_date = self.week_start(moment).date() + timedelta(days=7)
        return datetime(
            start_date.year,
            start_date.month,
            start_date.day,
            self.week_start_hour,
            tzinfo=ZoneInfo(self.timezone),
        )

    def week_end(self, week_start: datetime) -> datetime:
        local_start = self.localize(week_start)
        end_date = local_start.date() + timedelta(days=7)
        return datetime(
            end_date.year,
            end_date.month,
            end_date.day,
            self.week_start_hour,
            tzinfo=ZoneInfo(self.timezone),
        )

    def week_id(self, week_start: datetime) -> str:
        local_start = self.localize(week_start)
        year, week, _weekday = local_start.isocalendar()
        return f"{year}-W{week:02d}"

    def elapsed_work_hours(self, moment: datetime, *, week_start: datetime | None = None) -> float:
        local = self.localize(moment)
        start = self.localize(week_start) if week_start is not None else self.week_start(local)
        if local <= start:
            return 0.0
        elapsed = 0.0
        for day_offset in range(self.workdays):
            day_start_date = start.date() + timedelta(days=day_offset)
            day_start = datetime(
                day_start_date.year,
                day_start_date.month,
                day_start_date.day,
                self.week_start_hour,
                tzinfo=ZoneInfo(self.timezone),
            )
            day_end = day_start + timedelta(hours=self.workday_hours)
            if local >= day_end:
                elapsed += self.workday_hours
            elif local > day_start:
                elapsed += (local - day_start).total_seconds() / 3600.0
                break
            else:
                break
        return round(min(self.horizon_hours, elapsed), 3)


@dataclass(frozen=True)
class WeeklyPlanItem:
    operation_id: str
    order_id: str
    machine_id: int
    start_h: float
    end_h: float


@dataclass(frozen=True)
class WeeklyPlan:
    plan_id: str
    version: int
    status: WeeklyPlanStatus
    target_week_start: str
    target_week_end: str
    created_at: str
    approved_at: str
    source_run_id: str
    source_queue_hash: str
    emergency_reason: str
    items: tuple[WeeklyPlanItem, ...]

    @property
    def week_start(self) -> datetime:
        return datetime.fromisoformat(self.target_week_start)

    @property
    def week_end(self) -> datetime:
        return datetime.fromisoformat(self.target_week_end)

    def effective_status(
        self, now: datetime | None = None, *, policy: WeeklyPlanningPolicy | None = None
    ) -> str:
        planning_policy = policy or WeeklyPlanningPolicy()
        local_now = planning_policy.localize(now)
        if self.status == WeeklyPlanStatus.DRAFT:
            return WeeklyPlanStatus.DRAFT.value
        if local_now < self.week_start:
            return WeeklyPlanStatus.APPROVED.value
        if local_now < self.week_end:
            return "ACTIVE"
        return "CLOSED"


def queue_plan_key(queue_path: str | Path) -> str:
    canonical = str(Path(queue_path).resolve()).replace("\\", "/").casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _serialize_plan(plan: WeeklyPlan) -> bytes:
    payload = asdict(plan)
    payload["schema_version"] = WEEKLY_PLAN_SCHEMA_VERSION
    payload["status"] = plan.status.value
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def _deserialize_plan(data: bytes) -> WeeklyPlan:
    payload = json.loads(data.decode("utf-8"))
    schema_version = int(payload.pop("schema_version", 0))
    if schema_version > WEEKLY_PLAN_SCHEMA_VERSION:
        raise ValueError("Plan tygodniowy ma nowszy, nieobslugiwany format.")
    if schema_version < 1:
        raise ValueError("Plan tygodniowy nie ma obslugiwanej wersji formatu.")
    payload["status"] = WeeklyPlanStatus(payload["status"])
    payload["items"] = tuple(WeeklyPlanItem(**item) for item in payload.get("items", []))
    return WeeklyPlan(**payload)


class WeeklyPlanStore:
    """Versioned weekly plans for one queue, written atomically."""

    SCHEMA_VERSION = WEEKLY_PLAN_SCHEMA_VERSION

    def __init__(self, root: str | Path, queue_path: str | Path) -> None:
        self.queue_path = Path(queue_path).resolve()
        self.queue_key = queue_plan_key(self.queue_path)
        self.root = Path(root).resolve() / self.queue_key
        self.provider = LocalStorageProvider(self.root)
        self.audit = AuditLog(self.root / "weekly_audit.jsonl")

    @staticmethod
    def _version_key(plan_id: str, version: int) -> str:
        return f"{plan_id}/v{version:04d}.json"

    def list_versions(self, plan_id: str) -> tuple[WeeklyPlan, ...]:
        plans: list[WeeklyPlan] = []
        for entry in self.provider.list(plan_id):
            if entry.key.endswith(".json"):
                data, _stored = self.provider.read_bytes(entry.key)
                plans.append(_deserialize_plan(data))
        return tuple(sorted(plans, key=lambda plan: plan.version))

    def latest(self, plan_id: str) -> WeeklyPlan | None:
        versions = self.list_versions(plan_id)
        return versions[-1] if versions else None

    def plan_for_week(
        self, week_start: datetime, policy: WeeklyPlanningPolicy
    ) -> WeeklyPlan | None:
        return self.latest(policy.week_id(week_start))

    def current_plan(
        self, policy: WeeklyPlanningPolicy, now: datetime | None = None
    ) -> WeeklyPlan | None:
        plan = self.plan_for_week(policy.week_start(now), policy)
        if plan is None or plan.status != WeeklyPlanStatus.APPROVED:
            return None
        return plan

    def upcoming_plan(
        self, policy: WeeklyPlanningPolicy, now: datetime | None = None
    ) -> WeeklyPlan | None:
        return self.plan_for_week(policy.next_week_start(now), policy)

    def create_draft(
        self,
        *,
        target_week_start: datetime,
        policy: WeeklyPlanningPolicy,
        result: PlanningResult,
        source_queue_hash: str,
        source_run_id: str = "",
        start_offset_h: float = 0.0,
        exclude_frozen: bool = False,
        now: datetime | None = None,
    ) -> WeeklyPlan:
        plan_id = policy.week_id(target_week_start)
        latest = self.latest(plan_id)
        if latest is not None and latest.status == WeeklyPlanStatus.APPROVED:
            raise ValueError("Zatwierdzony plan tygodnia mozna zmienic tylko awaryjnie.")
        items = self._items_from_result(
            result,
            policy=policy,
            start_offset_h=start_offset_h,
            exclude_frozen=exclude_frozen,
        )
        if not items:
            raise ValueError("Brak operacji mieszczacych sie w planowanym tygodniu.")
        created_at = policy.localize(now).isoformat()
        localized_start = policy.localize(target_week_start)
        plan = WeeklyPlan(
            plan_id=plan_id,
            version=(latest.version + 1 if latest else 1),
            status=WeeklyPlanStatus.DRAFT,
            target_week_start=localized_start.isoformat(),
            target_week_end=policy.week_end(localized_start).isoformat(),
            created_at=created_at,
            approved_at="",
            source_run_id=source_run_id,
            source_queue_hash=source_queue_hash,
            emergency_reason="",
            items=items,
        )
        self._write(plan)
        self.audit.append(
            "WEEKLY_PLAN_DRAFTED",
            plan.plan_id,
            {"version": plan.version, "items": len(plan.items), "source_run_id": source_run_id},
        )
        return plan

    def approve(
        self,
        plan_id: str,
        *,
        policy: WeeklyPlanningPolicy,
        now: datetime | None = None,
    ) -> WeeklyPlan:
        latest = self.latest(plan_id)
        if latest is None:
            raise FileNotFoundError(f"Nie znaleziono szkicu planu {plan_id}.")
        if latest.status == WeeklyPlanStatus.APPROVED:
            return latest
        approved = replace(
            latest,
            version=latest.version + 1,
            status=WeeklyPlanStatus.APPROVED,
            approved_at=policy.localize(now).isoformat(),
        )
        self._write(approved)
        self.audit.append(
            "WEEKLY_PLAN_APPROVED",
            approved.plan_id,
            {"version": approved.version, "items": len(approved.items)},
        )
        return approved

    def emergency_replan(
        self,
        plan_id: str,
        *,
        policy: WeeklyPlanningPolicy,
        result: PlanningResult,
        reason: str,
        source_queue_hash: str,
        source_run_id: str = "",
        now: datetime | None = None,
    ) -> WeeklyPlan:
        latest = self.latest(plan_id)
        if latest is None or latest.status != WeeklyPlanStatus.APPROVED:
            raise ValueError("Brak zatwierdzonego planu do awaryjnej zmiany.")
        if not reason.strip():
            raise ValueError("Awaryjne przeplanowanie wymaga podania powodu.")
        local_now = policy.localize(now)
        if latest.effective_status(local_now, policy=policy) != "ACTIVE":
            raise ValueError("Awaryjnie mozna zmienic tylko aktywny tydzien.")
        elapsed_h = policy.elapsed_work_hours(local_now, week_start=latest.week_start)
        items = tuple(
            item
            for item in self._items_from_result(result, policy=policy)
            if item.end_h > elapsed_h
        )
        if not items:
            raise ValueError("Nowy plan nie zawiera pozostalych operacji aktywnego tygodnia.")
        replacement = WeeklyPlan(
            plan_id=latest.plan_id,
            version=latest.version + 1,
            status=WeeklyPlanStatus.APPROVED,
            target_week_start=latest.target_week_start,
            target_week_end=latest.target_week_end,
            created_at=policy.localize(now).isoformat(),
            approved_at=policy.localize(now).isoformat(),
            source_run_id=source_run_id,
            source_queue_hash=source_queue_hash,
            emergency_reason=reason.strip(),
            items=items,
        )
        self._write(replacement)
        self.audit.append(
            "WEEKLY_PLAN_EMERGENCY_REPLAN",
            replacement.plan_id,
            {
                "version": replacement.version,
                "previous_version": latest.version,
                "reason": replacement.emergency_reason,
                "items": len(replacement.items),
            },
        )
        return replacement

    def _write(self, plan: WeeklyPlan) -> None:
        self.provider.write_bytes(
            self._version_key(plan.plan_id, plan.version),
            _serialize_plan(plan),
        )

    @staticmethod
    def _items_from_result(
        result: PlanningResult,
        *,
        policy: WeeklyPlanningPolicy,
        start_offset_h: float = 0.0,
        exclude_frozen: bool = False,
    ) -> tuple[WeeklyPlanItem, ...]:
        items: list[WeeklyPlanItem] = []
        for step in result.steps:
            if exclude_frozen and (step.frozen or step.started):
                continue
            shifted_start = step.start_h - start_offset_h
            shifted_end = step.end_h - start_offset_h
            if shifted_end <= 0 or shifted_start >= policy.horizon_hours:
                continue
            items.append(
                WeeklyPlanItem(
                    operation_id=step.operation_id,
                    order_id=step.order_id,
                    machine_id=step.machine_id,
                    start_h=round(max(0.0, shifted_start), 3),
                    end_h=round(shifted_end, 3),
                )
            )
        return tuple(
            sorted(items, key=lambda item: (item.start_h, item.machine_id, item.operation_id))
        )


def apply_weekly_lock(
    frame: pd.DataFrame,
    plan: WeeklyPlan,
    policy: WeeklyPlanningPolicy,
    *,
    unavailable_machines: tuple[int, ...] = (),
) -> tuple[pd.DataFrame, tuple[str, ...], int]:
    """Freeze active-week items and release every other operation after the horizon."""

    out = frame.copy()
    by_operation = {item.operation_id: item for item in plan.items}
    unavailable = set(unavailable_machines)
    alerts: list[str] = []
    locked = 0
    existing_operations = set(out.get("operation_id", pd.Series(dtype=str)).astype(str))
    missing = sorted(set(by_operation) - existing_operations)
    if missing:
        alerts.append("W planie sa operacje nieobecne w kolejce: " + ", ".join(missing))
    for index, row in out.iterrows():
        operation_id = str(row.get("operation_id", ""))
        item = by_operation.get(operation_id)
        if item is not None:
            out.at[index, "frozen"] = True
            out.at[index, "fixed_machine_id"] = item.machine_id
            out.at[index, "fixed_start_h"] = item.start_h
            locked += 1
            if item.machine_id in unavailable:
                alerts.append(
                    f"{operation_id}: zaplanowana maszyna M{item.machine_id} jest niedostepna."
                )
            stock_status = str(row.get("stock_status", "")).strip().upper()
            if stock_status == "UNSCHEDULABLE" or str(row.get("missing_components", "")).strip():
                alerts.append(f"{operation_id}: brak komponentow dla zablokowanego planu.")
            continue
        ready_value = pd.to_numeric(
            pd.Series([row.get("components_ready_h", 0)]), errors="coerce"
        ).iloc[0]
        ready_h = 0.0 if pd.isna(ready_value) else float(ready_value)
        out.at[index, "components_ready_h"] = max(ready_h, policy.horizon_hours)
    return out, tuple(dict.fromkeys(alerts)), locked
