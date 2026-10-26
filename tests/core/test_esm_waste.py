from __future__ import annotations

import random
from dataclasses import replace
from itertools import permutations
from unittest.mock import patch

import pytest

from AOA.core.engineering_methods import _choose_robust, sequence_eco_flowshop
from AOA.core.esm_costs import objective_value
from AOA.core.esm_project import build_mopt_solution_tree, evaluate_esm_methods
from AOA.core.flowshop import FlowShopJob, evaluate_flowshop, flowshop_key, solve_flowshop
from AOA.core.monte_carlo import MonteCarloConfig
from AOA.core.optimization.models import Job


def independent(order, stages):
    """Separate recurrence including release, setup and one waste charge per job."""
    ends = [0.0] * stages
    waste = sto = 0.0
    previous = None
    for job in order:
        if job.stock_status == "UNSCHEDULABLE":
            continue
        factor = 0.0
        if previous is not None:
            material = previous.material != job.material
            shape = previous.shape != job.shape
            factor = 1.2 if material and shape else 1.0 if material else 0.45 if shape else 0.0
        upstream = job.components_ready_h
        setups = job.machine_setup_times or (job.setup_time,) * stages
        for stage in range(stages):
            ends[stage] = (
                max(ends[stage], upstream) + factor * setups[stage] + job.machine_times[stage]
            )
            upstream = ends[stage]
        waste += job.waste_kg + factor * job.changeover_waste_kg
        sto += max(0, ends[-1] - job.deadline)
        previous = job
    return tuple(round(v, 9) for v in (waste, sto, ends[-1]))


def conflict_jobs(stages=1):
    return [
        FlowShopJob(
            name,
            stages,
            due,
            material=material,
            machine_times=(1,) * stages,
            changeover_waste_kg=10,
            waste_kg=2,
        )
        for name, due, material in [("A", 1, "steel"), ("B", 2, "brass"), ("C", 3, "steel")]
    ]


@pytest.mark.parametrize("stages", range(1, 9))
@pytest.mark.parametrize("seed", range(4))
def test_waste_solver_matches_independent_complete_search(stages, seed):
    rng = random.Random(seed)
    jobs = [
        FlowShopJob(
            str(i),
            1,
            rng.randint(1, 55),
            material=rng.choice(["steel", "brass"]),
            shape=rng.choice(["round", "square"]),
            components_ready_h=rng.randint(0, 15),
            machine_times=tuple(rng.randint(1, 8) for _ in range(stages)),
            machine_setup_times=tuple(rng.randint(0, 4) for _ in range(stages)),
            waste_kg=rng.choice([0, 0.2, 1]),
            changeover_waste_kg=rng.choice([0, 0.5, 2, 8]),
            tardiness_cost_per_min=rng.choice([0, 1, 100]),
            allowed_tardiness_min=rng.randint(0, 20),
        )
        for i in range(5)
    ]
    if seed == 3:
        jobs[-1] = replace(jobs[-1], stock_status="UNSCHEDULABLE")
    oracle = min(independent(order, stages) for order in permutations(jobs))
    solved = solve_flowshop(jobs, n_machines=stages, objective="waste")
    assert solved.confirmed
    assert flowshop_key(solved.evaluation)[1:] == oracle
    assert solved.lower_bound == pytest.approx(oracle[0])
    assert sum(s.get("waste_kg", 0) for s in solved.evaluation["steps"]) == pytest.approx(oracle[0])
    best_path = max((p for p, state in solved.trace.items() if state["status"] == "best"), key=len)
    assert solved.trace[best_path]["objective_value"] == pytest.approx(oracle[0])
    assert solved.trace[best_path]["sto"] == pytest.approx(oracle[1])


def test_eco_can_trade_more_tardiness_for_less_waste_without_changing_default():
    jobs = conflict_jobs()
    original = tuple(jobs)
    default = evaluate_flowshop(sequence_eco_flowshop(jobs, n_machines=1), n_machines=1)
    waste = evaluate_flowshop(
        sequence_eco_flowshop(jobs, n_machines=1, objective="waste"),
        n_machines=1,
        objective="waste",
    )
    assert (default["sto"], default["total_waste_kg"]) == (0, 26)
    assert (waste["sto"], waste["total_waste_kg"]) == (1, 16)
    assert tuple(jobs) == original


