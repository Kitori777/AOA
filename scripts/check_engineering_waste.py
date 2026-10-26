"""Button-driven waste objective check, exports and a reproducible 3 x 10 report."""

from __future__ import annotations

import csv
import json
import time
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk

import AOA.gui.pages.engineering_mode_page as module
from AOA.config import BASE_DIR, DATA_DIR
from AOA.core.esm_costs import OBJECTIVES
from AOA.core.esm_project import evaluate_esm_methods
from AOA.gui.pages.engineering_mode_page import EngineeringModePage
from AOA.gui.pages.theory_page import TheoryPage


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "output/engineering-waste"
    output.mkdir(parents=True, exist_ok=True)
    before = {
        p: sha256(p.read_bytes()).hexdigest() for p in (DATA_DIR / "esm").rglob("*") if p.is_file()
    }
    source = BASE_DIR / "tests/fixtures/esm/esm_jobs_10_mixed_constraints.csv"
    root = ctk.CTk()
    root.withdraw()
    errors = []
    root.report_callback_exception = lambda *error: errors.append(error)
    page = EngineeringModePage(root)
    page.pack(fill="both", expand=True)
    deadline = time.monotonic() + 180
    windows = []
    original = module.GanttComparisonWindow

    def capture(parent, results):
        window = original(parent, results)
        window.withdraw()
        windows.append(window)
        return window

    def wait(predicate):
        while not predicate():
            assert time.monotonic() < deadline, (page.status_var.get(), errors)
            root.update()
            time.sleep(0.01)
        root.update_idletasks()

    try:
        wait(lambda: bool(page.jobs))
        assert page.objective_code() == "sto" and page.machine_var.get() == "3"
        page.path_var.set(str(source))
        page.load_selected_data()
        assert len(page.jobs) == 10 and page.machine_var.get() == "3"
        baseline = evaluate_esm_methods(page.jobs, ["ECO_WASTE"], n_machines=3)[0]
        page.objective_var.set(OBJECTIVES["waste"])
        page._objective_changed("")
        page.preset_buttons["all"].invoke()
        with patch.object(module, "GanttComparisonWindow", capture):
            page.gantt_button.invoke()
            wait(lambda: bool(windows))
        assert len(page.results) == 7 and len(windows[0].figures) == 2
        assert all(r["objective"] == "waste" for r in page.results)
        eco = next(r for r in page.results if r["method"] == "ECO_WASTE")
        mopt = next(r for r in page.results if r["method"] == "MOPT")
        robust = next(r for r in page.results if r["method"] == "ROBUST_MC")
        assert eco["total_waste_kg"] < baseline["total_waste_kg"]
        assert mopt["optimality_status"] == "OPTIMAL_CONFIRMED"
        assert robust["risk_validation_summary"]["seed"] == 43
        for figure in windows[0].figures:
            assert OBJECTIVES["waste"] in figure._suptitle.get_text()
            assert all("odpad =" in ax.get_title() for ax in figure.axes if ax.axison)
        with patch("AOA.gui.gantt_window.filedialog.askdirectory", return_value=str(output)):
            windows[0].export_button.invoke()
        for index, figure in enumerate(windows[0].figures, 1):
            figure.savefig(output / f"gantt-{index}.png", dpi=130)

        def tree_capture(_title, figure, note):
            assert "Minimalizacja odpadu" in note
            figure.savefig(output / "tree-waste.png", dpi=130)
            figure.savefig(output / "tree-waste.svg")

        with patch.object(page, "_show_figure", tree_capture):
            page.show_mopt_tree()
        for iid, result in page.result_by_iid.items():
            if result["method"] == "ECO_WASTE":
                page.result_tree.selection_set(iid)
        page.copy_result_description()
        assert "Minimalizacja odpadu [kg]" in root.clipboard_get()
        for kind in ("comparison", "operations"):
            destination = output / f"{kind}.csv"
            with patch.object(
                module.filedialog, "asksaveasfilename", return_value=str(destination)
            ):
                page.export_results(kind)
            with destination.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            assert rows and all(row["kryterium"] == "waste" for row in rows)

        theory = TheoryPage(root)
        theory.pack(fill="both", expand=True)
        with (
            patch.object(
                root, "pages", {"EngineeringModePage": page, "TheoryPage": theory}, create=True
            ),
            patch.object(root, "show", create=True),
        ):
            page.show_theory_gantts()
        wait(lambda: bool(theory.esm_comparison.results))
        theory_mopt = next(r for r in theory.esm_comparison.results if r["method"] == "MOPT")
        assert theory_mopt["objective"] == "waste"
        assert theory_mopt["total_waste_kg"] == mopt["total_waste_kg"]
        page.objective_var.set(OBJECTIVES["sto"])
        page._objective_changed("")
        assert not page.results and all(
            button.cget("state") == "disabled" for button in page.export_buttons
        )
        assert {p: sha256(p.read_bytes()).hexdigest() for p in before} == before
        assert not errors, errors

        results = windows[0].results
        fields = (
            "method",
            "objective",
            "order",
            "sto",
            "total_waste_kg",
            "total_tardiness_cost",
            "completion_total",
            "elapsed_s",
            "optimality_status",
            "search_states",
            "lower_bound",
        )
        verification = {
            "native_gui": "passed",
            "methods": 7,
            "gantt_pages": 2,
            "callbacks_errors": 0,
            "unchanged_data_files": len(before),
            "risk_validation_seed": 43,
            "theory_criterion_preserved": True,
            "stale_results_invalidated": True,
            "baseline_eco_sto": {key: baseline[key] for key in fields if key in baseline},
            "results": [{key: r[key] for key in fields if key in r} for r in results],
        }
        (output / "verification.json").write_text(
            json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        reduction = 100 * (1 - eco["total_waste_kg"] / baseline["total_waste_kg"])
        lines = [
            "# Minimalizacja odpadu — 3 maszyny i 10 zleceń",
            "",
            f"Źródło: `{source.name}`. Dane wejściowe pozostały bez zmian ({len(before)} pliki).",
            "",
            "W sekcji **Co chcesz minimalizować?** wybierz **Odpad**, zaznacz ECO Waste i uruchom obliczenia.",
            "",
            f"ECO: {baseline['total_waste_kg']:g} → {eco['total_waste_kg']:g} kg (−{reduction:.0f}%). "
            f"STO: {baseline['sto']:g} → {eco['sto']:g} min. To zamierzony kompromis: odpad ma pierwszeństwo.",
            "",
            f"MOpt potwierdził minimum {mopt['total_waste_kg']:g} kg; przy tym odpadzie znalazł STO {mopt['sto']:g} min. "
            f"ECO ma STO {eco['sto']:g} min, więc nie osiąga pełnego optimum kryterium z rozstrzyganiem remisów.",
            "",
            "| Metoda | Odpad [kg] | STO [min] | Koniec [min] | Obliczenia [s] | Status |",
            "|---|---:|---:|---:|---:|---|",
        ]
        lines.extend(
            f"| {r['method']} | {r['total_waste_kg']:g} | {r['sto']:g} | {r['completion_total']:g} | {r['elapsed_s']:.3f} | {r['optimality_status']} |"
            for r in results
        )
        lines.extend(
            [
                "",
                "![Gantty metod podstawowych](gantt-1.png)",
                "",
                "![Gantty ECO, Component i Robust](gantt-2.png)",
                "",
                "![Drzewo MOpt](tree-waste.png)",
                "",
                "Odpad bazowy i odpad zmiany materiału/kształtu naliczamy raz na zlecenie. "
                "Brak początkowego stanu linii oznacza zerowy odpad przezbrojenia przed pierwszym zleceniem. "
                "Zlecenia zablokowane nie są wykonywane i nie wnoszą odpadu.",
                "",
                "Robust zachowuje deterministyczny odpad; ryzyko opóźnień rozstrzyga remis. "
                "Awarie w tym modelu zatrzymują i wznawiają pracę, bez dodatkowych braków materiałowych. "
                "Jego wynik nie jest dowodem optimum probabilistycznego.",
                "",
                "Test natywnego GUI obejmuje przycisk Gantta (dwie strony 2×2), eksport CSV/PNG/SVG, "
                "przekazanie kryterium do Theory i unieważnienie wyników po zmianie celu. "
                "Szczegóły i czasy: [verification.json](verification.json).",
            ]
        )
        (output / "raport.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(
            f"ENGINEERING_WASTE_GUI_OK eco={eco['total_waste_kg']:g}kg baseline={baseline['total_waste_kg']:g}kg mopt={mopt['total_waste_kg']:g}kg proof=OK pages=2 theory=OK exports=OK data={len(before)}_unchanged",
            flush=True,
        )
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
