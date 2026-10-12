from __future__ import annotations

from matplotlib.figure import Figure

from AOA.core.esm_project import EsmTreeNode, build_esm_gantt_rows
from AOA.core.visualization_service import build_solution_tree_figure_from_records


def build_mopt_tree_figure(nodes: list[EsmTreeNode]) -> Figure:
    records = [
        {
            "id": node.node_id,
            "parent": node.parent_id,
            "label": node.label,
            "details": node.details,
            "edge_label": node.edge_label,
            "level": str(node.depth),
            "score": f"{node.score:g}",
            "is_best": "1" if node.chosen else "0",
            "status": node.status,
        }
        for node in nodes
    ]
    return build_solution_tree_figure_from_records(
        records,
        title=(
            "Drzewo rozwiazania MOpt | zielone = optimum, zolte = sprawdzone, czerwone = odrzucone"
        ),
    )


def build_esm_gantt_figure(result: dict, method_label: str) -> Figure:
    rows = build_esm_gantt_rows(result)
    machine_names = sorted(
        {str(row["machine"]) for row in rows},
        key=lambda name: int(name.removeprefix("M")),
    )
    machine_y = {name: index for index, name in enumerate(machine_names)}
    figure = Figure(
        figsize=(11, max(4.8, 1.25 * len(machine_names) + 2.5)), dpi=100, facecolor="#071019"
    )
    axis = figure.add_subplot(111)
    axis.set_facecolor("#0f172a")
    colors = ("#1479d1", "#0f766e", "#7c3aed", "#d97706", "#be185d")
    for index, row in enumerate(rows):
        start = float(row["start"])
        duration = float(row["duration"])
        setup = float(row.get("setup", 0.0))
        y = machine_y[str(row["machine"])]
        color = colors[index % len(colors)]
        if setup > 0:
            axis.barh(
                y,
                setup,
                left=max(0.0, start - setup),
                height=0.42,
                color="#64748b",
                edgecolor="#cbd5e1",
                hatch="//",
                alpha=0.8,
            )
        axis.barh(
            y,
            duration,
            left=start,
            height=0.42,
            color=color,
            edgecolor="#ef4444" if float(row["tardiness"]) > 0 else "#e5eef9",
            linewidth=2 if float(row["tardiness"]) > 0 else 1,
        )
        axis.text(
            start + duration / 2,
            y,
            str(row["job_id"]),
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
        )
        axis.axvline(float(row["deadline"]), color=color, linestyle=":", alpha=0.5)
    axis.set_yticks(list(range(len(machine_names))), machine_names)
    axis.invert_yaxis()
    axis.set_xlabel("Czas [min]")
    unscheduled = int(result.get("unscheduled_count", 0))
    suffix = f" | niezaplanowane: {unscheduled}" if unscheduled else ""
    axis.set_title(f"Gantt - {method_label}{suffix}", color="white")
    axis.grid(axis="x", color="#334155", alpha=0.45)
    axis.tick_params(colors="#cbd5e1")
    axis.xaxis.label.set_color("#cbd5e1")
    for spine in axis.spines.values():
        spine.set_color("#334155")
    figure.tight_layout()
    return figure
