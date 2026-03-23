from matplotlib.figure import Figure
from sklearn.tree import plot_tree
import seaborn as sns

from AOA.core.diagrams.correlation_matrix import prepare_correlation_matrix_data
from AOA.core.diagrams.decision_tree_diagram import prepare_decision_tree_data
from AOA.core.diagrams.gantt_chart import prepare_gantt_chart_data
from AOA.core.diagrams.line_chart import prepare_line_chart_data
from AOA.core.diagrams.similarity_matrix import prepare_similarity_matrix_data


def build_figure_from_request(df, chart_type, x_col=None, y_col=None):
    if df is None or df.empty:
        raise ValueError("Brak danych do wizualizacji")

    fig = Figure(figsize=(9, 5), dpi=100)
    ax = fig.add_subplot(111)

    if chart_type == "Scatter":
        if x_col not in df.columns or y_col not in df.columns:
            raise ValueError("Nieprawidłowe kolumny dla wykresu Scatter")

        ax.scatter(df[x_col], df[y_col])
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
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
        if x_col not in df.columns:
            raise ValueError("Nieprawidłowa kolumna dla histogramu")

        ax.hist(df[x_col].dropna(), bins=30)
        ax.set_xlabel(x_col)
        ax.set_ylabel("Liczność")
        return fig

    if chart_type == "Boxplot":
        if y_col not in df.columns:
            raise ValueError("Nieprawidłowa kolumna dla boxplot")

        ax.boxplot(df[y_col].dropna())
        ax.set_ylabel(y_col)
        return fig

    if chart_type == "Gantt":
        payload = prepare_gantt_chart_data(df)
        ax.barh(payload["labels"], payload["durations"], left=payload["starts"])
        ax.set_xlabel(payload["x_label"])
        return fig

    if chart_type == "CorrelationMatrix":
        payload = prepare_correlation_matrix_data(df)
        sns.heatmap(payload["matrix"], annot=True, cmap="coolwarm", ax=ax)
        ax.set_title(payload["title"])
        return fig

    if chart_type == "SimilarityMatrix":
        payload = prepare_similarity_matrix_data(df)
        sns.heatmap(
            payload["matrix"],
            annot=True,
            xticklabels=payload["labels"],
            yticklabels=payload["labels"],
            cmap="viridis",
            ax=ax
        )
        ax.set_title(payload["title"])
        return fig

    if chart_type == "DecisionTree":
        payload = prepare_decision_tree_data(df)
        plot_tree(
            payload["model"],
            feature_names=payload["feature_names"],
            filled=True,
            ax=ax
        )
        return fig

    raise ValueError(f"Nieobsługiwany typ wykresu: {chart_type}")
