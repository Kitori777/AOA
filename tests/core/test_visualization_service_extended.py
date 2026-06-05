import pandas as pd
import pytest
from matplotlib.figure import Figure

from AOA.core.visualization_service import (
    CHART_TYPES,
    _solution_tree_records,
    build_d3_dashboard_html_report,
    build_d3_html_report,
    build_figure_from_prompt,
    build_figure_from_request,
    build_solution_tree_template_csv,
    get_supported_chart_types,
    is_chart_supported_by_library,
    parse_visual_command,
    solution_tree_summary,
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


def _sample_tree_df():
    return pd.DataFrame(
        {
            "cena": [432.38332766541885, 51.481952988748176, 232.06632487064724, 335.4291115794715],
            "odpad": [
                0.07586888204711141,
                0.1413674253624776,
                0.12253948999662166,
                0.09529800223714452,
            ],
            "termin_h": [150, 30, 110, 60],
            "czas_produkcji_h": [10, 20, 100, 50],
            "ksztalt": ["trojkat", "trojkat", "trapez", "kwadrat"],
            "material": ["wiskoza", "mikrofibra", "mikrofibra", "bawelna"],
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
        ("SolutionTree", {}),
        ("ML Decision Tree", {}),
        ("Model Diagnostics", {"x_col": "x", "y_col": "y"}),
        ("Bar Chart", {"x_col": "ksztalt", "y_col": "y"}),
        ("Pie Chart", {"x_col": "ksztalt"}),
        ("Area Chart", {"x_col": "x", "y_col": "y"}),
        ("Violin Plot", {"x_col": "ksztalt", "y_col": "y"}),
        ("KDE Plot", {"x_col": "x", "y_col": "y"}),
        ("ECDF Plot", {"x_col": "x"}),
        ("Regression Plot", {"x_col": "x", "y_col": "y"}),
        ("Joint Plot", {"x_col": "x", "y_col": "y"}),
        ("Pair Plot", {}),
        ("Network Graph", {}),
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


def test_legacy_decision_tree_name_is_mapped_to_ml_decision_tree():
    fig = build_figure_from_request(_df(), "DecisionTree")
    html = build_d3_html_report(_df(), chart_type="DecisionTree")

    assert isinstance(fig, Figure)
    assert '"ML Decision Tree"' in html


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
    assert 'id="ctl-library"' in html
    assert "drawPlotlyChart" in html
    assert "drawAltairChart" in html


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
        ("Model Diagnostics", "drawModelDiagnostics"),
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
        ("SolutionTree", "drawSolutionTree"),
        ("ML Decision Tree", "drawDecisionTree"),
    ],
)
def test_build_d3_html_report_contains_chart_specific_renderers(chart_type, renderer):
    html = build_d3_html_report(_df(), x_col="x", y_col="y", z_col="z", chart_type=chart_type)

    assert f'chartType === "{chart_type}"' in html
    assert renderer in html


def test_d3_html_exposes_every_chart_type_in_selector():
    html = build_d3_html_report(_df(), x_col="x", y_col="y", z_col="z", chart_type="Scatter")

    assert "DecisionTree" not in CHART_TYPES
    assert "ML Decision Tree" in CHART_TYPES
    for chart_type in CHART_TYPES:
        assert chart_type in html


@pytest.mark.parametrize("chart_type", CHART_TYPES)
def test_d3_html_can_be_generated_for_every_chart_type(chart_type):
    html = build_d3_html_report(_df(), x_col="x", y_col="y", z_col="z", chart_type=chart_type)

    assert "<!doctype html>" in html
    assert "renderCurrentChart" in html
    assert f'"{chart_type}"' in html


def test_solution_tree_uses_csv_columns_and_template(tmp_path):
    df = pd.DataFrame(
        {
            "node_id": ["B1", "B2", "B3"],
            "parent_id": ["", "B1", "B2"],
            "label": ["B1", "B2", "B3"],
            "details": ["S0=180", "S'=170; Kop=30", "S'=70; Kop=90"],
            "edge_label": ["", "z1", "z3"],
        }
    )

    fig = build_figure_from_request(df, "SolutionTree")
    html = build_d3_html_report(df, chart_type="SolutionTree")
    template_path = build_solution_tree_template_csv(tmp_path / "tree.csv")

    assert isinstance(fig, Figure)
    assert "solutionTreeData" in html
    assert '"parent": "B1"' in html
    assert 'id="ctl-tree-algo"' in html
    assert 'id="ctl-tree-fit"' in html
    assert 'id="ctl-delete-tree"' in html
    assert "treeAlgorithms" in html
    assert "treeFitMode" in html
    assert "deletedTreeNodes" in html
    assert template_path.exists()
    assert "node_id,parent_id,label,details,edge_label,level,order" in template_path.read_text()


def test_solution_tree_ignores_library_override_and_keeps_tree_renderer():
    fig = build_figure_from_request(_df(), "SolutionTree", chart_library="NetworkX")
    html = build_d3_html_report(_df(), chart_type="SolutionTree", chart_library="Plotly")

    assert isinstance(fig, Figure)
    assert "NetworkX - SolutionTree" not in fig.axes[0].get_title()
    assert 'if (chartType === "SolutionTree")' in html
    assert html.index('if (chartType === "SolutionTree")') < html.index(
        'if (chartLibrary === "Plotly") return drawPlotlyChart();'
    )


def test_solution_tree_marks_visited_non_best_paths_yellow():
    df = _sample_tree_df()

    records = _solution_tree_records(df, max_nodes=80)
    html = build_d3_html_report(df, chart_type="SolutionTree")
    yellow_records = [record for record in records if record.get("status") == "pokonany"]
    yellow_edges = [record["edge_label"] for record in yellow_records]

    assert yellow_records
    assert yellow_edges == ["z1", "z3", "z4", "z2"]
    assert '"status": "pokonany"' in html
    assert 'status.includes("pokon")' in html
    assert "score <= parentScore" not in html


def test_solution_tree_sample_yellow_path_is_stable_when_rows_move():
    expected = ["z1", "z3", "z4", "z2"]
    variants = [
        _sample_tree_df(),
        _sample_tree_df().iloc[::-1].reset_index(drop=True),
        _sample_tree_df().sample(frac=1, random_state=42).reset_index(drop=True),
    ]

    for df in variants:
        records = _solution_tree_records(df, max_nodes=80)
        yellow_edges = [
            record["edge_label"] for record in records if record.get("status") == "pokonany"
        ]
        assert yellow_edges == expected


def test_solution_tree_does_not_force_pdf_path_for_different_examples():
    df = pd.DataFrame(
        {
            "sto_job_id": ["z1", "z2", "z3", "z4"],
            "czas_produkcji_h": [10, 20, 30, 40],
            "termin_h": [15, 45, 55, 90],
        }
    )

    records = _solution_tree_records(df, max_nodes=80)
    yellow_edges = [
        record["edge_label"] for record in records if record.get("status") == "pokonany"
    ]

    assert yellow_edges
    assert yellow_edges != ["z1", "z3", "z4", "z2"]


def test_solution_tree_marks_rejected_paths_red_and_reports_summary():
    df = pd.DataFrame(
        {
            "sto_job_id": ["z1", "z2", "z3", "z4"],
            "czas_produkcji_h": [10, 20, 30, 40],
            "termin_h": [15, 45, 55, 90],
        }
    )

    records = _solution_tree_records(df, max_nodes=80)
    html = build_d3_html_report(df, chart_type="SolutionTree")
    summary = solution_tree_summary(df)

    assert any(record.get("status") == "odrzucony" for record in records)
    assert summary["leaves"] > 0
    assert summary["roots"] == 1
    assert summary["rejected"] > 0
    assert "#dc2626" in html
    assert "treeSummary(treeRecords)" in html
    assert "treeHiddenLabels(allTreeRecords)" in html
    assert "<s>${label}</s>" in html


def test_library_support_limits_invalid_chart_choices():
    assert "Circular Network" in get_supported_chart_types("NetworkX")
    assert "Kamada-Kawai Network" in get_supported_chart_types("NetworkX")
    assert "Count Plot" in get_supported_chart_types("Seaborn")
    assert "Treemap" in get_supported_chart_types("Plotly")
    assert "Binned Scatter" in get_supported_chart_types("Altair")
    assert is_chart_supported_by_library("Regression Plot", "Seaborn")
    assert not is_chart_supported_by_library("Gantt", "NetworkX")


def test_plotly_and_altair_renderers_take_priority_over_d3():
    html = build_d3_html_report(
        _df(), x_col="x", y_col="y", z_col="z", chart_type="3D Scatter", chart_library="Plotly"
    )

    assert 'if (chartLibrary === "Plotly") return drawPlotlyChart();' in html
    assert 'type:"scatter3d"' in html
    assert "Biblioteka: Plotly" in html
    assert '"Plotly"' in html
    assert 'if (chartType === "SolutionTree")' in html
    assert 'if (chartType.includes("Network"))' in html


def test_altair_html_exposes_new_interactive_charts():
    html = build_d3_html_report(
        _df(), x_col="x", y_col="y", z_col="z", chart_type="Binned Scatter", chart_library="Altair"
    )

    assert 'if (chartLibrary === "Altair") return drawAltairChart();' in html
    assert '"Binned Scatter"' in html
    assert '"Interactive Brush"' in html
    assert 'select:{type:"interval"}' in html


def test_solution_tree_html_defaults_to_readable_full_tree_mode():
    html = build_d3_html_report(_df(), chart_type="SolutionTree")

    assert 'let treeFitMode = "large"' in html
    assert '<option value="large" selected>Całe drzewo - czytelne</option>' in html
    assert 'const readableTree = treeFitMode === "large" || treeFitMode === "manual"' in html
    assert '.style("width", readableTree ? `${canvasW}px` : "100%")' in html
    assert "svg.solution-tree-chart text" in html
    assert 'id="ctl-tree-zoom-in"' in html
    assert "treeZoomBehavior = d3.zoom()" in html
    assert 'svg.on(".zoom", null)' in html
