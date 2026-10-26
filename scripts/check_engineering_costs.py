"""Native button-driven cost checks and reproducible example exports."""

from __future__ import annotations

import csv
import json
import time
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk

import AOA.gui.pages.engineering_mode_page as module
from AOA.config import DATA_DIR
from AOA.core.esm_costs import OBJECTIVES, cost_parameters
from AOA.gui.pages.engineering_mode_page import EngineeringModePage
from AOA.gui.pages.theory_page import TheoryPage


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "output" / "engineering-costs"
    output.mkdir(parents=True, exist_ok=True)
    before = {
        p: sha256(p.read_bytes()).hexdigest() for p in (DATA_DIR / "esm").rglob("*") if p.is_file()
    }
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
        assert page.machine_var.get() == "3" and page.objective_code() == "sto"
        page.machine_var.set("1")
        page._machine_changed("1")
        page.objective_var.set(OBJECTIVES["cost"])
        page._objective_changed("")
        page.cost_button.invoke()
        editor = page.cost_editor
        assert editor is not None
        editor.withdraw()
        original_parameters = cost_parameters(page.jobs)
        editor.entries["Z3"][0].set("-1")
        editor.apply_button.invoke()
        assert editor.winfo_exists() and cost_parameters(page.jobs) == original_parameters
        editor.entries["Z3"][0].set("10")
        for _rate, grace in editor.entries.values():
            grace.set("10")
        editor.apply_button.invoke()
        assert not editor.winfo_exists()
        assert cost_parameters(page.jobs)["Z3"] == {"rate_per_min": 10, "grace_min": 10}
        page.preset_buttons["all"].invoke()
        with patch.object(module, "GanttComparisonWindow", capture):
            page.gantt_button.invoke()
            wait(lambda: bool(windows))
        assert len(page.results) == 7 and len(windows[0].figures) == 2
        mopt = next(r for r in page.results if r["method"] == "MOPT")
        assert (mopt["total_tardiness_cost"], mopt["sto"]) == (110, 130)
        assert mopt["order"] == ["Z2", "Z3", "Z1", "Z4"]
        robust = next(r for r in page.results if r["method"] == "ROBUST_MC")
        assert robust["risk_validation_summary"]["seed"] == 43
        assert "p90_tardiness_cost" in robust["risk_validation_summary"]
        for iid, result in page.result_by_iid.items():
            if result["method"] == "MOPT":
                page.result_tree.selection_set(iid)
        page.copy_result_description()
        assert (
            "110 j.p." in root.clipboard_get() and "Z3: 10 j.p./min, 10 min" in root.clipboard_get()
        )
        for kind in ("comparison", "operations"):
            destination = output / f"{kind}.csv"
            with patch.object(
                module.filedialog, "asksaveasfilename", return_value=str(destination)
            ):
                page.export_results(kind)
            with destination.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            assert all(row["kryterium"] == "cost" for row in rows)
            assert all(
                json.loads(row["parametry_kosztow_json"])["Z3"]["rate_per_min"] == 10
                for row in rows
            )
        with patch("AOA.gui.gantt_window.filedialog.askdirectory", return_value=str(output)):
            windows[0].export_button.invoke()
        captured = []

        def tree_capture(_title, figure, _note):
            captured.append(figure)
            figure.savefig(output / "tree-cost.png", dpi=130)
            figure.savefig(output / "tree-cost.svg")

        with patch.object(page, "_show_figure", tree_capture):
            page.show_mopt_tree()
        assert captured
        # In-memory overrides must survive handing off a scalar source CSV to Theory.
        theory = TheoryPage(root)
        theory.pack(fill="both", expand=True)
        with (
            patch.object(
                root, "pages", {"EngineeringModePage": page, "TheoryPage": theory}, create=True
            ),
            patch.object(root, "show", create=True),
        ):
            page.show_theory_gantts()
        comparison = theory.esm_comparison
        wait(lambda: bool(comparison.results))
        theory_mopt = next(r for r in comparison.results if r["method"] == "MOPT")
        assert theory_mopt["total_tardiness_cost"] == 110
        assert cost_parameters(comparison.jobs) == cost_parameters(page.jobs)
        # A stale editor may not apply its values to another source or settings.
        page.cost_button.invoke()
        stale = page.cost_editor
        stale.withdraw()
        page.path_var.set(
            str(
                DATA_DIR
                / "esm"
                / "article"
                / "costs"
                / "ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv"
            )
        )
        page.load_selected_data()
        assert page.objective_code() == "cost" and page.machine_var.get() == "1"
        stale.apply_button.invoke()
        assert stale.winfo_exists() and "Zmieniono" in stale.status.get()
        stale.destroy()
        page.objective_var.set(OBJECTIVES["sto"])
        page._objective_changed("")
        assert not page.results and all(
            button.cget("state") == "disabled" for button in page.export_buttons
        )
        page.run_button.invoke()
        wait(lambda: bool(page.results))
        time_mopt = next(r for r in page.results if r["method"] == "MOPT")
        assert (time_mopt["sto"], time_mopt["total_tardiness_cost"]) == (80, 600)
        page.path_var.set(
            str(
                DATA_DIR
                / "esm"
                / "article"
                / "costs"
                / "DYLEWSKI_2_maszyny/Przyklad_1/DYLEWSKI_Przyklad_1_W3_koszt_16.csv"
            )
        )
        page.load_selected_data()
        assert page.objective_code() == "cost" and page.machine_var.get() == "2"
        assert page.time_mode_code() == "file"
        page.machine_var.set("3")
        page._machine_changed("3")
        page.run_button.invoke()
        wait(lambda: bool(page.results))
        assert all(len(result["steps"]) == 9 for result in page.results)
        assert all(result["cost_parameters"]["Z3"]["rate_per_min"] == 2 for result in page.results)
        assert {p: sha256(p.read_bytes()).hexdigest() for p in before} == before
        assert not errors, errors
        (output / "verification.json").write_text(
            json.dumps(
                {
                    "source_data_unchanged": len(before),
                    "native_gui": "passed",
                    "methods": 7,
                    "scalar_source_with_in_memory_overrides": {
                        "cost": 110,
                        "sto": 130,
                        "order": mopt["order"],
                    },
                    "sto_mode": {"cost": 600, "sto": 80},
                    "risk_validation_seed": 43,
                    "editor_atomic_validation": True,
                    "stale_editor_rejected": True,
                    "theory_preserves_overrides": True,
                    "csv_export_preserves_parameters": True,
                    "callbacks_errors": 0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "ENGINEERING_COST_GUI_OK editor=OK memory_overrides=OK cost=110 sto=130 time_mode_sto=80_cost=600 theory=110 exports=OK MC_seed=43 csv_unchanged=OK",
            flush=True,
        )
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
