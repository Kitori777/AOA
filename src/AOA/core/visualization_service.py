from __future__ import annotations

import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from sklearn.tree import plot_tree

from AOA.core.diagrams.correlation_matrix import prepare_correlation_matrix_data
from AOA.core.diagrams.decision_tree_diagram import prepare_decision_tree_data
from AOA.core.diagrams.gantt_chart import prepare_gantt_chart_data
from AOA.core.diagrams.line_chart import prepare_line_chart_data
from AOA.core.diagrams.similarity_matrix import prepare_similarity_matrix_data

D3_CDN_URL = "https://cdn.jsdelivr.net/npm/d3@7"

COMMAND_CHART_ALIASES = {
    "scatter": "Scatter",
    "punkt": "Scatter",
    "punkty": "Scatter",
    "rozrzut": "Scatter",
    "line": "Line",
    "linia": "Line",
    "trend": "Line",
    "hist": "Histogram",
    "histogram": "Histogram",
    "box": "Boxplot",
    "boxplot": "Boxplot",
    "pudełko": "Boxplot",
    "heatmap": "Heatmap Density",
    "gęstość": "Heatmap Density",
    "gestosc": "Heatmap Density",
    "bubble": "Bubble Chart",
    "bąbel": "Bubble Chart",
    "babel": "Bubble Chart",
    "corr": "CorrelationMatrix",
    "korelacja": "CorrelationMatrix",
    "dashboard": "Production Dashboard",
    "produkcja": "Production Dashboard",
    "braki": "Missingness Map",
    "missing": "Missingness Map",
    "ranking": "Column Ranking",
    "outlier": "Outlier Map",
    "odstające": "Outlier Map",
    "odstajace": "Outlier Map",
}


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=[np.number]).columns.tolist()


def _default_columns(df: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    numeric_cols = _numeric_columns(df)
    cols = numeric_cols or list(df.columns)
    if not cols:
        return None, None, None
    return (
        cols[0],
        cols[1] if len(cols) > 1 else cols[0],
        cols[2] if len(cols) > 2 else (cols[1] if len(cols) > 1 else cols[0]),
    )


def _best_column_match(df: pd.DataFrame, token: str) -> str | None:
    cleaned = token.strip().strip(",.;:()[]{}").lower()
    if not cleaned:
        return None
    by_lower = {column.lower(): column for column in df.columns}
    if cleaned in by_lower:
        return by_lower[cleaned]
    cleaned_norm = cleaned.replace("_", "").replace("-", "")
    for column in df.columns:
        column_norm = column.lower().replace("_", "").replace("-", "")
        if cleaned_norm == column_norm or cleaned_norm in column_norm:
            return column
    return None


def parse_visual_command(df: pd.DataFrame, command: str) -> dict[str, str | None]:
    if df is None or df.empty:
        raise ValueError("Najpierw wczytaj dane.")
    text = command.strip()
    if not text:
        raise ValueError("Wpisz opis wykresu, np. 'scatter x cena y odpad'.")

    lowered = text.lower()
    chart_type = None
    for alias, resolved in COMMAND_CHART_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            chart_type = resolved
            break
    if chart_type is None:
        chart_type = "Scatter"

    x_default, y_default, z_default = _default_columns(df)
    result = {"chart_type": chart_type, "x_col": x_default, "y_col": y_default, "z_col": z_default}
    tokens = re.split(r"\s+", text)
    key_map = {
        "x": "x_col",
        "y": "y_col",
        "z": "z_col",
        "kolor": "z_col",
        "color": "z_col",
        "rozmiar": "z_col",
        "size": "z_col",
    }
    index = 0
    while index < len(tokens) - 1:
        token = tokens[index]
        key = token.lower().strip(":=")
        if key in key_map:
            match = _best_column_match(df, tokens[index + 1])
            if match is not None:
                result[key_map[key]] = match
            index += 2
            continue
        index += 1

    mentioned = [_best_column_match(df, token) for token in tokens]
    mentioned = [column for column in mentioned if column is not None]
    ordered_mentions = list(dict.fromkeys(mentioned))
    if ordered_mentions:
        result["x_col"] = result["x_col"] if " x " in f" {lowered} " else ordered_mentions[0]
    if len(ordered_mentions) > 1 and " y " not in f" {lowered} ":
        result["y_col"] = ordered_mentions[1]
    if len(ordered_mentions) > 2 and all(key not in lowered for key in (" z ", "kolor", "color")):
        result["z_col"] = ordered_mentions[2]

    if chart_type in {"Histogram"}:
        result["y_col"] = result["x_col"]
    if chart_type in {"Boxplot"} and ordered_mentions:
        result["y_col"] = ordered_mentions[0]
    return result


def _style_axes(ax, *, title: str | None = None) -> None:
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    ax.grid(True, alpha=0.18)
    ax.set_facecolor("#f8fafc")
    for spine in ax.spines.values():
        spine.set_alpha(0.25)


def _num(df: pd.DataFrame, col: str | None) -> pd.Series:
    if col not in df.columns:
        raise ValueError("Wybrana kolumna nie istnieje w danych")
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if series.empty:
        raise ValueError("Wybrana kolumna nie ma wartości liczbowych")
    return series


def _paired_numeric(df: pd.DataFrame, *cols: str | None) -> pd.DataFrame:
    valid_cols = [col for col in cols if col in df.columns]
    if len(valid_cols) != len(cols):
        raise ValueError("Wybierz poprawne kolumny liczbowe")
    result = df[valid_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if result.empty:
        raise ValueError("Wybrane kolumny nie mają wspólnych wartości liczbowych")
    return result


def build_visual_report(
    df: pd.DataFrame,
    x_col: str | None = None,
    y_col: str | None = None,
    z_col: str | None = None,
    chart_type: str | None = None,
) -> str:
    if df is None or df.empty:
        return "Brak danych do raportu."
    numeric_cols = _numeric_columns(df)
    lines = [
        "RAPORT DANYCH",
        "============",
        f"Widok: {chart_type or 'wykres'}",
        f"Rekordy: {len(df)}",
        f"Kolumny: {len(df.columns)}",
        f"Kolumny liczbowe: {len(numeric_cols)}",
        f"Braki danych: {int(df.isna().sum().sum())}",
    ]
    for label, col in (("X", x_col), ("Y", y_col), ("Z", z_col)):
        if col in numeric_cols:
            series = _num(df, col)
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            outliers = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
            lines.extend(
                [
                    "",
                    f"{label}: {col}",
                    f"  min / max: {series.min():.4g} / {series.max():.4g}",
                    f"  średnia / mediana: {series.mean():.4g} / {series.median():.4g}",
                    f"  odchylenie std: {series.std(ddof=0):.4g}",
                    f"  obserwacje odstające IQR: {outliers}",
                ]
            )
    if x_col in numeric_cols and y_col in numeric_cols:
        corr = float(df[[x_col, y_col]].corr(numeric_only=True).iloc[0, 1])
        lines.extend(["", f"Korelacja {x_col} ↔ {y_col}: {corr:.4f}"])
        if abs(corr) >= 0.7:
            lines.append("Wniosek: zależność wygląda na silną.")
        elif abs(corr) >= 0.35:
            lines.append("Wniosek: zależność wygląda na umiarkowaną.")
        else:
            lines.append("Wniosek: zależność liniowa wygląda na słabą.")
    lines.extend(
        [
            "",
            "Interakcja:",
            "- użyj lupy i przesuwania z paska Matplotlib,",
            "- w 3D przeciągnij wykres myszką, aby obrócić scenę,",
            "- zmieniaj X/Y/Z i typ wykresu jak w małym laboratorium danych.",
        ]
    )
    return "\n".join(lines)


def _production_dashboard(df: pd.DataFrame) -> Figure:
    numeric_cols = _numeric_columns(df)
    if not numeric_cols:
        raise ValueError("Production Dashboard wymaga kolumn liczbowych")
    fig = Figure(figsize=(11, 6.8), dpi=100, facecolor="#f8fafc")
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 2)

    time_col = "czas_produkcji_h" if "czas_produkcji_h" in df.columns else numeric_cols[0]
    deadline_col = (
        "termin_h" if "termin_h" in df.columns else numeric_cols[min(1, len(numeric_cols) - 1)]
    )
    quality_col = "pred_quality" if "pred_quality" in df.columns else numeric_cols[0]
    delay_col = "pred_delay" if "pred_delay" in df.columns else deadline_col
    common = _paired_numeric(df, time_col, deadline_col).head(3000)
    axes[0][0].scatter(common[time_col], common[deadline_col], alpha=0.62, s=26)
    axes[0][0].set_xlabel(time_col)
    axes[0][0].set_ylabel(deadline_col)
    _style_axes(axes[0][0], title="Czas produkcji względem terminu")

    series = _num(df, quality_col)
    axes[0][1].hist(series, bins=28, color="#2563eb", alpha=0.82)
    axes[0][1].axvline(series.mean(), color="#f97316", linewidth=2, label="średnia")
    axes[0][1].legend()
    axes[0][1].set_xlabel(quality_col)
    _style_axes(axes[0][1], title="Rozkład jakości / kluczowej zmiennej")

    if "material" in df.columns:
        grouped = df.groupby("material", dropna=False)[time_col].mean().sort_values()
        axes[1][0].barh(grouped.index.astype(str), grouped.values, color="#10b981")
        axes[1][0].set_xlabel(f"średni {time_col}")
        _style_axes(axes[1][0], title="Materiał a czas produkcji")
    else:
        _column_variability_subplot(df, axes[1][0])

    corr_cols = [
        col for col in [time_col, deadline_col, quality_col, delay_col] if col in numeric_cols
    ]
    corr_cols = list(dict.fromkeys(corr_cols))[:4]
    corr = df[corr_cols].corr(numeric_only=True).fillna(0.0)
    image = axes[1][1].imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    axes[1][1].set_xticks(range(len(corr_cols)), corr_cols, rotation=35, ha="right")
    axes[1][1].set_yticks(range(len(corr_cols)), corr_cols)
    _style_axes(axes[1][1], title="Szybka mapa korelacji")
    fig.colorbar(image, ax=axes[1][1], fraction=0.046, pad=0.04)
    fig.suptitle("Production Dashboard", fontsize=15, fontweight="bold")
    fig.tight_layout()
    return fig


def _column_variability_subplot(df: pd.DataFrame, ax) -> None:
    rows = []
    for col in _numeric_columns(df):
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if not series.empty:
            rows.append((col, float(series.std(ddof=0))))
    rows = sorted(rows, key=lambda item: item[1], reverse=True)[:8]
    labels = [item[0] for item in rows][::-1]
    values = [item[1] for item in rows][::-1]
    ax.barh(labels, values, color="#8b5cf6")
    ax.set_xlabel("odchylenie standardowe")
    _style_axes(ax, title="Najbardziej zmienne kolumny")


def _missingness_map(df: pd.DataFrame) -> Figure:
    if df.empty:
        raise ValueError("Brak danych do mapy braków")
    subset = df.iloc[: min(len(df), 250), : min(len(df.columns), 30)]
    missing = subset.isna().astype(int)
    fig = Figure(figsize=(11, 6.2), dpi=100, facecolor="#f8fafc")
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    image = ax.imshow(missing.T, aspect="auto", interpolation="nearest", cmap="Reds")
    ax.set_title("Missingness Map — gdzie są braki danych", fontsize=13, fontweight="bold")
    ax.set_xlabel("rekord")
    ax.set_ylabel("kolumna")
    ax.set_yticks(range(len(subset.columns)), subset.columns)
    fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02, label="brak")
    fig.tight_layout()
    return fig


