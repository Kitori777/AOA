from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED_TABLE_EXTENSIONS = {".csv", ".txt", ".tsv"}


def load_csv(path):
    """Load a CSV file into a pandas DataFrame.

    This function keeps the historical name because many parts of the app and
    tests use it. For the GUI it now accepts common table-like text files too:
    CSV, TSV and TXT with an automatically detected separator.
    """
    return load_table(path)


def load_table(path) -> pd.DataFrame:
    """Load CSV/TXT/TSV data with delimiter sniffing.

    The app should not assume that every user imports production data. This
    loader accepts generic tabular data and lets pandas infer the separator for
    CSV/TXT files. TSV is read with a tab separator explicitly.
    """
    file_path = Path(path)
    extension = file_path.suffix.lower()
    if extension not in SUPPORTED_TABLE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_TABLE_EXTENSIONS))
        raise ValueError(f"Nieobsługiwany format pliku: {extension}. Obsługiwane: {allowed}")

    if extension == ".tsv":
        return pd.read_csv(file_path, sep="\t")

    try:
        return pd.read_csv(file_path, sep=None, engine="python")
    except Exception:
        return pd.read_csv(file_path)


def save_csv(df, path):
    """Save a pandas DataFrame to CSV without the index column.

    Args:
        df: DataFrame to save.
        path: Target file path.
    """
    df.to_csv(path, index=False)