def test_equal_waste_is_broken_by_sto_and_not_cost():
    jobs = [
        FlowShopJob("A", 10, 10, machine_times=(10,), tardiness_cost_per_min=100),
        FlowShopJob("B", 1, 1, machine_times=(1,), tardiness_cost_per_min=1),
    ]
    result = solve_flowshop(jobs, n_machines=1, objective="waste").evaluation
    assert result["order"] == ["B", "A"] and result["sto"] == 1
    assert result["total_tardiness_cost"] == 100
    assert result["total_waste_kg"] == 0


def test_equal_waste_and_sto_are_broken_by_makespan():
    jobs = [
        FlowShopJob("B", 11, 100, machine_times=(10, 1)),
        FlowShopJob("A", 11, 100, machine_times=(1, 10)),
    ]
    result = solve_flowshop(jobs, n_machines=2, objective="waste").evaluation
    assert result["order"] == ["A", "B"]
    assert (result["total_waste_kg"], result["sto"], result["completion_total"]) == (0, 0, 12)


def test_waste_ranking_tree_and_scalar_input_share_the_same_criterion():
    jobs = [
        Job("A", 1, 1, material="a", changeover_waste_kg=10),
        Job("B", 1, 2, material="b", changeover_waste_kg=10),
        Job("C", 1, 3, material="a", changeover_waste_kg=10),
    ]
    results = evaluate_esm_methods(
        jobs, ["MT", "MO", "MZO", "ECO_WASTE", "MOPT"], objective="waste"
    )
    assert [flowshop_key(r) for r in results] == sorted(flowshop_key(r) for r in results)
    eco = next(r for r in results if r["method"] == "ECO_WASTE")
    assert eco["optimality_status"] == "OPTIMAL_CONFIRMED" and eco["waste_gap_kg"] == 0
    mt = next(r for r in results if r["method"] == "MT")
    assert mt["waste_gap_kg"] == 10 and mt["optimality_status"] == "GAP_TO_OPTIMUM"
    tree = build_mopt_solution_tree(jobs, objective="waste")
    assert "Odpad [kg]=10" in tree[0].details
    assert any("Odpad [kg] prefiksu=" in n.details for n in tree if n.depth)
    assert objective_value(eco) == 10
    with pytest.raises(ValueError):
        build_mopt_solution_tree(
            jobs,
            solution=next(r for r in results if r["method"] == "MOPT")["flowshop_solution"],
            objective="sto",
        )


def test_waste_limits_and_all_blocked_jobs_never_claim_a_complete_optimum():
    jobs = conflict_jobs(3)
    limited = solve_flowshop(jobs, n_machines=3, objective="waste", max_states=0)
    assert not limited.confirmed and limited.evaluation["optimality_status"] == "BEST_KNOWN"
    assert limited.lower_bound <= limited.evaluation["total_waste_kg"]
    blocked = [replace(j, stock_status="UNSCHEDULABLE") for j in jobs]
    result = solve_flowshop(blocked, n_machines=3, objective="waste").evaluation
    assert result["optimality_status"] == "PARTIAL_PLAN" and result["unscheduled_count"] == 3
    assert (result["sto"], result["total_waste_kg"], result["completion_total"]) == (0, 0, 0)


@pytest.mark.parametrize("solver", [False, True])
@pytest.mark.parametrize("transitions", [False, True])
def test_finite_inputs_with_overflowing_total_waste_are_rejected(solver, transitions):
    jobs = [
        FlowShopJob(
            str(i),
            1,
            10,
            material=str(i),
            shape=str(i),
            machine_times=(1,),
            waste_kg=0 if transitions else 1e308,
            changeover_waste_kg=1.7e308 if transitions else 0,
        )
        for i in range(2)
    ]
    with pytest.raises(ValueError, match="odpadu"):
        (solve_flowshop if solver else evaluate_flowshop)(jobs, n_machines=1, objective="waste")


def test_robust_keeps_deterministic_waste_first_and_uses_risk_only_for_ties():
    jobs = conflict_jobs()
    orders = [jobs, [jobs[0], jobs[2], jobs[1]], [jobs[2], jobs[0], jobs[1]]]
    candidates = [evaluate_flowshop(order, n_machines=1, objective="waste") for order in orders]
    with patch("AOA.core.monte_carlo._sample_downtime", return_value=(0, 0)):
        result = _choose_robust(candidates, n_machines=1, config=MonteCarloConfig(iterations=20))
    assert result["total_waste_kg"] == 16 and result["sto"] == 1
    assert result["risk_validation_summary"]["seed"] == 43
    # The simulator rounds event hours to six decimal places.
    assert result["risk_validation_summary"]["mean_lateness_min"] == pytest.approx(1, abs=6e-5)
    assert result["optimality_status"] == "RISK_ASSESSED"
