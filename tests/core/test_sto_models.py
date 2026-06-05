import pandas as pd

from AOA.core.sto_models import (
    apply_sto_result_to_dataframe,
    build_sto_report,
    evaluate_sequence,
    parse_jobs,
    run_selected_sto_models,
    sequence_mopt,
)


def test_parse_jobs_returns_three_jobs():
    jobs = parse_jobs("Z1,Z2,Z3", "10,20,100", "150,30,110")

    assert len(jobs) == 3
    assert jobs[0].job_id == "Z1"
    assert jobs[1].processing_time == 20.0
    assert jobs[2].deadline == 110.0


def test_run_selected_sto_models_returns_sorted_results():
    jobs = parse_jobs("Z1,Z2,Z3", "10,20,100", "150,30,110")
    results = run_selected_sto_models(jobs, ["MT", "MO", "MZO", "GENETIC"])

    assert len(results) == 4
    assert results[0]["sto"] <= results[-1]["sto"]
    assert all("method" in result for result in results)
    assert all("order" in result for result in results)
    assert all("steps" in result for result in results)


def test_build_sto_report_contains_best_and_worst_information():
    jobs = parse_jobs("Z1,Z2,Z3", "10,20,100", "150,30,110")
    results = run_selected_sto_models(jobs, ["MT", "MO", "MZO"])
    report = build_sto_report(jobs, results)

    assert "ANALIZA STO" in report
    assert "Najbardziej optymalny wynik:" in report
    assert "Najgorszy wynik:" in report
    assert "MODEL STO" in report
    assert "STO:" in report


def test_sequence_mopt_matches_pdf_three_job_example():
    jobs = parse_jobs("Z1,Z2,Z3", "10,20,100", "150,30,110")

    sequence = sequence_mopt(jobs)
    evaluation = evaluate_sequence(sequence)

    assert evaluation["order"] == ["Z2", "Z3", "Z1"]
    assert evaluation["sto"] == 10.0


def test_sequence_mopt_matches_pdf_four_job_example():
    jobs = parse_jobs("Z1,Z2,Z3,Z4", "10,20,100,50", "150,30,110,60")

    sequence = sequence_mopt(jobs)
    evaluation = evaluate_sequence(sequence)

    assert evaluation["order"] == ["Z2", "Z4", "Z1", "Z3"]
    assert evaluation["sto"] == 80.0


def test_apply_sto_result_adds_solution_tree_columns():
    jobs = parse_jobs("Z1,Z2,Z3", "10,20,100", "150,30,110")
    result = run_selected_sto_models(jobs, ["MOPT"])[0]

    df = apply_sto_result_to_dataframe(
        pd.DataFrame(
            {
                "sto_job_id": ["Z1", "Z2", "Z3"],
                "czas_produkcji_h": [10, 20, 100],
                "termin_h": [150, 30, 110],
            }
        ),
        result,
    )

    assert "solution_node_id" in df.columns
    assert "solution_parent_id" in df.columns
    assert "solution_details" in df.columns
    assert "solution_tree_json" in df.columns
