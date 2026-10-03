from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from AOA.core.machine_catalog import MachineSpec, ReliabilitySpec


@dataclass(frozen=True)
class MonteCarloConfig:
    iterations: int = 1000
    seed: int = 42
    risk_aversion: float = 0.5
    repair_sigma: float = 0.35

    def normalized(self) -> MonteCarloConfig:
        iterations = int(self.iterations)
        if iterations < 1 or iterations > 100_000:
            raise ValueError("Liczba symulacji Monte Carlo musi byc w zakresie 1..100000.")
        risk_aversion = float(self.risk_aversion)
        if not math.isfinite(risk_aversion) or risk_aversion < 0:
            raise ValueError("Wspolczynnik ostroznosci musi byc liczba nieujemna.")
        repair_sigma = float(self.repair_sigma)
        if not math.isfinite(repair_sigma) or repair_sigma < 0:
            raise ValueError("Zmiennosc czasu naprawy musi byc liczba nieujemna.")
        return MonteCarloConfig(iterations, int(self.seed), risk_aversion, repair_sigma)


@dataclass(frozen=True)
class MachineRiskResult:
    machine_id: str
    mean_downtime_h: float
    p50_downtime_h: float
    p90_downtime_h: float
    p95_downtime_h: float
    downtime_probability: float


@dataclass(frozen=True)
class MonteCarloResult:
    runs: pd.DataFrame
    machine_summary: pd.DataFrame
    summary: dict[str, float | int]


def default_queue_machine_specs(machine_ids: list[str]) -> tuple[MachineSpec, ...]:
    """Return conservative defaults used only by the ROBUST_MC queue method."""

    return tuple(
        MachineSpec(
            machine_id=machine_id,
            name=f"Maszyna {machine_id}",
            station_id="QUEUE",
            reliability=ReliabilitySpec(
                mtbf_h=80.0,
                mttr_h=2.0,
                post_changeover_failure_probability=0.03,
                post_changeover_risk_window_h=2.0,
                post_changeover_downtime_h=1.0,
            ),
        ).normalized(index)
        for index, machine_id in enumerate(machine_ids, 1)
    )


