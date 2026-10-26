from __future__ import annotations

import json
import random
from dataclasses import replace
from itertools import permutations
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from AOA.core.engineering_methods import _choose_robust
from AOA.core.esm_costs import DelayPenalty, cost_parameters, with_job_penalties
from AOA.core.esm_project import (
    build_mopt_solution_tree,
    dataframe_to_esm_jobs,
    evaluate_esm_methods,
    load_esm_jobs,
    prepare_esm_flow_jobs,
)
from AOA.core.flowshop import FlowShopJob, evaluate_flowshop, flowshop_key, solve_flowshop
from AOA.core.machine_catalog import MachineSpec, ReliabilitySpec
from AOA.core.monte_carlo import MonteCarloConfig, simulate_schedule_risk
from AOA.core.optimization.models import Job

DIRECTORY = Path("data/esm/article/costs")
CASES = json.loads((DIRECTORY / "manifest.json").read_text(encoding="utf-8"))


def independent(jobs, order, stages):
    ends = [0.0] * stages
    sto = cost = 0.0
    for index in order:
        job = jobs[index]
        previous = 0.0
        for stage in range(stages):
            previous = max(previous, ends[stage]) + job.machine_times[stage]
            ends[stage] = previous
        late = max(0.0, ends[-1] - job.deadline)
        sto += late
        cost += getattr(job, "tardiness_cost_per_min", 1.0) * max(
            0.0, late - getattr(job, "allowed_tardiness_min", 0.0)
        )
    return cost, sto, ends[-1]


@pytest.mark.parametrize("case", CASES, ids=[c["file"] for c in CASES])
def test_all_paper_variants_against_independent_exhaustive_search(case):
    path = DIRECTORY / case["file"]
    original = path.read_bytes()
    jobs = prepare_esm_flow_jobs(load_esm_jobs(path), n_machines=case["machines"])
    solved = solve_flowshop(jobs, n_machines=case["machines"], objective="cost", time_limit_s=20)
    oracle = min(
        (round(cost, 9), round(finish, 9))
        for cost, _sto, finish in (
            independent(jobs, p, case["machines"]) for p in permutations(range(len(jobs)))
        )
    )
    assert solved.confirmed
    assert solved.evaluation["total_tardiness_cost"] == case["expected_minimum_cost"] == oracle[0]
    assert solved.evaluation["completion_total"] == oracle[1]
    assert solved.lower_bound == oracle[0]
    assert sum(step.get("tardiness_cost", 0) for step in solved.evaluation["steps"]) == oracle[0]
    assert path.read_bytes() == original


@pytest.mark.parametrize("stages", [1, 2, 3, 8])
@pytest.mark.parametrize("seed", range(8))
def test_weighted_bounds_and_dominance_with_zero_rates_and_different_grace(stages, seed):
    rng = random.Random(seed)
    jobs = [
        FlowShopJob(
            str(i),
            1,
            rng.randint(1, 40),
            machine_times=tuple(rng.randint(1, 10) for _ in range(stages)),
            tardiness_cost_per_min=rng.choice([0, 0.1, 1, 3, 12]),
            allowed_tardiness_min=rng.randint(0, 20),
        )
        for i in range(5)
    ]
    solved = solve_flowshop(jobs, n_machines=stages, objective="cost")
    oracle = min(
        (round(c, 9), round(f, 9))
        for c, _t, f in (independent(jobs, p, stages) for p in permutations(range(len(jobs))))
    )
    assert solved.confirmed
    assert (
        round(solved.evaluation["total_tardiness_cost"], 9),
        solved.evaluation["completion_total"],
    ) == oracle


