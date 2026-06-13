from __future__ import annotations

import pandas as pd

from AOA.core.release_segments import (
    DATA_CONTRACT_FIELDS,
    REPORT_TEMPLATES,
    audit_html_controls,
    data_contract_summary,
    list_development_segments,
    report_template_summary,
    segment_summary,
)
from AOA.core.visualization_service import (
    build_d3_dashboard_html_report,
    build_d3_html_report,
)


def test_development_segments_cover_release_readme_plan() -> None:
    names = {segment.name for segment in list_development_segments()}

    assert "ALICE Reviewer" in names
    assert "Scenario Lab" in names
    assert "Model Registry UI" in names
    assert "Workflow History" in names
    assert "Dataset Library" in names
    assert "Report Templates" in names
    assert "Diagram QA" in names
    assert "Chart QA" in names
    assert "Data Contract" in names
    assert "Assistant Playbooks" in names
    assert "ocen diagram" in segment_summary()


def test_report_templates_and_data_contract_are_user_readable() -> None:
    assert "ml_validation" in REPORT_TEMPLATES
    assert "release_check" in REPORT_TEMPLATES
    assert "czas_h" in DATA_CONTRACT_FIELDS
    assert "NaN" in data_contract_summary()
    assert "executive_summary" in report_template_summary()


def test_interactive_chart_html_contains_wide_control_surface() -> None:
    df = pd.DataFrame(
        {
            "czas_h": [1.0, 2.5, 3.2, 4.0],
            "termin_h": [8.0, 7.5, 9.0, 11.0],
            "koszt": [120, 140, 90, 180],
            "jakosc": [0.8, 0.7, 0.9, 0.6],
        }
    )

    html = build_d3_html_report(df, x_col="koszt", y_col="jakosc", z_col="czas_h")
    audit = audit_html_controls(html, profile="interactive_chart")

    assert audit["missing"] == []
    assert "ctl-save-preset" in html
    assert "ctl-query" in html
    assert "ctl-trend" in html


def test_dashboard_html_contains_core_interactive_controls() -> None:
    df = pd.DataFrame(
        {
            "czas_h": [1.0, 2.5, 3.2, 4.0],
            "termin_h": [8.0, 7.5, 9.0, 11.0],
            "koszt": [120, 140, 90, 180],
            "jakosc": [0.8, 0.7, 0.9, 0.6],
        }
    )

    html = build_d3_dashboard_html_report(df, x_col="koszt", y_col="jakosc", z_col="czas_h")
    audit = audit_html_controls(html, profile="dashboard")

    assert audit["missing"] == []
    assert "Relacja X/Y" in html
    assert "Jakość danych" in html
