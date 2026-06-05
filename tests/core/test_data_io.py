import pandas as pd
import pytest

from AOA.core.data_io import load_csv, save_csv


def test_save_csv_creates_file(tmp_path):
    df = pd.DataFrame(
        {
            "cena": [100, 200],
            "odpad": [0.1, 0.2],
        }
    )

    file_path = tmp_path / "test_data.csv"

    save_csv(df, file_path)

    assert file_path.exists()


def test_load_csv_returns_dataframe(tmp_path):
    df = pd.DataFrame(
        {
            "cena": [100, 200],
            "odpad": [0.1, 0.2],
        }
    )

    file_path = tmp_path / "test_data.csv"
    df.to_csv(file_path, index=False)

    loaded_df = load_csv(file_path)

    assert isinstance(loaded_df, pd.DataFrame)
    assert list(loaded_df.columns) == ["cena", "odpad"]
    assert len(loaded_df) == 2


def test_save_and_load_csv_preserve_shape(tmp_path):
    df = pd.DataFrame(
        {
            "cena": [100, 200, 300],
            "odpad": [0.1, 0.2, 0.3],
            "termin_dni": [5, 10, 15],
        }
    )

    file_path = tmp_path / "roundtrip.csv"

    save_csv(df, file_path)
    loaded_df = load_csv(file_path)

    assert loaded_df.shape == df.shape
    assert list(loaded_df.columns) == list(df.columns)


def test_load_csv_detects_semicolon_delimiter(tmp_path):
    file_path = tmp_path / "semicolon.csv"
    file_path.write_text("cena;odpad\n10;0.2\n", encoding="utf-8")
    loaded_df = load_csv(file_path)
    assert list(loaded_df.columns) == ["cena", "odpad"]
    assert loaded_df.iloc[0]["cena"] == 10


def test_load_csv_raises_on_duplicate_normalized_columns(tmp_path):
    file_path = tmp_path / "dup.csv"
    file_path.write_text("Cena,cena\n10,11\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Zduplikowane nazwy kolumn"):
        load_csv(file_path)
