"""ECO, component readiness and risk methods scoped to engineering mode.

All scheduling stays in minutes. Only the Monte Carlo adapter exchanges
hours with the existing reliability simulator; shared full-mode logic is not
changed. Risk refers to fixed-order, pause-and-resume execution scenarios.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from math import sqrt

import pandas as pd

from AOA.core.esm_costs import DelayPenalty, validate_objective
from AOA.core.flowshop import (
    advance_flowshop,
    evaluate_flowshop,
    flowshop_key,
    flowshop_order,
    validate_flowshop,
)
from AOA.core.machine_catalog import MachineSpec
from AOA.core.monte_carlo import (
    MonteCarloConfig,
    default_queue_machine_specs,
    simulate_schedule_risk,
)
from AOA.core.optimization.models import Job


def _partition(jobs: Sequence[Job]) -> tuple[list[Job], list[Job]]:
    return (
        [j for j in jobs if j.stock_status != "UNSCHEDULABLE"],
        sorted((j for j in jobs if j.stock_status == "UNSCHEDULABLE"), key=lambda j: j.job_id),
    )


def _refine(
    seeds: Sequence[list[Job]],
    n_machines: int,
    *,
    max_evaluations: int = 3000,
    retained: list[list[Job]] | None = None,
    objective: str = "sto",
) -> list[Job]:
    """Insertion and swap descent with a shared, deterministic evaluation budget.

    First retain the former two-pass insertion baseline for each seed. Then
    continue from those incumbents until local convergence or the budget. This
    preserves useful alternative starts instead of spending everything on one.
    """
    cache: dict[tuple[str, ...], tuple] = {}

    class BudgetExhausted(Exception):
        pass

    def key(order: list[Job]) -> tuple:
        ids = tuple(j.job_id for j in order)
        if ids not in cache:
            if len(cache) >= max_evaluations:
                raise BudgetExhausted
            cache[ids] = (
                *flowshop_key(evaluate_flowshop(order, n_machines=n_machines, objective=objective)),
                ids,
            )
        return cache[ids]

    unique = {tuple(j.job_id for j in seed): seed for seed in seeds if seed}
    if not unique:
        return []
    if max_evaluations < len(unique):
        raise ValueError("Budzet musi obejmowac wszystkie kolejnosci poczatkowe.")
    best = min(unique.values(), key=key)

    def improve(current: list[Job], *, swaps: bool) -> list[Job]:
        nonlocal best
        candidate_best = current

        def consider(candidate: list[Job]) -> None:
            nonlocal candidate_best, best
            if key(candidate) < key(candidate_best):
                candidate_best = candidate
            if key(candidate) < key(best):
                best = candidate

        for i, job in enumerate(current):
            remaining = current[:i] + current[i + 1 :]
            for position in range(len(current)):
                consider(remaining[:position] + [job] + remaining[position:])
            if swaps:
                for j in range(i + 1, len(current)):
                    candidate = list(current)
                    candidate[i], candidate[j] = candidate[j], candidate[i]
                    consider(candidate)
        return candidate_best

    try:
        incumbents = []
        for seed in sorted(unique.values(), key=key)[:3]:
            current = list(seed)
            for _pass in range(2):
                improved = improve(current, swaps=False)
                if key(improved) >= key(current):
                    break
                current = improved
            incumbents.append(current)
        if retained is not None:
            # A nominal improvement can worsen stochastic execution. Retain the
            # former two-pass winner for the risk selector, alongside the new one.
            retained.append(list(best))
        for current in sorted(incumbents, key=key):
            while True:
                improved = improve(current, swaps=True)
                if key(improved) >= key(current):
                    break
                current = improved
    except BudgetExhausted:
        pass
    return best


def sequence_eco_flowshop(
    jobs: Sequence[Job],
    *,
    n_machines: int,
    retained: list[list[Job]] | None = None,
    objective: str = "sto",
) -> list[Job]:
    validate_flowshop(jobs, n_machines)
    active, blocked = _partition(jobs)
    seeds = [
        sorted(active, key=lambda j: (j.material, j.shape, j.deadline, j.job_id)),
        sorted(
            active, key=lambda j: (j.components_ready_h, j.material, j.shape, j.deadline, j.job_id)
        ),
        flowshop_order(active, "MT", n_machines),
        flowshop_order(active, "MO", n_machines),
    ]
    if objective == "sto":
        return _refine(seeds, n_machines, retained=retained) + blocked
    return _refine(seeds, n_machines, retained=retained, objective=objective) + blocked


def sequence_component_ready_flowshop(
    jobs: Sequence[Job],
    *,
    n_machines: int,
    retained: list[list[Job]] | None = None,
    objective: str = "sto",
) -> list[Job]:
    validate_flowshop(jobs, n_machines)
    active, blocked = _partition(jobs)
    remaining = list(active)
    dispatch: list[Job] = []
    available = (0.0,) * n_machines
    while remaining:
        clock = max(available[0], min(j.components_ready_h for j in remaining))
        ready = [j for j in remaining if j.components_ready_h <= clock]
        job = min(ready, key=lambda j: (j.deadline, sum(j.machine_times[:n_machines]), j.job_id))
        available, _setups = advance_flowshop(available, job, dispatch[-1] if dispatch else None)
        dispatch.append(job)
        remaining.remove(job)
    seeds = [
        dispatch,
        sorted(active, key=lambda j: (j.components_ready_h, j.deadline, j.job_id)),
        flowshop_order(active, "MT", n_machines),
    ]
    if objective == "sto":
        return _refine(seeds, n_machines, retained=retained) + blocked
    return _refine(seeds, n_machines, retained=retained, objective=objective) + blocked


def _events_in_hours(evaluation: dict) -> pd.DataFrame:
    """The only minutes -> hours boundary, covering setup and release as well."""
    return pd.DataFrame(
        [
            {
                "sto_job_id": step["job_id"],
                "machine_id": str(step["machine_id"]),
                "setup_start": (step["start_time"] - step.get("setup_time", 0.0)) / 60,
                "setup_h": step.get("setup_time", 0.0) / 60,
                "t_start": step["start_time"] / 60,
                "t_end": step["completion_time"] / 60,
                "czas_produkcji_h": (step["completion_time"] - step["start_time"]) / 60,
                "termin_h": step["deadline"] / 60,
            }
            for step in evaluation["steps"]
            if step.get("scheduled", True)
        ]
    )


def _risk_in_minutes(summary: dict) -> dict:
    return {
        key.removesuffix("_h") + "_min" if key.endswith("_h") else key: float(value) * 60
        if key.endswith("_h")
        else value
        for key, value in summary.items()
    }


def _mean_intervals(runs: pd.DataFrame) -> dict:
    """Approximate 95% Monte Carlo intervals for means, not prediction intervals."""
    count = len(runs)
    result: dict = {"mean_ci_available": count > 1}
    if count > 1:
        for source, target in (("total_lateness_h", "lateness"), ("makespan_h", "makespan")):
            values = runs[source] * 60
            mean = float(values.mean())
            margin = 1.96 * float(values.std(ddof=1)) / sqrt(count)
            result[f"mean_{target}_ci95_min"] = [max(0.0, mean - margin), mean + margin]
        if "total_tardiness_cost" in runs:
            values = runs["total_tardiness_cost"]
            mean = float(values.mean())
            margin = 1.96 * float(values.std(ddof=1)) / sqrt(count)
            result["mean_tardiness_cost_ci95"] = [max(0.0, mean - margin), mean + margin]
    return result


def _choose_robust(
    candidates: Sequence[dict],
    *,
    n_machines: int,
    machines: Sequence[MachineSpec] | None = None,
    config: MonteCarloConfig | None = None,
) -> dict:
    configuration = (config or MonteCarloConfig()).normalized()
    specs = (
        tuple(machines)
        if machines is not None
        else default_queue_machine_specs([str(i) for i in range(1, n_machines + 1)])
    )
    # The base operation durations already describe each stage/machine. Only
    # reliability is consumed here; speed is never applied a second time.
    if len(specs) != n_machines or {m.machine_id for m in specs} != {
        str(i) for i in range(1, n_machines + 1)
    }:
        raise ValueError("Profile ryzyka musza obejmowac maszyny o identyfikatorach 1...m.")
    best = None
    best_key = None
    for evaluation in candidates:
        cost_mode = evaluation.get("objective", "sto") == "cost"
        waste_mode = evaluation.get("objective") == "waste"
        penalties = {
            job_id: DelayPenalty(**parameters)
            for job_id, parameters in evaluation.get("cost_parameters", {}).items()
        }
        risk_kwargs = {"delay_penalties": penalties} if "cost_parameters" in evaluation else {}
        events = _events_in_hours(evaluation)
        if events.empty:
            result = {
                **evaluation,
                "risk_summary": {
                    "iterations": 0,
                    "seed": configuration.seed,
                    "available": False,
                    "reason": "Brak dopuszczonych operacji.",
                },
            }
            key = (
                evaluation["unscheduled_count"],
                float("inf"),
                evaluation["total_waste_kg"],
                float("inf"),
            )
        else:
            risk = simulate_schedule_risk(events, specs, configuration, **risk_kwargs)
            summary = _risk_in_minutes(risk.summary)
            summary["available"] = True
            late = summary["mean_tardiness_cost"] if cost_mode else summary["mean_lateness_min"]
            late_p90 = summary["p90_tardiness_cost"] if cost_mode else summary["p90_lateness_min"]
            finish = summary["mean_makespan_min"]
            key = (
                evaluation["unscheduled_count"],
                late + configuration.risk_aversion * max(0.0, late_p90 - late),
                evaluation["total_waste_kg"],
                finish
                + configuration.risk_aversion * max(0.0, summary["p90_makespan_min"] - finish),
            )
            result = {
                **evaluation,
                "risk_summary": summary,
                "risk_machine_summary": risk.machine_summary.to_dict("records"),
            }
        if waste_mode:
            # Failures only pause/resume operations in this model: kilograms
            # stay deterministic. Risk-adjusted tardiness breaks waste ties.
            key = (key[0], key[2], key[1], key[3])
        if best_key is None or key < best_key:
            best, best_key = result, key
    if best is None:
        raise ValueError("Brak wariantow do symulacji ryzyka.")
    # Hold out a second stream: it assesses the selected order and never selects
    # a new winner, avoiding another round of selection on the validation data.
    validation = {"available": False, "iterations": 0, "reason": "Brak dopuszczonych operacji."}
    if best["risk_summary"]["available"]:
        validation_kwargs = (
            {
                "delay_penalties": {
                    job_id: DelayPenalty(**parameters)
                    for job_id, parameters in best["cost_parameters"].items()
                }
            }
            if "cost_parameters" in best
            else {}
        )
        checked = simulate_schedule_risk(
            _events_in_hours(best),
            specs,
            replace(configuration, seed=configuration.seed + 1),
            **validation_kwargs,
        )
        validation = {
            **_risk_in_minutes(checked.summary),
            **_mean_intervals(checked.runs),
            "available": True,
        }
    return {
        **best,
        "method": "ROBUST_MC",
        "optimality_status": "RISK_ASSESSED",
        "risk_profiles": "user" if machines is not None else "synthetic_defaults",
        "risk_candidate_count": len(candidates),
        "risk_validation_summary": validation,
        "risk_validation_role": "held_out_assessment_only",
    }


def evaluate_robust_flowshop(
    jobs: Sequence[Job],
    *,
    n_machines: int,
    machines: Sequence[MachineSpec] | None = None,
    config: MonteCarloConfig | None = None,
    objective: str = "sto",
) -> dict:
    validate_flowshop(jobs, n_machines)
    validate_objective(objective)
    active, blocked = _partition(jobs)
    orders = [
        flowshop_order(active, method, n_machines) + blocked for method in ("MT", "MO", "MZO")
    ]
    retained: list[list[Job]] = []
    orders += [
        sequence_eco_flowshop(jobs, n_machines=n_machines, retained=retained, objective=objective),
        sequence_component_ready_flowshop(
            jobs, n_machines=n_machines, retained=retained, objective=objective
        ),
    ]
    orders += [order + blocked for order in retained]
    if active:
        orders += [
            sorted(active, key=lambda j: (j.machine_times[n_machines - 1], j.deadline, j.job_id))
            + blocked
        ]
    unique = {tuple(j.job_id for j in order): order for order in orders}
    candidates = [
        evaluate_flowshop(order, n_machines=n_machines, objective=objective)
        for order in unique.values()
    ]
    return _choose_robust(candidates, n_machines=n_machines, machines=machines, config=config)


def evaluate_robust_parallel(jobs: list[Job], *, n_machines: int) -> dict:
    """Fix engineering legacy CSV units without changing the full-mode runner."""
    from AOA.core.optimization.runner import run_selected_sto_models

    candidates = run_selected_sto_models(
        jobs,
        ["MT", "MO", "MZO", "ECO_WASTE", "COMPONENT_READY_EDD"],
        n_machines=n_machines,
    )
    unique = {tuple(r["order"]): r for r in candidates}
    return _choose_robust(list(unique.values()), n_machines=n_machines)