def _priority_timeline(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> Figure:
    numeric_cols = _numeric_columns(df)
    y_name = (
        "priority"
        if "priority" in numeric_cols
        else (y_col if y_col in numeric_cols else numeric_cols[0])
    )
    x_name = x_col if x_col in numeric_cols else None
    ordered = df.copy()
    if x_name is not None:
        ordered = ordered.sort_values(x_name)
    ordered = ordered.head(240).reset_index(drop=True)
    y = pd.to_numeric(ordered[y_name], errors="coerce").fillna(0)
    fig = Figure(figsize=(10.8, 6.2), dpi=100, facecolor="#f8fafc")
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    x_values = ordered[x_name] if x_name is not None else ordered.index
    ax.plot(x_values, y, linewidth=2.5, color="#2563eb", label=y_name)
    ax.fill_between(x_values, y, alpha=0.18, color="#2563eb")
    ax.scatter(x_values, y, s=18, color="#1d4ed8", alpha=0.75)
    ax.set_xlabel(x_name or "kolejność")
    ax.set_ylabel(y_name)
    ax.legend()
    _style_axes(ax, title="Timeline priorytetu / wyniku")
    fig.tight_layout()
    return fig


def _dashboard(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> Figure:
    numeric_cols = _numeric_columns(df)
    if not numeric_cols:
        raise ValueError("Dashboard wymaga kolumn liczbowych")
    x_name = x_col if x_col in numeric_cols else numeric_cols[0]
    y_name = y_col if y_col in numeric_cols else numeric_cols[min(1, len(numeric_cols) - 1)]
    common = _paired_numeric(df, x_name, y_name)
    x = common[x_name]
    y = common[y_name]
    fig = Figure(figsize=(10, 6.5), dpi=100)
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 2)
    axes[0][0].scatter(x, y, alpha=0.65)
    axes[0][0].set_title(f"Zależność: {x_name} ↔ {y_name}")
    axes[0][0].set_xlabel(x_name)
    axes[0][0].set_ylabel(y_name)
    axes[0][1].hist(x, bins=30, alpha=0.85)
    axes[0][1].axvline(x.mean(), linewidth=2, label="średnia")
    axes[0][1].set_title(f"Rozkład: {x_name}")
    axes[0][1].legend()
    axes[1][0].boxplot(y)
    axes[1][0].set_title(f"Odstające wartości: {y_name}")
    corr_cols = numeric_cols[: min(6, len(numeric_cols))]
    corr = df[corr_cols].corr(numeric_only=True).fillna(0.0)
    image = axes[1][1].imshow(corr, aspect="auto", vmin=-1, vmax=1)
    axes[1][1].set_title("Mini-korelacje")
    axes[1][1].set_xticks(range(len(corr_cols)), corr_cols, rotation=45, ha="right")
    axes[1][1].set_yticks(range(len(corr_cols)), corr_cols)
    fig.colorbar(image, ax=axes[1][1], fraction=0.046, pad=0.04)
    for ax in axes.ravel():
        ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def _diagnostics(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> Figure:
    common = _paired_numeric(df, x_col, y_col)
    x_name, y_name = common.columns[0], common.columns[1]
    coefficients = np.polyfit(common[x_name], common[y_name], deg=1)
    fitted = np.polyval(coefficients, common[x_name])
    residuals = common[y_name] - fitted
    standardized = (residuals - residuals.mean()) / (residuals.std(ddof=0) + 1e-9)
    fig = Figure(figsize=(10, 6.5), dpi=100)
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 2)
    axes[0][0].scatter(common[x_name], common[y_name], alpha=0.65)
    axes[0][0].plot(common[x_name], fitted, linewidth=2)
    axes[0][0].set_title("Dane i linia trendu")
    axes[0][1].scatter(fitted, residuals, alpha=0.65)
    axes[0][1].axhline(0, linewidth=1)
    axes[0][1].set_title("Reszty względem dopasowania")
    axes[1][0].scatter(fitted, np.sqrt(np.abs(standardized)), alpha=0.65)
    axes[1][0].set_title("Rozrzut błędu")
    sorted_residuals = np.sort(standardized)
    theoretical = np.linspace(-2, 2, len(sorted_residuals))
    axes[1][1].scatter(theoretical, sorted_residuals, alpha=0.65)
    axes[1][1].plot([-2, 2], [-2, 2], linewidth=1)
    axes[1][1].set_title("Normalność reszt — prosty QQ")
    for ax in axes.ravel():
        ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def _scatter_3d(
    df: pd.DataFrame, x_col: str | None, y_col: str | None, z_col: str | None
) -> Figure:
    common = _paired_numeric(df, x_col, y_col, z_col)
    x_name, y_name, z_name = common.columns
    fig = Figure(figsize=(9, 5.8), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111, projection="3d")
    points = ax.scatter(
        common[x_name], common[y_name], common[z_name], c=common[z_name], alpha=0.75
    )
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_zlabel(z_name)
    ax.set_title(f"3D Scatter: {x_name} / {y_name} / {z_name}")
    fig.colorbar(points, ax=ax, fraction=0.035, pad=0.08, label=z_name)
    fig.tight_layout()
    return fig


def _surface_3d(
    df: pd.DataFrame, x_col: str | None, y_col: str | None, z_col: str | None
) -> Figure:
    common = _paired_numeric(df, x_col, y_col, z_col).head(2500)
    x_name, y_name, z_name = common.columns
    x = common[x_name].to_numpy()
    y = common[y_name].to_numpy()
    z = common[z_name].to_numpy()
    fig = Figure(figsize=(9, 5.8), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_trisurf(x, y, z, linewidth=0.15, alpha=0.9)
    ax.scatter(x, y, z, s=5, alpha=0.25)
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_zlabel(z_name)
    ax.set_title(f"3D Surface: {z_name} względem {x_name} i {y_name}")
    fig.tight_layout()
    return fig


def _outlier_map(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> Figure:
    common = _paired_numeric(df, x_col, y_col)
    x_name, y_name = common.columns
    x = common[x_name]
    y = common[y_name]
    zx = np.abs((x - x.mean()) / (x.std(ddof=0) + 1e-9))
    zy = np.abs((y - y.mean()) / (y.std(ddof=0) + 1e-9))
    score = zx + zy
    fig = Figure(figsize=(9, 5.8), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    points = ax.scatter(x, y, c=score, alpha=0.75)
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_title("Mapa odstających obserwacji — im wyższy kolor, tym większe odchylenie")
    ax.grid(True, alpha=0.25)
    fig.colorbar(points, ax=ax, label="wynik odchylenia")
    fig.tight_layout()
    return fig


def _step_view(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> Figure:
    common = _paired_numeric(df, x_col, y_col).head(120)
    x_name, y_name = common.columns
    ordered = common.sort_values(x_name).reset_index(drop=True)
    rolling = ordered[y_name].rolling(8, min_periods=1).mean()
    fig = Figure(figsize=(9, 5.8), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot(
        ordered[x_name],
        ordered[y_name],
        marker="o",
        linewidth=1,
        alpha=0.45,
        label="kolejne punkty",
    )
    ax.plot(ordered[x_name], rolling, linewidth=3, label="trend krokowy")
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_title("Widok krokowy — prosta demonstracja zachowania danych")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    return fig


def _build_figure_legacy(df, chart_type, x_col=None, y_col=None, z_col=None):
    if df is None or df.empty:
        raise ValueError("Brak danych do wizualizacji")
    if chart_type == "Production Dashboard":
        return _production_dashboard(df)
    if chart_type == "Missingness Map":
        return _missingness_map(df)
    if chart_type == "Priority Timeline":
        return _priority_timeline(df, x_col, y_col)
    if chart_type == "Dashboard":
        return _dashboard(df, x_col, y_col)
    if chart_type == "Diagnostics":
        return _diagnostics(df, x_col, y_col)
    if chart_type == "3D Scatter":
        return _scatter_3d(df, x_col, y_col, z_col)
    if chart_type == "3D Surface":
        return _surface_3d(df, x_col, y_col, z_col)
    if chart_type == "Outlier Map":
        return _outlier_map(df, x_col, y_col)
    if chart_type == "Step View":
        return _step_view(df, x_col, y_col)
    fig = Figure(figsize=(9, 5), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    if chart_type == "Scatter":
        common = _paired_numeric(df, x_col, y_col)
        ax.scatter(common[common.columns[0]], common[common.columns[1]], alpha=0.65)
        ax.set_xlabel(common.columns[0])
        ax.set_ylabel(common.columns[1])
        ax.set_title(f"Scatter: {common.columns[0]} ↔ {common.columns[1]}")
        ax.grid(True, alpha=0.25)
        return fig
    if chart_type == "Line":
        payload = prepare_line_chart_data(df, x_col, y_col)
        ax.plot(payload["x"], payload["y"], linewidth=1, alpha=0.4, label="Dane")
        ax.plot(payload["x"], payload["y_smooth"], linewidth=3, label="Średnia krocząca (5)")
        ax.set_xlabel(payload["x_label"])
        ax.set_ylabel(payload["y_label"])
        ax.set_title(payload["title"])
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig
    if chart_type == "Histogram":
        series = _num(df, x_col)
        ax.hist(series, bins=30, alpha=0.85)
        ax.axvline(series.mean(), linewidth=2, label="średnia")
        ax.set_xlabel(x_col)
        ax.set_ylabel("Liczność")
        ax.set_title(f"Histogram: {x_col}")
        ax.legend()
        return fig
    if chart_type == "Boxplot":
        ax.boxplot(_num(df, y_col))
        ax.set_ylabel(y_col)
        ax.set_title(f"Boxplot: {y_col}")
        return fig
    if chart_type == "Gantt":
        payload = prepare_gantt_chart_data(df)
        ax.barh(payload["labels"], payload["durations"], left=payload["starts"])
        ax.set_xlabel(payload["x_label"])
        return fig
    if chart_type == "CorrelationMatrix":
        payload = prepare_correlation_matrix_data(df)
        matrix = payload["matrix"].fillna(0.0)
        image = ax.imshow(matrix, aspect="auto", vmin=-1, vmax=1)
        labels = list(matrix.columns)
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        ax.set_title(payload["title"])
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        return fig
    if chart_type == "SimilarityMatrix":
        payload = prepare_similarity_matrix_data(df)
        image = ax.imshow(payload["matrix"], aspect="auto")
        labels = payload["labels"]
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        ax.set_title(payload["title"])
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        return fig
    if chart_type == "DecisionTree":
        payload = prepare_decision_tree_data(df)
        plot_tree(payload["model"], feature_names=payload["feature_names"], filled=True, ax=ax)
        return fig
    raise ValueError(f"Nieobsługiwany typ wykresu: {chart_type}")


# --- extended interactive charts for Visual Lab ---
def _bubble_chart(
    df: pd.DataFrame, x_col: str | None, y_col: str | None, z_col: str | None
) -> Figure:
    common = _paired_numeric(df, x_col, y_col, z_col)
    x_name, y_name, z_name = common.columns
    size = common[z_name].abs()
    size = 40 + 420 * (size - size.min()) / (size.max() - size.min() + 1e-9)
    fig = Figure(figsize=(10, 6.2), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    points = ax.scatter(common[x_name], common[y_name], s=size, c=common[z_name], alpha=0.55)
    ax.set_title(f"Bubble Chart: rozmiar i kolor = {z_name}")
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.grid(True, alpha=0.22)
    fig.colorbar(points, ax=ax, label=z_name)
    fig.tight_layout()
    return fig


def _heatmap_density(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> Figure:
    common = _paired_numeric(df, x_col, y_col)
    x_name, y_name = common.columns
    fig = Figure(figsize=(10, 6.2), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    image = ax.hexbin(common[x_name], common[y_name], gridsize=32, mincnt=1)
    ax.set_title(f"Heatmap gęstości: {x_name} ↔ {y_name}")
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    fig.colorbar(image, ax=ax, label="liczba punktów")
    fig.tight_layout()
    return fig


def _pair_explorer(df: pd.DataFrame) -> Figure:
    numeric_cols = _numeric_columns(df)[:4]
    if len(numeric_cols) < 2:
        raise ValueError("Pair Explorer wymaga co najmniej dwóch kolumn liczbowych")
    fig = Figure(figsize=(10.8, 6.6), dpi=100)
    FigureCanvasAgg(fig)
    axes = fig.subplots(len(numeric_cols), len(numeric_cols))
    for row, y_name in enumerate(numeric_cols):
        for col, x_name in enumerate(numeric_cols):
            ax = axes[row][col]
            if row == col:
                ax.hist(pd.to_numeric(df[x_name], errors="coerce").dropna(), bins=20, alpha=0.8)
            else:
                common = df[[x_name, y_name]].apply(pd.to_numeric, errors="coerce").dropna()
                ax.scatter(common[x_name], common[y_name], alpha=0.45, s=12)
            if row == len(numeric_cols) - 1:
                ax.set_xlabel(x_name, fontsize=8)
            else:
                ax.set_xticks([])
            if col == 0:
                ax.set_ylabel(y_name, fontsize=8)
            else:
                ax.set_yticks([])
            ax.grid(True, alpha=0.16)
    fig.suptitle("Pair Explorer — szybkie relacje między kolumnami", y=0.99)
    fig.tight_layout()
    return fig


def _column_ranking(df: pd.DataFrame) -> Figure:
    rows = []
    for col in _numeric_columns(df):
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if not series.empty:
            rows.append((col, float(series.std(ddof=0))))
    rows = sorted(rows, key=lambda item: item[1], reverse=True)[:10]
    if not rows:
        raise ValueError("Column Ranking wymaga kolumn liczbowych")
    labels = [item[0] for item in rows]
    values = [item[1] for item in rows]
    fig = Figure(figsize=(10, 6.2), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.barh(labels[::-1], values[::-1])
    ax.set_title("Ranking zmienności kolumn liczbowych")
    ax.set_xlabel("odchylenie standardowe")
    ax.grid(True, axis="x", alpha=0.22)
    fig.tight_layout()
    return fig


def build_figure_from_request(df, chart_type, x_col=None, y_col=None, z_col=None):
    if df is None or df.empty:
        raise ValueError("Brak danych do wizualizacji")
    if chart_type == "Bubble Chart":
        return _bubble_chart(df, x_col, y_col, z_col)
    if chart_type == "Heatmap Density":
        return _heatmap_density(df, x_col, y_col)
    if chart_type == "Pair Explorer":
        return _pair_explorer(df)
    if chart_type == "Column Ranking":
        return _column_ranking(df)
    try:
        return _build_figure_legacy(df, chart_type, x_col, y_col, z_col)
    except ValueError as exc:
        if chart_type == "Scatter":
            raise ValueError("Nieprawidłowe kolumny dla wykresu Scatter") from exc
        if chart_type == "Histogram":
            raise ValueError("Nieprawidłowa kolumna dla histogramu") from exc
        if chart_type == "Boxplot":
            raise ValueError("Nieprawidłowa kolumna dla boxplot") from exc
        raise


def build_figure_from_prompt(df, command: str):
    parsed = parse_visual_command(df, command)
    return build_figure_from_request(
        df,
        parsed["chart_type"],
        parsed["x_col"],
        parsed["y_col"],
        parsed["z_col"],
    ), parsed


def build_d3_html_report(
    df: pd.DataFrame,
    x_col: str | None = None,
    y_col: str | None = None,
    z_col: str | None = None,
    chart_type: str | None = None,
    max_rows: int = 900,
) -> str:
    if df is None or df.empty:
        raise ValueError("Brak danych do raportu D3")
    x_default, y_default, z_default = _default_columns(df)
    x_name = x_col if x_col in df.columns else x_default
    y_name = y_col if y_col in df.columns else y_default
    z_name = z_col if z_col in df.columns else z_default
    export_cols = list(df.columns)
    export_df = df[export_cols].head(max_rows).replace([np.inf, -np.inf], np.nan)
    payload = export_df.where(pd.notna(export_df), None).to_dict(orient="records")
    data_json = json.dumps(payload, ensure_ascii=False)
    title = html.escape(chart_type or "D3 Visual Report")
    chart_js = json.dumps(chart_type or "Scatter", ensure_ascii=False)
    x_js = json.dumps(x_name, ensure_ascii=False)
    y_js = json.dumps(y_name, ensure_ascii=False)
    z_js = json.dumps(z_name, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <script src="{D3_CDN_URL}"></script>
  <script>
    if (!window.d3) {{
      document.write('<script src="https://unpkg.com/d3@7/dist/d3.min.js"><\\/script>');
    }}
  </script>
  <style>
    :root {{ color-scheme:dark; --bg:#07111c; --panel:#0e1b29; --border:#20364d; --muted:#9fb4cc; --grid:rgba(148,163,184,.18); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,Segoe UI,Arial,sans-serif; background:var(--bg); color:#e6f0ff; }}
    header {{ padding:22px 32px; border-bottom:1px solid var(--border); background:linear-gradient(135deg,#0c1d2d,#0a1624); }}
    h1 {{ margin:0 0 6px; font-size:26px; }}
    header div {{ color:var(--muted); }}
    main {{ padding:22px 32px; display:grid; grid-template-columns:minmax(720px,1fr) 360px; gap:18px; max-width:1680px; margin:0 auto; }}
    .panel {{ background:#0e1b29; border:1px solid var(--border); border-radius:10px; padding:18px; box-shadow:0 18px 45px rgba(0,0,0,.24); }}
    svg {{ width:100%; height:640px; display:block; background:#0b1220; border-radius:10px; }}
    .d3-error {{ min-height:420px; display:flex; align-items:center; justify-content:center; background:#0b1220; color:#dbeafe; border-radius:10px; padding:32px; text-align:center; font-size:18px; line-height:1.45; }}
    .tooltip {{ position:fixed; pointer-events:none; background:#020617; color:white; border:1px solid #38bdf8; box-shadow:0 16px 40px rgba(0,0,0,.35); border-radius:8px; padding:8px 10px; opacity:0; font-size:12px; }}
    .axis text {{ fill:#b8c7d9; }}
    .axis path,.axis line {{ stroke:#46617c; }}
    text {{ fill:#dbeafe; }}
    @media (max-width: 1100px) {{ main {{ grid-template-columns:1fr; padding:18px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div>D3.js | X: {html.escape(str(x_name))} | Y: {html.escape(str(y_name))} | kolor/rozmiar: {html.escape(str(z_name))}</div>
  </header>
  <main>
    <section class="panel"><svg id="chart"></svg></section>
    <aside class="panel">
      <h2>Jak czytać</h2>
      <p>Najedź na punkt, aby zobaczyć wartości. Kolor i rozmiar wykorzystują trzecią zmienną, jeśli jest dostępna.</p>
      <p>Liczba punktów: <strong id="count"></strong></p>
      <p>Źródło biblioteki: d3/d3 przez CDN.</p>
    </aside>
  </main>
  <div class="tooltip" id="tooltip"></div>
  <script>
    const data = {data_json};
    const chartType = {chart_js};
    const xKey = {x_js};
    const yKey = {y_js};
    const zKey = {z_js};
    function drawNativeFallback() {{
      document.getElementById("count").textContent = data.length;
      const chart = document.getElementById("chart");
      const width = 980;
      const height = 620;
      const margin = {{top: 74, right: 52, bottom: 74, left: 82}};
      const clean = data.map(d => ({{x: +d[xKey], y: +d[yKey], z: +d[zKey]}}))
        .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
      const xs = clean.map(d => d.x);
      const ys = clean.map(d => d.y);
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const minY = Math.min(...ys);
      const maxY = Math.max(...ys);
      const scale = (value, min, max, start, end) => start + ((value - min) / ((max - min) || 1)) * (end - start);
      chart.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      chart.innerHTML = "";
      const ns = "http://www.w3.org/2000/svg";
      const add = (name, attrs, text) => {{
        const node = document.createElementNS(ns, name);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
        if (text) node.textContent = text;
        chart.appendChild(node);
        return node;
      }};
      add("text", {{x: margin.left, y: 34, fill: "#e6f0ff", "font-size": 20, "font-weight": 700}}, "Awaryjny podgląd SVG");
      add("text", {{x: margin.left, y: 58, fill: "#9fb4cc", "font-size": 13}}, "D3.js nie załadował się z CDN, więc raport pokazuje prosty podgląd lokalny.");
      add("line", {{x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, stroke: "#94a3b8"}});
      add("line", {{x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, stroke: "#94a3b8"}});
      add("text", {{x: width / 2, y: height - 24, fill: "#dbeafe", "text-anchor": "middle"}}, xKey);
      add("text", {{x: 24, y: height / 2, fill: "#dbeafe", "text-anchor": "middle", transform: `rotate(-90 24 ${{height / 2}})`}}, yKey);
      clean.forEach((d, index) => {{
        const cx = scale(d.x, minX, maxX, margin.left, width - margin.right);
        const cy = scale(d.y, minY, maxY, height - margin.bottom, margin.top);
        const radius = Number.isFinite(d.z) ? Math.max(4, Math.min(14, 4 + d.z / ((Math.max(...clean.map(v => v.z || 0)) || 1)) * 10)) : 7;
        add("circle", {{cx, cy, r: radius, fill: index % 2 ? "#2563eb" : "#10b981", opacity: 0.78}});
      }});
    }}
    if (!window.d3) {{
      drawNativeFallback();
    }} else {{
    document.getElementById("count").textContent = data.length;
    const svg = d3.select("#chart");
    const box = svg.node().getBoundingClientRect();
    const width = Math.max(760, box.width || 980);
    const height = 620;
    svg.attr("viewBox", [0, 0, width, height]);
    const margin = {{top: 42, right: 38, bottom: 70, left: 78}};
    const tooltip = d3.select("#tooltip");
    const showTip = (event, html) => tooltip.style("opacity", 1).html(html).style("left", `${{event.clientX + 14}}px`).style("top", `${{event.clientY + 14}}px`);
    const hideTip = () => tooltip.style("opacity", 0);
    const addXAxis = scale => svg.append("g").attr("class","axis").attr("transform",`translate(0,${{height-margin.bottom}})`).call(d3.axisBottom(scale));
    const addYAxis = scale => svg.append("g").attr("class","axis").attr("transform",`translate(${{margin.left}},0)`).call(d3.axisLeft(scale));
    function axisLabels(xText, yText) {{
      svg.append("text").attr("x", width/2).attr("y", height-22).attr("fill","#dbeafe").attr("text-anchor","middle").text(xText);
      svg.append("text").attr("x", -height/2).attr("y", 24).attr("fill","#dbeafe").attr("text-anchor","middle").attr("transform","rotate(-90)").text(yText);
    }}

    function drawScatter() {{
    const clean = data.map(d => ({{
      x: +d[xKey],
      y: +d[yKey],
      z: +d[zKey],
      raw: d
    }})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
    const x = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([margin.left, width - margin.right]);
    const y = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([height - margin.bottom, margin.top]);
    const zValues = clean.map(d => Number.isFinite(d.z) ? d.z : 0);
    const zExtent = d3.extent(zValues);
    const color = d3.scaleSequential(zExtent, d3.interpolateTurbo);
    const size = d3.scaleSqrt().domain(zExtent).range([4, 14]);
    addXAxis(x);
    addYAxis(y);
    axisLabels(xKey, yKey);
    svg.append("g").selectAll("circle").data(clean).join("circle")
      .attr("cx", d => x(d.x)).attr("cy", d => y(d.y))
      .attr("r", d => Number.isFinite(d.z) ? size(d.z) : 6)
      .attr("fill", d => Number.isFinite(d.z) ? color(d.z) : "#2563eb")
      .attr("opacity", 0.74)
      .on("mouseenter", (event, d) => {{
        showTip(event, `${{xKey}}: <b>${{d.x}}</b><br>${{yKey}}: <b>${{d.y}}</b><br>${{zKey}}: <b>${{d.z}}</b>`);
      }})
      .on("mousemove", event => tooltip.style("left", `${{event.clientX + 14}}px`).style("top", `${{event.clientY + 14}}px`))
      .on("mouseleave", hideTip);
    }}

    function drawHistogram() {{
      const values = data.map(d => +d[xKey]).filter(Number.isFinite);
      const x = d3.scaleLinear().domain(d3.extent(values)).nice().range([margin.left, width - margin.right]);
      const bins = d3.bin().domain(x.domain()).thresholds(28)(values);
      const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length) || 1]).nice().range([height - margin.bottom, margin.top]);
      addXAxis(x);
      addYAxis(y);
      axisLabels(xKey, "liczność");
      svg.append("g").selectAll("rect").data(bins).join("rect")
        .attr("x", d => x(d.x0) + 1)
        .attr("y", d => y(d.length))
        .attr("width", d => Math.max(0, x(d.x1) - x(d.x0) - 1))
        .attr("height", d => y(0) - y(d.length))
        .attr("fill", "#2563eb").attr("opacity", 0.82)
        .on("mouseenter", (event, d) => showTip(event, `${{xKey}}: <b>${{d.x0.toFixed(2)}}-${{d.x1.toFixed(2)}}</b><br>liczność: <b>${{d.length}}</b>`))
        .on("mouseleave", hideTip);
    }}

    function drawLine() {{
      const clean = data.map((d, i) => ({{x: Number.isFinite(+d[xKey]) ? +d[xKey] : i, y: +d[yKey], raw: d}})).filter(d => Number.isFinite(d.y)).sort((a,b) => a.x-b.x);
      const x = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([margin.left, width - margin.right]);
      const y = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([height - margin.bottom, margin.top]);
      addXAxis(x); addYAxis(y); axisLabels(xKey, yKey);
      const line = d3.line().x(d => x(d.x)).y(d => y(d.y));
      svg.append("path").datum(clean).attr("fill","none").attr("stroke","#2563eb").attr("stroke-width",2.5).attr("d",line);
      svg.append("g").selectAll("circle").data(clean).join("circle")
        .attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).attr("r", 4).attr("fill", "#f97316")
        .on("mouseenter", (event, d) => showTip(event, `${{xKey}}: <b>${{d.x}}</b><br>${{yKey}}: <b>${{d.y}}</b>`))
        .on("mouseleave", hideTip);
    }}

    function drawGantt() {{
      const startKey = data[0] && ("t_start" in data[0] ? "t_start" : ("sto_start" in data[0] ? "sto_start" : null));
      const endKey = data[0] && ("t_end" in data[0] ? "t_end" : ("sto_end" in data[0] ? "sto_end" : null));
      let current = 0;
      const rows = data.slice(0, 80).map((d, i) => {{
        const duration = Number.isFinite(+d[xKey]) ? Math.max(0.1, +d[xKey]) : 1;
        const start = startKey ? (+d[startKey] || 0) : current;
        const end = endKey ? (+d[endKey] || start + duration) : start + duration;
        current = end;
        return {{label: d.ID || d.id || d.job_id || d.zlecenie || `#${{i+1}}`, start, end, raw: d}};
      }});
      const x = d3.scaleLinear().domain([0, d3.max(rows, d => d.end) || 1]).nice().range([margin.left, width - margin.right]);
      const y = d3.scaleBand().domain(rows.map(d => d.label)).range([margin.top, height - margin.bottom]).padding(0.18);
      addXAxis(x);
      svg.append("g").attr("class","axis").attr("transform",`translate(${{margin.left}},0)`).call(d3.axisLeft(y));
      axisLabels("czas", "zlecenie");
      svg.append("g").selectAll("rect").data(rows).join("rect")
        .attr("x", d => x(d.start)).attr("y", d => y(d.label))
        .attr("width", d => Math.max(2, x(d.end)-x(d.start))).attr("height", y.bandwidth())
        .attr("fill", "#10b981").attr("opacity", 0.82)
        .on("mouseenter", (event, d) => showTip(event, `${{d.label}}<br>start: <b>${{d.start.toFixed(2)}}</b><br>end: <b>${{d.end.toFixed(2)}}</b>`))
        .on("mouseleave", hideTip);
    }}

    function drawMissingness() {{
      const columns = Object.keys(data[0] || {{}}).slice(0, 30);
      const rows = data.slice(0, 220);
      const x = d3.scaleBand().domain(d3.range(rows.length)).range([margin.left, width - margin.right]);
      const y = d3.scaleBand().domain(columns).range([margin.top, height - margin.bottom]).padding(0.02);
      svg.append("g").attr("class","axis").attr("transform",`translate(${{margin.left}},0)`).call(d3.axisLeft(y));
      svg.append("g").selectAll("g").data(rows).join("g")
        .selectAll("rect").data((row, i) => columns.map(col => ({{row:i, col, missing: row[col] == null || row[col] === ""}}))).join("rect")
        .attr("x", d => x(d.row)).attr("y", d => y(d.col)).attr("width", x.bandwidth()).attr("height", y.bandwidth())
        .attr("fill", d => d.missing ? "#ef4444" : "#dbeafe");
      axisLabels("rekord", "kolumna");
    }}

    function drawColumnRanking() {{
      const keys = Object.keys(data[0] || {{}}).filter(key => data.some(d => Number.isFinite(+d[key])));
      const rows = keys.map(key => {{
        const values = data.map(d => +d[key]).filter(Number.isFinite);
        return {{key, value: d3.deviation(values) || 0}};
      }}).sort((a, b) => b.value - a.value).slice(0, 12);
      const left = 170;
      const x = d3.scaleLinear().domain([0, d3.max(rows, d => d.value) || 1]).nice().range([left, width - margin.right]);
      const y = d3.scaleBand().domain(rows.map(d => d.key)).range([margin.top, height - margin.bottom]).padding(0.22);
      addXAxis(x);
      svg.append("g").attr("class","axis").attr("transform",`translate(${{left}},0)`).call(d3.axisLeft(y));
      axisLabels("zmienność / odchylenie standardowe", "kolumna");
      svg.append("g").selectAll("rect").data(rows).join("rect")
        .attr("x", left).attr("y", d => y(d.key))
        .attr("width", d => Math.max(2, x(d.value) - left)).attr("height", y.bandwidth())
        .attr("rx", 6).attr("fill", "#34d399").attr("opacity", 0.9)
        .on("mouseenter", (event, d) => showTip(event, `${{d.key}}<br>zmienność: <b>${{d.value.toFixed(4)}}</b>`))
        .on("mouseleave", hideTip);
    }}

    function drawBoxplot() {{
      const values = data.map(d => +d[yKey]).filter(Number.isFinite).sort(d3.ascending);
      if (!values.length) return drawHistogram();
      const q1 = d3.quantile(values, 0.25), median = d3.quantile(values, 0.5), q3 = d3.quantile(values, 0.75);
      const min = d3.min(values), max = d3.max(values);
      const x = d3.scaleLinear().domain([min, max]).nice().range([margin.left, width - margin.right]);
      const y = height / 2;
      addXAxis(x);
      axisLabels(yKey, "boxplot");
      svg.append("line").attr("x1", x(min)).attr("x2", x(max)).attr("y1", y).attr("y2", y).attr("stroke", "#94a3b8").attr("stroke-width", 3);
      svg.append("rect").attr("x", x(q1)).attr("y", y - 70).attr("width", Math.max(3, x(q3)-x(q1))).attr("height", 140).attr("rx", 8).attr("fill", "#38bdf8").attr("opacity", 0.55);
      [min, median, max].forEach((value, i) => svg.append("line").attr("x1", x(value)).attr("x2", x(value)).attr("y1", y - 88).attr("y2", y + 88).attr("stroke", i === 1 ? "#fbbf24" : "#e2e8f0").attr("stroke-width", i === 1 ? 4 : 2));
      svg.append("text").attr("x", x(median) + 8).attr("y", y - 92).attr("fill", "#fde68a").text(`mediana: ${{median.toFixed(4)}}`);
    }}

    function drawDiagnostics() {{
      const clean = data.map(d => ({{x:+d[xKey], y:+d[yKey]}})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
      if (clean.length < 2) return drawScatter();
      const n = clean.length;
      const sx = d3.sum(clean, d => d.x), sy = d3.sum(clean, d => d.y);
      const sxy = d3.sum(clean, d => d.x * d.y), sx2 = d3.sum(clean, d => d.x * d.x);
      const a = (n * sxy - sx * sy) / ((n * sx2 - sx * sx) || 1);
      const b = (sy - a * sx) / n;
      const panels = [
        {{x: margin.left, y: margin.top, w: (width - margin.left - margin.right - 30) / 2, h: (height - margin.top - margin.bottom - 30) / 2, title: "Dane i trend"}},
        {{x: margin.left + (width - margin.left - margin.right + 30) / 2, y: margin.top, w: (width - margin.left - margin.right - 30) / 2, h: (height - margin.top - margin.bottom - 30) / 2, title: "Reszty"}},
        {{x: margin.left, y: margin.top + (height - margin.top - margin.bottom + 30) / 2, w: width - margin.left - margin.right, h: (height - margin.top - margin.bottom - 30) / 2, title: "Błąd bezwzględny"}}
      ];
      panels.forEach(p => svg.append("text").attr("x", p.x).attr("y", p.y - 8).attr("font-weight", 700).text(p.title));
      const x = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([panels[0].x, panels[0].x + panels[0].w]);
      const y = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([panels[0].y + panels[0].h, panels[0].y]);
      svg.append("g").attr("class","axis").attr("transform",`translate(0,${{panels[0].y + panels[0].h}})`).call(d3.axisBottom(x).ticks(5));
      svg.append("g").attr("class","axis").attr("transform",`translate(${{panels[0].x}},0)`).call(d3.axisLeft(y).ticks(5));
      svg.selectAll("circle.diag").data(clean).join("circle").attr("class","diag").attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).attr("r", 5).attr("fill", "#38bdf8").attr("opacity", .85);
      const domain = x.domain();
      svg.append("path").datum(domain.map(v => ({{x:v, y:a*v+b}}))).attr("fill","none").attr("stroke","#fbbf24").attr("stroke-width",2.5).attr("d", d3.line().x(d => x(d.x)).y(d => y(d.y)));
      const residuals = clean.map(d => ({{x:d.x, r:d.y - (a*d.x+b), abs:Math.abs(d.y - (a*d.x+b))}}));
      const rx = d3.scaleLinear().domain(d3.extent(residuals, d => d.x)).nice().range([panels[1].x, panels[1].x + panels[1].w]);
      const ry = d3.scaleLinear().domain(d3.extent(residuals, d => d.r)).nice().range([panels[1].y + panels[1].h, panels[1].y]);
      svg.append("g").attr("class","axis").attr("transform",`translate(0,${{panels[1].y + panels[1].h}})`).call(d3.axisBottom(rx).ticks(5));
      svg.append("g").attr("class","axis").attr("transform",`translate(${{panels[1].x}},0)`).call(d3.axisLeft(ry).ticks(5));
      svg.selectAll("circle.res").data(residuals).join("circle").attr("class","res").attr("cx", d => rx(d.x)).attr("cy", d => ry(d.r)).attr("r", 5).attr("fill", "#fb7185").attr("opacity", .85);
      const bx = d3.scaleBand().domain(residuals.map((_, i) => i)).range([panels[2].x, panels[2].x + panels[2].w]).padding(.2);
      const by = d3.scaleLinear().domain([0, d3.max(residuals, d => d.abs) || 1]).nice().range([panels[2].y + panels[2].h, panels[2].y]);
      svg.append("g").attr("class","axis").attr("transform",`translate(0,${{panels[2].y + panels[2].h}})`).call(d3.axisBottom(bx).tickValues([]));
      svg.append("g").attr("class","axis").attr("transform",`translate(${{panels[2].x}},0)`).call(d3.axisLeft(by).ticks(4));
      svg.selectAll("rect.err").data(residuals).join("rect").attr("class","err").attr("x", (_, i) => bx(i)).attr("y", d => by(d.abs)).attr("width", bx.bandwidth()).attr("height", d => panels[2].y + panels[2].h - by(d.abs)).attr("fill", "#a78bfa").attr("opacity", .85);
    }}

    function numericKeys(limit = 10) {{
      return Object.keys(data[0] || {{}})
        .filter(key => data.some(d => Number.isFinite(+d[key])))
        .slice(0, limit);
    }}

    function pearson(a, b) {{
      const pairs = data.map(d => [Number(d[a]), Number(d[b])])
        .filter(p => Number.isFinite(p[0]) && Number.isFinite(p[1]));
      if (pairs.length < 2) return a === b ? 1 : 0;
      const mx = d3.mean(pairs, p => p[0]);
      const my = d3.mean(pairs, p => p[1]);
      const num = d3.sum(pairs, p => (p[0] - mx) * (p[1] - my));
      const den = Math.sqrt(
        d3.sum(pairs, p => (p[0] - mx) ** 2) * d3.sum(pairs, p => (p[1] - my) ** 2)
      );
      return den ? num / den : 0;
    }}

    function drawMatrix(mode = "correlation") {{
      const keys = numericKeys(10);
      if (keys.length < 2) {{
        svg.append("text").attr("x", margin.left).attr("y", margin.top + 40).attr("font-size", 18)
          .text("Macierz wymaga co najmniej dwóch kolumn liczbowych.");
        return;
      }}
      const topPad = 96;
      const leftPad = Math.min(230, Math.max(130, d3.max(keys, d => d.length) * 8 + 42));
      const matrixW = width - margin.right - leftPad - 34;
      const matrixH = height - margin.bottom - topPad - 22;
      const size = Math.max(34, Math.min(matrixW / keys.length, matrixH / keys.length));
      const color = d3.scaleSequential().domain([-1, 1]).interpolator(d3.interpolateRdBu);
      const g = svg.append("g").attr("transform", `translate(${{leftPad}},${{topPad}})`);
      const valueFor = (row, col) => {{
        if (mode === "similarity") {{
          const c = Math.abs(pearson(row, col));
          return row === col ? 1 : c;
        }}
        return pearson(row, col);
      }};
      svg.append("text")
        .attr("x", leftPad)
        .attr("y", 38)
        .attr("font-size", 22)
        .attr("font-weight", 800)
        .text(mode === "similarity" ? "Macierz podobieństwa kolumn" : "Macierz korelacji Pearsona");
      svg.append("text")
        .attr("x", leftPad)
        .attr("y", 62)
        .attr("fill", "#9fb4cc")
        .text(mode === "similarity" ? "1 oznacza bardzo podobny przebieg, 0 brak podobieństwa liniowego." : "-1 silna odwrotna zależność, 0 brak liniowej zależności, 1 silna zgodna zależność.");
      const cells = [];
      keys.forEach((row, i) => keys.forEach((col, j) => cells.push({{row, col, i, j, value:valueFor(row, col)}})));
      g.selectAll("rect").data(cells).join("rect")
        .attr("x", d => d.j * size)
        .attr("y", d => d.i * size)
        .attr("width", size - 2)
        .attr("height", size - 2)
        .attr("rx", 6)
        .attr("fill", d => mode === "similarity" ? d3.interpolateYlGnBu(d.value) : color(-d.value))
        .on("mouseenter", (event, d) => showTip(event, `${{d.row}} ↔ ${{d.col}}<br>wartość: <b>${{d.value.toFixed(3)}}</b>`))
        .on("mouseleave", hideTip);
      g.selectAll("text.value").data(cells).join("text")
        .attr("class", "value")
        .attr("x", d => d.j * size + size / 2)
        .attr("y", d => d.i * size + size / 2 + 5)
        .attr("text-anchor", "middle")
        .attr("font-size", Math.max(10, Math.min(15, size * 0.22)))
        .attr("fill", d => Math.abs(d.value) > 0.58 ? "#ffffff" : "#0f172a")
        .attr("font-weight", 700)
        .text(d => d.value.toFixed(2));
      keys.forEach((key, i) => {{
        g.append("text").attr("x", -10).attr("y", i * size + size / 2 + 5)
          .attr("text-anchor", "end").attr("font-size", 12).attr("fill", "#dbeafe").text(key);
        g.append("text").attr("x", i * size + size / 2).attr("y", -12)
          .attr("text-anchor", "start").attr("font-size", 12).attr("fill", "#dbeafe")
          .attr("transform", `rotate(-42 ${{i * size + size / 2}} -12)`).text(key);
      }});
      const legendX = leftPad + keys.length * size + 24;
      const legendH = Math.min(260, keys.length * size);
      const defs = svg.append("defs");
      const grad = defs.append("linearGradient").attr("id", "matrixLegend").attr("x1", "0%").attr("y1", "100%").attr("x2", "0%").attr("y2", "0%");
      d3.range(0, 1.01, 0.1).forEach(t => grad.append("stop").attr("offset", `${{t * 100}}%`).attr("stop-color", mode === "similarity" ? d3.interpolateYlGnBu(t) : color(1 - 2 * t)));
      svg.append("rect").attr("x", legendX).attr("y", topPad).attr("width", 18).attr("height", legendH).attr("fill", "url(#matrixLegend)");
      const legend = d3.scaleLinear().domain(mode === "similarity" ? [0, 1] : [-1, 1]).range([topPad + legendH, topPad]);
      svg.append("g").attr("class", "axis").attr("transform", `translate(${{legendX + 18}},0)`).call(d3.axisRight(legend).ticks(5));
    }}

    function drawCorrelationMatrix() {{
      drawMatrix("correlation");
    }}

    function drawSimilarityMatrix() {{
      drawMatrix("similarity");
    }}

    function drawBubbleChart() {{
      const clean = data.map(d => ({{x:+d[xKey], y:+d[yKey], z:+d[zKey], raw:d}}))
        .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
      const x = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([margin.left, width - margin.right]);
      const y = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([height - margin.bottom, margin.top]);
      const zExtent = d3.extent(clean, d => Number.isFinite(d.z) ? d.z : 1);
      const size = d3.scaleSqrt().domain(zExtent).range([8, 32]);
      const color = d3.scaleSequential().domain(zExtent).interpolator(d3.interpolateViridis);
      addXAxis(x); addYAxis(y); axisLabels(xKey, yKey);
      svg.append("text").attr("x", margin.left).attr("y", 28).attr("font-size", 20).attr("font-weight", 800).text(`Bubble Chart: rozmiar i kolor = ${{zKey}}`);
      svg.append("g").selectAll("circle").data(clean).join("circle")
        .attr("cx", d => x(d.x)).attr("cy", d => y(d.y))
        .attr("r", d => Number.isFinite(d.z) ? size(d.z) : 10)
        .attr("fill", d => Number.isFinite(d.z) ? color(d.z) : "#38bdf8")
        .attr("opacity", .72).attr("stroke", "#dbeafe").attr("stroke-width", .7)
        .on("mouseenter", (event, d) => showTip(event, `${{xKey}}: <b>${{d.x}}</b><br>${{yKey}}: <b>${{d.y}}</b><br>${{zKey}}: <b>${{d.z}}</b>`))
        .on("mouseleave", hideTip);
    }}

    function drawOutlierMap() {{
      const clean = data.map(d => ({{x:+d[xKey], y:+d[yKey], raw:d}})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
      const mx = d3.mean(clean, d => d.x), my = d3.mean(clean, d => d.y);
      const sx = d3.deviation(clean, d => d.x) || 1, sy = d3.deviation(clean, d => d.y) || 1;
      clean.forEach(d => d.score = Math.abs((d.x - mx) / sx) + Math.abs((d.y - my) / sy));
      const x = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([margin.left, width - margin.right]);
      const y = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([height - margin.bottom, margin.top]);
      const color = d3.scaleSequential().domain(d3.extent(clean, d => d.score)).interpolator(d3.interpolateInferno);
      addXAxis(x); addYAxis(y); axisLabels(xKey, yKey);
      svg.append("text").attr("x", margin.left).attr("y", 28).attr("font-size", 20).attr("font-weight", 800).text("Outlier Map: jaśniejsze punkty są bardziej odstające");
      svg.append("g").selectAll("circle").data(clean).join("circle")
        .attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).attr("r", d => 6 + d.score * 2.2)
        .attr("fill", d => color(d.score)).attr("opacity", .82)
        .on("mouseenter", (event, d) => showTip(event, `${{xKey}}: <b>${{d.x}}</b><br>${{yKey}}: <b>${{d.y}}</b><br>wynik odstawania: <b>${{d.score.toFixed(2)}}</b>`))
        .on("mouseleave", hideTip);
    }}

    function drawHeatmapDensity() {{
      const clean = data.map(d => ({{x:+d[xKey], y:+d[yKey]}})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
      const x = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([margin.left, width - margin.right]);
      const y = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([height - margin.bottom, margin.top]);
      addXAxis(x); addYAxis(y); axisLabels(xKey, yKey);
      const density = d3.contourDensity()
        .x(d => x(d.x)).y(d => y(d.y)).size([width, height]).bandwidth(34)(clean);
      const color = d3.scaleSequential().domain([0, d3.max(density, d => d.value) || 1]).interpolator(d3.interpolateMagma);
      svg.append("g").selectAll("path").data(density).join("path")
        .attr("d", d3.geoPath()).attr("fill", d => color(d.value)).attr("opacity", .62);
      svg.append("g").selectAll("circle").data(clean).join("circle")
        .attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).attr("r", 3.5).attr("fill", "#dbeafe").attr("opacity", .62);
      svg.append("text").attr("x", margin.left).attr("y", 28).attr("font-size", 20).attr("font-weight", 800).text("Heatmap Density: obszary skupienia rekordów");
    }}

    function drawPairExplorer() {{
      const keys = numericKeys(4);
      if (keys.length < 2) return drawScatter();
      const gridTop = 54;
      const gridLeft = 92;
      const gap = 24;
      const cell = Math.min((width - gridLeft - margin.right - gap * (keys.length - 1)) / keys.length, (height - gridTop - margin.bottom - gap * (keys.length - 1)) / keys.length);
      svg.append("text").attr("x", gridLeft).attr("y", 28).attr("font-size", 20).attr("font-weight", 800).text("Pair Explorer: relacje każdej kolumny z każdą");
      keys.forEach((rowKey, i) => keys.forEach((colKey, j) => {{
        const gx = gridLeft + j * (cell + gap);
        const gy = gridTop + i * (cell + gap);
        const g = svg.append("g").attr("transform", `translate(${{gx}},${{gy}})`);
        g.append("rect").attr("width", cell).attr("height", cell).attr("rx", 10).attr("fill", "#0f172a").attr("stroke", "#20364d");
        if (i === j) {{
          const values = data.map(d => +d[colKey]).filter(Number.isFinite);
          const x = d3.scaleLinear().domain(d3.extent(values)).nice().range([12, cell - 12]);
          const bins = d3.bin().domain(x.domain()).thresholds(10)(values);
          const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length) || 1]).range([cell - 28, 24]);
          g.selectAll("rect.hist").data(bins).join("rect").attr("class","hist")
            .attr("x", d => x(d.x0)).attr("y", d => y(d.length))
            .attr("width", d => Math.max(1, x(d.x1) - x(d.x0) - 1)).attr("height", d => cell - 28 - y(d.length))
            .attr("fill", "#38bdf8").attr("opacity", .78);
          g.append("text").attr("x", cell / 2).attr("y", 18).attr("text-anchor", "middle").attr("font-weight", 700).text(colKey);
        }} else {{
          const pairs = data.map(d => ({{x:+d[colKey], y:+d[rowKey]}})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
          const x = d3.scaleLinear().domain(d3.extent(pairs, d => d.x)).nice().range([18, cell - 12]);
          const y = d3.scaleLinear().domain(d3.extent(pairs, d => d.y)).nice().range([cell - 18, 12]);
          g.selectAll("circle").data(pairs).join("circle")
            .attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).attr("r", 3.8).attr("fill", "#34d399").attr("opacity", .72)
            .on("mouseenter", (event, d) => showTip(event, `${{colKey}}: <b>${{d.x}}</b><br>${{rowKey}}: <b>${{d.y}}</b>`))
            .on("mouseleave", hideTip);
        }}
        if (j === 0) g.append("text").attr("x", -8).attr("y", cell / 2).attr("text-anchor", "end").attr("fill", "#9fb4cc").text(rowKey);
        if (i === keys.length - 1) g.append("text").attr("x", cell / 2).attr("y", cell + 16).attr("text-anchor", "middle").attr("fill", "#9fb4cc").text(colKey);
      }}));
    }}

    function drawPseudo3DScatter() {{
      const clean = data.map(d => ({{x:+d[xKey], y:+d[yKey], z:+d[zKey]}})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y) && Number.isFinite(d.z));
      const sx = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([-260, 260]);
      const sy = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([180, -180]);
      const sz = d3.scaleLinear().domain(d3.extent(clean, d => d.z)).nice().range([0, 180]);
      const color = d3.scaleSequential().domain(d3.extent(clean, d => d.z)).interpolator(d3.interpolateTurbo);
      const project = d => ({{px: width / 2 + sx(d.x) + sy(d.y) * .42, py: height / 2 + sy(d.y) * .22 - sz(d.z), ...d}});
      const points = clean.map(project).sort((a, b) => a.py - b.py);
      svg.append("text").attr("x", margin.left).attr("y", 28).attr("font-size", 20).attr("font-weight", 800).text("3D Scatter: rzut izometryczny X/Y/Z");
      svg.append("g").attr("opacity", .32).selectAll("line").data([[-300,0,300,0],[0,-220,0,220],[-220,120,220,-120]]).join("line")
        .attr("x1", d => width/2 + d[0]).attr("y1", d => height/2 + d[1]).attr("x2", d => width/2 + d[2]).attr("y2", d => height/2 + d[3]).attr("stroke","#94a3b8");
      svg.selectAll("circle.iso").data(points).join("circle").attr("class","iso")
        .attr("cx", d => d.px).attr("cy", d => d.py).attr("r", 7).attr("fill", d => color(d.z)).attr("opacity", .82)
        .on("mouseenter", (event, d) => showTip(event, `${{xKey}}: <b>${{d.x}}</b><br>${{yKey}}: <b>${{d.y}}</b><br>${{zKey}}: <b>${{d.z}}</b>`))
        .on("mouseleave", hideTip);
    }}

    function drawPseudo3DSurface() {{
      const clean = data.map(d => ({{x:+d[xKey], y:+d[yKey], z:+d[zKey]}})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y) && Number.isFinite(d.z));
      const sx = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([-300, 300]);
      const sy = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([190, -190]);
      const sz = d3.scaleLinear().domain(d3.extent(clean, d => d.z)).nice().range([0, 190]);
      const color = d3.scaleSequential().domain(d3.extent(clean, d => d.z)).interpolator(d3.interpolateViridis);
      const project = d => [width / 2 + sx(d.x) + sy(d.y) * .42, height / 2 + sy(d.y) * .22 - sz(d.z)];
      svg.append("text").attr("x", margin.left).attr("y", 28).attr("font-size", 20).attr("font-weight", 800).text("3D Surface: siatka wysokości Z");
      const triangles = d3.Delaunay.from(clean, d => sx(d.x), d => sy(d.y)).triangles;
      for (let i = 0; i < triangles.length; i += 3) {{
        const tri = [clean[triangles[i]], clean[triangles[i+1]], clean[triangles[i+2]]];
        const avg = d3.mean(tri, d => d.z);
        svg.append("path").attr("d", "M" + tri.map(d => project(d).join(",")).join("L") + "Z")
          .attr("fill", color(avg)).attr("stroke", "#0b1220").attr("stroke-width", .7).attr("opacity", .82);
      }}
    }}

    function drawDecisionTree() {{
      const values = data.map(d => +d[xKey]).filter(Number.isFinite).sort(d3.ascending);
      const pivot = d3.quantile(values, .5) || 0;
      const yValues = data.map(d => +d[yKey]).filter(Number.isFinite);
      const high = d3.quantile(yValues.sort(d3.ascending), .75) || 0;
      const treeData = {{
        name: `${{xKey}} ≤ ${{pivot.toFixed(2)}}?`,
        children: [
          {{name: `TAK`, children:[{{name:`niższe ${{yKey}}`}}, {{name:`próg ${{high.toFixed(2)}}`}}]}},
          {{name: `NIE`, children:[{{name:`wyższe ${{yKey}}`}}, {{name:`sprawdź ${{zKey}}`}}]}}
        ]
      }};
      const root = d3.hierarchy(treeData);
      d3.tree().size([width - margin.left - margin.right, height - margin.top - margin.bottom])(root);
      const g = svg.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
      svg.append("text").attr("x", margin.left).attr("y", 28).attr("font-size", 20).attr("font-weight", 800).text("Decision Tree: uproszczony podgląd reguł");
      g.selectAll("path.link").data(root.links()).join("path").attr("class","link")
        .attr("d", d3.linkVertical().x(d => d.x).y(d => d.y)).attr("fill","none").attr("stroke","#5b7591").attr("stroke-width",2);
      const node = g.selectAll("g.node").data(root.descendants()).join("g").attr("class","node").attr("transform", d => `translate(${{d.x}},${{d.y}})`);
      node.append("rect").attr("x",-82).attr("y",-18).attr("width",164).attr("height",36).attr("rx",10).attr("fill", d => d.children ? "#1d4ed8" : "#10b981").attr("stroke","#bfdbfe");
      node.append("text").attr("text-anchor","middle").attr("dy",5).attr("font-weight",700).text(d => d.data.name);
    }}

    function drawProductionDashboard() {{
      const numericKeys = Object.keys(data[0] || {{}})
        .filter(key => data.some(d => Number.isFinite(+d[key])));
      const clean = data.map(d => ({{
        x: +d[xKey],
        y: +d[yKey],
        z: +d[zKey],
        raw: d
      }})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
      const gap = 30;
      const panelW = (width - margin.left - margin.right - gap) / 2;
      const panelH = (height - margin.top - margin.bottom - gap) / 2;
      const panels = [
        {{x: margin.left, y: margin.top}},
        {{x: margin.left + panelW + gap, y: margin.top}},
        {{x: margin.left, y: margin.top + panelH + gap}},
        {{x: margin.left + panelW + gap, y: margin.top + panelH + gap}}
      ];
      const panel = (slot, title) => {{
        const g = svg.append("g").attr("transform", `translate(${{slot.x}},${{slot.y}})`);
        g.append("rect")
          .attr("width", panelW).attr("height", panelH)
          .attr("rx", 12).attr("fill", "#ffffff").attr("stroke", "#cbd5e1");
        g.append("text")
          .attr("x", 14).attr("y", 24).attr("fill", "#0f172a")
          .attr("font-weight", 700).text(title);
        return g;
      }};
      const localAxis = (g, xScale, yScale, innerW, innerH, xLabel, yLabel) => {{
        g.append("g")
          .attr("class", "axis")
          .attr("transform", `translate(0,${{innerH}})`)
          .call(d3.axisBottom(xScale).ticks(5));
        g.append("g").attr("class", "axis").call(d3.axisLeft(yScale).ticks(5));
        g.append("text")
          .attr("x", innerW / 2).attr("y", innerH + 36)
          .attr("text-anchor", "middle").attr("fill", "#334155").text(xLabel);
        g.append("text")
          .attr("x", -innerH / 2).attr("y", -42)
          .attr("text-anchor", "middle").attr("transform", "rotate(-90)")
          .attr("fill", "#334155").text(yLabel);
      }};

      const scatter = panel(panels[0], "Relacja X/Y");
      const sx = scatter.append("g").attr("transform", "translate(58,42)");
      const innerW = panelW - 82;
      const innerH = panelH - 92;
      if (clean.length) {{
        const x = d3.scaleLinear().domain(d3.extent(clean, d => d.x)).nice().range([0, innerW]);
        const y = d3.scaleLinear().domain(d3.extent(clean, d => d.y)).nice().range([innerH, 0]);
        const zValues = clean.map(d => Number.isFinite(d.z) ? d.z : 0);
        const zExtent = d3.extent(zValues);
        const color = d3.scaleSequential(zExtent, d3.interpolateTurbo);
        const size = d3.scaleSqrt().domain(zExtent).range([4, 12]);
        localAxis(sx, x, y, innerW, innerH, xKey, yKey);
        sx.selectAll("circle").data(clean).join("circle")
          .attr("cx", d => x(d.x)).attr("cy", d => y(d.y))
          .attr("r", d => Number.isFinite(d.z) ? size(d.z) : 6)
          .attr("fill", d => Number.isFinite(d.z) ? color(d.z) : "#2563eb")
          .attr("opacity", 0.78)
          .on("mouseenter", (event, d) => showTip(event, `${{xKey}}: <b>${{d.x}}</b><br>${{yKey}}: <b>${{d.y}}</b><br>${{zKey}}: <b>${{d.z}}</b>`))
          .on("mouseleave", hideTip);
      }}

      const hist = panel(panels[1], `Rozkład: ${{xKey}}`);
      const hx = hist.append("g").attr("transform", "translate(58,42)");
      const values = data.map(d => +d[xKey]).filter(Number.isFinite);
      if (values.length) {{
        const x = d3.scaleLinear().domain(d3.extent(values)).nice().range([0, innerW]);
        const bins = d3.bin().domain(x.domain()).thresholds(16)(values);
        const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length) || 1]).nice().range([innerH, 0]);
        localAxis(hx, x, y, innerW, innerH, xKey, "liczba");
        hx.selectAll("rect").data(bins).join("rect")
          .attr("x", d => x(d.x0) + 1)
          .attr("y", d => y(d.length))
          .attr("width", d => Math.max(1, x(d.x1) - x(d.x0) - 2))
          .attr("height", d => innerH - y(d.length))
          .attr("fill", "#2563eb").attr("opacity", 0.82)
          .on("mouseenter", (event, d) => showTip(event, `${{xKey}}: <b>${{d.x0.toFixed(2)}}-${{d.x1.toFixed(2)}}</b><br>liczba: <b>${{d.length}}</b>`))
          .on("mouseleave", hideTip);
      }}

      const category = panel(panels[2], "Kategorie / zmienność");
      const cg = category.append("g").attr("transform", "translate(96,42)");
      const catKey = data[0] && ("material" in data[0] ? "material" : ("ksztalt" in data[0] ? "ksztalt" : null));
      const bars = catKey
        ? d3.rollups(data, v => v.length, d => d[catKey] ?? "brak").slice(0, 8).map(([label, value]) => ({{label, value}}))
        : numericKeys.slice(0, 8).map(key => ({{label: key, value: d3.deviation(data.map(d => +d[key]).filter(Number.isFinite)) || 0}}));
      if (bars.length) {{
        const x = d3.scaleLinear().domain([0, d3.max(bars, d => d.value) || 1]).nice().range([0, innerW - 28]);
        const y = d3.scaleBand().domain(bars.map(d => d.label)).range([0, innerH]).padding(0.22);
        cg.append("g").attr("class", "axis").call(d3.axisLeft(y));
        cg.append("g").attr("class", "axis").attr("transform", `translate(0,${{innerH}})`).call(d3.axisBottom(x).ticks(4));
        cg.selectAll("rect").data(bars).join("rect")
          .attr("x", 0).attr("y", d => y(d.label))
          .attr("width", d => x(d.value)).attr("height", y.bandwidth())
          .attr("fill", "#10b981").attr("opacity", 0.84)
          .on("mouseenter", (event, d) => showTip(event, `${{d.label}}: <b>${{d.value.toFixed ? d.value.toFixed(2) : d.value}}</b>`))
          .on("mouseleave", hideTip);
      }}

      const quality = panel(panels[3], "Braki danych");
      const qg = quality.append("g").attr("transform", "translate(104,42)");
      const missing = Object.keys(data[0] || {{}}).slice(0, 8).map(col => ({{
        label: col,
        value: data.filter(d => d[col] == null || d[col] === "").length
      }}));
      if (missing.length) {{
        const x = d3.scaleLinear().domain([0, d3.max(missing, d => d.value) || 1]).nice().range([0, innerW - 36]);
        const y = d3.scaleBand().domain(missing.map(d => d.label)).range([0, innerH]).padding(0.22);
        qg.append("g").attr("class", "axis").call(d3.axisLeft(y));
        qg.append("g").attr("class", "axis").attr("transform", `translate(0,${{innerH}})`).call(d3.axisBottom(x).ticks(4));
        qg.selectAll("rect").data(missing).join("rect")
          .attr("x", 0).attr("y", d => y(d.label))
          .attr("width", d => Math.max(2, x(d.value))).attr("height", y.bandwidth())
          .attr("fill", d => d.value ? "#ef4444" : "#93c5fd")
          .attr("opacity", 0.86)
          .on("mouseenter", (event, d) => showTip(event, `${{d.label}}<br>braki: <b>${{d.value}}</b>`))
          .on("mouseleave", hideTip);
      }}
    }}

    if (chartType === "Production Dashboard" || chartType === "Dashboard") drawProductionDashboard();
    else if (chartType === "Diagnostics") drawDiagnostics();
    else if (chartType === "CorrelationMatrix") drawCorrelationMatrix();
    else if (chartType === "SimilarityMatrix") drawSimilarityMatrix();
    else if (chartType === "Column Ranking") drawColumnRanking();
    else if (chartType === "Histogram") drawHistogram();
    else if (chartType === "Boxplot") drawBoxplot();
    else if (chartType === "Line" || chartType === "Priority Timeline" || chartType === "Step View") drawLine();
    else if (chartType === "Gantt") drawGantt();
    else if (chartType === "Missingness Map") drawMissingness();
    else if (chartType === "Bubble Chart") drawBubbleChart();
    else if (chartType === "Heatmap Density") drawHeatmapDensity();
    else if (chartType === "Outlier Map") drawOutlierMap();
    else if (chartType === "Pair Explorer") drawPairExplorer();
    else if (chartType === "3D Scatter") drawPseudo3DScatter();
    else if (chartType === "3D Surface") drawPseudo3DSurface();
    else if (chartType === "DecisionTree") drawDecisionTree();
    else drawScatter();
    }}
  </script>
</body>
</html>"""


def save_d3_html_report(df: pd.DataFrame, path: str | Path, **kwargs) -> Path:
    output_path = Path(path)
    output_path.write_text(build_d3_html_report(df, **kwargs), encoding="utf-8")
    return output_path


def build_d3_dashboard_html_report(
    df: pd.DataFrame,
    x_col: str | None = None,
    y_col: str | None = None,
    z_col: str | None = None,
    max_rows: int = 900,
) -> str:
    if df is None or df.empty:
        raise ValueError("Brak danych do dashboardu D3")

    x_default, y_default, z_default = _default_columns(df)
    x_name = x_col if x_col in df.columns else x_default
    y_name = y_col if y_col in df.columns else y_default
    z_name = z_col if z_col in df.columns else z_default
    export_df = df.head(max_rows).replace([np.inf, -np.inf], np.nan)
    payload = export_df.where(pd.notna(export_df), None).to_dict(orient="records")
    data_json = json.dumps(payload, ensure_ascii=False)
    columns_json = json.dumps(list(export_df.columns), ensure_ascii=False)
    x_js = json.dumps(x_name, ensure_ascii=False)
    y_js = json.dumps(y_name, ensure_ascii=False)
    z_js = json.dumps(z_name, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AOA D3 Dashboard</title>
  <script src="{D3_CDN_URL}"></script>
  <script>
    if (!window.d3) {{
      document.write('<script src="https://unpkg.com/d3@7/dist/d3.min.js"><\\/script>');
    }}
  </script>
  <style>
    :root {{
      color-scheme: dark;
      --bg:#07111c; --panel:#0e1b29; --border:#20364d; --text:#e6f0ff;
      --muted:#9fb4cc; --grid:rgba(148,163,184,.18); --blue:#38bdf8;
      --green:#34d399; --yellow:#fbbf24; --red:#fb7185; --violet:#a78bfa;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0; font-family:Inter,Segoe UI,Arial,sans-serif;
      background:radial-gradient(circle at 15% 0%, rgba(56,189,248,.15), transparent 34%), var(--bg);
      color:var(--text);
    }}
    header {{
      padding:24px 32px 18px;
      background:linear-gradient(135deg,#0c1d2d,#0a1624);
      border-bottom:1px solid var(--border);
    }}
    h1 {{ margin:0 0 8px; font-size:28px; letter-spacing:0; }}
    .subhead {{ color:var(--muted); font-size:14px; }}
    main {{ padding:22px 32px 30px; max-width:1680px; margin:0 auto; }}
    .cards {{ display:grid; grid-template-columns:repeat(4,minmax(170px,1fr)); gap:14px; margin-bottom:18px; }}
    .card {{
      min-height:96px; padding:16px 18px;
      background:linear-gradient(180deg,rgba(16,34,53,.98),rgba(10,22,36,.98));
      border:1px solid var(--border); border-left:4px solid var(--blue); border-radius:10px;
      box-shadow:0 18px 45px rgba(0,0,0,.22);
    }}
    .card:nth-child(2) {{ border-left-color:var(--green); }}
    .card:nth-child(3) {{ border-left-color:var(--violet); }}
    .card:nth-child(4) {{ border-left-color:var(--yellow); }}
    .card span {{ display:block; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; margin-bottom:12px; }}
    .card strong {{ font-size:28px; line-height:1; }}
    .grid {{ display:grid; grid-template-columns:minmax(560px,1.15fr) minmax(440px,.85fr); gap:18px; align-items:start; }}
    .panel {{
      min-height:420px; padding:18px; background:rgba(14,27,41,.96);
      border:1px solid var(--border); border-radius:10px; box-shadow:0 18px 45px rgba(0,0,0,.24);
    }}
    .panel.wide {{ min-height:500px; }}
    .panel h2 {{ margin:0 0 4px; font-size:18px; }}
    .panel p {{ margin:0 0 14px; color:var(--muted); font-size:13px; }}
    svg {{ width:100%; height:340px; display:block; overflow:visible; }}
    .wide svg {{ height:420px; }}
    .axis text {{ fill:#b8c7d9; font-size:11px; }}
    .axis path,.axis line {{ stroke:#46617c; }}
    .grid-line line {{ stroke:var(--grid); }}
    .label {{ fill:#dbeafe; font-size:12px; }}
    .fallback {{
      min-height:320px; border:1px dashed #45617c; border-radius:10px; display:flex;
      align-items:center; justify-content:center; color:var(--muted); text-align:center;
      padding:24px; background:#0a1624;
    }}
    .tooltip {{
      position:fixed; z-index:10; pointer-events:none; opacity:0; max-width:260px;
      padding:10px 12px; border-radius:8px; background:#020617; border:1px solid #38bdf8;
      box-shadow:0 16px 40px rgba(0,0,0,.35); color:#f8fafc; font-size:12px; line-height:1.45;
    }}
    @media (max-width: 1100px) {{ .grid,.cards {{ grid-template-columns:1fr; }} main {{ padding:18px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>AOA D3 Dashboard</h1>
    <div class="subhead">X: {html.escape(str(x_name))} | Y: {html.escape(str(y_name))} | kolor/rozmiar: {html.escape(str(z_name))}</div>
  </header>
  <main>
    <section class="cards">
      <div class="card"><span>Rekordy</span><strong id="rows"></strong></div>
      <div class="card"><span>Kolumny</span><strong id="cols"></strong></div>
      <div class="card"><span>Liczbowe</span><strong id="numeric"></strong></div>
      <div class="card"><span>Braki danych</span><strong id="missing"></strong></div>
    </section>
    <section class="grid">
      <div class="panel wide"><h2>Relacja X/Y</h2><p>Rozrzut danych, trend liniowy i kolor według trzeciej zmiennej.</p><svg id="scatter"></svg></div>
      <div class="panel"><h2>Rozkład X</h2><p>Histogram z linią średniej i rozkładem wartości.</p><svg id="histogram"></svg></div>
      <div class="panel"><h2>Kategorie lub zmienność</h2><p>Najważniejsze kategorie albo najbardziej zmienne kolumny.</p><svg id="bars"></svg></div>
      <div class="panel"><h2>Jakość danych</h2><p>Braki danych w kolumnach, pokazane jako udział procentowy.</p><svg id="missingness"></svg></div>
    </section>
  </main>
  <div class="tooltip" id="tooltip"></div>
  <script>
    const data = {data_json};
    const columns = {columns_json};
    const xKey = {x_js};
    const yKey = {y_js};
    const zKey = {z_js};
    const numericColumns = columns.filter(col => data.some(row => Number.isFinite(+row[col])));
    const missingTotal = data.reduce((sum, row) => sum + columns.filter(col => row[col] == null || row[col] === "").length, 0);
    document.getElementById("rows").textContent = data.length;
    document.getElementById("cols").textContent = columns.length;
    document.getElementById("numeric").textContent = numericColumns.length;
    document.getElementById("missing").textContent = missingTotal;

    function fallback(id, text) {{
      document.getElementById(id).outerHTML = `<div class="fallback">${{text}}</div>`;
    }}

    if (!window.d3) {{
      ["scatter", "histogram", "bars", "missingness"].forEach(id => fallback(id, "D3.js nie załadował się z CDN. Dane i metryki są w nagłówku dashboardu."));
    }} else {{
      const tooltip = d3.select("#tooltip");
      const fmt = value => Number.isFinite(+value) ? d3.format(".4~g")(+value) : String(value ?? "");
      const showTip = (event, lines) => tooltip
        .style("opacity", 1)
        .style("left", `${{event.clientX + 14}}px`)
        .style("top", `${{event.clientY + 14}}px`)
        .html(lines.join("<br>"));
      const moveTip = event => tooltip
        .style("left", `${{event.clientX + 14}}px`)
        .style("top", `${{event.clientY + 14}}px`);
      const hideTip = () => tooltip.style("opacity", 0);
      const margin = {{top: 22, right: 28, bottom: 54, left: 64}};
      function setup(id) {{
        const svg = d3.select(`#${{id}}`);
        const box = svg.node().getBoundingClientRect();
        const width = Math.max(460, box.width || 560);
        const height = id === "scatter" ? 420 : 340;
        svg.attr("viewBox", [0, 0, width, height]);
        return {{svg, width, height, innerW: width - margin.left - margin.right, innerH: height - margin.top - margin.bottom}};
      }}
      function axes(g, x, y, innerH) {{
        g.append("g").attr("class", "grid-line")
          .call(d3.axisLeft(y).ticks(5).tickSize(-x.range()[1]).tickFormat(""));
        g.append("g").attr("class", "axis").attr("transform", `translate(0,${{innerH}})`).call(d3.axisBottom(x).ticks(5));
        g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5));
      }}
      function axisLabels(g, innerW, innerH, xLabel, yLabel) {{
        g.append("text").attr("class", "label").attr("x", innerW / 2).attr("y", innerH + 42)
          .attr("text-anchor", "middle").text(xLabel);
        g.append("text").attr("class", "label").attr("x", -innerH / 2).attr("y", -46)
          .attr("text-anchor", "middle").attr("transform", "rotate(-90)").text(yLabel);
      }}
      function extentWithPadding(values) {{
        const extent = d3.extent(values);
        if (!Number.isFinite(extent[0]) || !Number.isFinite(extent[1])) return [0, 1];
        if (extent[0] === extent[1]) return [extent[0] - 1, extent[1] + 1];
        const pad = (extent[1] - extent[0]) * 0.06;
        return [extent[0] - pad, extent[1] + pad];
      }}

      const scatterClean = data.map(row => ({{x:+row[xKey], y:+row[yKey], z:+row[zKey]}})).filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
      if (scatterClean.length) {{
        const c = setup("scatter");
        const g = c.svg.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
        const x = d3.scaleLinear().domain(extentWithPadding(scatterClean.map(d => d.x))).nice().range([0, c.innerW]);
        const y = d3.scaleLinear().domain(extentWithPadding(scatterClean.map(d => d.y))).nice().range([c.innerH, 0]);
        const zValues = scatterClean.map(d => Number.isFinite(d.z) ? d.z : 0);
        const zExtent = extentWithPadding(zValues);
        const color = d3.scaleSequential(zExtent, d3.interpolateTurbo);
        const size = d3.scaleSqrt().domain(zExtent).range([6, 18]);
        axes(g, x, y, c.innerH);
        axisLabels(g, c.innerW, c.innerH, xKey, yKey);
        const regression = (() => {{
          const n = scatterClean.length;
          const sx = d3.sum(scatterClean, d => d.x);
          const sy = d3.sum(scatterClean, d => d.y);
          const sxy = d3.sum(scatterClean, d => d.x * d.y);
          const sx2 = d3.sum(scatterClean, d => d.x * d.x);
          const denom = n * sx2 - sx * sx;
          if (!denom) return null;
          const a = (n * sxy - sx * sy) / denom;
          const b = (sy - a * sx) / n;
          const domain = x.domain();
          return [{{x: domain[0], y: a * domain[0] + b}}, {{x: domain[1], y: a * domain[1] + b}}];
        }})();
        if (regression) {{
          g.append("path")
            .datum(regression)
            .attr("fill", "none")
            .attr("stroke", "#fbbf24")
            .attr("stroke-width", 2.5)
            .attr("stroke-dasharray", "8 6")
            .attr("d", d3.line().x(d => x(d.x)).y(d => y(d.y)));
        }}
        g.selectAll("circle").data(scatterClean).join("circle")
          .attr("cx", d => x(d.x)).attr("cy", d => y(d.y))
          .attr("r", d => Number.isFinite(d.z) ? size(d.z) : 8)
          .attr("fill", d => Number.isFinite(d.z) ? color(d.z) : "#38bdf8")
          .attr("stroke", "#0b1220")
          .attr("stroke-width", 1.4)
          .attr("opacity", 0.9)
          .on("mouseenter", (event, d) => showTip(event, [
            `<b>${{xKey}}</b>: ${{fmt(d.x)}}`,
            `<b>${{yKey}}</b>: ${{fmt(d.y)}}`,
            `<b>${{zKey}}</b>: ${{fmt(d.z)}}`,
          ]))
          .on("mousemove", moveTip)
          .on("mouseleave", hideTip);
      }} else fallback("scatter", "Brak par liczbowych X/Y.");

      const histValues = data.map(row => +row[xKey]).filter(Number.isFinite);
      if (histValues.length) {{
        const c = setup("histogram");
        const g = c.svg.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
        const x = d3.scaleLinear().domain(extentWithPadding(histValues)).nice().range([0, c.innerW]);
        const bins = d3.bin().domain(x.domain()).thresholds(18)(histValues);
        const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length) || 1]).nice().range([c.innerH, 0]);
        axes(g, x, y, c.innerH);
        axisLabels(g, c.innerW, c.innerH, xKey, "liczba");
        g.selectAll("rect").data(bins).join("rect")
          .attr("x", d => x(d.x0) + 1).attr("y", d => y(d.length))
          .attr("width", d => Math.max(1, x(d.x1) - x(d.x0) - 2))
          .attr("height", d => c.innerH - y(d.length))
          .attr("rx", 4)
          .attr("fill", "#38bdf8").attr("opacity", 0.86)
          .on("mouseenter", (event, d) => showTip(event, [
            `<b>${{xKey}}</b>: ${{fmt(d.x0)}}-${{fmt(d.x1)}}`,
            `<b>liczba</b>: ${{d.length}}`,
          ]))
          .on("mousemove", moveTip)
          .on("mouseleave", hideTip);
        const mean = d3.mean(histValues);
        g.append("line")
          .attr("x1", x(mean)).attr("x2", x(mean))
          .attr("y1", 0).attr("y2", c.innerH)
          .attr("stroke", "#fbbf24").attr("stroke-width", 2.5);
        g.append("text")
          .attr("x", x(mean) + 7).attr("y", 16)
          .attr("fill", "#fde68a").attr("font-size", 12)
          .text(`średnia: ${{fmt(mean)}}`);
      }} else fallback("histogram", "Wybrana kolumna X nie jest liczbowa.");

      const catKey = data[0] && ("material" in data[0] ? "material" : ("ksztalt" in data[0] ? "ksztalt" : null));
      const barData = catKey
        ? d3.rollups(data, v => v.length, d => d[catKey] ?? "brak").map(([label, value]) => ({{label, value}})).slice(0, 10)
        : numericColumns.slice(0, 10).map(col => ({{label: col, value: d3.deviation(data.map(row => +row[col]).filter(Number.isFinite)) || 0}}));
      if (barData.length) {{
        const c = setup("bars");
        const left = Math.min(150, Math.max(86, d3.max(barData, d => String(d.label).length) * 7 + 20));
        const g = c.svg.append("g").attr("transform", `translate(${{left}},${{margin.top}})`);
        const innerW = c.width - left - margin.right;
        const x = d3.scaleLinear().domain([0, d3.max(barData, d => d.value) || 1]).nice().range([0, innerW]);
        const y = d3.scaleBand().domain(barData.map(d => d.label)).range([0, c.innerH]).padding(0.22);
        g.append("g").attr("class", "grid-line")
          .call(d3.axisTop(x).ticks(4).tickSize(-c.innerH).tickFormat(""));
        g.append("g").attr("class", "axis").call(d3.axisLeft(y));
        g.append("g").attr("class", "axis").attr("transform", `translate(0,${{c.innerH}})`).call(d3.axisBottom(x).ticks(5));
        g.selectAll("rect").data(barData).join("rect")
          .attr("x", 0).attr("y", d => y(d.label)).attr("width", d => x(d.value)).attr("height", y.bandwidth())
          .attr("rx", 6).attr("fill", "#34d399").attr("opacity", 0.9)
          .on("mouseenter", (event, d) => showTip(event, [`<b>${{d.label}}</b>`, `wartość: ${{fmt(d.value)}}`]))
          .on("mousemove", moveTip)
          .on("mouseleave", hideTip);
        g.selectAll("text.value").data(barData).join("text")
          .attr("class", "value")
          .attr("x", d => x(d.value) + 8)
          .attr("y", d => y(d.label) + y.bandwidth() / 2 + 4)
          .attr("fill", "#d1fae5")
          .attr("font-size", 12)
          .text(d => fmt(d.value));
      }} else fallback("bars", "Brak danych do rankingu.");

      const c = setup("missingness");
      const shownColumns = columns.slice(0, 12);
      const missing = shownColumns.map(label => ({{
        label,
        value: data.filter(row => row[label] == null || row[label] === "").length / Math.max(1, data.length)
      }}));
      const left = Math.min(150, Math.max(86, d3.max(missing, d => String(d.label).length) * 7 + 20));
      const g = c.svg.append("g").attr("transform", `translate(${{left}},${{margin.top}})`);
      const innerW = c.width - left - margin.right;
      const x = d3.scaleLinear().domain([0, 1]).range([0, innerW]);
      const y = d3.scaleBand().domain(missing.map(d => d.label)).range([0, c.innerH]).padding(0.24);
      g.append("g").attr("class", "grid-line")
        .call(d3.axisTop(x).ticks(4).tickSize(-c.innerH).tickFormat(""));
      g.append("g").attr("class", "axis").call(d3.axisLeft(y));
      g.append("g").attr("class", "axis").attr("transform", `translate(0,${{c.innerH}})`).call(d3.axisBottom(x).ticks(5).tickFormat(d3.format(".0%")));
      g.selectAll("rect").data(missing).join("rect")
        .attr("x", 0).attr("y", d => y(d.label))
        .attr("width", d => Math.max(3, x(d.value)))
        .attr("height", y.bandwidth())
        .attr("rx", 6)
        .attr("fill", d => d.value ? "#fb7185" : "#60a5fa")
        .attr("opacity", 0.9)
        .on("mouseenter", (event, d) => showTip(event, [`<b>${{d.label}}</b>`, `braki: ${{d3.format(".1%")(d.value)}}`]))
        .on("mousemove", moveTip)
        .on("mouseleave", hideTip);
      g.selectAll("text.value").data(missing).join("text")
        .attr("x", d => Math.max(8, x(d.value) + 8))
        .attr("y", d => y(d.label) + y.bandwidth() / 2 + 4)
        .attr("fill", "#dbeafe")
        .attr("font-size", 12)
        .text(d => d3.format(".0%")(d.value));
    }}
  </script>
</body>
</html>"""


def save_d3_dashboard_html_report(df: pd.DataFrame, path: str | Path, **kwargs) -> Path:
    output_path = Path(path)
    output_path.write_text(build_d3_dashboard_html_report(df, **kwargs), encoding="utf-8")
    return output_path
