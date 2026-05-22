from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ViewerResult:
    df: pd.DataFrame
    text: str
    report: str


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=[np.number]).columns.tolist()


def _format_number(value: float) -> str:
    if pd.isna(value):
        return "brak"
    return f"{value:.4g}"


@dataclass(frozen=True)
class DatasetProfile:
    rows: int
    columns: int
    numeric_columns: int
    categorical_columns: int
    missing_values: int
    duplicate_rows: int


def build_dataset_profile(df: pd.DataFrame) -> DatasetProfile:
    if df is None or df.empty:
        return DatasetProfile(0, 0, 0, 0, 0, 0)
    numeric_cols = _numeric_columns(df)
    return DatasetProfile(
        rows=len(df),
        columns=len(df.columns),
        numeric_columns=len(numeric_cols),
        categorical_columns=len([col for col in df.columns if col not in numeric_cols]),
        missing_values=int(df.isna().sum().sum()),
        duplicate_rows=int(df.duplicated().sum()),
    )


def build_missing_report(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "Brak danych do raportu braków."
    missing = df.isna().sum().sort_values(ascending=False)
    missing = missing[missing > 0]
    if missing.empty:
        return "BRAKI DANYCH\n===========\nNie wykryto brakujących wartości."
    lines = ["BRAKI DANYCH", "==========="]
    for column, count in missing.head(20).items():
        percent = 100 * count / max(len(df), 1)
        lines.append(f"- {column}: {count} ({percent:.1f}%)")
    return "\n".join(lines)


def filter_sort_limit_dataframe(
    df: pd.DataFrame,
    *,
    query: str = "",
    sort_column: str | None = None,
    descending: bool = False,
    limit: int = 200,
    numeric_column: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    top_mode: str = "all",
) -> pd.DataFrame:
    """Return a user-facing table preview after filtering, sorting and limiting."""
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    query = query.strip()
    if query:
        mask = (
            result.astype(str)
            .apply(lambda col: col.str.contains(query, case=False, na=False), axis=0)
            .any(axis=1)
        )
        result = result.loc[mask]

    if numeric_column and numeric_column in result.columns:
        numeric_values = pd.to_numeric(result[numeric_column], errors="coerce")
        if min_value is not None:
            result = result.loc[numeric_values >= min_value]
            numeric_values = numeric_values.loc[result.index]
        if max_value is not None:
            result = result.loc[numeric_values <= max_value]

    if top_mode in {"largest", "smallest"} and numeric_column and numeric_column in result.columns:
        numeric_values = pd.to_numeric(result[numeric_column], errors="coerce")
        result = (
            result.assign(_aoa_sort_value=numeric_values)
            .dropna(subset=["_aoa_sort_value"])
            .sort_values("_aoa_sort_value", ascending=top_mode == "smallest", kind="mergesort")
            .drop(columns=["_aoa_sort_value"])
        )
    elif sort_column and sort_column in result.columns:
        result = result.sort_values(sort_column, ascending=not descending, kind="mergesort")

    if limit <= 0:
        limit = 200
    return result.head(limit)


def build_column_profile(df: pd.DataFrame, column: str | None) -> str:
    if df is None or df.empty or not column or column not in df.columns:
        return "Wybierz kolumnę, aby zobaczyć jej profil."

    series = df[column]
    missing = int(series.isna().sum())
    unique = int(series.nunique(dropna=True))
    lines = [
        f"PROFIL KOLUMNY: {column}",
        "=" * (16 + len(column)),
        f"Typ: {series.dtype}",
        f"Braki danych: {missing}",
        f"Unikalne wartości: {unique}",
    ]

    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if not numeric.empty:
            q1 = float(numeric.quantile(0.25))
            q3 = float(numeric.quantile(0.75))
            iqr = q3 - q1
            outliers = int(((numeric < q1 - 1.5 * iqr) | (numeric > q3 + 1.5 * iqr)).sum())
            lines.extend(
                [
                    f"Min / max: {_format_number(float(numeric.min()))} / {_format_number(float(numeric.max()))}",
                    f"Średnia: {_format_number(float(numeric.mean()))}",
                    f"Mediana: {_format_number(float(numeric.median()))}",
                    f"Odchylenie std: {_format_number(float(numeric.std(ddof=0)))}",
                    f"IQR: {_format_number(float(iqr))}",
                    f"Odstające IQR: {outliers}",
                ]
            )
    else:
        top_values = series.astype(str).value_counts(dropna=True).head(6)
        lines.append("Najczęstsze wartości:")
        lines.extend(f"- {idx}: {count}" for idx, count in top_values.items())

    return "\n".join(lines)


def build_dataset_report(df: pd.DataFrame, visible_df: pd.DataFrame | None = None) -> str:
    if df is None or df.empty:
        return "Brak danych do raportu."

    numeric_cols = _numeric_columns(df)
    categorical_cols = [col for col in df.columns if col not in numeric_cols]
    visible_count = len(visible_df) if visible_df is not None else len(df)
    missing_total = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    lines = [
        "PODSUMOWANIE PLIKU",
        "=================",
        f"Wiersze w pliku: {len(df)}",
        f"Wiersze po filtrze: {visible_count}",
        f"Kolumny: {len(df.columns)}",
        f"Kolumny liczbowe: {len(numeric_cols)}",
        f"Kolumny tekstowe/kategorialne: {len(categorical_cols)}",
        f"Braki danych: {missing_total}",
        f"Duplikaty wierszy: {duplicate_rows}",
        "",
        "Co możesz zrobić:",
        "- wpisz tekst w filtrze, aby zawęzić dane,",
        "- wybierz kolumnę sortowania,",
        "- obejrzyj profil wybranej kolumny,",
        "- używaj tego widoku jako startu do dalszej analizy danych.",
    ]
    return "\n".join(lines)


def build_viewer_result(
    df: pd.DataFrame,
    *,
    query: str = "",
    sort_column: str | None = None,
    descending: bool = False,
    limit: int = 200,
    profile_column: str | None = None,
    numeric_column: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    top_mode: str = "all",
) -> ViewerResult:
    visible_df = filter_sort_limit_dataframe(
        df,
        query=query,
        sort_column=sort_column,
        descending=descending,
        limit=limit,
        numeric_column=numeric_column,
        min_value=min_value,
        max_value=max_value,
        top_mode=top_mode,
    )
    text = visible_df.to_string(index=True) if not visible_df.empty else "Brak wierszy po filtrze."
    report = build_dataset_report(df, visible_df)
    if profile_column:
        report = f"{report}\n\n{build_column_profile(df, profile_column)}"
    return ViewerResult(df=visible_df, text=text, report=report)
