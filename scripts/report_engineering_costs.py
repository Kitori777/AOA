"""Reproduce paper minima and a 3-machine/10-job experiment without editing source CSVs."""

from __future__ import annotations

import csv
import json
from hashlib import sha256
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg

from AOA.core.esm_costs import DelayPenalty, cost_parameters, with_job_penalties
from AOA.core.esm_project import (
    ESM_METHODS,
    build_mopt_solution_tree,
    evaluate_esm_methods,
    load_esm_jobs,
)
from AOA.gui.engineering_charts import build_esm_gantt_grid_figure, build_mopt_tree_figure
from AOA.gui.engineering_exports import (
    EngineeringContext,
    comparison_rows,
    operation_rows,
    write_csv,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "engineering-costs"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline = {
        path: sha256(path.read_bytes()).hexdigest() for path in (ROOT / "data/esm").rglob("*.csv")
    }
    examples = ROOT / "data/esm/article/costs"
    cases = json.loads((examples / "manifest.json").read_text(encoding="utf-8"))
    paper_rows = []
    for case in cases:
        jobs = load_esm_jobs(examples / case["file"])
        result = evaluate_esm_methods(
            jobs, ["MOPT"], n_machines=case["machines"], objective="cost"
        )[0]
        assert result["total_tardiness_cost"] == case["expected_minimum_cost"]
        assert result["optimality_status"] == "OPTIMAL_CONFIRMED"
        paper_rows.append(
            {
                "case": case["file"],
                "machines": case["machines"],
                "cost": result["total_tardiness_cost"],
                "paper_cost": case["paper_minimum_cost"],
                "confirmed": True,
                "order": " -> ".join(result["order"]),
                "discrepancy": case["discrepancy"],
            }
        )
    with (OUTPUT / "paper-variants.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(paper_rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(paper_rows)

    source = ROOT / "tests/fixtures/esm/esm_flow_10_eco_components.csv"
    original = load_esm_jobs(source)
    rates = [1, 4, 10, 2, 8, 0.5, 6, 1, 3, 12]
    grace = [0, 10, 5, 0, 15, 0, 5, 10, 0, 5]
    parameters = {
        job.job_id: DelayPenalty(rate, tolerance)
        for job, rate, tolerance in zip(original, rates, grace, strict=True)
    }
    jobs = with_job_penalties(original, parameters)
    results = evaluate_esm_methods(
        jobs, list(ESM_METHODS), n_machines=3, time_mode="file", objective="cost"
    )
    time_mopt = evaluate_esm_methods(
        jobs, ["MOPT"], n_machines=3, time_mode="file", objective="sto"
    )[0]
    context = EngineeringContext(
        str(source),
        3,
        "file",
        sha256(source.read_bytes()).hexdigest(),
        "cost",
        json.dumps(cost_parameters(jobs), sort_keys=True),
    )
    write_csv(
        OUTPUT / "production-3x10-comparison.csv",
        comparison_rows(results, context),
        source_path=str(source),
    )
    write_csv(
        OUTPUT / "production-3x10-operations.csv",
        operation_rows(results, context),
        source_path=str(source),
    )
    for start in range(0, len(results), 4):
        # Keep the same canonical method layout as the native window.
        by_method = {r["method"]: r for r in results}
        canonical = [by_method[method] for method in ESM_METHODS]
        figure = build_esm_gantt_grid_figure(
            canonical[start : start + 4],
            context_results=canonical,
            title="Koszty — 3 maszyny, 10 zleceń",
        )
        FigureCanvasAgg(figure)
        for extension in ("png", "svg"):
            figure.savefig(OUTPUT / f"production-3x10-page{start // 4 + 1}.{extension}", dpi=140)
        figure.clear()
    mopt = next(r for r in results if r["method"] == "MOPT")
    nodes = build_mopt_solution_tree(
        jobs, n_machines=3, solution=mopt["flowshop_solution"], max_nodes=45
    )
    tree = build_mopt_tree_figure(nodes)
    FigureCanvasAgg(tree)
    tree.savefig(OUTPUT / "production-3x10-tree.png", dpi=130)
    tree.savefig(OUTPUT / "production-3x10-tree.svg")
    tree.clear()
    assert all(sha256(path.read_bytes()).hexdigest() == digest for path, digest in baseline.items())
    summary = {
        "paper_variants": paper_rows,
        "source_csvs_unchanged": len(baseline),
        "production_source_sha256": context.source_sha256,
        "parameters": cost_parameters(jobs),
        "cost_mopt": {
            key: mopt[key]
            for key in (
                "sto",
                "total_tardiness_cost",
                "order",
                "optimality_status",
                "search_states",
                "elapsed_s",
            )
        },
        "sto_mopt": {
            key: time_mopt[key]
            for key in ("sto", "total_tardiness_cost", "order", "optimality_status")
        },
        "results": [
            {key: value for key, value in r.items() if key != "flowshop_solution"} for r in results
        ],
    }
    (OUTPUT / "results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Koszty opóźnień — weryfikacja",
        "",
        "16 wariantów artykułów potwierdzono pełnym przeglądem w testach i MOpt w tym raporcie.",
        "Pierwszy dokument P2/W2: 300 zamiast podanego 330; dane zachowane.",
        "",
        "## 3 maszyny i 10 zleceń",
        "",
        "Źródło: esm_flow_10_eco_components.csv. Stawki i tolerancje nałożono w pamięci; są zapisane w results.json i eksporcie CSV.",
        "",
        "| Metoda | STO [min] | Koszt [j.p.] | Odpad [kg] | Status |",
        "|---|---:|---:|---:|---|",
    ]
    lines += [
        f"| {r['method']} | {r['sto']:.3f} | {r['total_tardiness_cost']:.3f} | {r['total_waste_kg']:.2f} | {r['optimality_status']} |"
        for r in results
    ]
    lines += [
        "",
        f"MOpt w trybie STO: STO={time_mopt['sto']:.3f} min, koszt={time_mopt['total_tardiness_cost']:.3f} j.p., status={time_mopt['optimality_status']}.",
        "",
        "Robust wybiera według ryzyka kosztu; nominalny koszt nie dowodzi optimum ryzyka. P90 w eksporcie pochodzi z niezależnej serii.",
        "Czasy obliczeń dotyczą bieżącego uruchomienia; nie są porównaniem wydajności komputerów.",
        "",
        "![Cztery podstawowe metody](production-3x10-page1.png)",
        "![Trzy metody dodatkowe](production-3x10-page2.png)",
        "[Drzewo MOpt](production-3x10-tree.svg)",
    ]
    (OUTPUT / "raport.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "papers": len(paper_rows),
                "cost_mopt": summary["cost_mopt"],
                "sto_mopt": summary["sto_mopt"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
