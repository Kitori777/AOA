import pandas as pd

from AOA.core.data_analytics_service import ANALYTICS_WORKFLOWS, run_analytics_workflow


def _df():
    return pd.DataFrame(
        {
            "cena": [10, 20, 15, 30],
            "odpad": [2, 5, 3, 8],
            "termin_h": [4, 8, 7, 12],
            "material": ["A", "A", "B", "C"],
        }
    )


def test_all_data_analytics_workflows_return_result():
    df = _df()

    for workflow in ANALYTICS_WORKFLOWS:
        result = run_analytics_workflow(df, workflow, metric="cena", dimension="material")

        assert result.title
        assert result.body
        assert result.recommended_chart


def test_index_does_not_require_loaded_data():
    result = run_analytics_workflow(None, "Index")

    assert "Data Analytics" in result.title
    assert "Analyze Data Quality" in result.body
    assert "Chart QA" in result.body


def test_metric_diagnostics_mentions_drivers_and_segments():
    result = run_analytics_workflow(_df(), "Metric Diagnostics", "cena", "material")

    assert "drivery" in result.body.lower() or "driver" in result.body.lower()
    assert "Segmenty" in result.body


def test_workflows_do_not_crash_when_metric_and_dimension_are_same():
    result = run_analytics_workflow(_df(), "KPI Reporting", "cena", "cena")

    assert "KPI Reporting" in result.title
    assert "Segmenty" in result.body


def test_workflows_do_not_crash_with_duplicate_column_names():
    df = pd.DataFrame(
        [
            [10, 12, 2, "A"],
            [20, 21, 5, "A"],
            [15, 18, 3, "B"],
        ],
        columns=["cena", "cena", "odpad", "material"],
    )

    result = run_analytics_workflow(df, "KPI Reporting", "cena", "cena")

    assert "KPI Reporting" in result.title
    assert result.body


def test_expanded_analytics_workflows_return_decision_ready_content():
    df = _df()
    expected = {
        "Executive Summary": "Decyzja robocza",
        "Opportunity Sizing": "najwiekszy potencjal",
        "Chart QA": "Kontrola doboru wykresow HTML",
        "Risk & Caveats": "Ryzyka interpretacji",
        "Action Plan": "Minimalny pakiet",
    }

    for workflow, phrase in expected.items():
        result = run_analytics_workflow(df, workflow, metric="cena", dimension="material")

        assert result.title == workflow
        assert phrase in result.body
        assert result.recommended_chart


def test_analytics_studio_workflows_cover_exploration_tasks():
    df = _df()
    expected = {
        "Statistical Summary": "Statystyki kolumn liczbowych",
        "Segment Explorer": "Ranking segmentow",
        "Correlation Explorer": "Najsilniejsze relacje",
        "Outlier Analysis": "Granice IQR",
        "Pivot Summary": "Metryka: cena",
        "Data Dictionary": "Kolumny:",
    }

    for workflow, phrase in expected.items():
        result = run_analytics_workflow(df, workflow, metric="cena", dimension="material")

        assert result.title == workflow
        assert phrase in result.body