def simulate_schedule_risk(
    events: pd.DataFrame,
    machines: tuple[MachineSpec, ...] | list[MachineSpec],
    config: MonteCarloConfig | None = None,
) -> MonteCarloResult:
    """Simulate pause-and-resume failures while preserving job and machine order."""

    if events is None or events.empty:
        raise ValueError("Monte Carlo wymaga niepustego harmonogramu zdarzen.")
    required = {"machine_id", "sto_job_id", "t_start", "t_end"}
    missing = sorted(required - set(events.columns))
    if missing:
        raise ValueError("Brak kolumn wymaganych przez Monte Carlo: " + ", ".join(missing))
    configuration = (config or MonteCarloConfig()).normalized()
    normalized_machines = tuple(
        machine.normalized(index) for index, machine in enumerate(machines, 1)
    )
    machine_by_id = {machine.machine_id: machine for machine in normalized_machines}
    event_machine_ids = {str(value) for value in events["machine_id"].tolist()}
    unknown = sorted(event_machine_ids - set(machine_by_id))
    if unknown:
        raise ValueError("Brak parametrow niezawodnosci dla maszyn: " + ", ".join(unknown))

    prepared = events.reset_index(drop=True).copy()
    prepared["_event_order"] = range(len(prepared))
    prepared = prepared.sort_values(
        ["t_start", "t_end", "_event_order"], kind="stable"
    ).reset_index(drop=True)
    event_records: list[dict[str, Any]] = []
    final_events: dict[str, dict[str, Any]] = {}
    for record in prepared.to_dict("records"):
        machine_id = str(record["machine_id"])
        job_id = str(record["sto_job_id"])
        setup_h = max(0.0, _number(record.get("setup_h"), 0.0))
        processing_h = max(
            0.0,
            _number(
                record.get("czas_produkcji_h"),
                _number(record["t_end"]) - _number(record["t_start"]),
            ),
        )
        compact = {
            "machine_id": machine_id,
            "job_id": job_id,
            "event_order": int(record["_event_order"]),
            "setup_h": setup_h,
            "processing_h": processing_h,
            "baseline_release": _number(
                record.get("setup_start"), _number(record["t_start"])
            ),
            "baseline_end": _number(record["t_end"]),
            "deadline": _number(record.get("termin_h"), 0.0),
        }
        event_records.append(compact)
        current = final_events.get(job_id)
        if current is None or (compact["baseline_end"], compact["event_order"]) > (
            current["baseline_end"],
            current["event_order"],
        ):
            final_events[job_id] = compact
    rng = np.random.default_rng(configuration.seed)
    run_rows: list[dict[str, float | int]] = []
    downtime_by_machine: dict[str, list[float]] = {
        machine_id: [] for machine_id in sorted(machine_by_id)
    }

    for run_index in range(configuration.iterations):
        machine_ready: dict[str, float] = {}
        job_ready: dict[str, float] = {}
        completion_by_event: dict[int, float] = {}
        machine_downtime = {machine_id: 0.0 for machine_id in machine_by_id}
        failure_count = 0
        for event in event_records:
            machine_id = event["machine_id"]
            job_id = event["job_id"]
            machine = machine_by_id[machine_id]
            start = max(
                event["baseline_release"],
                machine_ready.get(machine_id, 0.0),
                job_ready.get(job_id, 0.0),
            )
            downtime_h, failures = _sample_downtime(
                rng,
                machine.reliability,
                processing_h=event["processing_h"],
                setup_h=event["setup_h"],
                repair_sigma=configuration.repair_sigma,
            )
            end = start + event["setup_h"] + event["processing_h"] + downtime_h
            machine_ready[machine_id] = end
            job_ready[job_id] = end
            completion_by_event[event["event_order"]] = end
            machine_downtime[machine_id] += downtime_h
            failure_count += failures

        makespan = max(completion_by_event.values(), default=0.0)
        total_lateness = 0.0
        late_jobs = 0
        for final_event in final_events.values():
            deadline = final_event["deadline"]
            lateness = (
                max(0.0, completion_by_event[final_event["event_order"]] - deadline)
                if deadline > 0
                else 0.0
            )
            total_lateness += lateness
            late_jobs += int(lateness > 0)
        total_downtime = sum(machine_downtime.values())
        run_rows.append(
            {
                "run": run_index + 1,
                "makespan_h": makespan,
                "total_lateness_h": total_lateness,
                "late_jobs": late_jobs,
                "downtime_h": total_downtime,
                "failure_count": failure_count,
            }
        )
        for machine_id, downtime_h in machine_downtime.items():
            downtime_by_machine[machine_id].append(downtime_h)

    runs = pd.DataFrame(run_rows)
    machine_results = [
        _machine_result(machine_id, np.asarray(values, dtype=float))
        for machine_id, values in downtime_by_machine.items()
    ]
    machine_summary = pd.DataFrame([result.__dict__ for result in machine_results])
    mean_makespan = float(runs["makespan_h"].mean())
    p90_makespan = float(runs["makespan_h"].quantile(0.9))
    summary: dict[str, float | int] = {
        "iterations": configuration.iterations,
        "seed": configuration.seed,
        "mean_makespan_h": round(mean_makespan, 6),
        "p50_makespan_h": round(float(runs["makespan_h"].quantile(0.5)), 6),
        "p90_makespan_h": round(p90_makespan, 6),
        "p95_makespan_h": round(float(runs["makespan_h"].quantile(0.95)), 6),
        "mean_lateness_h": round(float(runs["total_lateness_h"].mean()), 6),
        "p90_lateness_h": round(float(runs["total_lateness_h"].quantile(0.9)), 6),
        "mean_downtime_h": round(float(runs["downtime_h"].mean()), 6),
        "p90_downtime_h": round(float(runs["downtime_h"].quantile(0.9)), 6),
        "failure_probability": round(float((runs["failure_count"] > 0).mean()), 6),
        "risk_score_h": round(
            mean_makespan
            + configuration.risk_aversion * max(0.0, p90_makespan - mean_makespan),
            6,
        ),
    }
    return MonteCarloResult(runs, machine_summary, summary)


def _sample_downtime(
    rng: np.random.Generator,
    reliability: ReliabilitySpec,
    *,
    processing_h: float,
    setup_h: float,
    repair_sigma: float,
) -> tuple[float, int]:
    value = reliability.normalized()
    downtime = 0.0
    failures = 0
    if value.mtbf_h > 0 and processing_h > 0:
        failures = int(rng.poisson(processing_h / value.mtbf_h))
        if failures:
            if repair_sigma == 0:
                downtime += failures * value.mttr_h
            else:
                mu = math.log(value.mttr_h) - repair_sigma**2 / 2
                downtime += float(rng.lognormal(mu, repair_sigma, failures).sum())
    if setup_h > 0 and value.post_changeover_failure_probability > 0:
        exposure = 1.0
        if value.post_changeover_risk_window_h > 0:
            exposure = min(processing_h, value.post_changeover_risk_window_h) / value.post_changeover_risk_window_h
        if rng.random() < value.post_changeover_failure_probability * exposure:
            failures += 1
            downtime += value.post_changeover_downtime_h or value.mttr_h
    return downtime, failures


def _machine_result(machine_id: str, values: np.ndarray) -> MachineRiskResult:
    return MachineRiskResult(
        machine_id=machine_id,
        mean_downtime_h=round(float(values.mean()), 6),
        p50_downtime_h=round(float(np.quantile(values, 0.5)), 6),
        p90_downtime_h=round(float(np.quantile(values, 0.9)), 6),
        p95_downtime_h=round(float(np.quantile(values, 0.95)), 6),
        downtime_probability=round(float((values > 0).mean()), 6),
    )


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default
