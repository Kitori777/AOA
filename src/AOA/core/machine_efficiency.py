from __future__ import annotations

import math

import pandas as pd

from AOA.core.machine_catalog import MachineSpec
from AOA.core.monte_carlo import MonteCarloResult


def build_machine_efficiency(
    events: pd.DataFrame,
    machines: tuple[MachineSpec, ...] | list[MachineSpec] = (),
    risk: MonteCarloResult | None = None,
) -> pd.DataFrame:
    """Return an inspectable, one-row-per-machine performance table."""

    if events is None or events.empty:
        raise ValueError("Raport efektywnosci wymaga zdarzen produkcyjnych.")
    required = {"machine_id", "t_start", "t_end"}
    missing = sorted(required - set(events.columns))
    if missing:
        raise ValueError("Brak kolumn raportu efektywnosci: " + ", ".join(missing))
    machine_by_id = {machine.machine_id: machine.normalized(index) for index, machine in enumerate(machines, 1)}
    horizon = max(0.0, float(pd.to_numeric(events["t_end"], errors="coerce").max()))
    rows: list[dict[str, float | int | str]] = []
    for machine_id, group in events.groupby(events["machine_id"].astype(str), sort=True):
        machine = machine_by_id.get(machine_id)
        productive = _sum(group, "czas_produkcji_h", fallback_end_start=True)
        setup = _sum(group, "setup_h")
        deterministic_downtime = _sum(group, "downtime_h")
        planned = machine.planned_hours_h if machine and machine.planned_hours_h > 0 else horizon
        planned = max(planned, productive + setup + deterministic_downtime, 1e-9)
        idle = max(0.0, planned - productive - setup - deterministic_downtime)
        availability = max(0.0, min(1.0, (planned - deterministic_downtime) / planned))
        base_duration = _sum(group, "base_duration_h")
        performance = min(1.0, base_duration / productive) if productive > 0 and base_duration > 0 else 1.0
        quality = _quality_ratio(group)
        oee = availability * performance * quality
        lateness = (
            pd.to_numeric(group["lateness_h"], errors="coerce").fillna(0.0)
            if "lateness_h" in group.columns
            else pd.Series(0.0, index=group.index)
        )
        late_jobs = int((lateness > 0).sum())
        row: dict[str, float | int | str] = {
            "machine_id": machine_id,
            "machine_name": machine.name if machine else machine_id,
            "station_id": machine.station_id if machine else str(group.get("station_id", pd.Series([""])).iloc[0]),
            "jobs": len(group),
            "productive_h": round(productive, 6),
            "setup_h": round(setup, 6),
            "idle_h": round(idle, 6),
            "downtime_h": round(deterministic_downtime, 6),
            "utilization_pct": round(productive / planned * 100, 3),
            "availability_pct": round(availability * 100, 3),
            "performance_pct": round(performance * 100, 3),
            "quality_pct": round(quality * 100, 3),
            "estimated_oee_pct": round(oee * 100, 3),
            "throughput_per_h": round(len(group) / planned, 6),
            "late_jobs": late_jobs,
            "cost": round(_sum(group, "cost"), 6),
            "waste": round(_sum(group, "waste"), 6),
            "energy_kwh": round(_sum(group, "energy_kwh"), 6),
        }
        rows.append(row)
    report = pd.DataFrame(rows)
    if risk is not None and not risk.machine_summary.empty:
        report = report.merge(risk.machine_summary, on="machine_id", how="left")
    return report


def efficiency_summary(report: pd.DataFrame) -> dict[str, float | int]:
    if report is None or report.empty:
        return {
            "machines": 0,
            "productive_h": 0.0,
            "setup_h": 0.0,
            "downtime_h": 0.0,
            "mean_utilization_pct": 0.0,
            "mean_estimated_oee_pct": 0.0,
        }
    return {
        "machines": len(report),
        "productive_h": round(float(report["productive_h"].sum()), 6),
        "setup_h": round(float(report["setup_h"].sum()), 6),
        "downtime_h": round(float(report["downtime_h"].sum()), 6),
        "mean_utilization_pct": round(float(report["utilization_pct"].mean()), 3),
        "mean_estimated_oee_pct": round(float(report["estimated_oee_pct"].mean()), 3),
    }


def _sum(group: pd.DataFrame, column: str, *, fallback_end_start: bool = False) -> float:
    if column in group.columns:
        values = pd.to_numeric(group[column], errors="coerce").fillna(0.0)
        return float(values.sum())
    if fallback_end_start:
        end = pd.to_numeric(group["t_end"], errors="coerce").fillna(0.0)
        start = pd.to_numeric(group["t_start"], errors="coerce").fillna(0.0)
        return float((end - start).clip(lower=0.0).sum())
    return 0.0


def _quality_ratio(group: pd.DataFrame) -> float:
    if "quality" not in group.columns:
        return 1.0
    values = pd.to_numeric(group["quality"], errors="coerce").dropna()
    if values.empty:
        return 1.0
    mean = float(values.mean())
    if mean > 1:
        mean /= 100.0
    if not math.isfinite(mean):
        return 1.0
    return max(0.0, min(1.0, mean))
