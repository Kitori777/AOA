from __future__ import annotations

import re

import numpy as np
import pandas as pd

COMMAND_CHART_ALIASES = {
    "scatter": "Scatter", "punkt": "Scatter", "punkty": "Scatter", "rozrzut": "Scatter",
    "line": "Line", "linia": "Line", "trend": "Line", "hist": "Histogram", "histogram": "Histogram",
    "bar": "Bar Chart", "bars": "Bar Chart", "slupki": "Bar Chart", "pie": "Pie Chart", "area": "Area Chart",
    "violin": "Violin Plot", "kde": "KDE Plot", "ecdf": "ECDF Plot", "regression": "Regression Plot",
    "regresja": "Regression Plot", "joint": "Joint Plot", "pairplot": "Pair Plot", "box": "Boxplot",
    "boxplot": "Boxplot", "pudełko": "Boxplot", "heatmap": "Heatmap Density", "gęstość": "Heatmap Density",
    "gestosc": "Heatmap Density", "bubble": "Bubble Chart", "bąbel": "Bubble Chart", "babel": "Bubble Chart",
    "corr": "CorrelationMatrix", "korelacja": "CorrelationMatrix", "diagnostics": "Diagnostics",
    "diagnostyka": "Model Diagnostics", "diagnostyka_modelu": "Model Diagnostics", "modelcheck": "Model Diagnostics",
    "posterior": "Model Diagnostics", "residuals": "Model Diagnostics", "dashboard": "Production Dashboard",
    "produkcja": "Production Dashboard", "esm": "ESM Best Method", "best_method": "ESM Best Method",
    "najlepsza_metoda": "ESM Best Method", "tree": "SolutionTree", "drzewo": "SolutionTree",
    "drzewo_rozwiazan": "SolutionTree", "solutiontree": "SolutionTree", "solution_tree": "SolutionTree",
    "network": "Network Graph", "graf": "Network Graph", "siec": "Network Graph", "braki": "Missingness Map",
    "missing": "Missingness Map", "ranking": "Column Ranking", "outlier": "Outlier Map",
    "odstające": "Outlier Map", "odstajace": "Outlier Map", "pca": "PCA State Segments",
    "segmenty": "PCA State Segments", "lda": "LDA vs t-SNE", "tsne": "LDA vs t-SNE",
    "kmeans": "KMeans vs GMM", "gmm": "KMeans vs GMM",
}


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=[np.number]).columns.tolist()


def default_columns(df: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    columns = numeric_columns(df) or list(df.columns)
    if not columns:
        return None, None, None
    return columns[0], columns[1] if len(columns) > 1 else columns[0], columns[min(2, len(columns) - 1)]


def best_column_match(df: pd.DataFrame, token: str) -> str | None:
    cleaned = token.strip().strip(",.;:()[]{}").lower()
    if not cleaned:
        return None
    by_lower = {column.lower(): column for column in df.columns}
    if cleaned in by_lower:
        return by_lower[cleaned]
    cleaned_norm = cleaned.replace("_", "").replace("-", "")
    return next(
        (column for column in df.columns if cleaned_norm == column.lower().replace("_", "").replace("-", "")
         or cleaned_norm in column.lower().replace("_", "").replace("-", "")),
        None,
    )


def parse_visual_command(df: pd.DataFrame, command: str) -> dict[str, str | None]:
    if df is None or df.empty:
        raise ValueError("Najpierw wczytaj dane.")
    text = command.strip()
    if not text:
        raise ValueError("Wpisz opis wykresu, np. 'scatter x cena y odpad'.")
    lowered = text.lower()
    chart_type = next(
        (resolved for alias, resolved in COMMAND_CHART_ALIASES.items() if re.search(rf"\b{re.escape(alias)}\b", lowered)),
        "Scatter",
    )
    x_default, y_default, z_default = default_columns(df)
    result = {"chart_type": chart_type, "x_col": x_default, "y_col": y_default, "z_col": z_default}
    tokens = re.split(r"\s+", text)
    key_map = {"x": "x_col", "y": "y_col", "z": "z_col", "kolor": "z_col", "color": "z_col", "rozmiar": "z_col", "size": "z_col"}
    index = 0
    while index < len(tokens) - 1:
        key = tokens[index].lower().strip(":=")
        if key in key_map:
            match = best_column_match(df, tokens[index + 1])
            if match is not None:
                result[key_map[key]] = match
            index += 2
        else:
            index += 1
    ordered_mentions = list(dict.fromkeys(filter(None, (best_column_match(df, token) for token in tokens))))
    if ordered_mentions:
        result["x_col"] = result["x_col"] if " x " in f" {lowered} " else ordered_mentions[0]
    if len(ordered_mentions) > 1 and " y " not in f" {lowered} ":
        result["y_col"] = ordered_mentions[1]
    if chart_type == "Histogram":
        result["y_col"] = result["x_col"]
    if chart_type == "Boxplot" and ordered_mentions:
        result["y_col"] = ordered_mentions[0]
    return result
