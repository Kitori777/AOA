"""Generate the local, inspectable ESM report and vector/raster chart previews."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg

from AOA.core.esm_project import (
    build_mopt_solution_tree,
    evaluate_esm_methods,
    list_esm_scenarios,
    load_esm_jobs,
)
from AOA.gui.engineering_charts import build_esm_gantt_figure, build_mopt_tree_figure

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "engineering"
FEATURED = {
    "esm_paper_01.csv": "Artykuł: przykład 1",
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    sections = []
    markdown = [
        "# Raport ESM: przepływ przez wiele maszyn",
        "",
        "Dane z publikacji dostępnych na liście programu. Czasy dotyczą pojedynczego "
        "uruchomienia silnika w tym środowisku, bez renderowania i startu GUI.",
        "",
        "STO oznacza sumę dodatnich opóźnień po ostatniej maszynie. "
        "Remis rozstrzyga czas zakończenia całej produkcji.",
        "",
    ]
    for scenario in list_esm_scenarios(ROOT / "data" / "esm"):
        jobs = load_esm_jobs(scenario.path)
        if not jobs[0].machine_times:
            continue
        machines = len(jobs[0].machine_times)
        results = evaluate_esm_methods(jobs, ["MT", "MO", "MZO", "MOPT"], n_machines=machines)
        mopt = next(r for r in results if r["method"] == "MOPT")
        solved = mopt["flowshop_solution"]
        title = FEATURED.get(scenario.path.name, scenario.label)
        table = [
            "| Metoda | STO [min] | Koniec [min] | Obliczenia [s] | Status |",
            "|---|---:|---:|---:|---|",
        ]
        html_rows = []
        for result in results:
            proof = (
                "potwierdzone optimum"
                if result["optimality_status"] == "OPTIMAL_CONFIRMED"
                else ("gorszy od optimum" if solved.confirmed else "bez potwierdzenia optimum")
            )
            record = {
                "plik": scenario.path.name,
                "maszyny": machines,
                "zlecenia": len(jobs),
                "metoda": result["method"],
                "sto_min": result["sto"],
                "koniec_min": result["completion_total"],
                "obliczenia_s": result["elapsed_s"],
                "status": proof,
                "kolejnosc": " -> ".join(result["order"]),
                "stany_mopt": solved.visited if result["method"] == "MOPT" else 0,
                "odciecia_mopt": solved.pruned if result["method"] == "MOPT" else 0,
            }
            records.append(record)
            table.append(
                f"| {result['method']} | {result['sto']:g} | {result['completion_total']:g} | "
                f"{result['elapsed_s']:.4f} | {proof} |"
            )
            html_rows.append(
                f"<tr><td>{result['method']}</td><td>{result['sto']:g}</td>"
                f"<td>{result['completion_total']:g}</td><td>{result['elapsed_s']:.4f}</td>"
                f"<td>{proof}</td></tr>"
            )
        markdown += [
            f"## {title}",
            "",
            f"Źródło: `{scenario.path.relative_to(ROOT).as_posix()}`. "
            f"{machines} maszyn, {len(jobs)} zleceń.",
            "",
            *table,
            "",
            f"Kolejność MOpt: {' → '.join(mopt['order'])}.",
            "",
            f"Przejrzano {solved.visited} stanów, odcięto {solved.pruned}; "
            f"poprawy w przeszukiwaniu: {solved.improvements}. "
            f"Status: {mopt['search_status']}.",
            f"STO najlepszej reguły: {mopt['initial_sto']:g} min → po poprawianiu kolejności: "
            f"{mopt['seed_sto']:g} min → wynik MOpt: {mopt['sto']:g} min.",
            "",
        ]
        images = ""
        if scenario.path.name in FEATURED:
            stem = scenario.path.stem
            nodes = build_mopt_solution_tree(
                jobs, n_machines=machines, solution=solved, max_nodes=35
            )
            tree = build_mopt_tree_figure(nodes)
            FigureCanvasAgg(tree)
            tree.savefig(OUTPUT / f"{stem}-tree.svg")
            # Raster preview preserves the native layout; vector report has
            # zoom controls for reading individual nodes at full resolution.
            tree.savefig(OUTPUT / f"{stem}-tree.png", dpi=55)
            gantt = build_esm_gantt_figure(mopt, "MOpt")
            FigureCanvasAgg(gantt)
            gantt.savefig(OUTPUT / f"{stem}-gantt.png", dpi=140)
            gantt.savefig(OUTPUT / f"{stem}-gantt.svg")
            markdown += [
                f"![Gantt MOpt]({stem}-gantt.png)",
                "",
                f"[Drzewo wektorowe: {len(nodes)} widocznych węzłów]({stem}-tree.svg)",
                "",
            ]
            images = (
                f'<img class="gantt" src="{stem}-gantt.svg" alt="Harmonogram MOpt: {html.escape(title)}">'
                "<p>Zielone: najlepsza ścieżka; żółte: sprawdzone; czerwone: odcięte. "
                "LB to dolna granica. Ukryte gałęzie nie oznaczają odcięcia. "
                f"Pokazano {len(nodes)} węzłów; obliczenia obejmowały {solved.visited} stanów.</p>"
                '<div class="controls"><button onclick="zoom(this,1.3)">Powiększ drzewo</button>'
                '<button onclick="zoom(this,1/1.3)">Pomniejsz</button>'
                f'<a href="{stem}-tree.svg">Otwórz pełne SVG</a></div>'
                f'<div class="tree"><img width="1800" src="{stem}-tree.svg" '
                f'alt="Drzewo MOpt: {html.escape(title)}"></div>'
            )
            tree.clear()
            gantt.clear()
        sections.append(
            f"<details {'open' if scenario.path.name == 'esm_flow_10_three_machines.csv' else ''}>"
            f"<summary>{html.escape(title)}</summary><p>{machines} maszyn · {len(jobs)} zleceń · "
            f"{html.escape(scenario.path.name)}</p><table><thead><tr><th>Metoda</th><th>STO [min]</th>"
            "<th>Koniec [min]</th><th>Obliczenia [s]</th><th>Status</th></tr></thead><tbody>"
            + "".join(html_rows)
            + "</tbody></table><p><b>Kolejność MOpt:</b> "
            + html.escape(" → ".join(mopt["order"]))
            + f"</p><p>Stany: {solved.visited} · Odcięcia: {solved.pruned} · "
            f"{html.escape(mopt['search_status'])}</p><p>STO najlepszej reguły: "
            f"{mopt['initial_sto']:g} min → po poprawianiu: {mopt['seed_sto']:g} min "
            f"→ MOpt: {mopt['sto']:g} min.</p>{images}</details>"
        )
        print(
            f"{scenario.path.name}: MOpt={mopt['sto']:g}, {solved.visited} states, "
            f"{solved.elapsed_s:.4f}s, confirmed={solved.confirmed}",
            flush=True,
        )
    (OUTPUT / "wyniki.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (OUTPUT / "wyniki.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (OUTPUT / "raport.md").write_text("\n".join(markdown), encoding="utf-8")
    page = """<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESM — przepływ przez wiele maszyn</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef3f8;color:#12283e;font:16px/1.6 system-ui,sans-serif}
