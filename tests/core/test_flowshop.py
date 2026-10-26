from __future__ import annotations

import random
from dataclasses import replace
from itertools import permutations
from pathlib import Path

import pandas as pd
import pytest

from AOA.core.esm_project import (
    build_esm_gantt_rows,
    build_mopt_solution_tree,
    dataframe_to_esm_jobs,
    evaluate_esm_methods,
    load_esm_jobs,
)
from AOA.core.flowshop import FlowShopJob, evaluate_flowshop, solve_flowshop
from AOA.gui.engineering_charts import build_esm_gantt_figure, build_mopt_tree_figure


def independent_score(jobs, order, stages):
    """Small exhaustive test oracle, independent of solver bounds and recurrence helper."""
    matrix = [[0.0] * stages for _ in order]
    score = 0.0
    for row, i in enumerate(order):
        for machine in range(stages):
            upstream = matrix[row][machine - 1] if machine else 0
            preceding = matrix[row - 1][machine] if row else 0
            matrix[row][machine] = max(upstream, preceding) + jobs[i].machine_times[machine]
        score += max(0, matrix[row][-1] - jobs[i].deadline)
    return score, matrix[-1][-1]


@pytest.mark.parametrize(("example", "expected"), [(1, 9), (2, 6), (3, 1), (4, 0)])
def test_paper_examples_reproduce_tables(example, expected):
    jobs = load_esm_jobs(f"data/esm/article/esm_paper_{example:02}.csv")
    result = solve_flowshop(jobs, n_machines=2)
    assert result.confirmed
    assert result.evaluation["sto"] == expected
    oracle = min(independent_score(jobs, p, 2) for p in permutations(range(len(jobs))))
    assert (result.evaluation["sto"], result.evaluation["completion_total"]) == oracle


def test_paper_three_shorter_makespan_can_have_worse_tardiness():
    jobs = load_esm_jobs("data/esm/article/esm_paper_03.csv")
    optimum = evaluate_flowshop([jobs[1], jobs[2], jobs[0]], n_machines=2)
    short = evaluate_flowshop(jobs, n_machines=2)
    assert (optimum["sto"], optimum["completion_total"]) == (1, 18)
    assert (short["sto"], short["completion_total"]) == (4, 15)


@pytest.mark.parametrize("stages", [1, 2, 3, 8])
@pytest.mark.parametrize("seed", range(5))
def test_branch_bounds_and_dominance_agree_with_exhaustive_oracle(stages, seed):
    rng = random.Random(seed)
    jobs = []
    for i in range(6):
        times = tuple(rng.randint(1, 16) / 4 for _ in range(stages))
        jobs.append(
            FlowShopJob(
                job_id=f"J{i}",
                processing_time=sum(times),
                deadline=rng.randint(5, 35),
                machine_times=times,
            )
        )
    oracle = min(independent_score(jobs, p, stages) for p in permutations(range(6)))
    result = solve_flowshop(jobs, n_machines=stages)
    assert result.confirmed
    assert (result.evaluation["sto"], result.evaluation["completion_total"]) == oracle


def test_primary_ten_job_example_is_solved_and_all_rules_are_comparable():
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_three_machines.csv")
    results = evaluate_esm_methods(jobs, ["MT", "MO", "MZO", "MOPT"], n_machines=3)
    assert {r["method"]: r["sto"] for r in results} == {
        "MT": 157,
        "MO": 328,
        "MZO": 458,
        "MOPT": 96,
    }
    assert results[0]["method"] == "MOPT"
    assert results[0]["optimality_status"] == "OPTIMAL_CONFIRMED"
    for result in results:
        assert len(result["steps"]) == 30
        assert set(result["order"]) == {j.job_id for j in jobs}
        assert sum(s["tardiness_positive"] for s in result["steps"]) == result["sto"]
        assert result["unscheduled_count"] == 0
        for machine in range(1, 4):
            operations = [s for s in result["steps"] if s["machine_id"] == machine]
            assert [s["job_id"] for s in operations] == result["order"]
            assert all(
                a["completion_time"] <= b["start_time"]
                for a, b in zip(operations, operations[1:], strict=False)
            )
        for job in jobs:
            operations = [s for s in result["steps"] if s["job_id"] == job.job_id]
            assert all(
                a["completion_time"] <= b["start_time"]
                for a, b in zip(operations, operations[1:], strict=False)
            )


