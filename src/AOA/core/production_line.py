from __future__ import annotations

import heapq
import math
import re
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from AOA.core.formula_engine import SafeFormula, compile_formula

MAX_EVENT_ROWS = 2_000_000
BASE_FORMULA_VARIABLES = {
    "cena",
    "odpad",
    "termin_h",
    "czas_produkcji_h",
    "x",
    "y",
    "z",
    "job_index",
    "station_index",
    "resource_index",
    "prev_duration",
    "prev_end",
    "cost_total",
    "waste_total",
    "quality",
    "duration",
    "start",
    "end",
}


def _safe_id(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip()).strip("_")
    return (cleaned or fallback)[:80]


@dataclass(frozen=True)
class StationSpec:
    station_id: str
    name: str
    resources: int = 1
    duration_formula: str = "czas_produkcji_h"
    cost_formula: str = "0"
    waste_formula: str = "0"
    quality_formula: str = "quality"

    def normalized(self, index: int) -> StationSpec:
        return StationSpec(
            station_id=_safe_id(self.station_id, f"S{index}"),
            name=self.name.strip() or f"Stanowisko {index}",
            resources=int(self.resources),
            duration_formula=self.duration_formula.strip(),
            cost_formula=self.cost_formula.strip() or "0",
            waste_formula=self.waste_formula.strip() or "0",
            quality_formula=self.quality_formula.strip() or "quality",
        )


