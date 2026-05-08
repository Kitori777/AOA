from __future__ import annotations

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


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=[np.number]).columns.tolist()


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
