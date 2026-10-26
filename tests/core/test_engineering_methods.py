from __future__ import annotations

import random
from dataclasses import replace
from itertools import permutations

import pandas as pd
import pytest

from AOA.core.engineering_methods import (
    _refine,
    evaluate_robust_flowshop,
    sequence_component_ready_flowshop,
    sequence_eco_flowshop,
)
from AOA.core.esm_project import (
    ESM_METHODS,
    build_esm_gantt_rows,
    build_mopt_solution_tree,
    dataframe_to_esm_jobs,
    evaluate_esm_methods,
    load_esm_jobs,
)
from AOA.core.flowshop import FlowShopJob, evaluate_flowshop, flowshop_key, solve_flowshop
from AOA.core.machine_catalog import MachineSpec, ReliabilitySpec
from AOA.core.monte_carlo import MonteCarloConfig
from AOA.core.optimization.models import Job
from AOA.gui.engineering_charts import build_esm_gantt_figure

EXAMPLE = "tests/fixtures/esm/esm_flow_10_eco_components.csv"
EXTRA = ["ECO_WASTE", "COMPONENT_READY_EDD", "ROBUST_MC"]


def independent_extended_score(jobs, order, stages):
    """Independent tiny exhaustive oracle, without production helpers."""
    ready = [0.0] * stages
    previous = None
    sto = waste = 0.0
    for i in order:
        job = jobs[i]
        if job.stock_status == "UNSCHEDULABLE":
            continue
        factor = 0.0
        if previous is not None:
            different_material = job.material != previous.material
            different_shape = job.shape != previous.shape
            factor = (
                1.2
                if different_material and different_shape
                else 1
                if different_material
                else 0.45
                if different_shape
                else 0
            )
        upstream = job.components_ready_h
        for stage in range(stages):
            setup = (job.machine_setup_times or (job.setup_time,) * stages)[stage] * factor
            upstream = max(ready[stage], upstream) + setup + job.machine_times[stage]
            ready[stage] = upstream
        sto += max(0, ready[-1] - job.deadline)
        waste += job.waste_kg + job.changeover_waste_kg * factor
        previous = job
    return tuple(round(v, 9) for v in (sto, waste, ready[-1]))


@pytest.mark.parametrize("stages", [1, 3, 8])
@pytest.mark.parametrize("seed", range(5))
def test_extended_bounds_and_last_material_state_agree_with_exhaustive_search(stages, seed):
    rng = random.Random(seed)
    jobs = [
        FlowShopJob(
            job_id=f"J{i}",
            processing_time=1,
            deadline=rng.randint(5, 45),
            machine_times=tuple(rng.randint(1, 8) for _ in range(stages)),
            machine_setup_times=tuple(rng.randint(0, 5) for _ in range(stages)),
            material=rng.choice(["a", "b"]),
            shape=rng.choice(["P", "W"]),
            waste_kg=0.2,
            changeover_waste_kg=rng.randint(0, 3),
            components_ready_h=rng.randint(0, 15),
        )
        for i in range(5)
    ]
    expected = min(
        independent_extended_score(jobs, order, stages) for order in permutations(range(5))
    )
    solved = solve_flowshop(jobs, n_machines=stages)
    assert solved.confirmed
    assert flowshop_key(solved.evaluation)[1:] == pytest.approx(expected)


def test_setup_ready_and_waste_are_counted_once_at_the_right_stage():
    a = FlowShopJob(
        "A",
        5,
        100,
        machine_times=(2, 3),
        machine_setup_times=(2, 4),
        material="a",
        shape="P",
        waste_kg=1,
        changeover_waste_kg=1,
    )
    same = evaluate_flowshop([a, replace(a, job_id="B")], n_machines=2)
    changed = evaluate_flowshop([a, replace(a, job_id="B", material="b")], n_machines=2)
    delayed = evaluate_flowshop(
        [a, replace(a, job_id="B", material="b", components_ready_h=10)], n_machines=2
    )
    assert (same["completion_total"], same["total_waste_kg"]) == (8, 2)
    assert (changed["completion_total"], changed["total_waste_kg"]) == (13, 3)
    assert delayed["completion_total"] == 21
    assert [s["setup_start"] for s in delayed["steps"] if s["job_id"] == "B"] == [10, 14]
    assert sum(s["waste_kg"] for s in delayed["steps"]) == delayed["total_waste_kg"]