def test_expensive_z3_changes_the_optimal_order_and_leaves_real_sto_visible():
    jobs = load_esm_jobs(DIRECTORY / "ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv")
    costs = evaluate_esm_methods(
        jobs, ["MOPT", "MT", "MO", "MZO", "ECO_WASTE", "COMPONENT_READY_EDD"], objective="cost"
    )
    time = evaluate_esm_methods(jobs, ["MOPT"], objective="sto")[0]
    optimum = next(r for r in costs if r["method"] == "MOPT")
    assert optimum["order"] == ["Z2", "Z3", "Z1", "Z4"]
    assert (optimum["total_tardiness_cost"], optimum["sto"]) == (110, 130)
    assert (time["total_tardiness_cost"], time["sto"]) == (600, 80)
    tree = build_mopt_solution_tree(jobs, solution=optimum["flowshop_solution"])
    assert "Koszt [j.p.]=110" in tree[0].details
    assert "STO=130 min" in tree[0].details
    assert "j.p." in next(node.details for node in tree if node.depth > 0)


@pytest.mark.parametrize("stages", [1, 3, 8])
def test_runtime_machine_count_never_redistributes_rate_or_grace(stages):
    jobs = load_esm_jobs(DIRECTORY / "ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv")
    prepared = prepare_esm_flow_jobs(jobs, n_machines=stages, time_mode="total")
    assert cost_parameters(prepared) == cost_parameters(jobs)
    evaluation = evaluate_flowshop(prepared, n_machines=stages, objective="cost")
    assert (
        sum(s["tardiness_cost"] for s in evaluation["steps"]) == evaluation["total_tardiness_cost"]
    )


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
@pytest.mark.parametrize("column", ["koszt_opoznienia_na_min", "dopuszczalne_opoznienie_min"])
def test_bad_csv_penalty_is_rejected_with_a_row_number(value, column):
    with pytest.raises(ValueError, match="Wiersz 2"):
        dataframe_to_esm_jobs(
            pd.DataFrame(
                [{"zlecenie": "Z1", "czas_obrobki_min": 10, "termin_min": 5, column: value}]
            )
        )


def test_penalty_is_only_charged_beyond_tolerance_and_only_after_last_operation():
    assert DelayPenalty(3, 10).charge(30, 20) == 0
    assert DelayPenalty(3, 10).charge(32, 20) == 6
    jobs = [
        FlowShopJob(
            "A", 40, 20, machine_times=(20, 20), tardiness_cost_per_min=3, allowed_tardiness_min=10
        )
    ]
    result = evaluate_flowshop(jobs, n_machines=2, objective="cost")
    assert result["sto"] == 20 and result["total_tardiness_cost"] == 30
    assert [step["tardiness_cost"] for step in result["steps"]] == [0, 30]


def test_partial_plan_and_zero_budget_never_claim_full_optimum():
    jobs = load_esm_jobs(DIRECTORY / "ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv")
    result = evaluate_esm_methods(jobs, ["MOPT"], objective="cost", max_states=0)[0]
    assert result["optimality_status"] == "BEST_KNOWN"
    assert result["lower_bound"] <= result["total_tardiness_cost"]
    jobs[0] = replace(jobs[0], stock_status="UNSCHEDULABLE")
    partial = evaluate_esm_methods(jobs, ["MOPT"], objective="cost")[0]
    assert partial["optimality_status"] == "PARTIAL_PLAN" and partial["unscheduled_count"] == 1


def test_editing_penalties_preserves_all_other_job_fields_and_original_objects():
    original = Job("A", 30, 20, material="steel", components_ready_h=5, machine_times=(10, 20))
    jobs = with_job_penalties([original], {"A": DelayPenalty(4, 7)})
    assert jobs[0].material == "steel" and jobs[0].machine_times == (10, 20)
    assert jobs[0].components_ready_h == 5
    assert cost_parameters(jobs)["A"] == {"rate_per_min": 4, "grace_min": 7}
    assert not hasattr(original, "tardiness_cost_per_min")
    with pytest.raises(ValueError):
        with_job_penalties([original], {"other": DelayPenalty()})


