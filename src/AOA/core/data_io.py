from __future__ import annotations

import csv
from collections import Counter
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
        df = pd.read_csv(file_path, sep="\t")
        _validate_columns(df, file_path)
        return df

    delimiter = _detect_delimiter(file_path)
    try:
        if delimiter:
            df = pd.read_csv(file_path, sep=delimiter)
        else:
            df = pd.read_csv(file_path, sep=None, engine="python")
    except Exception:
        df = pd.read_csv(file_path)
    _validate_columns(df, file_path)
    return df


def save_csv(df, path):
    """Save a pandas DataFrame to CSV without the index column.

    Args:
        df: DataFrame to save.
        path: Target file path.
    """
    df.to_csv(path, index=False)


def _detect_delimiter(file_path: Path) -> str | None:
    try:
        with file_path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            sample = "".join(handle.readline() for _ in range(8))
        if not sample.strip():
            return ","
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        return dialect.delimiter
    except Exception:
        return None


def _validate_columns(df: pd.DataFrame, file_path: Path) -> None:
    if df is None or df.empty and len(df.columns) == 0:
        raise ValueError(f"Plik {file_path.name} nie zawiera naglowkow kolumn.")
    normalized = [str(col).strip().lower() for col in df.columns]
    duplicates = [name for name, count in Counter(normalized).items() if count > 1]
    if duplicates:
        dup_list = ", ".join(sorted(duplicates))
        raise ValueError(f"Zduplikowane nazwy kolumn po normalizacji: {dup_list}")
