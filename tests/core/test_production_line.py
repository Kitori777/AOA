from __future__ import annotations

import json

import pandas as pd
import pytest

from AOA.core import production_line as production_line_core
from AOA.core.features import prepare_features
from AOA.core.formula_engine import compile_formula
from AOA.core.production_line import (
    MAX_EVENT_ROWS,
    ProductionLineSpec,
    StationSpec,
    simulate_production_line,
    validate_production_line,
)
from AOA.core.production_line_designer import ProductionLineDraft
from AOA.core.result_viewer_service import build_viewer_result
from AOA.core.services import production_line as production_line_service


def _jobs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "job_id": ["A", "B", "C"],
            "czas_produkcji_h": [2.0, 3.0, 1.0],
            "termin_h": [10.0, 8.0, 12.0],
            "cena": [100.0, 120.0, 80.0],
            "odpad": [0.1, 0.2, 0.05],
        }
    )


def _spec() -> ProductionLineSpec:
    return ProductionLineSpec(
        line_id="linia_testowa",
        name="Linia testowa",
        stations=(
            StationSpec(
                station_id="ciecie",
                name="Ciecie",
                resources=2,
                duration_formula="czas_produkcji_h",
                cost_formula="cena * 0.05",
                waste_formula="odpad * 0.1",
                quality_formula="quality * 0.99",
            ),
            StationSpec(
                station_id="pakowanie",
                name="Pakowanie",
                resources=1,
                duration_formula="max(0.5, prev_duration * 0.5)",
                cost_formula="2",
                quality_formula="quality * 0.98",
            ),
        ),
    )


def test_formula_engine_accepts_math_and_rejects_code_execution() -> None:
    formula = compile_formula("max(1, p * 1.5) + sqrt(x)", {"p", "x"})
    assert formula.evaluate({"p": 2, "x": 9}) == 6.0

    with pytest.raises(ValueError, match="Niedozwol"):
        compile_formula("__import__('os').system('dir')", {"p"})
    with pytest.raises(ValueError, match="nieznana zmienna"):
        compile_formula("sekret + 1", {"p"})


def test_production_line_simulates_parallel_resources_and_compact_events() -> None:
    result = simulate_production_line(_spec(), _jobs())

    assert len(result.events) == 6
    assert result.events["machine_id"].str.startswith(("ciecie:", "pakowanie:")).all()
    assert set(result.events[result.events["station_id"] == "ciecie"]["machine_id"]) == {
        "ciecie:M1",
        "ciecie:M2",
    }
    assert result.kpis["jobs"] == 3
    assert result.kpis["stations"] == 2
    assert result.kpis["makespan_h"] > 0
    assert "duration_formula" not in result.events.columns
    assert "solution_tree_json" not in result.events.columns
    assert set(result.events.columns) == {
        "line_id",
        "sto_job_id",
        "job_order",
        "station_id",
        "station_name",
        "station_order",
        "machine_id",
        "t_start",
        "t_end",
        "czas_produkcji_h",
        "termin_h",
        "lateness_h",
        "cost",
        "waste",
        "quality",
    }


def test_production_line_is_deterministic_and_preserves_fractional_times() -> None:
    first = simulate_production_line(_spec(), _jobs())
    second = simulate_production_line(_spec(), _jobs())
    pd.testing.assert_frame_equal(first.events, second.events)
    assert 1.5 in first.events["czas_produkcji_h"].tolist()


def test_production_line_reports_station_for_invalid_formula() -> None:
    spec = ProductionLineSpec(
        line_id="bad",
        name="Bad",
        stations=(StationSpec("s1", "Laser", duration_formula="unknown + 1"),),
    )
    with pytest.raises(ValueError, match="Laser.*nieznana zmienna"):
        simulate_production_line(spec, _jobs())


def test_production_line_rejects_duplicate_job_ids() -> None:
    jobs = _jobs()
    jobs.loc[1, "job_id"] = "A"
    with pytest.raises(ValueError, match="musza byc unikalne"):
        simulate_production_line(_spec(), jobs)


def test_production_line_flow_saves_json_once_and_light_csv(monkeypatch, tmp_path) -> None:
    spec_dir = tmp_path / "specs"
    monkeypatch.setattr(production_line_service, "PRODUCTION_LINES_DIR", spec_dir)

    output = production_line_service.run_production_line_flow(_spec(), _jobs(), output_dir=tmp_path)

    assert output["spec_path"].exists()
    assert output["visual_path"].exists()
    assert output["summary_path"].exists()
    saved = pd.read_csv(output["visual_path"])
    payload = json.loads(output["spec_path"].read_text(encoding="utf-8"))
    assert len(saved) == 6
    assert "duration_formula" not in saved.columns
    assert "station_name" not in saved.columns
    assert "czas_produkcji_h" not in saved.columns
    assert "lateness_h" not in saved.columns
    assert len(saved.columns) == 12
    assert payload["stations"][0]["duration_formula"] == "czas_produkcji_h"

    summary = pd.read_csv(output["summary_path"])
    assert len(summary) == len(_jobs())
    assert production_line_service.PRODUCTION_LINE_SUMMARY_COLUMNS == summary.columns[:9].tolist()
    assert {"cena", "odpad", "czas_produkcji_h", "line_completion_h"} <= set(summary)