@pytest.mark.parametrize("limits", [{"max_states": 0}, {"max_states": 1}, {"time_limit_s": 0}])
def test_budget_exhaustion_keeps_feasible_incumbent_without_claiming_optimum(limits):
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_three_machines.csv")
    result = solve_flowshop(jobs, n_machines=3, **limits)
    assert not result.confirmed
    assert result.stop_reason
    assert result.evaluation["optimality_status"] == "BEST_KNOWN"
    assert result.lower_bound <= result.evaluation["sto"]
    assert len(result.evaluation["steps"]) == 30
    nodes = build_mopt_solution_tree(jobs, n_machines=3, solution=result, max_nodes=11)
    assert len(nodes) == 11
    assert "niepotwierdzone" in nodes[0].details


def test_tree_is_capped_preserves_solution_and_only_uses_real_trace_records():
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_three_machines.csv")
    solved = solve_flowshop(jobs, n_machines=3)
    nodes = build_mopt_solution_tree(jobs, n_machines=3, solution=solved, max_nodes=40)
    assert len(nodes) <= 40
    by_id = {n.node_id: n for n in nodes}
    for node in nodes:
        if node.parent_id:
            assert node.parent_id in by_id
            assert by_id[node.parent_id].depth + 1 == node.depth
    best = [n for n in nodes if n.chosen and n.parent_id]
    assert [n.edge_label for n in sorted(best, key=lambda n: n.depth)] == solved.evaluation["order"]
    assert any(n.status == "odrzucony" for n in nodes)
    assert len(solved.trace) <= 2511
    assert "STO=96" in nodes[0].details
    figure = build_mopt_tree_figure(nodes)
    best_leaf = next(n for n in best if n.leaf)
    leaf_text = next(
        t.get_text() for t in figure.axes[0].texts if t.get_text().startswith(best_leaf.label)
    )
    assert solved.evaluation["order"][-1] in leaf_text.split("kolejnosc:")[1]


def test_tree_refuses_a_cached_solution_for_different_input():
    jobs = load_esm_jobs("data/esm/article/esm_paper_01.csv")
    solved = solve_flowshop(jobs, n_machines=2)
    with pytest.raises(ValueError, match="tych samych danych"):
        build_mopt_solution_tree(
            [replace(jobs[0], deadline=1), *jobs[1:]], n_machines=2, solution=solved
        )


def test_every_bundled_flow_file_runs_all_four_methods():
    for path in Path("data/esm").rglob("*.csv"):
        jobs = load_esm_jobs(path)
        if not jobs[0].machine_times:
            continue
        count = len(jobs[0].machine_times)
        assert 1 <= count <= 8
        results = evaluate_esm_methods(jobs, ["MT", "MO", "MZO", "MOPT"], n_machines=count)
        assert len(results) == 4
        assert next(r for r in results if r["method"] == "MOPT")["optimality_status"] == (
            "PARTIAL_PLAN"
            if any(j.stock_status == "UNSCHEDULABLE" for j in jobs)
            else "OPTIMAL_CONFIRMED"
        )


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-1", "abc", ""])
def test_csv_rejects_invalid_stage_times_with_row_number(value):
    frame = pd.DataFrame({"zlecenie": ["Z1"], "czas_m1_min": [value], "termin_min": [10]})
    with pytest.raises(ValueError, match="Wiersz 2"):
        dataframe_to_esm_jobs(frame)


@pytest.mark.parametrize(
    "columns",
    [
        {"czas_m2_min": [2]},
        {"czas_m1_min": [1], "czas_m3_min": [3]},
        {"czas_m1_min": [1], "czas_m9_min": [9]},
    ],
)
def test_csv_rejects_missing_or_excess_machine_columns(columns):
    with pytest.raises(ValueError, match="bez luk"):
        dataframe_to_esm_jobs(pd.DataFrame({"zlecenie": ["Z1"], "termin_min": [10], **columns}))


def test_flowshop_rejects_missing_times_and_parallel_only_constraints():
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_three_machines.csv")
    with pytest.raises(ValueError, match="wybrano 4"):
        solve_flowshop(jobs, n_machines=4)
    with pytest.raises(ValueError, match="stalej trasy"):
        solve_flowshop([replace(jobs[0], eligible_machines=(1,))], n_machines=3)


def test_eight_machine_gantt_has_all_operations_and_stable_job_colours():
    jobs = load_esm_jobs("tests/fixtures/esm/esm_flow_10_eight_machines.csv")
    result = evaluate_esm_methods(jobs, ["MO"], n_machines=8)[0]
    assert len(build_esm_gantt_rows(result)) == 80
    figure = build_esm_gantt_figure(result, "MO")
    axis = figure.axes[0]
    assert [t.get_text() for t in axis.get_yticklabels()] == [f"M{i}" for i in range(1, 9)]
    assert len({p.get_facecolor() for p in axis.patches[:8]}) == 1
    assert len(axis.lines) == 10  # deadlines only once per job, on its final operation
