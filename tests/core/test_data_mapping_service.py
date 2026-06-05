import pandas as pd
import pytest

from AOA.core.services.data_mapping import (
    apply_data_mapping,
    required_fields,
    suggest_mapping,
)


def test_suggest_mapping_uses_aliases() -> None:
    columns = [
        "price",
        "deadline",
        "processing_time",
        "shape",
        "material",
        "width",
        "height",
        "depth",
    ]
    mapping = suggest_mapping(columns)
    assert mapping["cena"] == "price"
    assert mapping["termin_h"] == "deadline"
    assert mapping["czas_produkcji_h"] == "processing_time"
    assert mapping["x"] == "width"


def test_required_fields_for_modes() -> None:
    ml_only = required_fields(require_ml=True, require_sto=False)
    sto_only = required_fields(require_ml=False, require_sto=True)
    both = required_fields(require_ml=True, require_sto=True)
    assert "cena" in ml_only
    assert "termin_h" in sto_only
    assert ml_only.issubset(both)
    assert sto_only.issubset(both)


def test_apply_data_mapping_for_sto_minimum_columns() -> None:
    df = pd.DataFrame(
        {
            "duration": [10, 20],
            "due_date": [50, 60],
            "job_id": ["A1", "A2"],
        }
    )
    mapping = {
        "czas_produkcji_h": "duration",
        "termin_h": "due_date",
        "sto_job_id": "job_id",
    }
    out = apply_data_mapping(df, mapping, require_ml=False, require_sto=True)["full_df"]
    assert list(out["czas_produkcji_h"]) == [10, 20]
    assert list(out["termin_h"]) == [50, 60]
    assert list(out["sto_job_id"]) == ["A1", "A2"]


def test_apply_data_mapping_fills_defaults_for_ml() -> None:
    df = pd.DataFrame(
        {
            "cena": [100.0],
            "odpad": [0.2],
            "termin_h": [30],
            "czas_produkcji_h": [12],
        }
    )
    out = apply_data_mapping(df, {}, require_ml=True, require_sto=False)["full_df"]
    assert out.loc[0, "ksztalt"] == "kwadrat"
    assert out.loc[0, "material"] == "mikrofibra"
    assert out.loc[0, "x"] == 30.0


def test_apply_data_mapping_rejects_non_numeric_required() -> None:
    df = pd.DataFrame(
        {
            "cena": ["abc"],
            "odpad": [0.1],
            "termin_h": [10],
            "czas_produkcji_h": [5],
        }
    )
    with pytest.raises(ValueError):
        apply_data_mapping(df, {}, require_ml=True, require_sto=False)