def test_resources_duration_and_station_order_have_observable_effects() -> None:
    jobs = pd.DataFrame(
        {
            "job_id": ["A", "B"],
            "czas_produkcji_h": [2.0, 4.0],
            "termin_h": [10.0, 10.0],
        }
    )
    base = simulate_production_line(
        ProductionLineSpec(
            "base",
            "Base",
            (StationSpec("cut", "Cut", 1, "czas_produkcji_h"), StationSpec("pack", "Pack", 1, "1")),
        ),
        jobs,
    )
    parallel = simulate_production_line(
        ProductionLineSpec(
            "parallel",
            "Parallel",
            (StationSpec("cut", "Cut", 2, "czas_produkcji_h"), StationSpec("pack", "Pack", 1, "1")),
        ),
        jobs,
    )
    faster = simulate_production_line(
        ProductionLineSpec(
            "faster",
            "Faster",
            (
                StationSpec("cut", "Cut", 1, "czas_produkcji_h / 2"),
                StationSpec("pack", "Pack", 1, "1"),
            ),
        ),
        jobs,
    )
    reordered = simulate_production_line(
        ProductionLineSpec(
            "reordered",
            "Reordered",
            (StationSpec("pack", "Pack", 1, "1"), StationSpec("cut", "Cut", 1, "czas_produkcji_h")),
        ),
        jobs,
    )

    assert (base.kpis["makespan_h"], parallel.kpis["makespan_h"], faster.kpis["makespan_h"]) == (
        7.0,
        5.0,
        4.0,
    )
    assert parallel.kpis["throughput_per_h"] > base.kpis["throughput_per_h"]
    assert reordered.events.iloc[0]["station_id"] == "pack"
    assert base.events.iloc[0]["station_id"] == "cut"


def test_formula_context_controls_cost_waste_quality_and_previous_station() -> None:
    jobs = pd.DataFrame(
        {"job_id": ["A"], "czas_produkcji_h": [2.0], "termin_h": [2.5], "cena": [10.0]}
    )
    spec = ProductionLineSpec(
        "context",
        "Context",
        (
            StationSpec("s1", "Start", 1, "czas_produkcji_h", "duration * 3", "0.2", "99"),
            StationSpec(
                "s2",
                "Finish",
                1,
                "prev_duration / 2 + prev_end - 2",
                "cost_total + resource_index",
                "waste_total + station_index / 10",
                "quality - 1",
            ),
        ),
    )

    result = simulate_production_line(spec, jobs)

    assert result.events["czas_produkcji_h"].tolist() == [2.0, 1.0]
    assert result.kpis["makespan_h"] == 3.0
    assert result.kpis["late_jobs"] == 1
    assert result.kpis["total_cost"] == 13.0
    assert result.kpis["total_waste"] == 0.6
    assert result.kpis["mean_quality"] == 98.0


@pytest.mark.parametrize(
    ("stations", "message"),
    [
        ((), "przynajmniej jedno"),
        ((StationSpec("s", "A"), StationSpec("s", "B")), "unikalne"),
        ((StationSpec("s", "A", 0),), "1..1000"),
        ((StationSpec("s", "A", 1001),), "1..1000"),
        ((StationSpec("s", "A", duration_formula=""),), "Wzor nie moze byc pusty"),
    ],
)
def test_line_validation_rejects_invalid_structure(stations, message) -> None:
    with pytest.raises(ValueError, match=message):
        validate_production_line(ProductionLineSpec("bad", "Bad", stations))


@pytest.mark.parametrize(
    ("field", "formula", "message"),
    [
        ("duration_formula", "0", "czas musi byc wiekszy"),
        ("duration_formula", "-1", "czas nie moze byc ujemny"),
        ("cost_formula", "-1", "koszt nie moze byc ujemny"),
        ("waste_formula", "-1", "odpad nie moze byc ujemny"),
    ],
)
def test_line_rejects_invalid_formula_results(field, formula, message) -> None:
    values = {field: formula}
    station = StationSpec("s", "Test", **values)
    with pytest.raises(ValueError, match=message):
        simulate_production_line(ProductionLineSpec("bad", "Bad", (station,)), _jobs())


