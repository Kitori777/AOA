from __future__ import annotations

D3_CDN_URL = "https://cdn.jsdelivr.net/npm/d3@7"
VISUAL_LIBRARIES = ["Matplotlib", "Seaborn", "Plotly", "Altair", "NetworkX"]
CHART_TYPES = [
    "ESM Best Method", "Production Line Dashboard", "Production Dashboard", "Dashboard",
    "Diagnostics", "Model Diagnostics", "Pair Explorer", "Pair Plot", "Joint Plot", "3D Scatter",
    "3D Surface", "Bubble Chart", "Heatmap Density", "Treemap", "Sunburst", "Funnel",
    "Waterfall", "Radar Chart", "KDE Plot", "ECDF Plot", "Violin Plot", "Count Plot",
    "Strip Plot", "Swarm Plot", "Point Plot", "Bar Estimate", "Regression Plot", "Stacked Bar",
    "Binned Scatter", "Faceted Scatter", "Interactive Brush", "Outlier Map", "DBSCAN Anomaly",
    "PCA State Segments", "LDA vs t-SNE", "KMeans vs GMM", "Step View", "Priority Timeline",
    "Area Chart", "Missingness Map", "Column Ranking", "Bar Chart", "Pie Chart", "Scatter",
    "Line", "Histogram", "Boxplot", "Gantt", "SolutionTree", "ML Decision Tree", "Network Graph",
    "Circular Network", "Spring Network", "Shell Network", "Kamada-Kawai Network", "Tree Network",
    "CorrelationMatrix", "SimilarityMatrix",
]
SEABORN_CHART_TYPES = [
    "Scatter", "Histogram", "Boxplot", "Count Plot", "Strip Plot", "Swarm Plot", "Point Plot",
    "Bar Estimate", "Violin Plot", "KDE Plot", "ECDF Plot", "Regression Plot", "Joint Plot",
    "Pair Plot", "Heatmap Density", "CorrelationMatrix",
]
PLOTLY_CHART_TYPES = [
    "Scatter", "Line", "Histogram", "Boxplot", "Violin Plot", "Bar Chart", "Pie Chart",
    "Area Chart", "Bubble Chart", "3D Scatter", "3D Surface", "Heatmap Density", "Treemap",
    "Sunburst", "Funnel", "Waterfall", "Radar Chart", "CorrelationMatrix", "Production Dashboard",
    "Dashboard", "SolutionTree", "Network Graph",
]
ALTAIR_CHART_TYPES = [
    "Scatter", "Line", "Histogram", "Boxplot", "Bar Chart", "Stacked Bar", "Pie Chart",
    "Area Chart", "Bubble Chart", "Binned Scatter", "Faceted Scatter", "Interactive Brush",
    "Heatmap Density", "Regression Plot", "ECDF Plot", "Missingness Map", "Column Ranking",
]
NETWORKX_CHART_TYPES = [
    "Network Graph", "Circular Network", "Spring Network", "Shell Network",
    "Kamada-Kawai Network", "Tree Network", "SolutionTree",
]
_D3_EXCLUDED = {
    "Treemap", "Sunburst", "Funnel", "Waterfall", "Radar Chart", "Count Plot", "Strip Plot",
    "Swarm Plot", "Point Plot", "Bar Estimate", "Stacked Bar", "Binned Scatter", "Faceted Scatter",
    "Interactive Brush", "Circular Network", "Spring Network", "Shell Network",
    "Kamada-Kawai Network", "Tree Network",
}
D3_CHART_TYPES = [chart_type for chart_type in CHART_TYPES if chart_type not in _D3_EXCLUDED]
LIBRARY_CHART_SUPPORT = {
    "Matplotlib": CHART_TYPES, "Seaborn": SEABORN_CHART_TYPES, "Plotly": PLOTLY_CHART_TYPES,
    "Altair": ALTAIR_CHART_TYPES, "NetworkX": NETWORKX_CHART_TYPES,
}
CHART_PICKER_META = {
    "Production Line Dashboard": ("Linia", "PL", "stanowiska i KPI"),
    "Production Dashboard": ("Dashboard", "▦", "panel KPI"), "Dashboard": ("Dashboard", "▦", "panel EDA"),
    "ESM Best Method": ("STO", "★", "najlepsza metoda"), "SolutionTree": ("STO", "⑂", "drzewo rozwiazan"),
    "Gantt": ("STO", "▤", "harmonogram"), "Priority Timeline": ("STO", "↗", "kolejnosc"),
    "Step View": ("STO", "⌁", "kroki"), "Scatter": ("Podstawowe", "•", "relacja X/Y"),
    "Line": ("Podstawowe", "⌁", "trend"), "Histogram": ("Podstawowe", "▥", "rozkład"),
    "Bar Chart": ("Podstawowe", "▮", "porownanie"), "Pie Chart": ("Podstawowe", "◔", "udzialy"),
    "Boxplot": ("Statystyka", "▣", "rozrzut"), "KDE Plot": ("Statystyka", "≈", "gestosc"),
    "ECDF Plot": ("Statystyka", "∫", "dystrybuanta"), "Violin Plot": ("Statystyka", "◈", "ksztalt rozkladu"),
    "Regression Plot": ("Statystyka", "⟋", "linia trendu"), "CorrelationMatrix": ("Macierze", "▦", "korelacje"),
    "SimilarityMatrix": ("Macierze", "▧", "podobienstwo"), "Heatmap Density": ("Macierze", "░", "gestosc 2D"),
    "Missingness Map": ("Jakosc", "□", "braki"), "Outlier Map": ("Jakosc", "!", "odstajace"),
    "Column Ranking": ("Jakosc", "≡", "ranking kolumn"), "3D Scatter": ("Zaawansowane", "◇", "3D punkty"),
    "3D Surface": ("Zaawansowane", "▱", "powierzchnia"), "Bubble Chart": ("Zaawansowane", "●", "rozmiar jako Z"),
    "Pair Explorer": ("Zaawansowane", "⌘", "pary zmiennych"), "ML Decision Tree": ("ML", "⑂", "drzewo ML"),
    "Network Graph": ("Sieci", "◎", "graf"), "Circular Network": ("Sieci", "◎", "uklad kolowy"),
    "Spring Network": ("Sieci", "◎", "uklad spring"), "Shell Network": ("Sieci", "◎", "uklad shell"),
    "Kamada-Kawai Network": ("Sieci", "◎", "uklad Kamada"), "Tree Network": ("Sieci", "⑂", "siec drzewa"),
}
SOLUTION_TREE_TEMPLATE_COLUMNS = ["node_id", "parent_id", "label", "details", "edge_label", "level", "order"]


def get_supported_chart_types(chart_library: str) -> list[str]:
    return list(LIBRARY_CHART_SUPPORT.get(chart_library, CHART_TYPES))


def is_chart_supported_by_library(chart_type: str, chart_library: str) -> bool:
    normalized = "ML Decision Tree" if chart_type == "DecisionTree" else chart_type
    return normalized in get_supported_chart_types(chart_library)


def coerce_chart_for_library(chart_type: str, chart_library: str) -> str:
    normalized = "ML Decision Tree" if chart_type == "DecisionTree" else chart_type
    supported = get_supported_chart_types(chart_library)
    return normalized if normalized in supported else supported[0] if supported else "Scatter"
