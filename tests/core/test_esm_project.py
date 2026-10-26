from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from AOA.core.esm_project import (
    ESM_MAX_MACHINES,
    ESM_METHODS,
    build_esm_gantt_rows,
    build_mopt_solution_tree,
    dataframe_to_esm_jobs,
    esm_method_warnings,
    evaluate_esm_methods,
    list_esm_scenarios,
    load_esm_jobs,
)
from AOA.core.queue_service import normalize_queue_frame
from AOA.gui.engineering_charts import build_esm_gantt_figure, build_mopt_tree_figure


def test_esm_file_matches_pdf_and_allows_only_requested_methods() -> None:
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")

    assert [(job.job_id, job.processing_time, job.deadline) for job in jobs] == [
        ("Z1", 10.0, 150.0),
        ("Z2", 20.0, 30.0),
        ("Z3", 100.0, 110.0),
        ("Z4", 50.0, 60.0),
    ]
    results = evaluate_esm_methods(jobs, list(ESM_METHODS))
    assert {result["method"] for result in results} == set(ESM_METHODS)
    assert set(ESM_METHODS) == {
        "MT",
        "MO",
        "MZO",
        "MOPT",
        "ECO_WASTE",
        "COMPONENT_READY_EDD",
        "ROBUST_MC",
    }
    mopt = next(result for result in results if result["method"] == "MOPT")
    assert mopt["order"] == ["Z2", "Z4", "Z1", "Z3"]
    assert mopt["sto"] == 80.0


def test_esm_rejects_bad_rows_with_row_number() -> None:
    frame = pd.DataFrame(
        {
            "zlecenie": ["Z1", "Z1"],
            "czas_obrobki_min": [10, "abc"],
            "termin_min": [20, 30],
        }
    )

    with pytest.raises(ValueError, match="Wiersz 3: powtorzone zlecenie Z1"):
        dataframe_to_esm_jobs(frame)


def test_esm_limits_input_to_ten_jobs() -> None:
    frame = pd.DataFrame(
        {
            "zlecenie": [f"Z{index}" for index in range(11)],
            "czas_obrobki_min": [10] * 11,
            "termin_min": [100] * 11,
        }
    )

    with pytest.raises(ValueError, match="maksymalnie 10"):
        dataframe_to_esm_jobs(frame)


def test_esm_rejects_algorithms_outside_engineering_mode() -> None:
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")

    with pytest.raises(ValueError, match="nie udostepnia metod: GENETIC"):
        evaluate_esm_methods(jobs, ["MT", "GENETIC"])


def test_esm_menu_contains_only_article_examples_and_the_main_file() -> None:
    scenarios = list_esm_scenarios("data/esm")

    assert len(scenarios) == 21
    assert all(s.path.name == "esm_jobs.csv" or "article" in s.path.parts for s in scenarios)
    assert len([s for s in scenarios if s.label.startswith("ART3 |")]) == 7
    assert len([s for s in scenarios if s.label.startswith("DYLEWSKI |")]) == 9
    assert len([s for s in scenarios if s.label.startswith("MPER 2017 |")]) == 4
    assert scenarios[1].path.name == "ART3_Przyklad_2_W2_koszt_300_zamiast_330.csv"
    assert "300 zamiast 330" in scenarios[1].label
    assert scenarios[0].path.name == "esm_jobs.csv"
    assert scenarios[0].machine_count == 1


def test_replaced_example_supplies_explicit_three_stage_times() -> None:
    jobs = load_esm_jobs("tests/fixtures/esm/esm_jobs_08_changeovers.csv")

    assert len(jobs) == 8
    assert all(len(job.machine_times) == 3 for job in jobs)
    assert all(job.processing_time == sum(job.machine_times) for job in jobs)


def test_three_new_methods_run_on_three_machines() -> None:
    jobs = [
        replace(
            job, material="bawelna", shape="PLYTA", waste_kg=1, setup_time=3, components_ready_h=5
        )
        for job in load_esm_jobs("data/esm/esm_jobs.csv")
    ]
    methods = ["ECO_WASTE", "COMPONENT_READY_EDD", "ROBUST_MC"]
    results = evaluate_esm_methods(jobs, methods, n_machines=3)

    assert {result["method"] for result in results} == set(methods)
    assert all(result["machine_count"] == 3 for result in results)
    assert all(result["total_waste_kg"] > 0 for result in results)
    robust = next(result for result in results if result["method"] == "ROBUST_MC")
    assert robust["risk_summary"]["iterations"] == 1000


