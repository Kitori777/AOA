from __future__ import annotations

from itertools import permutations
from pathlib import Path

import pytest
from matplotlib.patches import Rectangle

from AOA.core.esm_project import (
    ESM_COMPARISON_METHODS,
    ESM_METHODS,
    build_mopt_solution_tree,
    evaluate_esm_methods,
    load_esm_jobs,
    prepare_esm_flow_jobs,
)
from AOA.core.flowshop import FlowShopJob, flowshop_key
from AOA.core.optimization.models import Job
from AOA.gui.engineering_charts import (
    build_esm_gantt_comparison_figure,
    build_esm_gantt_grid_figure,
)


@pytest.mark.parametrize("machines", [1, 2, 3, 8])
@pytest.mark.parametrize("mode", ["total", "per_machine"])
def test_single_time_runs_all_methods_through_each_machine_without_changing_input(machines, mode):
    path = Path("data/esm/esm_jobs.csv")
    source = path.read_bytes()
    jobs = load_esm_jobs(path)
    original = list(jobs)
    results = evaluate_esm_methods(jobs, list(ESM_METHODS), n_machines=machines, time_mode=mode)
    by_id = {j.job_id: j for j in jobs}
    for result in results:
        assert result["model"] == "flowshop"
        assert len(result["steps"]) == len(jobs) * machines
        ends: dict[tuple[str, int], float] = {}
        available = [0.0] * machines
        total_tardiness = 0.0
        for step in result["steps"]:
            stage = step["machine_id"] - 1
            job = by_id[step["job_id"]]
            duration = job.processing_time / machines if mode == "total" else job.processing_time
            assert step["processing_time"] == pytest.approx(duration)
            assert step["start_time"] >= available[stage] - 1e-8
            assert step["start_time"] >= ends.get((job.job_id, stage - 1), 0) - 1e-8
            available[stage] = step["completion_time"]
            ends[job.job_id, stage] = step["completion_time"]
            if stage == machines - 1:
                total_tardiness += max(0.0, step["completion_time"] - job.deadline)
        assert result["sto"] == pytest.approx(total_tardiness)
    # Independent exhaustive recurrence for all four jobs, without production helpers.
    scores = []
    for order in permutations(jobs):
        available = [0.0] * machines
        sto = 0.0
        for job in order:
            upstream = 0.0
            duration = job.processing_time / machines if mode == "total" else job.processing_time
            for stage in range(machines):
                upstream = max(available[stage], upstream) + duration
                available[stage] = upstream
            sto += max(0.0, upstream - job.deadline)
        scores.append((round(sto, 9), 0.0, round(available[-1], 9)))
    optimum = next(r for r in results if r["method"] == "MOPT")
    assert optimum["optimality_status"] == "OPTIMAL_CONFIRMED"
    assert flowshop_key(optimum)[1:] == min(scores)
    assert path.read_bytes() == source
    assert jobs == original and all(not j.machine_times for j in jobs)


def test_existing_explicit_examples_can_be_recalculated_for_any_machine_count():
    for path in Path("data/esm").rglob("*.csv"):
        source = path.read_bytes()
        jobs = load_esm_jobs(path)
        for count in range(1, 9):
            mode = "file" if len(jobs[0].machine_times) == count else "total"
            result = evaluate_esm_methods(jobs, ["MT"], n_machines=count, time_mode=mode)[0]
            assert (
                len([s for s in result["steps"] if s["scheduled"]])
                == (len(jobs) - result["unscheduled_count"]) * count
            )
        assert path.read_bytes() == source


def test_explicit_setup_data_is_preserved_or_redistributed_with_processing_times():
    job = FlowShopJob("Z1", 60, 200, machine_times=(10, 20, 30), machine_setup_times=(2, 4, 6))
    assert prepare_esm_flow_jobs([job], n_machines=3, time_mode="file") == [job]
    divided = prepare_esm_flow_jobs([job], n_machines=2, time_mode="total")[0]
    assert divided.machine_times == (30, 30)
    assert divided.setup_time == 6
    assert job.machine_setup_times == (2, 4, 6)
    repeated = prepare_esm_flow_jobs([job], n_machines=2, time_mode="per_machine")[0]
    assert repeated.machine_times == (60, 60)
    assert repeated.setup_time == 12


