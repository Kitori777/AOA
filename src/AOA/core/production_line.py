from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from AOA.core.formula_engine import SafeFormula, compile_formula
from AOA.core.machine_catalog import MachineCatalog, MachineSpec, build_default_machines
from AOA.core.product_routing import (
    ProductRoute,
    ProductRoutingCatalog,
    RouteOperation,
    product_id_from_row,
)

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
    "machine_speed_factor",
    "machine_waste_factor",
    "machine_energy_kwh_per_hour",
    "machine_cost_per_hour",
    "machine_setup_time_h",
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
    machines: tuple[MachineSpec, ...] = ()
    product_routes: tuple[ProductRoute, ...] = ()

    def normalized(self) -> ProductionLineSpec:
        stations = tuple(
            station.normalized(index) for index, station in enumerate(self.stations, 1)
        )
        machines = self.machines or build_default_machines(
            (station.station_id, station.name, station.resources) for station in stations
        )
        catalog = MachineCatalog(tuple(machines)).normalized(
            station.station_id for station in stations
        )
        if self.machines:
            counts = {
                station.station_id: len(catalog.for_station(station.station_id))
                for station in stations
            }
            stations = tuple(
                StationSpec(
                    station.station_id,
                    station.name,
                    counts[station.station_id] or station.resources,
                    station.duration_formula,
                    station.cost_formula,
                    station.waste_formula,
                    station.quality_formula,
                )
                for station in stations
            )
        return ProductionLineSpec(
            line_id=_safe_id(self.line_id, "production_line"),
            name=self.name.strip() or "Moja linia produkcyjna",
            stations=stations,
            machines=catalog.machines,
            product_routes=tuple(route.normalized() for route in self.product_routes),
        )

    def to_dict(self) -> dict[str, Any]:
        normalized = self.normalized()
        return {
            "line_id": normalized.line_id,
            "name": normalized.name,
            "stations": [asdict(station) for station in normalized.stations],
            "machines": [machine.to_dict() for machine in normalized.machines],
            "product_routes": [route.to_dict() for route in normalized.product_routes],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProductionLineSpec:
        stations = tuple(StationSpec(**item) for item in payload.get("stations", []))
        return cls(
            line_id=str(payload.get("line_id") or "production_line"),
            name=str(payload.get("name") or "Moja linia produkcyjna"),
            stations=stations,
            machines=MachineCatalog.from_list(payload.get("machines")).machines,
            product_routes=ProductRoutingCatalog.from_list(
                payload.get("product_routes")
            ).routes,
        ).normalized()


@dataclass(frozen=True)
class ProductionLineResult:
    events: pd.DataFrame
    job_summary: pd.DataFrame
    kpis: dict[str, float | int]
    machine_events: pd.DataFrame


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
    machine_catalog = MachineCatalog(normalized.machines).normalized(station_ids)
    for station in normalized.stations:
        if not machine_catalog.for_station(station.station_id):
            raise ValueError(f"Stanowisko {station.name} nie ma przypisanej maszyny.")
    ProductRoutingCatalog(normalized.product_routes).normalized(
        station_order=tuple(station_ids),
        machine_ids={machine.machine_id for machine in normalized.machines},
    )
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
    product_ids = [product_id_from_row(source.iloc[index]) for index in range(len(source))]
    route_catalog = ProductRoutingCatalog(spec.product_routes)
    routes = [route_catalog.for_product(product_id) for product_id in product_ids]
    configured_products = {route.product_id for route in spec.product_routes}
    missing_products = sorted(
        {product_id for product_id in product_ids if configured_products and product_id}
        - configured_products
    )
    if missing_products:
        raise ValueError(
            "Brak tras technologicznych dla produktow: " + ", ".join(missing_products)
        )
    allowed = set(BASE_FORMULA_VARIABLES)
    allowed.update(str(column) for column in source.columns if str(column).isidentifier())
    events: list[dict[str, Any]] = []

    for station_index, station in enumerate(spec.stations, start=1):
        formulas = _compile_station_formulas(station, allowed)
        machines = tuple(
            machine for machine in spec.machines if machine.station_id == station.station_id
        )
        availability = {machine.machine_id: 0.0 for machine in machines}
        previous_products = {machine.machine_id: "" for machine in machines}
        ordered_jobs = sorted(
            (
                index
                for index in range(len(source))
                if _route_contains_station(routes[index], station.station_id)
            ),
            key=lambda index: (states[index]["ready"], index),
        )
        for source_index in ordered_jobs:
            state = states[source_index]
            row = source.iloc[source_index]
            product_id = product_ids[source_index]
            material = str(row.get("material", "")).strip()
            route = routes[source_index]
            operation = _route_operation(route, station.station_id)
            operation_id = operation.operation_id if operation is not None else station.station_id
            permitted_ids = set(operation.allowed_machine_ids) if operation is not None else set()
            candidates: list[tuple[float, str, int, MachineSpec, dict[str, float]]] = []
            for resource_index, machine in enumerate(machines, 1):
                if permitted_ids and machine.machine_id not in permitted_ids:
                    continue
                if not machine.capability.accepts(
                    product=product_id,
                    material=material,
                    operation=operation_id,
                ):
                    continue
                setup_h = (
                    machine.setup_time_h
                    if previous_products[machine.machine_id]
                    and previous_products[machine.machine_id] != product_id
                    else 0.0
                )
                setup_start = max(float(state["ready"]), availability[machine.machine_id])
                start = setup_start + setup_h
                variables = _formula_variables(
                    row,
                    state,
                    station_index=station_index,
                    resource_index=resource_index,
                )
                variables.update(
                    machine_speed_factor=machine.speed_factor,
                    machine_waste_factor=machine.waste_factor,
                    machine_energy_kwh_per_hour=machine.energy_kwh_per_hour,
                    machine_cost_per_hour=machine.cost_per_hour,
                    machine_setup_time_h=machine.setup_time_h,
                )
                base_duration = _non_negative(
                    formulas["duration"].evaluate(variables), station.name, "czas"
                )
                duration = base_duration / machine.speed_factor
                if duration <= 0:
                    raise ValueError(
                        f"Stanowisko {station.name}: czas musi byc wiekszy od zera."
                    )
                end = start + duration
                variables.update({"duration": duration, "start": start, "end": end})
                base_cost = _non_negative(
                    formulas["cost"].evaluate(variables), station.name, "koszt"
                )
                base_waste = _non_negative(
                    formulas["waste"].evaluate(variables), station.name, "odpad"
                )
                metrics = {
                    "setup_start": setup_start,
                    "setup_h": setup_h,
                    "start": start,
                    "end": end,
                    "base_duration": base_duration,
                    "duration": duration,
                    "cost": base_cost + (duration + setup_h) * machine.cost_per_hour,
                    "waste": base_waste * machine.waste_factor,
                    "energy": (duration + setup_h) * machine.energy_kwh_per_hour,
                }
                candidates.append((end, machine.machine_id, resource_index, machine, metrics))
            if not candidates:
                job_id = state["job_id"]
                raise ValueError(
                    f"Zlecenie {job_id}: brak maszyny dla produktu {product_id or 'bez ID'}, "
                    f"materialu {material or 'bez ograniczen'} i operacji {operation_id}."
                )
            _, _, resource_index, machine, metrics = min(candidates)
            duration = metrics["duration"]
            end = metrics["end"]
            variables = _formula_variables(
                row,
                state,
                station_index=station_index,
                resource_index=resource_index,
            )
            variables.update({"duration": duration, "start": metrics["start"], "end": end})
            quality = formulas["quality"].evaluate(variables)
            if not math.isfinite(quality):
                raise ValueError(f"Stanowisko {station.name}: jakosc nie jest poprawna liczba.")

            deadline = _numeric(row.get("termin_h"), default=0.0)
            lateness = max(0.0, end - deadline) if deadline > 0 else 0.0
            state.update(
                ready=end,
                prev_duration=duration,
                cost_total=float(state["cost_total"]) + metrics["cost"],
                waste_total=float(state["waste_total"]) + metrics["waste"],
                quality=quality,
            )
            availability[machine.machine_id] = end
            previous_products[machine.machine_id] = product_id
            events.append(
                {
                    "line_id": spec.line_id,
                    "sto_job_id": state["job_id"],
                    "job_order": state["job_order"],
                    "station_id": station.station_id,
                    "station_name": station.name,
                    "station_order": station_index,
                    "operation_id": operation_id,
                    "product_id": product_id,
                    "machine_id": machine.machine_id,
                    "machine_name": machine.name,
                    "setup_start": round(metrics["setup_start"], 6),
                    "setup_h": round(metrics["setup_h"], 6),
                    "t_start": round(metrics["start"], 6),
                    "t_end": round(end, 6),
                    "czas_produkcji_h": round(duration, 6),
                    "base_duration_h": round(metrics["base_duration"], 6),
                    "termin_h": round(deadline, 6),
                    "lateness_h": round(lateness, 6),
                    "cost": round(metrics["cost"], 6),
                    "waste": round(metrics["waste"], 6),
                    "energy_kwh": round(metrics["energy"], 6),
                    "machine_speed_factor": machine.speed_factor,
                    "machine_waste_factor": machine.waste_factor,
                    "quality": round(quality, 6),
                }
            )

    machine_event_df = pd.DataFrame(events)
    state_by_job = {str(state["job_id"]): state for state in states}
    summary_rows = []
    for index, state in enumerate(states):
        deadline = _numeric(source.iloc[index].get("termin_h"), default=0.0)
        completion = float(state["ready"])
        summary_rows.append(
            {
                "sto_job_id": state["job_id"],
                "job_order": state["job_order"],
                "t_end": completion,
                "termin_h": deadline,
                "lateness_h": max(0.0, completion - deadline) if deadline > 0 else 0.0,
                "quality": state["quality"],
            }
        )
    job_summary = pd.DataFrame(summary_rows)
    job_summary["cost_total"] = job_summary["sto_job_id"].map(
        lambda job_id: round(float(state_by_job[str(job_id)]["cost_total"]), 6)
    )
    job_summary["waste_total"] = job_summary["sto_job_id"].map(
        lambda job_id: round(float(state_by_job[str(job_id)]["waste_total"]), 6)
    )
    makespan = float(machine_event_df["t_end"].max()) if not machine_event_df.empty else 0.0
    kpis: dict[str, float | int] = {
        "jobs": len(source),
        "stations": len(spec.stations),
        "events": len(machine_event_df),
        "makespan_h": round(makespan, 6),
        "throughput_per_h": round(len(source) / makespan, 6) if makespan > 0 else 0.0,
        "machines": len(spec.machines),
        "late_jobs": int((job_summary["lateness_h"] > 0).sum()),
        "total_lateness_h": round(float(job_summary["lateness_h"].sum()), 6),
        "total_cost": round(float(job_summary["cost_total"].sum()), 6),
        "total_waste": round(float(job_summary["waste_total"].sum()), 6),
        "total_energy_kwh": round(float(machine_event_df["energy_kwh"].sum()), 6),
        "mean_quality": round(float(job_summary["quality"].mean()), 6),
    }
    compact_columns = [
        "line_id",
        "sto_job_id",
        "job_order",
        "station_id",
        "station_name",
        "station_order",
        "machine_id",
        "t_start",
        "t_end",
        "czas_produkcji_h",
        "termin_h",
        "lateness_h",
        "cost",
        "waste",
        "quality",
    ]
    return ProductionLineResult(
        events=machine_event_df[compact_columns].copy(),
        job_summary=job_summary,
        kpis=kpis,
        machine_events=machine_event_df,
    )


def _compile_station_formulas(station: StationSpec, allowed: set[str]) -> dict[str, SafeFormula]:
    return {
        "duration": compile_formula(station.duration_formula, allowed),
        "cost": compile_formula(station.cost_formula, allowed),
        "waste": compile_formula(station.waste_formula, allowed),
        "quality": compile_formula(station.quality_formula, allowed),
    }


def _route_operation(route: ProductRoute | None, station_id: str) -> RouteOperation | None:
    if route is None:
        return None
    return next(
        (operation for operation in route.operations if operation.station_id == station_id),
        None,
    )


def _route_contains_station(route: ProductRoute | None, station_id: str) -> bool:
    return route is None or any(
        operation.station_id == station_id for operation in route.operations
    )


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
