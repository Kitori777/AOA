from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from AOA.gui.engineering_exports import (
    EngineeringContext,
    comparison_rows,
    format_result_description,
    operation_rows,
    write_csv,
)


@pytest.fixture
def context(tmp_path):
    return EngineeringContext(str(tmp_path / "źródło.csv"), 3, "total", "abc123")


def result(**overrides):
    return {
        "method": "MOPT",
        "order": ["Żółć; 1", "Z2"],
        "sto": 13.333333333333334,
        "completion_total": 126.66666666666667,
        "total_waste_kg": 0.25,
        "elapsed_s": 0.005,
        "optimality_status": "OPTIMAL_CONFIRMED",
        "steps": [
            {
                "job_id": "Żółć; 1",
                "machine_id": 3,
                "scheduled": True,
                "start_time": 100,
                "completion_time": 120,
                "processing_time": 20,
                "setup_start": 98,
                "setup_time": 2,
                "deadline": 110,
                "tardiness_positive": 10,
                "waste_kg": 0.25,
            }
        ],
        **overrides,
    }


def test_csv_round_trip_preserves_polish_text_numbers_and_context(tmp_path, context):
    data = result()
    original = deepcopy(data)
    rows = comparison_rows([data], context)
    path = write_csv(tmp_path / "wyniki.csv", rows, source_path=context.source_path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        saved = list(csv.DictReader(stream, delimiter=";"))
    assert saved[0]["kolejnosc"] == "Żółć; 1 -> Z2"
    assert float(saved[0]["sto_min"].replace(",", ".")) == data["sto"]
    assert saved[0]["plik_zrodlowy"] == context.source_path
    assert saved[0]["sha256_csv"] == "abc123"
    assert saved[0]["liczba_maszyn"] == "3"
    assert saved[0]["interpretacja_czasu"] == "total"
    assert saved[0]["p90_konca_min"] == ""
    assert data == original


def test_operation_export_keeps_blocked_job_without_inventing_zero_times(context):
    data = result(optimality_status="PARTIAL_PLAN", unscheduled_count=1, blocked_jobs=["Z2"])
    data["steps"].append(
        {
            "job_id": "Z2",
            "machine_id": 0,
            "scheduled": False,
            "unscheduled_reason": "Brak komponentów",
            "tardiness_positive": 0,
        }
    )
    rows = operation_rows([data], context)
    assert rows[0]["maszyna"] == 3
    assert rows[0]["start_przezbrojenia_min"] == 98
    assert rows[1]["zlecenie"] == "Z2"
    assert rows[1]["zaplanowane"] == "nie"
    assert rows[1]["powod_braku"] == "Brak komponentów"
    assert (
        rows[1]["maszyna"]
        == rows[1]["koniec_min"]
        == rows[1]["opoznienie_po_ostatniej_maszynie_min"]
        == ""
    )
    text = format_result_description(data, context)
    assert "plan niepełny" in text and "tylko zaplanowanej części" in text
    assert "optimum potwierdzone" not in text


def test_interrupted_mopt_is_never_described_as_confirmed(context):
    data = result(optimality_status="BEST_KNOWN", search_stop_reason="limit czasu")
    row = comparison_rows([data], context)[0]
    assert row["status_optimum"] == "BEST_KNOWN"
    assert row["powod_zatrzymania_mopt"] == "limit czasu"
    text = format_result_description(data, context)
    assert "optimum niepotwierdzone" in text and "limit czasu" in text
    assert "optimum potwierdzone" not in text


def test_robust_export_uses_independent_validation_instead_of_selection(context):
    data = result(
        method="ROBUST_MC",
        optimality_status="RISK_ASSESSED",
        risk_summary={
            "available": True,
            "iterations": 1000,
            "seed": 42,
            "p90_makespan_min": 900,
            "p90_lateness_min": 800,
        },
        risk_validation_summary={
            "available": True,
            "iterations": 1000,
            "seed": 43,
            "p90_makespan_min": 130,
            "p90_lateness_min": 24,
        },
    )
    row = comparison_rows([data], context)[0]
    assert row["p90_konca_min"] == 130 and row["p90_sto_min"] == 24
    assert row["ziarno_mc"] == 43 and row["seria_mc"] == "niezależna weryfikacja"
    text = format_result_description(data, context)
    assert "ziarno 43" in text and "130.00" in text and "900" not in text
    assert "brak dowodu optimum probabilistycznego" in text


@pytest.mark.parametrize("operation", [comparison_rows, operation_rows])
def test_exports_preserve_rank_and_never_serialize_solver_objects(operation, context):
    first, second = result(), result(method="MO", sto=25)
    first["flowshop_solution"] = object()
    rows = operation([first, second], context)
    assert [row["metoda"] for row in rows] == ["MOpt", "MO / SPT"]
    assert all("flowshop_solution" not in row for row in rows)


def test_source_csv_is_protected_even_through_relative_path(tmp_path, context, monkeypatch):
    source = Path(context.source_path)
    source.write_text("original", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="źródłowego"):
        write_csv(
            source.name, comparison_rows([result()], context), source_path=context.source_path
        )
    assert source.read_text(encoding="utf-8") == "original"


def test_failed_write_preserves_existing_export_and_removes_temporary_file(tmp_path, context):
    path = tmp_path / "wyniki.csv"
    path.write_bytes(b"previous report")
    with patch("AOA.gui.engineering_exports.os.replace", side_effect=PermissionError("locked")):
        with pytest.raises(PermissionError):
            write_csv(path, comparison_rows([result()], context), source_path=context.source_path)
    assert path.read_bytes() == b"previous report"
    assert not list(tmp_path.glob("*.tmp"))


def test_failure_while_writing_rows_does_not_leave_partial_report(tmp_path, context):
    path = tmp_path / "wyniki.csv"
    path.write_bytes(b"previous report")
    with pytest.raises(ValueError):
        write_csv(path, [{"column": 1}, {"unexpected_column": 2}], source_path=context.source_path)
    assert path.read_bytes() == b"previous report"
    assert not list(tmp_path.glob("*.tmp"))


def test_no_empty_csv_is_created(tmp_path, context):
    path = tmp_path / "empty.csv"
    with pytest.raises(ValueError, match="Brak wyników"):
        write_csv(path, [], source_path=context.source_path)
    assert not path.exists()
