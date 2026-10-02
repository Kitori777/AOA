import pytest

from AOA.core.sto_models import (
    OPTIMIZATION_OBJECTIVES,
    Job,
    parse_jobs,
    run_selected_sto_models,
    sequence_genetic,
    sequence_mopt,
)


def test_parse_jobs_rejects_empty_inputs():
    with pytest.raises(ValueError, match="Wprowadź komplet danych"):
        parse_jobs("", "", "")


def test_parse_jobs_rejects_length_mismatch():
    with pytest.raises(ValueError, match="Liczba zleceń, czasów i terminów musi być taka sama"):
        parse_jobs("A,B", "1", "2,3")


@pytest.mark.parametrize(
    ("processing_text", "deadlines_text"),
    [
        ("0,2", "4,5"),
        ("-1,2", "4,5"),
        ("1,2", "0,5"),
        ("1,2", "-4,5"),
    ],
)
def test_parse_jobs_rejects_non_positive_processing_or_deadline(processing_text, deadlines_text):
    with pytest.raises(ValueError, match="ujemne rzeczy|dodatnie"):
        parse_jobs("A,B", processing_text, deadlines_text)


def test_run_selected_sto_models_rejects_no_methods():
    jobs = parse_jobs("A,B,C", "2,1,3", "5,4,9")

    with pytest.raises(ValueError, match="Wybierz przynajmniej jeden model STO"):
        run_selected_sto_models(jobs, [])


def test_run_selected_sto_models_returns_result_for_each_method():
    jobs = parse_jobs("A,B,C", "2,1,3", "5,4,9")

    results = run_selected_sto_models(jobs, ["MT", "MO", "MZO", "MOPT", "GENETIC"])

    assert len(results) == 5
    for item in results:
        assert "method" in item
        assert "order" in item
        assert "steps" in item
        assert "sto" in item
        assert isinstance(item["order"], list)
        assert isinstance(item["steps"], list)


def test_sequence_genetic_for_small_input_returns_permutation_of_jobs():
    jobs = [
        Job("A", 2.0, 6.0),
        Job("B", 1.0, 3.0),
        Job("C", 4.0, 10.0),
    ]

    seq = sequence_genetic(jobs, seed=42)

    assert sorted(job.job_id for job in seq) == ["A", "B", "C"]


def test_sequence_genetic_for_large_input_returns_permutation_of_jobs():
    jobs = [Job(f"J{i}", float(i % 5 + 1), float(i + 5)) for i in range(1, 10)]

    seq = sequence_genetic(jobs, population_size=10, generations=5, seed=42)

    assert len(seq) == len(jobs)
    assert sorted(job.job_id for job in seq) == sorted(job.job_id for job in jobs)


@pytest.mark.parametrize("objective", OPTIMIZATION_OBJECTIVES)
def test_every_exclusive_objective_reports_exact_quality_for_four_jobs(objective):
    jobs = [
        Job("A", 4, 5, material="bawelna", waste_kg=2.0),
        Job("B", 1, 8, material="poliester", waste_kg=0.2),
        Job("C", 3, 7, material="bawelna", waste_kg=1.0),
        Job("D", 2, 4, material="poliester", waste_kg=0.4),
    ]

    results = run_selected_sto_models(
        jobs,
        ["MT", "MOPT", "ECO_WASTE"],
        n_machines=2,
        objective=objective,
    )

    assert results[0]["objective"] == objective
    assert results[0]["optimality_status"] == "OPTIMAL_CONFIRMED"
    assert results[0]["optimality_gap_pct"] == 0.0


def test_mopt_uses_bounded_fallback_for_large_single_machine_queue():
    jobs = [Job(f"J{index}", 1, index + 5) for index in range(19)]

    sequence = sequence_mopt(jobs)

    assert len(sequence) == 19
    assert {job.job_id for job in sequence} == {job.job_id for job in jobs}
