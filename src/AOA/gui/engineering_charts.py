from __future__ import annotations

from matplotlib.figure import Figure

from AOA.core.esm_project import EsmTreeNode, build_esm_gantt_rows


def build_mopt_tree_figure(nodes: list[EsmTreeNode]) -> Figure:
    figure = Figure(figsize=(12, 7), dpi=100, facecolor="#071019")
    axis = figure.add_subplot(111)
    axis.set_facecolor("#071019")
    by_depth: dict[int, list[EsmTreeNode]] = {}
    for node in nodes:
        by_depth.setdefault(node.depth, []).append(node)
    positions: dict[str, tuple[float, float]] = {}
    for depth, level_nodes in by_depth.items():
        count = len(level_nodes)
        for index, node in enumerate(level_nodes):
            x = (index + 1) / (count + 1)
            y = 1.0 - depth / max(1, len(by_depth))
            positions[node.node_id] = (x, y)
    for node in nodes:
        if node.parent_id:
            x0, y0 = positions[node.parent_id]
            x1, y1 = positions[node.node_id]
            axis.plot(
                [x0, x1],
                [y0, y1],
                color="#35c98b" if node.chosen else "#64748b",
                linewidth=2 if node.chosen else 1,
                alpha=0.9,
            )
    for node in nodes:
        x, y = positions[node.node_id]
        color = "#0f766e" if node.chosen else "#334155"
        axis.text(
            x,
            y,
            f"{node.label}\n{node.details}",
            ha="center",
            va="center",
            color="white",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.45",
                "facecolor": color,
                "edgecolor": "#8ddbd1" if node.chosen else "#64748b",
            },
        )
    axis.set_title("Drzewo rozwiazania MOpt", color="white", fontsize=16, pad=18)
    axis.set_xlim(0, 1)
    axis.set_ylim(-0.04, 1.06)
    axis.axis("off")
    figure.tight_layout()
    return figure


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
