from __future__ import annotations

from collections.abc import Callable

from AOA.core.mh_models import get_mh_model_names
from AOA.core.mh_models.custom import get_custom_heuristic_config, sequence_custom_heuristic
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
        if method in method_map:
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
        )
        result = {"method": method, **evaluation}
        result["table_text"] = format_steps_table(result["steps"])
        results.append(result)
    results.sort(key=lambda item: (*metric_key(item, jobs, objective), item["method"]))
    if results:
        reference = results[0]
        exact_reference = None
        if len(jobs) <= 8:
            exact_reference = evaluate_sequence(
                best_by_full_search(
                    jobs,
                    n_machines=n_machines,
                    objective=objective,
                    unavailable_machines=unavailable_machines,
                ),
                n_machines=n_machines,
                objective=objective,
                unavailable_machines=unavailable_machines,
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
