from __future__ import annotations

import math

import pandas as pd

from .models import OperationSpec, PlanningResult


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _number(value: object, default: float = 0.0) -> float:
    text = _text(value).replace(",", ".")
    return float(text) if text else default


def _integer(value: object, default: int = 0) -> int:
    text = _text(value)
    return int(float(text)) if text else default


def _optional_number(value: object) -> float | None:
    text = _text(value).replace(",", ".")
    return float(text) if text else None


def _optional_integer(value: object) -> int | None:
    text = _text(value)
    return int(float(text)) if text else None


def _boolean(value: object) -> bool:
    return _text(value).casefold() in {"1", "true", "yes", "tak", "y"}


def _tokens(value: object) -> tuple[str, ...]:
    normalized = _text(value).replace(",", "|").replace(";", "|")
    return tuple(token.strip() for token in normalized.split("|") if token.strip())


def dataframe_to_operations(
    frame: pd.DataFrame,
    *,
    order_priorities: dict[str, int] | None = None,
) -> list[OperationSpec]:
    if frame is None or frame.empty:
        return []
    required = {"zlecenie_id", "czas_produkcji_h", "termin_h"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("Brak kolumn operacji: " + ", ".join(missing))
    priorities = order_priorities or {}
    operations: list[OperationSpec] = []
    for index, row in frame.reset_index(drop=True).iterrows():
        order_id = _text(row.get("zlecenie_id"))
        operation_id = _text(row.get("operation_id")) or f"{order_id}-OP{index + 1}"
        eligible = tuple(
            _integer(token)
            for token in _tokens(row.get("dozwolone_maszyny", ""))
            if _integer(token) > 0
        )
        priority = _integer(row.get("priority", 0)) + priorities.get(order_id, 0) * 100
        operations.append(
            OperationSpec(
                operation_id=operation_id,
                order_id=order_id,
                processing_time_h=_number(row.get("czas_produkcji_h")),
                deadline_h=_number(row.get("termin_h")),
                predecessors=_tokens(row.get("predecessors", "")),
                eligible_machines=eligible,
                components_ready_h=_number(row.get("components_ready_h", 0)),
                setup_time_h=_number(row.get("czas_przezbrojenia_h", 0)),
                waste_kg=_number(row.get("odpad_kg", row.get("odpad", 0))),
                energy_kwh=_number(row.get("energia_kwh", 0)),
                priority=priority,
                frozen=_boolean(row.get("frozen", False)),
                started=_boolean(row.get("started", False)),
                fixed_machine_id=_optional_integer(row.get("fixed_machine_id")),
                fixed_start_h=_optional_number(row.get("fixed_start_h")),
                station_type=_text(row.get("station_type", "")),
                product_id=_text(
                    row.get("product_id", row.get("produkt_id", row.get("produkt", "")))
                ),
                material=_text(row.get("material", "")),
            )
        )
    return operations


def planning_result_to_dataframe(result: PlanningResult) -> pd.DataFrame:
    columns = [
        "lp",
        "operation_id",
        "job_id",
        "machine_id",
        "start_time",
        "completion_time",
        "deadline",
        "tardiness_positive",
        "components_ready_h",
        "predecessor_ready_h",
        "frozen",
        "started",
        "scheduled",
        "reason",
    ]
    rows = [
        {
            "lp": index,
            "operation_id": step.operation_id,
            "job_id": step.order_id,
            "machine_id": step.machine_id,
            "start_time": step.start_h,
            "completion_time": step.end_h,
            "deadline": step.deadline_h,
            "tardiness_positive": step.tardiness_h,
            "components_ready_h": step.components_ready_h,
            "predecessor_ready_h": step.predecessor_ready_h,
            "frozen": step.frozen,
            "started": step.started,
            "scheduled": True,
            "reason": step.reason,
        }
        for index, step in enumerate(result.steps, start=1)
    ]
    return pd.DataFrame(rows, columns=columns)