def test_all_seven_methods_respect_the_same_resources_on_the_ten_job_example():
    jobs = load_esm_jobs(EXAMPLE)
    results = evaluate_esm_methods(jobs, list(ESM_METHODS), n_machines=3)
    assert len(results) == 7
    by_id = {j.job_id: j for j in jobs}
    for result in results:
        assert len(result["steps"]) == 30
        order = [
            next(i for i, j in enumerate(jobs) if j.job_id == name) for name in result["order"]
        ]
        assert flowshop_key(result)[1:] == pytest.approx(independent_extended_score(jobs, order, 3))
        for step in result["steps"]:
            if step["machine_id"] == 1:
                assert step["setup_start"] >= by_id[step["job_id"]].components_ready_h - 1e-9
        for machine in range(1, 4):
            steps = [s for s in result["steps"] if s["machine_id"] == machine]
            assert all(
                a["completion_time"] <= b["setup_start"] + 1e-9
                for a, b in zip(steps, steps[1:], strict=False)
            )
        assert len(build_esm_gantt_rows(result)) == 30
    robust = next(r for r in results if r["method"] == "ROBUST_MC")
    assert robust["optimality_status"] == "RISK_ASSESSED"
    assert robust["risk_summary"]["iterations"] == 1000
    assert robust["risk_summary"]["mean_makespan_min"] >= robust["completion_total"] - 0.001


@pytest.mark.parametrize("method", EXTRA + ["MOPT", "MT"])
def test_missing_components_block_the_whole_order_without_partial_operations(method):
    jobs = load_esm_jobs(EXAMPLE)[:3]
    jobs[1] = replace(jobs[1], stock_status="UNSCHEDULABLE")
    result = evaluate_esm_methods(jobs, [method], n_machines=3)[0]
    assert result["unscheduled_count"] == 1
    assert result["blocked_jobs"] == [jobs[1].job_id]
    assert result["optimality_status"] == "PARTIAL_PLAN"
    assert len(build_esm_gantt_rows(result)) == 6
    assert not any(s["scheduled"] for s in result["steps"] if s["job_id"] == jobs[1].job_id)
    if method == "MOPT":
        nodes = build_mopt_solution_tree(jobs, n_machines=3, solution=result["flowshop_solution"])
        assert any(n.chosen and n.leaf and n.depth == 2 for n in nodes)


def test_all_orders_blocked_returns_a_partial_plan_and_unavailable_risk():
    jobs = [replace(j, stock_status="UNSCHEDULABLE") for j in load_esm_jobs(EXAMPLE)[:2]]
    results = evaluate_esm_methods(jobs, [*EXTRA, "MOPT"], n_machines=3)
    for result in results:
        assert result["unscheduled_count"] == 2
        assert result["completion_total"] == 0
        assert result["optimality_status"] == "PARTIAL_PLAN"
        assert not build_esm_gantt_rows(result)
        figure = build_esm_gantt_figure(result, result["method"])
        assert len(figure.axes[0].get_yticklabels()) == 3
    robust = next(r for r in results if r["method"] == "ROBUST_MC")
    assert robust["risk_summary"]["available"] is False


def test_mc_hours_conversion_and_no_failure_control_reproduce_nominal_schedule():
    jobs = load_esm_jobs(EXAMPLE)[:3]
    machines = [MachineSpec(str(i), f"M{i}", "FLOW") for i in range(1, 4)]
    result = evaluate_robust_flowshop(
        jobs, n_machines=3, machines=machines, config=MonteCarloConfig(iterations=50)
    )
    risk = result["risk_summary"]
    assert risk["failure_probability"] == 0
    assert risk["mean_makespan_min"] == pytest.approx(result["completion_total"], abs=0.001)
    assert risk["mean_lateness_min"] == pytest.approx(result["sto"], abs=0.001)