def test_base_esm_reports_honest_assumptions_for_extended_methods() -> None:
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")
    warnings = esm_method_warnings(
        jobs,
        ["ECO_WASTE", "COMPONENT_READY_EDD", "ROBUST_MC"],
    )

    assert len(warnings) == 3
    assert "wartosci neutralnych" in warnings[0]
    assert "gotowe od 0 min" in warnings[1]
    assert "profili niezawodnosci" in warnings[2]


def test_engineering_mode_rejects_more_than_eight_machines() -> None:
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")

    with pytest.raises(ValueError, match=f"1 do {ESM_MAX_MACHINES}"):
        evaluate_esm_methods(jobs, ["MT"], n_machines=9)


def test_mopt_tree_matches_pdf_backward_branching_and_exact_optimum() -> None:
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")
    nodes = build_mopt_solution_tree(jobs)
    chosen = [node.edge_label for node in nodes if node.chosen and node.parent_id]

    assert chosen == ["Z3", "Z1", "Z4", "Z2"]
    assert "S0=180 | Kop=0" in nodes[0].details
    assert "p: Z1=30, Z2=150, Z3=70, Z4=120" in nodes[0].details
    assert nodes[0].details.endswith("optimum STO=80")
    assert any(node.status == "pokonany" for node in nodes)
    assert any(node.status == "odrzucony" for node in nodes)
    assert any(
        "kolejnosc: Z2 -> Z4 -> Z1 -> Z3 | STO=80" in node.details
        for node in nodes
        if node.chosen and node.leaf
    )
    assert max(node.depth for node in nodes) == 4


def test_mopt_tree_caps_large_visual_trace_without_losing_best_path() -> None:
    jobs = load_esm_jobs("tests/fixtures/esm/esm_jobs_10_mixed_constraints.csv")
    nodes = build_mopt_solution_tree(jobs, max_nodes=80, n_machines=3)

    assert len(nodes) <= 80
    assert "Widok" in nodes[0].details
    assert len([node for node in nodes if node.chosen and node.parent_id]) == 10
    assert any(node.chosen and node.leaf for node in nodes)


def test_gantt_rows_are_sequential_and_minute_based() -> None:
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")
    result = evaluate_esm_methods(jobs, ["MOPT"])[0]
    rows = build_esm_gantt_rows(result)

    assert [row["job_id"] for row in rows] == ["Z2", "Z4", "Z1", "Z3"]
    assert [row["start"] for row in rows] == [0.0, 20.0, 70.0, 80.0]
    assert rows[-1]["end"] == 180.0


def test_gantt_rows_and_figure_show_multiple_machines() -> None:
    jobs = load_esm_jobs("tests/fixtures/esm/esm_jobs_07_parallel_balance.csv")
    result = evaluate_esm_methods(jobs, ["MO"], n_machines=3)[0]
    rows = build_esm_gantt_rows(result)
    figure = build_esm_gantt_figure(result, "MO")

    assert {row["machine"] for row in rows} == {"M1", "M2", "M3"}
    assert [tick.get_text() for tick in figure.axes[0].get_yticklabels()] == ["M1", "M2", "M3"]


def test_auto_queue_accepts_esm_minutes_and_converts_to_hours() -> None:
    frame = pd.read_csv("data/esm/esm_jobs.csv", dtype=str)
    normalized = normalize_queue_frame(frame)

    assert normalized["zlecenie_id"].tolist() == ["Z1", "Z2", "Z3", "Z4"]
    assert normalized["czas_produkcji_h"].astype(float).tolist() == pytest.approx(
        [10 / 60, 20 / 60, 100 / 60, 50 / 60]
    )
    assert normalized["termin_h"].astype(float).tolist() == pytest.approx(
        [150 / 60, 30 / 60, 110 / 60, 60 / 60]
    )


def test_engineering_figures_render_with_expected_titles() -> None:
    jobs = load_esm_jobs("data/esm/esm_jobs.csv")
    result = evaluate_esm_methods(jobs, ["MOPT"])[0]

    tree = build_mopt_tree_figure(build_mopt_solution_tree(jobs))
    gantt = build_esm_gantt_figure(result, "MOpt")

    assert tree.axes[0].get_title().startswith("Drzewo rozwiazania MOpt")
    assert any("X" in text.get_text() for text in tree.axes[0].texts)
    assert gantt.axes[0].get_title() == "Gantt - MOpt"
    assert gantt.axes[0].get_xlabel() == "Czas [min]"
