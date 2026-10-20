from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Patch

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
            "Drzewo rozwiazania MOpt | zielone = najlepsza sciezka, zolte = sprawdzone, czerwone = odciecia"
        ),
        detail_line_limit=8 if nodes and "Przeplyw" in nodes[0].label else 4,
    )


COLORS = (
    "#1479d1",
    "#0f766e",
    "#7c3aed",
    "#d97706",
    "#be185d",
    "#0369a1",
    "#4d7c0f",
    "#a21caf",
    "#b45309",
    "#475569",
)


def _job_colors(results: list[dict]) -> dict[str, str]:
    ids = sorted({str(step["job_id"]) for result in results for step in result.get("steps", [])})
    return {job_id: COLORS[i % len(COLORS)] for i, job_id in enumerate(ids)}


def _draw_gantt(
    axis: Axes,
    result: dict,
    method_label: str,
    *,
    job_colors: dict[str, str],
    horizon: float | None = None,
    compact: bool = False,
) -> None:
    rows = build_esm_gantt_rows(result)
    machine_names = sorted(
        {str(row["machine"]) for row in rows},
        key=lambda name: int(name.removeprefix("M")),
    )
    if result.get("model") == "flowshop":
        machine_names = [f"M{i}" for i in range(1, result["machine_count"] + 1)]
    machine_y = {name: index for index, name in enumerate(machine_names)}
    axis.set_facecolor("#0f172a")
    horizon_value = (
        float(horizon)
        if horizon is not None
        else max((float(row["start"]) + float(row["duration"]) for row in rows), default=1.0)
    )
    # Very loose due dates must not compress the actual schedule into a sliver.
    shown_end = max(1.0, horizon_value * 1.05)
    distant_deadlines = [
        row for row in rows if row["final_operation"] and float(row["deadline"]) > shown_end
    ]
    for row in rows:
        start = float(row["start"])
        duration = float(row["duration"])
        setup = float(row.get("setup", 0.0))
        y = machine_y[str(row["machine"])]
        color = job_colors[str(row["job_id"])]
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
            fontsize=8,
            rotation=90 if duration < horizon_value * (0.04 if compact else 0.025) else 0,
        )
        if row["final_operation"]:
            axis.axvline(float(row["deadline"]), color=color, linestyle=":", alpha=0.35)
    axis.set_yticks(list(range(len(machine_names))), machine_names)
    axis.set_xlim(0, shown_end)
    if distant_deadlines:
        axis.text(
            1,
            1.01,
            f"Terminy poza zakresem osi: {len(distant_deadlines)} (po zakonczeniu produkcji)",
            transform=axis.transAxes,
            ha="right",
            color="#cbd5e1",
            fontsize=8,
        )
    axis.invert_yaxis()
    axis.set_xlabel("Czas [min]")
    unscheduled = int(result.get("unscheduled_count", 0))
    suffix = f" | niezaplanowane: {unscheduled}" if unscheduled else ""
    title = f"Gantt - {method_label}{suffix}"
    if compact:
        title += f"\nSTO = {result['sto']:.2f} min | koniec = {result['completion_total']:.2f} min"
    axis.set_title(
        title, color="white", fontsize=10 if compact else 12, pad=20 if distant_deadlines else 10
    )
    axis.grid(axis="x", color="#334155", alpha=0.45)
    axis.tick_params(colors="#cbd5e1")
    axis.xaxis.label.set_color("#cbd5e1")
    for spine in axis.spines.values():
        spine.set_color("#334155")


def build_esm_gantt_figure(result: dict, method_label: str) -> Figure:
    figure = Figure(
        figsize=(11, max(4.8, 1.25 * result.get("machine_count", 1) + 2.5)),
        dpi=100,
        facecolor="#071019",
    )
    _draw_gantt(figure.add_subplot(111), result, method_label, job_colors=_job_colors([result]))
    if result.get("model") == "flowshop":
        figure.text(
            0.5,
            0.02,
            f"Przeplyw | {result['machine_count']} maszyn | STO={result['sto']:g} min | "
            f"Koniec={result['completion_total']:g} min | odpad={result['total_waste_kg']:.2f} kg | "
            "szare: przezbrojenie; czerwone: opoznienie",
            ha="center",
            color="#cbd5e1",
            fontsize=8,
        )
    figure.tight_layout(rect=(0, 0.05, 1, 1))
    return figure


GANTT_METHOD_LABELS = {
    "MT": "MT / EDD",
    "MO": "MO / SPT",
    "MZO": "MZO / LPT",
    "MOPT": "MOpt",
    "ECO_WASTE": "ECO Waste",
    "COMPONENT_READY_EDD": "Component Ready + EDD",
    "ROBUST_MC": "Robust Monte Carlo",
}


def build_esm_gantt_grid_figure(
    results: list[dict],
    *,
    context_results: list[dict] | None = None,
    title: str = "Porownanie harmonogramow - te same dane",
) -> Figure:
    """One page of at most four real schedules, with scales shared across pages."""
    if not 1 <= len(results) <= 4 or len({r["method"] for r in results}) != len(results):
        raise ValueError("Strona Ganttow wymaga od 1 do 4 roznych metod.")
    context = context_results if context_results is not None else results
    if not context:
        raise ValueError("Brak wynikow do porownania.")
    combined = [*context, *results]
    counts = {r["machine_count"] for r in combined}
    orders = [{s["job_id"] for s in r["steps"]} for r in combined]
    if len(counts) != 1 or any(ids != orders[0] for ids in orders):
        raise ValueError("Gantty musza dotyczyc tych samych zlecen i liczby maszyn.")
    figure = Figure(
        figsize=(13, max(7.5, 1.0 * results[0]["machine_count"] + 4)), dpi=100, facecolor="#071019"
    )
    colors = _job_colors(context)
    horizon = max(r["completion_total"] for r in context) or 1
    for index in range(4):
        axis = figure.add_subplot(2, 2, index + 1)
        if index < len(results):
            result = results[index]
            _draw_gantt(
                axis,
                result,
                GANTT_METHOD_LABELS.get(result["method"], result["method"]),
                job_colors=colors,
                horizon=horizon,
                compact=True,
            )
        else:
            axis.set_facecolor("#071019")
            axis.set_axis_off()
            axis.text(
                0.5,
                0.5,
                "Brak kolejnej wybranej metody",
                ha="center",
                va="center",
                color="#64748b",
                transform=axis.transAxes,
            )
    figure.suptitle(title, color="white", fontsize=14)
    handles = [Patch(facecolor=color, label=job) for job, color in colors.items()]
    if handles:
        figure.legend(
            handles=handles,
            loc="lower center",
            ncol=min(10, len(handles)),
            facecolor="#0f172a",
            labelcolor="white",
            edgecolor="#334155",
            fontsize=9,
        )
    figure.tight_layout(rect=(0, 0.055, 1, 0.95), h_pad=3, w_pad=2)
    return figure


def build_esm_gantt_comparison_figure(results: list[dict]) -> Figure:
    """Theory's fixed four-method comparison uses the same grid as the main button."""
    methods = ("MT", "MO", "MZO", "MOPT")
    by_method = {r["method"]: r for r in results}
    if any(method not in by_method for method in methods):
        raise ValueError("Porownanie wymaga wynikow MT, MO, MZO i MOpt.")
    return build_esm_gantt_grid_figure(
        [by_method[method] for method in methods],
        title="Teoria ESM - te same dane, cztery harmonogramy",
    )