def test_mc_propagates_an_upstream_failure_through_all_three_stages():
    job = FlowShopJob("Z1", 6, 1000, machine_times=(2, 2, 2))
    machines = [
        MachineSpec(
            str(i),
            f"M{i}",
            "FLOW",
            reliability=ReliabilitySpec(mtbf_h=0.01, mttr_h=0.5) if i == 1 else ReliabilitySpec(),
        )
        for i in range(1, 4)
    ]
    result = evaluate_robust_flowshop(
        [job],
        n_machines=3,
        machines=machines,
        config=MonteCarloConfig(iterations=100, repair_sigma=0),
    )
    risk = result["risk_summary"]
    assert risk["mean_makespan_min"] == pytest.approx(6 + risk["mean_downtime_min"], abs=0.001)
    assert risk["p90_makespan_min"] > 6


def test_mc_is_repeatable_for_a_fixed_seed():
    jobs = load_esm_jobs(EXAMPLE)[:3]
    config = MonteCarloConfig(iterations=60, seed=123)
    first = evaluate_robust_flowshop(jobs, n_machines=3, config=config)
    second = evaluate_robust_flowshop(jobs, n_machines=3, config=config)
    assert first["order"] == second["order"]
    assert first["risk_summary"] == second["risk_summary"]
    assert first["risk_validation_summary"] == second["risk_validation_summary"]


@pytest.mark.parametrize("stages", range(1, 9))
def test_refined_methods_remain_feasible_on_one_through_eight_machines(stages):
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_eight_machines.csv")
    for method in (sequence_eco_flowshop, sequence_component_ready_flowshop):
        sequence = method(jobs, n_machines=stages)
        assert {j.job_id for j in sequence} == {j.job_id for j in jobs}
        evaluated = evaluate_flowshop(sequence, n_machines=stages)
        indices = [jobs.index(j) for j in sequence]
        assert flowshop_key(evaluated)[1:] == pytest.approx(
            independent_extended_score(jobs, indices, stages)
        )


@pytest.mark.parametrize(
    ("filename", "expected"), [("eco_trap", (86, 30, 205)), ("component_wait", (92, 22, 193))]
)
def test_counterexamples_reach_the_proven_optimum_after_additional_refinement(filename, expected):
    jobs = load_esm_jobs(f"tests/fixtures/esm/esm_flow_10_{filename}.csv")
    optimum = solve_flowshop(jobs, n_machines=3)
    assert optimum.confirmed
    for method in (sequence_eco_flowshop, sequence_component_ready_flowshop):
        result = evaluate_flowshop(method(jobs, n_machines=3), n_machines=3)
        assert flowshop_key(result)[1:] == expected
        assert flowshop_key(result) == flowshop_key(optimum.evaluation)


def test_refinement_budget_returns_a_complete_nonworse_incumbent(monkeypatch):
    import AOA.core.engineering_methods as module

    jobs = load_esm_jobs(EXAMPLE)
    baseline = evaluate_flowshop(jobs, n_machines=3)
    original = module.evaluate_flowshop
    evaluations = []

    def counted(*args, **kwargs):
        evaluations.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "evaluate_flowshop", counted)
    order = _refine([jobs], 3, max_evaluations=12)
    assert len(evaluations) == 12
    assert len(order) == len(jobs)
    assert flowshop_key(original(order, n_machines=3)) <= flowshop_key(baseline)


def test_intentional_idle_avoids_delaying_the_urgent_delivery():
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_intentional_idle.csv")
    busy = evaluate_flowshop(jobs, n_machines=3)
    solved = solve_flowshop(jobs, n_machines=3)
    assert busy["sto"] == 35
    assert solved.confirmed and solved.evaluation["sto"] == 0
    first = solved.evaluation["steps"][0]
    assert (first["job_id"], first["setup_start"]) == ("Z2", 5)
    figure = build_esm_gantt_figure(solved.evaluation, "MOpt")
    assert 70 < figure.axes[0].get_xlim()[1] < 80
    assert any("Terminy poza zakresem" in text.get_text() for text in figure.axes[0].texts)


