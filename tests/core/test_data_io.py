import pandas as pd

from AOA.core.data_io import load_csv, save_csv


def test_save_csv_creates_file(tmp_path):
    df = pd.DataFrame({
        "cena": [100, 200],
        "odpad": [0.1, 0.2],
    })

    file_path = tmp_path / "test_data.csv"

    save_csv(df, file_path)

    assert file_path.exists()


def test_load_csv_returns_dataframe(tmp_path):
    df = pd.DataFrame({
        "cena": [100, 200],
        "odpad": [0.1, 0.2],
    })

    file_path = tmp_path / "test_data.csv"
    df.to_csv(file_path, index=False)

    loaded_df = load_csv(file_path)

    assert isinstance(loaded_df, pd.DataFrame)
    assert list(loaded_df.columns) == ["cena", "odpad"]
    assert len(loaded_df) == 2


def test_save_and_load_csv_preserve_shape(tmp_path):
    df = pd.DataFrame({
        "cena": [100, 200, 300],
        "odpad": [0.1, 0.2, 0.3],
        "termin_dni": [5, 10, 15],
    })

    file_path = tmp_path / "roundtrip.csv"

    save_csv(df, file_path)
    loaded_df = load_csv(file_path)

    assert loaded_df.shape == df.shape
    assert list(loaded_df.columns) == list(df.columns)
