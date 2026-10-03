from __future__ import annotations

from collections.abc import Callable
from itertools import permutations

import pandas as pd

from AOA.core.machine_catalog import MachineSpec
from AOA.core.mh_models import get_mh_model_names
from AOA.core.mh_models.custom import get_custom_heuristic_config, sequence_custom_heuristic
from AOA.core.monte_carlo import (
    MonteCarloConfig,
    default_queue_machine_specs,
    simulate_schedule_risk,
)
from AOA.core.optimization.evaluation import evaluate_sequence
from AOA.core.optimization.heuristics import (
    best_by_full_search,
    sequence_component_ready_edd,
    sequence_cr,
    sequence_eco_waste,
    sequence_edd_spt,
    sequence_genetic,
    sequence_local_search,
    sequence_lpt_edd,
    sequence_mo,
    sequence_mopt,
    sequence_mt,
    sequence_mzo,
    sequence_neh,
    sequence_random_restart,
    sequence_slack,
    sequence_spt_edd,
)
from AOA.core.optimization.models import Job
from AOA.core.optimization.objectives import OPTIMIZATION_OBJECTIVES, balanced_score, metric_key
from AOA.core.optimization.results import format_steps_table


def run_selected_sto_models(
    jobs: list[Job], selected_methods: list[str], n_machines: int = 1,
    objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
    machine_specs: tuple[MachineSpec, ...] | list[MachineSpec] | None = None,
) -> list[dict]:
    if not selected_methods:
        raise ValueError("Wybierz przynajmniej jeden model STO.")
    if objective not in OPTIMIZATION_OBJECTIVES:
        raise ValueError(f"Nieznany cel optymalizacji: {objective}")
    method_map: dict[str, Callable[[list[Job]], list[Job]]] = {
        "MT": sequence_mt, "MO": sequence_mo, "MZO": sequence_mzo,
        "MOPT": lambda values: sequence_mopt(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        "GENETIC": lambda values: sequence_genetic(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        "SLACK": sequence_slack, "CR": sequence_cr, "EDD_SPT": sequence_edd_spt,
        "SPT_EDD": sequence_spt_edd, "LPT_EDD": sequence_lpt_edd,
        "NEH": lambda values: sequence_neh(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        "LOCAL_SEARCH": lambda values: sequence_local_search(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        "RANDOM_RESTART": lambda values: sequence_random_restart(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        "ECO_WASTE": lambda values: sequence_eco_waste(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        "COMPONENT_READY_EDD": lambda values: sequence_component_ready_edd(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
    }
    results: list[dict] = []
    for method in selected_methods:
        if method not in get_mh_model_names():
            raise ValueError(f"Nieznana metoda STO: {method}")
        custom_config = get_custom_heuristic_config(method)
        risk_result = None
        if method == "ROBUST_MC":
            sequence, risk_result = _robust_mc_sequence(
                jobs,
                n_machines=n_machines,
                objective=objective,
                unavailable_machines=unavailable_machines,
                machine_specs=machine_specs,
            )
        elif method in method_map:
            sequence = method_map[method](jobs)
        elif custom_config is not None:
            sequence = sequence_custom_heuristic(jobs, custom_config)
        else:
            raise ValueError(f"Nieznana metoda STO: {method}")
        evaluation = evaluate_sequence(
            sequence,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
            machine_specs=machine_specs,
        )
        result = {"method": method, **evaluation}
        if risk_result is not None:
            result["risk_summary"] = risk_result.summary
            result["risk_machine_summary"] = risk_result.machine_summary.to_dict("records")
        result["table_text"] = format_steps_table(result["steps"])
        results.append(result)
    results.sort(key=lambda item: (*metric_key(item, jobs, objective), item["method"]))
    if results:
        reference = results[0]
        exact_reference = None
        if len(jobs) <= 8:
            exact_sequence = (
                _best_with_machine_specs(
                    jobs,
                    n_machines=n_machines,
                    objective=objective,
                    unavailable_machines=unavailable_machines,
                    machine_specs=machine_specs,
                )
                if machine_specs is not None
                else best_by_full_search(
                    jobs,
                    n_machines=n_machines,
                    objective=objective,
                    unavailable_machines=unavailable_machines,
                )
            )
            exact_reference = evaluate_sequence(
                exact_sequence,
                n_machines=n_machines,
                objective=objective,
                unavailable_machines=unavailable_machines,
                machine_specs=machine_specs,
            )
            reference = exact_reference
        reference_score = balanced_score(reference, jobs)
        for index, result in enumerate(results):
            same_as_reference = metric_key(result, jobs, objective) == metric_key(reference, jobs, objective)
            result["optimality_status"] = (
                "OPTIMAL_CONFIRMED" if exact_reference is not None and same_as_reference
                else "GAP_TO_OPTIMUM" if exact_reference is not None
                else "BEST_KNOWN" if index == 0 else "CANDIDATE"
            )
            score = balanced_score(result, jobs)
            result["optimality_gap_pct"] = round(
                max(0.0, score - reference_score) / max(abs(reference_score), 1e-9) * 100, 3
            )
    return results


def _robust_mc_sequence(
    jobs: list[Job],
    *,
    n_machines: int,
    objective: str,
    unavailable_machines: tuple[int, ...],
    machine_specs: tuple[MachineSpec, ...] | list[MachineSpec] | None = None,
):
    candidate_builders: tuple[Callable[[list[Job]], list[Job]], ...] = (
        sequence_mt,
        sequence_mo,
        sequence_mzo,
        sequence_slack,
        sequence_cr,
        lambda values: sequence_neh(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        lambda values: sequence_local_search(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        lambda values: sequence_eco_waste(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
        lambda values: sequence_component_ready_edd(
            values,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        ),
    )
    candidates: dict[tuple[str, ...], list[Job]] = {}
    for builder in candidate_builders:
        sequence = builder(jobs)
        candidates.setdefault(tuple(job.job_id for job in sequence), sequence)
    machine_ids = [
        str(machine_id)
        for machine_id in range(1, n_machines + 1)
        if machine_id not in set(unavailable_machines)
    ]
    if not machine_ids:
        raise ValueError("ROBUST_MC wymaga przynajmniej jednej dostepnej maszyny.")
    if machine_specs is None:
        machines = default_queue_machine_specs(machine_ids)
    else:
        machines = tuple(
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
            for index, machine in enumerate(machine_specs, 1)
            if index not in set(unavailable_machines)
        )
    config = MonteCarloConfig()
    best_sequence: list[Job] | None = None
    best_risk = None
    best_key: tuple | None = None
    for sequence in candidates.values():
        evaluation = evaluate_sequence(
            sequence,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
            machine_specs=machine_specs,
        )
        events = _evaluation_events(evaluation)
        if events.empty:
            continue
        risk = simulate_schedule_risk(events, machines, config)
        mean_makespan = float(risk.summary["mean_makespan_h"])
        p90_makespan = float(risk.summary["p90_makespan_h"])
        mean_lateness = float(risk.summary["mean_lateness_h"])
        p90_lateness = float(risk.summary["p90_lateness_h"])
        robust_time = mean_makespan + config.risk_aversion * max(
            0.0, p90_makespan - mean_makespan
        )
        robust_lateness = mean_lateness + config.risk_aversion * max(
            0.0, p90_lateness - mean_lateness
        )
        candidate_key: tuple[object, ...]
        if objective == "waste_then_deadline":
            candidate_key = (evaluation["unscheduled_count"], evaluation["total_waste_kg"], robust_lateness, robust_time)
        elif objective == "makespan_then_deadline":
            candidate_key = (evaluation["unscheduled_count"], robust_time, robust_lateness, evaluation["total_waste_kg"])
        elif objective == "balanced":
            candidate_key = (
                evaluation["unscheduled_count"],
                balanced_score(evaluation, jobs) + robust_lateness / max(1.0, sum(job.deadline for job in jobs)),
                robust_time,
            )
        else:
            candidate_key = (evaluation["unscheduled_count"], robust_lateness, evaluation["total_waste_kg"], robust_time)
        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_sequence = sequence
            best_risk = risk
    if best_sequence is None or best_risk is None:
        raise ValueError("ROBUST_MC nie znalazl wykonalnego wariantu kolejki.")
    return best_sequence, best_risk


def _best_with_machine_specs(
    jobs: list[Job],
    *,
    n_machines: int,
    objective: str,
    unavailable_machines: tuple[int, ...],
    machine_specs: tuple[MachineSpec, ...] | list[MachineSpec],
) -> list[Job]:
    best_sequence = list(jobs)
    best_key: tuple | None = None
    for candidate in permutations(jobs):
        sequence = list(candidate)
        evaluation = evaluate_sequence(
            sequence,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
            machine_specs=machine_specs,
        )
        candidate_key = metric_key(evaluation, jobs, objective)
        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_sequence = sequence
    return best_sequence


def _evaluation_events(evaluation: dict) -> pd.DataFrame:
    rows = []
    for step in evaluation.get("steps", []):
        if not step.get("scheduled", True):
            continue
        rows.append(
            {
                "sto_job_id": step["job_id"],
                "machine_id": str(step["machine_id"]),
                "setup_start": float(step["start_time"]) - float(step["setup_time"]),
                "setup_h": float(step["setup_time"]),
                "t_start": float(step["start_time"]),
                "t_end": float(step["completion_time"]),
                "czas_produkcji_h": max(
                    0.0, float(step["completion_time"]) - float(step["start_time"])
                ),
                "termin_h": float(step["deadline"]),
            }
        )
    return pd.DataFrame(rows)