main{max-width:1250px;margin:auto;padding:32px 24px}header{background:#102c43;color:white;padding:26px;border-radius:16px}
h1{margin:0;font-size:30px}header p{color:#cde8ed}details{margin:20px 0;background:white;padding:22px;border-radius:12px;border:1px solid #ccdce5}
summary{font-size:20px;font-weight:700;cursor:pointer}table{width:100%;border-collapse:collapse;margin:18px 0}
td,th{padding:10px 12px;text-align:left;border-bottom:1px solid #dde6ed}th{background:#edf6f6}td:nth-child(2){font-weight:700;color:#08776e}
.gantt{width:100%;margin:16px 0}.tree{overflow:auto;max-height:800px;border:1px solid #d9e2ed;background:#f8fafc}
.tree img{max-width:none;display:block}.controls{display:flex;gap:12px;align-items:center;margin:12px 0;flex-wrap:wrap}
button{background:#087b72;color:white;border:0;border-radius:8px;padding:10px 16px;cursor:pointer;font:inherit}a{color:#086b79}
@media(max-width:700px){main{padding:12px}details{padding:12px}table{font-size:12px}td,th{padding:5px}}
</style><main><header><h1>ESM: 3 maszyny · 10 zleceń</h1>
<p>Porównanie MT, MO, MZO i MOpt. Każde zlecenie przechodzi przez wszystkie maszyny.
Cel: minimalna suma dodatnich opóźnień po ostatniej operacji, następnie czas zakończenia produkcji.</p></header>
<p>Raport z rzeczywistych obliczeń. Dane syntetyczne poza czterema przykładami MPER 2017-0026.
Czasy dotyczą pojedynczego uruchomienia silnika w tym środowisku, bez renderowania i startu GUI.
Kliknij nazwę przykładu, aby rozwinąć wyniki. Drzewa można powiększać i przewijać.</p>
<p><a href="wyniki.csv">Pełne wyniki CSV</a> · <a href="wyniki.json">Wyniki JSON</a> · <a href="raport.md">Raport tekstowy</a></p>
"""
    page += "".join(sections)
    page += """<p>Model: wspólna kolejność na wszystkich maszynach, czekanie między etapami,
bez blokowania poprzedniej maszyny. Limit MOpt: 10 s / 100 000 stanów. Status potwierdzenia
wynika z ukończenia przeglądu z poprawnymi granicami. Solver nie wylicza wszystkich remisów.</p>
</main><script>
function zoom(button,factor){const box=button.parentElement.nextElementSibling,image=box.querySelector('img');
const center=(box.scrollLeft+box.clientWidth/2)/image.width;
image.width=Math.min(16000,Math.max(600,image.width*factor));
box.scrollLeft=center*image.width-box.clientWidth/2;}
function centerTree(section){const box=section.querySelector('.tree');if(box&&!box.dataset.centered){
const image=box.querySelector('img');if(!image.complete){image.addEventListener('load',()=>centerTree(section),{once:true});return;}
requestAnimationFrame(()=>{box.scrollLeft=Math.max(0,(image.width-box.clientWidth)/2);box.dataset.centered='1';});}}
document.querySelectorAll('details').forEach(section=>{section.addEventListener('toggle',()=>{
if(section.open)centerTree(section);});if(section.open)centerTree(section);});
</script></html>"""
    (OUTPUT / "raport.html").write_text(page, encoding="utf-8")
    print(OUTPUT / "raport.html")


if __name__ == "__main__":
    main()