@pytest.mark.parametrize("mode", ["total", "per_machine"])
def test_tree_uses_the_same_runtime_operations_as_the_gantt(mode):
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")
    result = evaluate_esm_methods(jobs, ["MOPT"], n_machines=3, time_mode=mode)[0]
    nodes = build_mopt_solution_tree(jobs, n_machines=3, solution=result["flowshop_solution"])
    assert len([n for n in nodes if n.chosen and n.parent_id]) == 4
    assert any(n.chosen and n.leaf for n in nodes)
    assert result["flowshop_solution"].evaluation["sto"] == result["sto"]


def test_four_gantts_have_matching_axes_colors_and_actual_operations():
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")
    results = evaluate_esm_methods(jobs, list(ESM_COMPARISON_METHODS), n_machines=3)
    figure = build_esm_gantt_comparison_figure(results)
    assert len(figure.axes) == 4
    by_method = {r["method"]: r for r in results}
    colors: dict[str, object] = {}
    for method, axis in zip(ESM_COMPARISON_METHODS, figure.axes, strict=True):
        assert axis.get_xlim() == figure.axes[0].get_xlim()
        assert [t.get_text() for t in axis.get_yticklabels()] == ["M1", "M2", "M3"]
        assert len(axis.patches) == 12
        for step, patch in zip(by_method[method]["steps"], axis.patches, strict=True):
            assert isinstance(patch, Rectangle)
            assert patch.get_x() == pytest.approx(step["start_time"])
            assert patch.get_width() == pytest.approx(step["processing_time"])
            color = patch.get_facecolor()
            assert colors.setdefault(step["job_id"], color) == color


def test_comparison_rejects_missing_methods():
    with pytest.raises(ValueError, match="MT, MO, MZO"):
        build_esm_gantt_comparison_figure([])


def test_all_seven_methods_fit_two_pages_with_the_same_scale_and_job_colors():
    results = evaluate_esm_methods(
        load_esm_jobs("data/esm/esm_jobs.csv"), list(ESM_METHODS), n_machines=3
    )
    by_method = {r["method"]: r for r in results}
    ordered = [by_method[m] for m in ESM_METHODS]
    pages = [
        build_esm_gantt_grid_figure(ordered[start : start + 4], context_results=ordered)
        for start in (0, 4)
    ]
    assert [sum(axis.axison for axis in page.axes) for page in pages] == [4, 3]
    all_limits = [axis.get_xlim() for page in pages for axis in page.axes if axis.axison]
    assert all(limits == all_limits[0] for limits in all_limits)
    colors: dict[str, object] = {}
    for result, axis in zip(ordered, [a for p in pages for a in p.axes if a.axison], strict=True):
        assert len(axis.patches) == 12
        for step, rectangle in zip(result["steps"], axis.patches, strict=True):
            assert (
                colors.setdefault(step["job_id"], rectangle.get_facecolor())
                == rectangle.get_facecolor()
            )


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_grid_keeps_one_panel_for_each_selected_method(count):
    results = evaluate_esm_methods(
        load_esm_jobs("data/esm/esm_jobs.csv"), list(ESM_COMPARISON_METHODS), n_machines=2
    )
    figure = build_esm_gantt_grid_figure(results[:count])
    assert len(figure.axes) == 4
    assert sum(axis.axison for axis in figure.axes) == count


def test_grid_rejects_empty_or_oversized_pages():
    with pytest.raises(ValueError, match="1 do 4"):
        build_esm_gantt_grid_figure([])
    result = {"method": "MT"}
    with pytest.raises(ValueError, match="1 do 4"):
        build_esm_gantt_grid_figure([result] * 5)


@pytest.mark.parametrize("machines", [0, 9, True, 2.5])
def test_runtime_adapter_rejects_invalid_counts(machines):
    with pytest.raises(ValueError, match="1 do 8"):
        prepare_esm_flow_jobs([Job("Z1", 10, 30)], n_machines=machines)


def test_runtime_adapter_rejects_unknown_mode_or_missing_stage_data():
    with pytest.raises(ValueError, match="Nieznany"):
        prepare_esm_flow_jobs([Job("Z1", 10, 30)], n_machines=2, time_mode="unknown")
    with pytest.raises(ValueError, match="Brak czasow etapow"):
        prepare_esm_flow_jobs([Job("Z1", 10, 30)], n_machines=2, time_mode="file")