def test_mc_charges_each_final_job_in_minutes_and_preserves_legacy_runs():
    events = pd.DataFrame(
        [
            {"sto_job_id": "A", "machine_id": "1", "t_start": 0, "t_end": 0.5, "termin_h": 0.1},
            {"sto_job_id": "B", "machine_id": "1", "t_start": 0.5, "t_end": 1, "termin_h": 0.5},
        ]
    )
    machines = [
        MachineSpec(machine_id="1", name="M1", station_id="QUEUE", reliability=ReliabilitySpec())
    ]
    config = MonteCarloConfig(iterations=20)
    with patch("AOA.core.monte_carlo._sample_downtime", return_value=(0.1, 1)):
        legacy = simulate_schedule_risk(events, machines, config)
        charged = simulate_schedule_risk(
            events,
            machines,
            config,
            delay_penalties={"A": DelayPenalty(2, 5), "B": DelayPenalty(7, 10)},
        )
    pd.testing.assert_frame_equal(legacy.runs, charged.runs.drop(columns="total_tardiness_cost"))
    # A finishes at 36 min, B at 72 min: 2*(36-6-5) + 7*(72-30-10) = 274.
    assert charged.runs["total_tardiness_cost"].tolist() == pytest.approx([274] * 20)
    assert charged.summary["p90_tardiness_cost"] == pytest.approx(274)
    assert "p90_tardiness_cost" not in legacy.summary


@pytest.mark.parametrize("stages", [1, 3, 8])
@pytest.mark.parametrize("seed", range(4))
def test_cost_bounds_with_component_release_and_sequence_dependent_setups(stages, seed):
    rng = random.Random(seed)
    jobs = [
        FlowShopJob(
            str(i),
            1,
            rng.randint(5, 80),
            machine_times=tuple(rng.randint(1, 7) for _ in range(stages)),
            machine_setup_times=tuple(rng.randint(0, 3) for _ in range(stages)),
            material=str(i % 2),
            shape=str(i % 3),
            components_ready_h=rng.randint(0, 15),
            waste_kg=i % 2,
            changeover_waste_kg=0.5,
            tardiness_cost_per_min=rng.choice([0, 0.5, 1, 5]),
            allowed_tardiness_min=rng.randint(0, 15),
        )
        for i in range(5)
    ]
    oracle = min(
        flowshop_key(evaluate_flowshop(order, n_machines=stages, objective="cost"))
        for order in permutations(jobs)
    )
    result = solve_flowshop(jobs, n_machines=stages, objective="cost")
    assert result.confirmed and flowshop_key(result.evaluation) == oracle


def test_robust_cost_criterion_selects_money_instead_of_total_lateness():
    jobs = prepare_esm_flow_jobs(
        load_esm_jobs(DIRECTORY / "ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv"),
        n_machines=1,
    )
    by_id = {j.job_id: j for j in jobs}
    candidates = [
        evaluate_flowshop([by_id[j] for j in order], n_machines=1, objective="cost")
        for order in [("Z2", "Z4", "Z1", "Z3"), ("Z2", "Z3", "Z1", "Z4")]
    ]
    config = MonteCarloConfig(iterations=20)
    with patch("AOA.core.monte_carlo._sample_downtime", return_value=(0, 0)):
        cost = _choose_robust(candidates, n_machines=1, config=config)
        time = _choose_robust(
            [{**c, "objective": "sto"} for c in candidates], n_machines=1, config=config
        )
    assert cost["total_tardiness_cost"] == cost["risk_summary"]["mean_tardiness_cost"] == 110
    assert cost["risk_validation_summary"]["p90_tardiness_cost"] == 110
    assert cost["risk_validation_summary"]["seed"] == 43
    assert time["sto"] == 80 and time["risk_validation_summary"]["mean_tardiness_cost"] == 600
    assert cost["optimality_status"] == "RISK_ASSESSED"


def test_cost_tree_rejects_a_cached_solution_for_another_objective():
    jobs = prepare_esm_flow_jobs(
        load_esm_jobs(DIRECTORY / "ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv"),
        n_machines=1,
    )
    solved = solve_flowshop(jobs, n_machines=1, objective="cost")
    with pytest.raises(ValueError):
        build_mopt_solution_tree(jobs, solution=solved, objective="sto")


def test_penalty_overflow_and_unknown_objective_are_rejected():
    with pytest.raises(ValueError, match="zakres"):
        DelayPenalty(1e308).charge(1e308, 1)
    with pytest.raises(ValueError, match="kryterium"):
        evaluate_esm_methods(
            load_esm_jobs(DIRECTORY / "ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv"),
            ["MT"],
            objective="other",
        )