def test_limited_mopt_can_lose_to_a_heuristic_without_disproving_its_optimum():
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_urgent.csv")
    limited = solve_flowshop(jobs, n_machines=3, max_states=100)
    component = evaluate_flowshop(
        sequence_component_ready_flowshop(jobs, n_machines=3), n_machines=3
    )
    exact = solve_flowshop(jobs, n_machines=3)
    assert not limited.confirmed and limited.stop_reason == "limit stanow"
    assert limited.evaluation["sto"] == 90
    assert component["sto"] < limited.evaluation["sto"]
    assert exact.confirmed and exact.evaluation["sto"] == 43
    assert flowshop_key(exact.evaluation) <= flowshop_key(component)


def test_independent_mc_validation_assesses_the_locked_order_without_reselecting():
    from AOA.core.engineering_methods import _events_in_hours
    from AOA.core.monte_carlo import default_queue_machine_specs, simulate_schedule_risk

    jobs = load_esm_jobs(EXAMPLE)[:3]
    config = MonteCarloConfig(iterations=100, seed=123)
    result = evaluate_robust_flowshop(jobs, n_machines=3, config=config)
    validation = result["risk_validation_summary"]
    direct = simulate_schedule_risk(
        _events_in_hours(result),
        default_queue_machine_specs(["1", "2", "3"]),
        replace(config, seed=124),
    )
    assert validation["seed"] == 124 and validation["iterations"] == 100
    assert validation["mean_lateness_min"] == pytest.approx(direct.summary["mean_lateness_h"] * 60)
    assert result["risk_validation_role"] == "held_out_assessment_only"
    low, high = validation["mean_lateness_ci95_min"]
    assert low <= direct.runs["total_lateness_h"].mean() * 60 <= high
    assert validation["mean_ci_available"]


def test_one_simulation_does_not_claim_a_confidence_interval():
    result = evaluate_robust_flowshop(
        load_esm_jobs(EXAMPLE)[:1], n_machines=3, config=MonteCarloConfig(iterations=1)
    )
    assert result["risk_validation_summary"]["mean_ci_available"] is False


def test_robust_keeps_the_previous_risk_candidate_after_nominal_refinement(monkeypatch):
    import AOA.core.engineering_methods as module

    candidates = []

    def capture(values, **kwargs):
        candidates.extend(values)
        return min(values, key=flowshop_key)

    monkeypatch.setattr(module, "_choose_robust", capture)
    evaluate_robust_flowshop(load_esm_jobs(EXAMPLE), n_machines=3)
    previous_order = ["Z3", "Z1", "Z6", "Z5", "Z2", "Z10", "Z7", "Z4", "Z9", "Z8"]
    assert any(c["order"] == previous_order and c["sto"] == pytest.approx(103) for c in candidates)
    assert min(c["sto"] for c in candidates) == pytest.approx(96)


def test_engineering_legacy_mc_60_minutes_is_not_treated_as_sixty_hours():
    result = evaluate_esm_methods([Job("Z1", 60, 120)], ["ROBUST_MC"], n_machines=1)[0]
    risk = result["risk_summary"]
    assert 0.003 < risk["failure_probability"] < 0.025
    assert risk["iterations"] == 1000
    assert risk["p50_makespan_min"] == 60
    assert "mean_makespan_h" not in risk


@pytest.mark.parametrize(
    "column", ["components_ready_min", "odpad_kg", "czas_przezbrojenia_m1_min"]
)
def test_bad_optional_values_are_reported_with_the_csv_row(column):
    frame = pd.DataFrame(
        {"zlecenie": ["Z1"], "czas_m1_min": [2], "termin_min": [20], column: ["inf"]}
    )
    with pytest.raises(ValueError, match="Wiersz 2"):
        dataframe_to_esm_jobs(frame)


def test_setup_column_without_matching_machine_is_rejected():
    frame = pd.DataFrame(
        {
            "zlecenie": ["Z1"],
            "czas_m1_min": [2],
            "termin_min": [20],
            "czas_przezbrojenia_m2_min": [3],
        }
    )
    with pytest.raises(ValueError, match="odpowiadajacych"):
        dataframe_to_esm_jobs(frame)
