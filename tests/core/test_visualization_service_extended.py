import pandas as pd
import pytest
from matplotlib.figure import Figure

from AOA.core.visualization_service import (
    build_d3_dashboard_html_report,
    build_d3_html_report,
    build_figure_from_prompt,
    build_figure_from_request,
    parse_visual_command,
)


def _df():
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4],
            "y": [10, 20, 15, 30],
            "z": [5, 6, 7, 8],
            "t_start": [0, 1, 3, 6],
            "t_end": [1, 3, 6, 10],
            "czas_produkcji_h": [1, 2, 3, 4],
            "termin_h": [2, 4, 7, 12],
            "ksztalt": ["kwadrat", "trojkat", "trapez", "romb"],
        }
    )


@pytest.mark.parametrize(
    "chart_type,kwargs",
    [
        ("Scatter", {"x_col": "x", "y_col": "y"}),
        ("Line", {"x_col": "x", "y_col": "y"}),
        ("Histogram", {"x_col": "x"}),
        ("Boxplot", {"y_col": "y"}),
        ("Gantt", {}),
        ("CorrelationMatrix", {}),
        ("SimilarityMatrix", {}),
        ("DecisionTree", {}),
        ("Production Dashboard", {}),
        ("Missingness Map", {}),
        ("Priority Timeline", {"x_col": "x", "y_col": "y"}),
    ],
)
def test_build_figure_from_request_supported_chart_types(chart_type, kwargs):
    fig = build_figure_from_request(_df(), chart_type, **kwargs)

    assert isinstance(fig, Figure)


def test_build_figure_from_request_rejects_empty_df():
    with pytest.raises(ValueError, match="Brak danych do wizualizacji"):
        build_figure_from_request(pd.DataFrame(), "Scatter", x_col="x", y_col="y")


def test_build_figure_from_request_rejects_bad_scatter_columns():
    with pytest.raises(ValueError, match="Nieprawidłowe kolumny dla wykresu Scatter"):
        build_figure_from_request(_df(), "Scatter", x_col="bad", y_col="y")


def test_build_figure_from_request_rejects_bad_histogram_column():
    with pytest.raises(ValueError, match="Nieprawidłowa kolumna dla histogramu"):
        build_figure_from_request(_df(), "Histogram", x_col="bad")


def test_build_figure_from_request_rejects_bad_boxplot_column():
    with pytest.raises(ValueError, match="Nieprawidłowa kolumna dla boxplot"):
        build_figure_from_request(_df(), "Boxplot", y_col="bad")


def test_build_figure_from_request_rejects_unsupported_chart_type():
    with pytest.raises(ValueError, match="Nieobsługiwany typ wykresu"):
        build_figure_from_request(_df(), "Pie")


def test_parse_visual_command_maps_prompt_to_chart_and_columns():
    parsed = parse_visual_command(_df(), "scatter x x y y kolor z")

    assert parsed["chart_type"] == "Scatter"
    assert parsed["x_col"] == "x"
    assert parsed["y_col"] == "y"
    assert parsed["z_col"] == "z"


def test_build_figure_from_prompt_returns_figure_and_parsed_request():
    fig, parsed = build_figure_from_prompt(_df(), "histogram x")

    assert isinstance(fig, Figure)
    assert parsed["chart_type"] == "Histogram"
    assert parsed["x_col"] == "x"


def test_build_d3_html_report_contains_d3_and_inline_data():
    html = build_d3_html_report(_df(), x_col="x", y_col="y", z_col="z", chart_type="Scatter")

    assert "d3@7" in html
    assert "const data" in html
    assert '"x": 1' in html
    assert "drawNativeFallback" in html


def test_build_d3_dashboard_html_report_contains_multi_panel_dashboard():
    html = build_d3_dashboard_html_report(_df(), x_col="x", y_col="y", z_col="z")

    assert "AOA D3 Dashboard" in html
    assert 'id="scatter"' in html
    assert 'id="histogram"' in html
    assert 'id="bars"' in html
    assert 'id="missingness"' in html
    assert "numericColumns" in html


@pytest.mark.parametrize(
    ("chart_type", "renderer"),
    [
        ("Histogram", "drawHistogram"),
        ("Gantt", "drawGantt"),
        ("Line", "drawLine"),
        ("Production Dashboard", "drawProductionDashboard"),
        ("Dashboard", "drawProductionDashboard"),
        ("Missingness Map", "drawMissingness"),
        ("Diagnostics", "drawDiagnostics"),
        ("Boxplot", "drawBoxplot"),
        ("Column Ranking", "drawColumnRanking"),
        ("CorrelationMatrix", "drawCorrelationMatrix"),
        ("SimilarityMatrix", "drawSimilarityMatrix"),
        ("Bubble Chart", "drawBubbleChart"),
        ("Heatmap Density", "drawHeatmapDensity"),
        ("Outlier Map", "drawOutlierMap"),
        ("Pair Explorer", "drawPairExplorer"),
        ("3D Scatter", "drawPseudo3DScatter"),
        ("3D Surface", "drawPseudo3DSurface"),
        ("DecisionTree", "drawDecisionTree"),
    ],
)
def test_build_d3_html_report_contains_chart_specific_renderers(chart_type, renderer):
    html = build_d3_html_report(_df(), x_col="x", y_col="y", z_col="z", chart_type=chart_type)

    assert f'chartType === "{chart_type}"' in html
    assert renderer in html