@dataclass(frozen=True)
class ProductionLineSpec:
    line_id: str
    name: str
    stations: tuple[StationSpec, ...]

    def normalized(self) -> ProductionLineSpec:
        return ProductionLineSpec(
            line_id=_safe_id(self.line_id, "production_line"),
            name=self.name.strip() or "Moja linia produkcyjna",
            stations=tuple(
                station.normalized(index) for index, station in enumerate(self.stations, 1)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProductionLineSpec:
        stations = tuple(StationSpec(**item) for item in payload.get("stations", []))
        return cls(
            line_id=str(payload.get("line_id") or "production_line"),
            name=str(payload.get("name") or "Moja linia produkcyjna"),
            stations=stations,
        ).normalized()


@dataclass(frozen=True)
class ProductionLineResult:
    events: pd.DataFrame
    job_summary: pd.DataFrame
    kpis: dict[str, float | int]


def validate_production_line(
    spec: ProductionLineSpec, columns: list[str] | None = None
) -> ProductionLineSpec:
    normalized = spec.normalized()
    if not normalized.stations:
        raise ValueError("Linia produkcyjna musi zawierac przynajmniej jedno stanowisko.")
    station_ids = [station.station_id for station in normalized.stations]
    if len(station_ids) != len(set(station_ids)):
        raise ValueError("Identyfikatory stanowisk musza byc unikalne.")

    allowed = set(BASE_FORMULA_VARIABLES)
    allowed.update(column for column in (columns or []) if str(column).isidentifier())
    for station in normalized.stations:
        if station.resources <= 0 or station.resources > 1000:
            raise ValueError(
                f"Stanowisko {station.name}: liczba maszyn musi byc w zakresie 1..1000."
            )
        for label, formula in (
            ("czas", station.duration_formula),
            ("koszt", station.cost_formula),
            ("odpad", station.waste_formula),
            ("jakosc", station.quality_formula),
        ):
            try:
                compile_formula(formula, allowed)
            except ValueError as exc:
                raise ValueError(f"Stanowisko {station.name}, wzor {label}: {exc}") from exc
    return normalized


def simulate_production_line(spec: ProductionLineSpec, jobs: pd.DataFrame) -> ProductionLineResult:
    if jobs is None or jobs.empty:
        raise ValueError("Brak zlecen do symulacji linii produkcyjnej.")
    spec = validate_production_line(spec, [str(column) for column in jobs.columns])
    event_count = len(jobs) * len(spec.stations)
    if event_count > MAX_EVENT_ROWS:
        raise ValueError(
            f"Symulacja utworzylaby {event_count:,} wierszy. Limit lekkiego wyniku to {MAX_EVENT_ROWS:,}."
        )

    source = jobs.reset_index(drop=True).copy()
    job_id_col = next(
        (
            column
            for column in ("sto_job_id", "job_id", "zlecenie", "id")
            if column in source.columns
        ),
        None,
    )
    job_ids = (
        source[job_id_col].astype(str).tolist()
        if job_id_col
        else [f"JOB_{index + 1}" for index in range(len(source))]
    )
    if len(job_ids) != len(set(job_ids)):
        raise ValueError("Identyfikatory zlecen w linii produkcyjnej musza byc unikalne.")
    states = [
        {
            "job_id": job_ids[index],
            "job_order": index + 1,
            "ready": 0.0,
            "prev_duration": 0.0,
            "cost_total": 0.0,
            "waste_total": 0.0,
            "quality": 1.0,
        }
        for index in range(len(source))
    ]
    allowed = set(BASE_FORMULA_VARIABLES)
    allowed.update(str(column) for column in source.columns if str(column).isidentifier())
    events: list[dict[str, Any]] = []

    for station_index, station in enumerate(spec.stations, start=1):
        formulas = _compile_station_formulas(station, allowed)
        resource_heap = [
            (0.0, resource_index) for resource_index in range(1, station.resources + 1)
        ]
        heapq.heapify(resource_heap)
        ordered_jobs = sorted(range(len(source)), key=lambda index: (states[index]["ready"], index))
        for source_index in ordered_jobs:
            state = states[source_index]
            available, resource_index = heapq.heappop(resource_heap)
            start = max(float(state["ready"]), float(available))
            variables = _formula_variables(
                source.iloc[source_index],
                state,
                station_index=station_index,
                resource_index=resource_index,
            )
            duration = _non_negative(formulas["duration"].evaluate(variables), station.name, "czas")
            if duration <= 0:
                raise ValueError(f"Stanowisko {station.name}: czas musi byc wiekszy od zera.")
            end = start + duration
            variables.update({"duration": duration, "start": start, "end": end})
            cost = _non_negative(formulas["cost"].evaluate(variables), station.name, "koszt")
            waste = _non_negative(formulas["waste"].evaluate(variables), station.name, "odpad")
            quality = formulas["quality"].evaluate(variables)
            if not math.isfinite(quality):
                raise ValueError(f"Stanowisko {station.name}: jakosc nie jest poprawna liczba.")

            deadline = _numeric(source.iloc[source_index].get("termin_h"), default=0.0)
            lateness = max(0.0, end - deadline) if deadline > 0 else 0.0
            resource_id = f"{station.station_id}:M{resource_index}"
            state.update(
                ready=end,
                prev_duration=duration,
                cost_total=float(state["cost_total"]) + cost,
                waste_total=float(state["waste_total"]) + waste,
                quality=quality,
            )
            heapq.heappush(resource_heap, (end, resource_index))
            events.append(
                {
                    "line_id": spec.line_id,
                    "sto_job_id": state["job_id"],
                    "job_order": state["job_order"],
                    "station_id": station.station_id,
                    "station_name": station.name,
                    "station_order": station_index,
                    "machine_id": resource_id,
                    "t_start": round(start, 6),
                    "t_end": round(end, 6),
                    "czas_produkcji_h": round(duration, 6),
                    "termin_h": round(deadline, 6),
                    "lateness_h": round(lateness, 6),
                    "cost": round(cost, 6),
                    "waste": round(waste, 6),
                    "quality": round(quality, 6),
                }
            )

    event_df = pd.DataFrame(events)
    final_station = len(spec.stations)
    final_rows = event_df[event_df["station_order"] == final_station].copy()
    state_by_job = {str(state["job_id"]): state for state in states}
    job_summary = final_rows[
        ["sto_job_id", "job_order", "t_end", "termin_h", "lateness_h", "quality"]
    ].copy()
    job_summary["cost_total"] = job_summary["sto_job_id"].map(
        lambda job_id: round(float(state_by_job[str(job_id)]["cost_total"]), 6)
    )
    job_summary["waste_total"] = job_summary["sto_job_id"].map(
        lambda job_id: round(float(state_by_job[str(job_id)]["waste_total"]), 6)
    )
    makespan = float(event_df["t_end"].max()) if not event_df.empty else 0.0
    kpis: dict[str, float | int] = {
        "jobs": len(source),
        "stations": len(spec.stations),
        "events": len(event_df),
        "makespan_h": round(makespan, 6),
        "throughput_per_h": round(len(source) / makespan, 6) if makespan > 0 else 0.0,
        "late_jobs": int((final_rows["lateness_h"] > 0).sum()),
        "total_lateness_h": round(float(final_rows["lateness_h"].sum()), 6),
        "total_cost": round(float(job_summary["cost_total"].sum()), 6),
        "total_waste": round(float(job_summary["waste_total"].sum()), 6),
        "mean_quality": round(float(job_summary["quality"].mean()), 6),
    }
    return ProductionLineResult(events=event_df, job_summary=job_summary, kpis=kpis)


def _compile_station_formulas(station: StationSpec, allowed: set[str]) -> dict[str, SafeFormula]:
    return {
        "duration": compile_formula(station.duration_formula, allowed),
        "cost": compile_formula(station.cost_formula, allowed),
        "waste": compile_formula(station.waste_formula, allowed),
        "quality": compile_formula(station.quality_formula, allowed),
    }


def _formula_variables(
    row: pd.Series, state: dict[str, Any], *, station_index: int, resource_index: int
) -> dict[str, float]:
    variables = {name: 0.0 for name in BASE_FORMULA_VARIABLES}
    for name, value in row.items():
        if str(name).isidentifier():
            variables[str(name)] = _numeric(value)
    variables.update(
        job_index=float(state["job_order"]),
        station_index=float(station_index),
        resource_index=float(resource_index),
        prev_duration=float(state["prev_duration"]),
        prev_end=float(state["ready"]),
        cost_total=float(state["cost_total"]),
        waste_total=float(state["waste_total"]),
        quality=float(state["quality"]),
    )
    return variables


def _numeric(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _non_negative(value: float, station_name: str, field: str) -> float:
    if value < 0:
        raise ValueError(f"Stanowisko {station_name}: {field} nie moze byc ujemny.")
    return float(value)