def test_line_generates_job_ids_and_enforces_event_limit(monkeypatch) -> None:
    jobs = _jobs().drop(columns="job_id")
    result = simulate_production_line(_spec(), jobs)
    assert result.job_summary["sto_job_id"].tolist() == ["JOB_1", "JOB_2", "JOB_3"]

    monkeypatch.setattr(production_line_core, "MAX_EVENT_ROWS", 5)
    with pytest.raises(ValueError, match="Limit lekkiego wyniku"):
        simulate_production_line(_spec(), _jobs())
    assert MAX_EVENT_ROWS == 2_000_000


def test_summary_is_compatible_with_results_and_ml(monkeypatch, tmp_path) -> None:
    jobs = pd.DataFrame(
        {
            "job_id": ["A", "B"],
            "cena": [100.0, 120.0],
            "odpad": [0.1, 0.2],
            "termin_h": [10.0, 8.0],
            "czas_produkcji_h": [2.0, 3.0],
            "ksztalt": ["kwadrat", "trojkat"],
            "material": ["bawelna", "poliester"],
            "x": [2.0, 3.0],
            "y": [4.0, 2.0],
            "z": [0.2, 0.3],
        }
    )
    monkeypatch.setattr(production_line_service, "PRODUCTION_LINES_DIR", tmp_path / "specs")
    output = production_line_service.run_production_line_flow(_spec(), jobs, output_dir=tmp_path)

    summary = output["summary"]
    viewer = build_viewer_result(summary, sort_column="line_completion_h")
    features, quality_target, delay_target, _scaler = prepare_features(summary)

    assert len(viewer.df) == 2
    assert "PODSUMOWANIE PLIKU" in viewer.report
    assert features.shape[0] == len(summary)
    assert len(quality_target) == len(delay_target) == len(summary)


def test_each_run_uses_unique_output_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(production_line_service, "PRODUCTION_LINES_DIR", tmp_path / "specs")
    first = production_line_service.run_production_line_flow(_spec(), _jobs(), output_dir=tmp_path)
    second = production_line_service.run_production_line_flow(_spec(), _jobs(), output_dir=tmp_path)

    assert first["visual_path"] != second["visual_path"]
    assert first["summary_path"] != second["summary_path"]
    assert first["visual_path"].exists() and second["visual_path"].exists()


def test_flow_removes_partial_outputs_when_summary_write_fails(monkeypatch, tmp_path) -> None:
    spec_dir = tmp_path / "specs"
    monkeypatch.setattr(production_line_service, "PRODUCTION_LINES_DIR", spec_dir)
    original_to_csv = pd.DataFrame.to_csv

    def failing_to_csv(frame, path, *args, **kwargs):
        if "production_line_summary" in str(path):
            raise OSError("disk full")
        return original_to_csv(frame, path, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_csv", failing_to_csv)

    with pytest.raises(OSError, match="disk full"):
        production_line_service.run_production_line_flow(_spec(), _jobs(), output_dir=tmp_path)

    assert not list(tmp_path.glob("production_line_*.csv"))
    assert not list(tmp_path.rglob("*.tmp"))
    assert not (spec_dir / "linia_testowa.json").exists()


def test_loading_project_rejects_malformed_json(tmp_path) -> None:
    invalid = tmp_path / "bad.json"
    invalid.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="obiekt JSON"):
        production_line_service.load_production_line_spec(invalid)


def test_graphical_project_save_load_and_run_preserve_layout(monkeypatch, tmp_path) -> None:
    spec_dir = tmp_path / "specs"
    monkeypatch.setattr(production_line_service, "PRODUCTION_LINES_DIR", spec_dir)
    project = ProductionLineDraft.from_spec(_spec())
    project.move_station("ciecie", 340, 260)
    project_path = production_line_service.save_production_line_project(project)

    loaded = production_line_service.load_production_line_project(project_path)
    output = production_line_service.run_production_line_flow(
        loaded.to_spec(columns=list(_jobs().columns)),
        _jobs(),
        output_dir=tmp_path,
        project=loaded,
    )
    saved_payload = json.loads(output["spec_path"].read_text(encoding="utf-8"))

    assert loaded.layouts["ciecie"].x == 340
    assert saved_payload["schema_version"] == 2
    assert saved_payload["layout"][0]["station_id"] == "ciecie"
    assert saved_payload["connections"] == [{"source": "ciecie", "target": "pakowanie"}]


def test_changing_only_graphical_layout_does_not_change_simulation() -> None:
    project = ProductionLineDraft.from_spec(_spec())
    before = simulate_production_line(project.to_spec(columns=list(_jobs().columns)), _jobs())

    project.move_station("ciecie", 900, 500)
    project.move_station("pakowanie", 40, 40)
    after = simulate_production_line(project.to_spec(columns=list(_jobs().columns)), _jobs())

    pd.testing.assert_frame_equal(before.events, after.events)
    assert before.kpis == after.kpis
