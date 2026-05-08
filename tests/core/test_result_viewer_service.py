import pandas as pd

from AOA.core.result_viewer_service import (
    build_column_profile,
    build_dataset_report,
    build_viewer_result,
    filter_sort_limit_dataframe,
)


def test_filter_sort_limit_dataframe_filters_and_sorts():
    df = pd.DataFrame({"name": ["alpha", "beta", "alphabet"], "score": [2, 3, 1]})

    result = filter_sort_limit_dataframe(
        df,
        query="alpha",
        sort_column="score",
        descending=True,
        limit=1,
    )

    assert result["name"].tolist() == ["alpha"]


def test_build_column_profile_for_numeric_column():
    df = pd.DataFrame({"value": [1, 2, 3, 100]})

    profile = build_column_profile(df, "value")

    assert "PROFIL KOLUMNY: value" in profile
    assert "Średnia" in profile
    assert "Odstające IQR" in profile


def test_build_dataset_report_contains_visible_count():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    visible = df.head(2)

    report = build_dataset_report(df, visible)

    assert "Wiersze w pliku: 3" in report
    assert "Wiersze po filtrze: 2" in report


def test_build_viewer_result_returns_text_and_report():
    df = pd.DataFrame({"city": ["Głogów", "Lubin"], "value": [10, 20]})

    result = build_viewer_result(df, query="głog", profile_column="value")

    assert "Głogów" in result.text
    assert "PODSUMOWANIE PLIKU" in result.report
    assert "PROFIL KOLUMNY: value" in result.report
