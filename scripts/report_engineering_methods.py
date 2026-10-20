"""Reproduce eight engineering case studies, including a frozen two-pass baseline."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import platform
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from generate_esm_examples import THESIS_CASES
from matplotlib.backends.backend_agg import FigureCanvasAgg

import AOA.core.engineering_methods as engineering
from AOA.core.esm_project import build_mopt_solution_tree, evaluate_esm_methods, load_esm_jobs
from AOA.core.flowshop import evaluate_flowshop, flowshop_key, solve_flowshop
from AOA.core.monte_carlo import (
    MonteCarloConfig,
    default_queue_machine_specs,
    simulate_schedule_risk,
)
from AOA.gui.engineering_charts import build_esm_gantt_figure, build_mopt_tree_figure

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "engineering-case-studies"
METHODS = ["MT", "MO", "MZO", "MOPT", "ECO_WASTE", "COMPONENT_READY_EDD", "ROBUST_MC"]
EXTRA = METHODS[4:]
NAMES = {
    "MT": "MT",
    "MO": "MO",
    "MZO": "MZO",
    "MOPT": "MOpt",
    "ECO_WASTE": "ECO Waste",
    "COMPONENT_READY_EDD": "Component Ready + EDD",
    "ROBUST_MC": "Robust Monte Carlo",
}


def baseline_refine(seeds, n_machines, *, retained=None):
    """Frozen pre-change refinement: top three seeds, two insertion passes."""
    cache = {}

    def key(order):
        ids = tuple(j.job_id for j in order)
        if ids not in cache:
            cache[ids] = (*flowshop_key(evaluate_flowshop(order, n_machines=n_machines)), ids)
        return cache[ids]

    unique = {tuple(j.job_id for j in seed): seed for seed in seeds if seed}
    if not unique:
        return []
    best = min(unique.values(), key=key)
    for seed in sorted(unique.values(), key=key)[:3]:
        current = list(seed)
        for _ in range(2):
            old_key = key(current)
            candidates = [current]
            for i, job in enumerate(current):
                remaining = current[:i] + current[i + 1 :]
                candidates.extend(
                    remaining[:p] + [job] + remaining[p:] for p in range(len(current))
                )
            current = min(candidates, key=key)
            if key(current) >= old_key:
                break
        if key(current) < key(best):
            best = current
    if retained is not None:
        retained.append(list(best))
    return best


def before_results(jobs):
    # The temporary replacement is only in this single-threaded report process.
    # Simulator and seed selection match the old method; holdout does not select.
    with patch.object(engineering, "_refine", baseline_refine):
        results = []
        for method, function in [
            ("ECO_WASTE", engineering.sequence_eco_flowshop),
            ("COMPONENT_READY_EDD", engineering.sequence_component_ready_flowshop),
        ]:
            evaluation = evaluate_flowshop(function(jobs, n_machines=3), n_machines=3)
            results.append({**evaluation, "method": method})
        results.append(engineering.evaluate_robust_flowshop(jobs, n_machines=3))
    return results


def saved_result(result):
    keys = [
        "method",
        "sto",
        "completion_total",
        "total_waste_kg",
        "order",
        "steps",
        "unscheduled_count",
        "blocked_jobs",
        "elapsed_s",
        "optimality_status",
        "search_status",
        "search_states",
        "search_pruned",
        "search_stop_reason",
        "lower_bound",
        "risk_summary",
        "risk_validation_summary",
        "risk_candidate_count",
        "risk_validation_role",
    ]
    return {key: result[key] for key in keys if key in result}


def image(figure, stem, *, tree=False):
    FigureCanvasAgg(figure)
    figure.savefig(OUTPUT / f"{stem}.svg")
    figure.savefig(OUTPUT / f"{stem}.png", dpi=55 if tree else 125)
    figure.clear()
    return (
        f"<a href='{stem}.svg' target='_blank'><img loading='lazy' src='{stem}.png' "
        f"alt='{html.escape(stem)}'></a>"
    )


def compare_risk(result, seed=43, iterations=3000):
    risk = simulate_schedule_risk(
        engineering._events_in_hours(result),
        default_queue_machine_specs(["1", "2", "3"]),
        MonteCarloConfig(seed=seed, iterations=iterations),
    )
    return {**engineering._risk_in_minutes(risk.summary), **engineering._mean_intervals(risk.runs)}


def case_evidence(stem, jobs, reference, before, after):
    evidence = {}
    if stem == "esm_flow_10_urgent":
        limited = solve_flowshop(jobs, n_machines=3, max_states=100)
        evidence["limited_mopt"] = saved_result({**limited.evaluation, "method": "MOPT_100"})
        evidence["limited_confirmed"] = limited.confirmed
        nodes = build_mopt_solution_tree(jobs, n_machines=3, solution=limited, max_nodes=35)
        image(build_mopt_tree_figure(nodes), stem + "-limited-tree", tree=True)
    elif stem == "esm_flow_10_intentional_idle":
        evidence["busy_order"] = saved_result(evaluate_flowshop(jobs, n_machines=3))
        evidence["first_start_min"] = reference["steps"][0]["setup_start"]
    elif stem == "esm_jobs_10_mixed_constraints":
        grouped = sorted(jobs, key=lambda j: (j.material, j.deadline, j.job_id))
        evidence["grouped_materials"] = saved_result(evaluate_flowshop(grouped, n_machines=3))
    elif stem == "esm_flow_10_eco_components":
        evidence["risk_comparison"] = {
            "MOpt": compare_risk(reference),
            "Robust po": compare_risk(after["ROBUST_MC"]),
            "Robust przed": compare_risk(before["ROBUST_MC"]),
        }
    elif stem == "esm_flow_10_multiple_optima":
        by_id = {j.job_id: j for j in jobs}
        order = [by_id[name] for name in reference["order"]]
        alternative = list(reversed(order))
        evaluation = evaluate_flowshop(alternative, n_machines=3)
        assert flowshop_key(evaluation) == flowshop_key(reference)
        evidence["another_optimum"] = saved_result(evaluation)
        evidence["unGrouped"] = saved_result(evaluate_flowshop(jobs, n_machines=3))
    elif stem == "esm_flow_10_blocked_components":
        admitted = [
            replace(j, stock_status="WAITING_COMPONENTS" if j.components_ready_h else "READY")
            for j in jobs
        ]
        complete = solve_flowshop(admitted, n_machines=3)
        evidence["all_components_available_control"] = saved_result(complete.evaluation)
        evidence["control_confirmed"] = complete.confirmed
    return evidence


def findings(stem, before, after, reference, evidence):
    def score(r):
        return f"STO {r['sto']:.2f} min, odpad {r['total_waste_kg']:.2f} kg, koniec {r['completion_total']:.2f} min"

    if stem == "esm_flow_10_urgent":
        limited = evidence["limited_mopt"]
        return [
            f"MOpt po 100 stanach: {score(limited)}; optimum niepotwierdzone. "
            f"Component po poprawie: {score(after['COMPONENT_READY_EDD'])}. "
            f"Pełny MOpt: {score(reference)}. Heurystyka może pokonać przerwane wyszukiwanie.",
            "Limit 100 stanów jest parametrem eksperymentu. W aplikacji MOpt nadal używa domyślnie 100000 stanów i 10 s.",
        ]
    if stem == "esm_flow_10_eco_trap":
        return [
            f"ECO przed: {score(before['ECO_WASTE'])}; po: {score(after['ECO_WASTE'])}. "
            "Dodatkowe ruchy usuwają odpad bez pogorszenia terminowości."
        ]
    if stem == "esm_flow_10_component_wait":
        return [
            f"Component przed: {score(before['COMPONENT_READY_EDD'])}; po: {score(after['COMPONENT_READY_EDD'])}. "
            "Samo dopuszczanie zleceń według gotowości nie zastępuje poprawiania całej kolejności."
        ]
    if stem == "esm_flow_10_intentional_idle":
        return [
            f"Rozpoczęcie od dostępnego Z1: {score(evidence['busy_order'])}. "
            f"MOpt: {score(reference)}; pierwsza operacja zaczyna się w {evidence['first_start_min']:g} min. "
            "Warto poczekać na pilne Z2, zamiast natychmiast blokować M1 długim zleceniem."
        ]
    if stem == "esm_jobs_10_mixed_constraints":
        return [
            f"MOpt: {score(reference)}. Proste grupowanie materiałów: {score(evidence['grouped_materials'])}. "
            "MOpt daje pierwszeństwo STO. Mniejszy odpad przy większym STO nie podważa tego optimum."
        ]
    if stem == "esm_flow_10_eco_components":
        rows = evidence["risk_comparison"]
        return [
            "Niezależne porównanie ustalonych kolejności: 3000 realizacji, ziarno 43, te same syntetyczne profile maszyn. "
            + "; ".join(
                f"{name}: średnie STO {r['mean_lateness_min']:.2f}, P90 {r['p90_lateness_min']:.2f} min"
                for name, r in rows.items()
            )
            + ".",
            "Niższe nominalne STO nie gwarantuje niższego P90. Wyniki są estymacją z próby; "
            "ten sam numer ziarna nie przypisuje identycznej awarii tej samej operacji w różnych kolejnościach. "
            "Przykład nie dowodzi stochastycznej optymalności Robust.",
        ]
    if stem == "esm_flow_10_multiple_optima":
        return [
            f"MOpt i odwrócona kolejność rodzin mają identyczne {score(reference)}. "
            f"Kolejność naprzemienna: {score(evidence['unGrouped'])}. "
            "Zerowe STO nie wystarcza do porównania metod; odpad rozstrzyga między planami. "
            "W obrębie każdej rodziny zamiana identycznych operacji tworzy kolejne równorzędne optima."
        ]
    return [
        f"Plan z zablokowanym Z4: {score(reference)}, ale tylko 9 zleceń. "
        f"Kontrola po dopuszczeniu Z4: {score(evidence['all_components_available_control'])}. "
        "Niższe STO planu niepełnego nie oznacza lepszego rozwiązania tego samego problemu. "
        "Potwierdzenie MOpt dotyczy wyłącznie dopuszczonych zleceń."
    ]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    all_records, cases, sections, markdown = (
        [],
        [],
        [],
        [
            "# Przypadki do pracy inżynierskiej",
            "",
            "Dane syntetyczne; każdy przypadek: 3 maszyny, 10 zleceń. "
            "Zestawy wybrano celowo dla konkretnych zjawisk, bez szacowania ich częstości w przemyśle.",
            "",
        ],
    )
    for stem, title, origin in THESIS_CASES:
        source = ROOT / "data" / "esm" / "examples" / f"{stem}.csv"
        jobs = load_esm_jobs(source)
        before = {r["method"]: r for r in before_results(jobs)}
        started = perf_counter()
        results = evaluate_esm_methods(jobs, METHODS, n_machines=3)
        total_time = perf_counter() - started
        after = {r["method"]: r for r in results}
        reference = after["MOPT"]
        evidence = case_evidence(stem, jobs, reference, before, after)
        conclusions = findings(stem, before, after, reference, evidence)
        paragraphs = "".join(f"<p>{html.escape(text)}</p>" for text in conclusions)
        rows = []
        for phase, mapping in [("przed", before), ("po", after)]:
            for method, result in mapping.items():
                status = result.get("optimality_status", "CANDIDATE")
                if phase == "przed":
                    status = (
                        "PARTIAL_PLAN"
                        if result["unscheduled_count"]
                        else (
                            "RISK_ASSESSED"
                            if method == "ROBUST_MC"
                            else "OPTIMAL_CONFIRMED"
                            if reference["optimality_status"] == "OPTIMAL_CONFIRMED"
                            and flowshop_key(reference) == flowshop_key(result)
                            else "GAP_TO_OPTIMUM"
                        )
                    )
                record = {
                    "przypadek": stem,
                    "wersja": phase,
                    "metoda": method,
                    "sto_min": result["sto"],
                    "odpad_kg": result["total_waste_kg"],
                    "koniec_min": result["completion_total"],
                    "niezaplanowane": result["unscheduled_count"],
                    "czas_s": result.get("elapsed_s") if phase == "po" else None,
                    "status": status,
                    "kolejnosc": " -> ".join(result["order"]),
                }
                all_records.append(record)
                timing = f"{record['czas_s']:.4f}" if record["czas_s"] is not None else "—"
                rows.append(
                    f"<tr><td>{NAMES[method]} {phase}</td><td>{result['sto']:.2f}</td>"
                    f"<td>{result['total_waste_kg']:.2f}</td><td>{result['completion_total']:.2f}</td>"
                    f"<td>{timing}</td><td>{status}</td></tr>"
                )
        plots = []
        for method in [*EXTRA, "MOPT"]:
            result = after[method]
            plots.append(
                f"<details><summary>Gantt: {NAMES[method]}</summary><p>"
                + html.escape(" → ".join(result["order"]))
                + "</p>"
                + image(build_esm_gantt_figure(result, NAMES[method]), stem + "-" + method.lower())
                + "</details>"
            )
        nodes = build_mopt_solution_tree(
            jobs, n_machines=3, solution=reference["flowshop_solution"], max_nodes=35
        )
        plots.append(
            "<details><summary>Drzewo MOpt — pełny rozmiar po kliknięciu</summary>"
            + image(build_mopt_tree_figure(nodes), stem + "-tree", tree=True)
            + "<p>Zielone: ścieżka najlepszego planu; żółte: sprawdzone alternatywy; czerwone: odcięcia. "
            "Widok zawiera do 35 węzłów i zachowuje całą najlepszą ścieżkę. "
            "Ścieżka startowa może być odtworzonym planem początkowym, co opisują węzły. "
            "Pełne wyszukiwanie nie jest ograniczone rozmiarem rysunku.</p></details>"
        )
        if "limited_mopt" in evidence:
            plots.append(
                "<details><summary>Drzewo MOpt po 100 stanach</summary>"
                f"<a href='{stem}-limited-tree.svg'><img loading='lazy' src='{stem}-limited-tree.png' "
                "alt='Drzewo przerwanego wyszukiwania'></a><p>Optimum niepotwierdzone.</p></details>"
            )
        risk_text = ""
        validation = after["ROBUST_MC"]["risk_validation_summary"]
        if validation.get("available"):
            low, high = validation["mean_lateness_ci95_min"]
            training = after["ROBUST_MC"]["risk_summary"]
            risk_text = (
                f"<p>Robust: wybór na 1000 realizacjach (42), średnie STO {training['mean_lateness_min']:.2f} min. "
                f"Weryfikacja na osobnych 1000 (43): średnie STO {validation['mean_lateness_min']:.2f} min, "
                f"P90 {validation['p90_lateness_min']:.2f} min. Przybliżony przedział 95% dla średniej: "
                f"{low:.2f}–{high:.2f} min. Nie jest to przedział pojedynczej realizacji.</p>"
            )
        source_html = html.escape(str(source.relative_to(ROOT)))
        sections.append(
            f"<section id='{stem}'><h2>{html.escape(title)}</h2>{paragraphs}"
            "<div class='table'><table><thead><tr><th>Metoda / wersja</th><th>STO [min]</th>"
            "<th>Odpad [kg]</th><th>Koniec [min]</th><th>Czas [s]</th><th>Status</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table></div>"
            + risk_text
            + "".join(plots)
            + f"<details><summary>Dane i odtwarzanie</summary><p>{source_html}; {html.escape(origin)}.</p>"
            f"<p>MOpt: {reference['search_states']} stanów, {reference['search_pruned']} odcięć; "
            f"{html.escape(reference['search_status'])}. Łączne obliczenie siedmiu metod: {total_time:.3f} s.</p>"
            "<p><a href='wyniki.json'>Wyniki z kolejnościami, operacjami i parametrami</a></p></details></section>"
        )
        markdown += [
            f"## {title}",
            "",
            *conclusions,
            "",
            f"Dane: `{source_html}`; {origin}.",
            "",
            "| Metoda | STO przed → po [min] | Odpad przed → po [kg] |",
            "|---|---:|---:|",
        ]
        for method in EXTRA:
            markdown.append(
                f"| {NAMES[method]} | {before[method]['sto']:.2f} → {after[method]['sto']:.2f} | "
                f"{before[method]['total_waste_kg']:.2f} → {after[method]['total_waste_kg']:.2f} |"
            )
        markdown += [
            "",
            f"MOpt: {reference['search_status']}; STO {reference['sto']:.2f} min.",
            "",
            f"![Gantt MOpt]({stem}-mopt.png)",
            "",
            f"[Drzewo SVG]({stem}-tree.svg)",
            "",
        ]
        cases.append(
            {
                "id": stem,
                "title": title,
                "source": str(source.relative_to(ROOT)),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "origin": origin,
                "findings": conclusions,
                "before": {k: saved_result(v) for k, v in before.items()},
                "after": {k: saved_result(v) for k, v in after.items()},
                "evidence": evidence,
            }
        )
        print(
            json.dumps(
                {
                    "case": stem,
                    "before_after": {m: [before[m]["sto"], after[m]["sto"]] for m in EXTRA},
                    "mopt": reference["sto"],
                    "status": reference["optimality_status"],
                }
            ),
            flush=True,
        )
    methods = (
        "Model: permutacyjny przepływ M1 → M2 → M3, bufory pośrednie, brak wyprzedzania. "
        "Przezbrojenie po dostarczeniu zlecenia na etap; gotowość komponentów blokuje start M1. "
        "Ocena leksykograficzna: niezaplanowane zlecenia, suma dodatnich opóźnień po M3 (STO), odpad, koniec produkcji. "
        "Przed: odtworzenie poprzednich dwóch przebiegów na tych samych nowych danych; po: obecny silnik. "
        "Nowy refiner: trzy wybrane starty, wstawianie i zamiana, do 3000 różnych ocen na metodę. "
        "Robust zachowuje poprzednie wyniki ECO/Component obok nowych, bo poprawa nominalna nie musi poprawiać ryzyka. "
        "Ocenia ograniczony zbiór kandydatów: średnie STO + 0.5 × max(0, P90 STO − średnie STO), "
        "potem odpad i analogiczna miara końca. Nie przeszukuje wszystkich permutacji. "
        "Serie wyboru i weryfikacji używają ziaren 42 i 43; weryfikacja nie zmienia zwycięzcy. "
        "Profile syntetyczne: MTBF 80 h, MTTR 2 h, ryzyko po przezbrojeniu 3%, okno 2 h, postój 1 h; "
        "zmienność napraw 0.35. Przedziały średniej: średnia ± 1.96 × błąd standardowy. "
        "Weryfikacja symulacji nie stanowi walidacji modelu rzeczywistej fabryki. "
        "MOpt: limit 10 s / 100000 stanów, poza jawnym eksperymentem 100 stanów. "
        "Status PARTIAL_PLAN oznacza plan niepełny, OPTIMAL_CONFIRMED — potwierdzone optimum, "
        "GAP_TO_OPTIMUM — gorszą wartość całego celu, RISK_ASSESSED — ocenę symulacyjną. "
        "Czasy dotyczą pojedynczych obliczeń silnika w tym środowisku, bez renderowania, i nie są benchmarkiem sprzętu."
    )
    markdown += [
        "## Metoda i ograniczenia",
        "",
        methods,
        "",
        "Odtworzenie: `.venv/Scripts/python.exe scripts/generate_esm_examples.py`, "
        "następnie `.venv/Scripts/python.exe scripts/report_engineering_methods.py`.",
    ]
    (OUTPUT / "raport.md").write_text("\n".join(markdown), encoding="utf-8")
    (OUTPUT / "wyniki.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "machines": 3,
                "jobs_per_case": 10,
                "python": platform.python_version(),
                "source_code_sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                    for name in [
                        "src/AOA/core/engineering_methods.py",
                        "src/AOA/core/flowshop.py",
                        "src/AOA/core/esm_project.py",
                        "src/AOA/core/monte_carlo.py",
                        "src/AOA/gui/engineering_charts.py",
                        "scripts/generate_esm_examples.py",
                        "scripts/report_engineering_methods.py",
                    ]
                },
                "methodology": methods,
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with (OUTPUT / "wyniki.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_records[0]))
        writer.writeheader()
        writer.writerows(all_records)
    nav = " · ".join(
        f"<a href='#{stem}'>{html.escape(title)}</a>" for stem, title, _ in THESIS_CASES
    )
    page = (
        "<!doctype html><html lang='pl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Kiedy harmonogram optymalny nie wystarcza — osiem studiów przypadku</title><style>"
        "*{box-sizing:border-box}body{margin:0;background:#eef3f8;color:#17324b;font:16px/1.65 system-ui,sans-serif}"
        "main{max-width:1250px;margin:auto;padding:26px 20px}header{background:#102c43;color:white;padding:26px;border-radius:12px}"
        "h1{font-size:28px;line-height:1.3}h2{font-size:23px}section{background:white;padding:22px;margin:24px 0;border-radius:12px}"
        "table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;text-align:left;border-bottom:1px solid #dbe6ee}"
        "th{background:#edf7f6}.table{overflow:auto}img{max-width:100%;height:auto;display:block;margin:16px auto}"
        "a{color:#08796f}summary{cursor:pointer;color:#08796f;font-weight:600}details{margin:14px 0}nav{padding:18px 0}"
        "@media(max-width:650px){main{padding:10px}header,section{padding:14px}h1{font-size:24px}td,th{padding:5px}}"
        "</style><main><header><h1>Kiedy harmonogram optymalny nie wystarcza</h1>"
        "<p>Osiem syntetycznych studiów przypadku do pracy inżynierskiej · 3 maszyny × 10 zleceń</p></header>"
        "<p>MOpt z potwierdzonym optimum rozstrzyga zadany cel deterministyczny. Limit wyszukiwania, "
        "odpad, awarie i niekompletny plan wymagają osobnej interpretacji wyniku. "
        "Ulepszone ECO i Component osiągają optimum w przykładach pułapki przezbrojeń i dostaw; "
        "pozostałe przypadki pokazują także granice tych metod.</p>"
        f"<p><a href='wyniki.csv'>Tabela CSV</a> · <a href='wyniki.json'>Pełne dane wynikowe</a> · "
        f"<a href='raport.md'>Raport tekstowy</a></p><nav>{nav}</nav>"
        + "".join(sections)
        + f"<section><h2>Metoda i ograniczenia</h2><p>{html.escape(methods)}</p>"
        "<p>Odtwarzanie: generator przykładów, potem scripts/report_engineering_methods.py. "
        "Plik JSON zawiera wyniki operacji i sumy kontrolne źródłowych CSV.</p></section></main></html>"
    )
    (OUTPUT / "raport.html").write_text(page, encoding="utf-8")
    print(OUTPUT / "raport.html", flush=True)


if __name__ == "__main__":
    main()
