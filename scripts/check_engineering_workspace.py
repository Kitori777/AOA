"""Hidden native checks of button-driven ESM flow and Theory's 2 x 2 comparison."""

from __future__ import annotations

import csv
import time
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk
from PIL import Image

import AOA.gui.pages.engineering_mode_page as engineering_module
from AOA.config import DATA_DIR
from AOA.core.esm_project import ESM_TIME_MODES
from AOA.gui.pages.engineering_mode_page import EngineeringModePage
from AOA.gui.pages.theory_page import TheoryPage


def main() -> None:
    csv_before = {path: path.read_bytes() for path in (DATA_DIR / "esm").rglob("*.csv")}
    output = Path(__file__).resolve().parents[1] / "output" / "engineering-grid"
    output.mkdir(parents=True, exist_ok=True)
    qol_output = output.parent / "engineering-qol"
    qol_output.mkdir(parents=True, exist_ok=True)
    root = ctk.CTk()
    root.withdraw()
    page = EngineeringModePage(root)
    page.pack(fill="both", expand=True)
    deadline = time.monotonic() + 180
    callback_errors = []
    root.report_callback_exception = lambda *error: callback_errors.append(error)
    captured = []
    original_grid = engineering_module.GanttComparisonWindow
    gantt_windows = []

    def capture_grid(parent, results):
        window = original_grid(parent, results)
        window.withdraw()
        gantt_windows.append(window)
        return window

    grid_patch = patch.object(engineering_module, "GanttComparisonWindow", capture_grid)
    grid_patch.start()
    original_show = page._show_figure

    def capture(title, figure, note):
        captured.append(figure)
        original_show(title, figure, note)
        for widget in page.winfo_children():
            if isinstance(widget, ctk.CTkToplevel):
                widget.withdraw()

    chart_patch = patch.object(page, "_show_figure", capture)
    chart_patch.start()

    def wait_until(predicate):
        while not predicate():
            assert time.monotonic() < deadline, "GUI smoke timeout"
            root.update()
            time.sleep(0.01)
        root.update_idletasks()

    try:
        wait_until(lambda: bool(page.jobs))
        assert len(page.jobs) == 4 and page.machine_var.get() == "3"
        assert Path(page.path_var.get()).name == "esm_jobs.csv"
        assert not page.results
        page.preset_buttons["extra"].invoke()
        assert sum(variable.get() for variable in page.method_vars.values()) == 3
        page.preset_buttons["all"].invoke()
        assert all(variable.get() for variable in page.method_vars.values())
        page.preset_buttons["basic"].invoke()
        assert sum(variable.get() for variable in page.method_vars.values()) == 4
        page.gantt_button.invoke()  # The actual button callback must calculate, then open.
        assert page.run_button.cget("state") == "disabled"
        assert page.progress.winfo_manager() == "grid" and "0.0 s" in page.activity_var.get()
        wait_until(lambda: len(gantt_windows) == 1)
        assert all(len(r["steps"]) == 12 for r in page.results)
        assert all(r["model"] == "flowshop" for r in page.results)
        assert page.run_button.cget("state") == "normal"
        assert page.progress.winfo_manager() == ""
        assert all(button.cget("state") == "normal" for button in page.export_buttons)
        assert "esm_jobs.csv" in page.context_var.get()
        page.export_buttons[2].invoke()
        assert "STO:" in root.clipboard_get() and "Maszyny: 3" in root.clipboard_get()
        for kind, index in (("comparison", 0), ("operations", 1)):
            path = qol_output / f"{kind}.csv"
            with patch.object(
                engineering_module.filedialog, "asksaveasfilename", return_value=str(path)
            ):
                page.export_buttons[index].invoke()
            with path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            assert len(rows) == (4 if kind == "comparison" else 48)
            assert all(
                row["liczba_maszyn"] == "3" and row["interpretacja_czasu"] == "total"
                for row in rows
            )
        with patch.object(engineering_module.filedialog, "asksaveasfilename", return_value=""):
            page.export_results("comparison")
        with (
            patch.object(
                engineering_module.filedialog, "asksaveasfilename", return_value=page.path_var.get()
            ),
            patch.object(engineering_module.messagebox, "showerror") as blocked,
        ):
            page.export_results("comparison")
            blocked.assert_called_once()
        assert [t.get_text() for t in gantt_windows[0].figures[0].axes[0].get_yticklabels()] == [
            "M1",
            "M2",
            "M3",
        ]
        page.show_mopt_tree()
        assert len(captured) == 1
        assert len(gantt_windows[0].figures) == 1
        assert sum(axis.axison for axis in gantt_windows[0].figures[0].axes) == 4
        # The real top-level canvas must fill a maximized-size window.
        first_window = gantt_windows[0]
        first_window.deiconify()
        first_window.geometry("1920x1000+0+0")
        wait_until(lambda: first_window.canvases[0].get_tk_widget().winfo_width() > 1800)
        canvas_widget = first_window.canvases[0].get_tk_widget()
        wait_until(
            lambda: abs(first_window.figures[0].bbox.width - canvas_widget.winfo_width()) < 2
        )
        assert canvas_widget.winfo_height() > 750
        first_window._layout(0)
        first_window.figures[0].savefig(output / "main-button-four-methods.png", dpi=100)
        first_window.figures[0].savefig(output / "main-button-four-methods.svg")
        first_window.withdraw()
        # Changing checkboxes after computing four methods must compute the missing three.
        for variable in page.method_vars.values():
            variable.set(True)
        previous_windows = len(gantt_windows)
        page.gantt_button.invoke()
        wait_until(lambda: len(gantt_windows) == previous_windows + 1)
        all_window = gantt_windows[-1]
        assert len(all_window.results) == 7 and len(all_window.figures) == 2
        assert [sum(axis.axison for axis in figure.axes) for figure in all_window.figures] == [4, 3]
        assert all_window.figures[0].axes[0].get_xlim() == all_window.figures[1].axes[0].get_xlim()
        all_window.tabs.set("Metody 5-7")
        all_window.deiconify()
        all_window.geometry("1920x1000+0+0")
        wait_until(lambda: all_window.canvases[1].get_tk_widget().winfo_width() > 1800)
        all_window._layout(1)
        all_window.figures[1].savefig(output / "main-button-seven-methods-page2.png", dpi=100)
        all_window.figures[1].savefig(output / "main-button-seven-methods-page2.svg")
        all_window.withdraw()
        with patch("AOA.gui.gantt_window.filedialog.askdirectory", return_value=str(qol_output)):
            all_window.export_button.invoke()
        bundles = list(qol_output.glob("esm_gantty_*"))
        latest = max(bundles)
        assert len(list(latest.glob("*.png"))) == len(list(latest.glob("*.svg"))) == 2
        with (
            Image.open(latest / "gantty_01.png") as first,
            Image.open(latest / "gantty_02.png") as second,
        ):
            assert first.size == second.size
        assert all(path.stat().st_size > 1000 for path in latest.iterdir())
        before_failure = set(qol_output.iterdir())
        with (
            patch("AOA.gui.gantt_window.filedialog.askdirectory", return_value=str(qol_output)),
            patch.object(all_window.figures[1], "savefig", side_effect=OSError("render test")),
            patch("AOA.gui.gantt_window.messagebox.showerror") as export_error,
        ):
            all_window.export_all()
            export_error.assert_called_once()
        assert set(qol_output.iterdir()) == before_failure
        assert all_window.export_button.cget("state") == "normal"
        with patch("AOA.gui.gantt_window.filedialog.askdirectory", return_value=""):
            all_window.export_all()
        assert set(qol_output.iterdir()) == before_failure
        for name, variable in page.method_vars.items():
            variable.set(name in {"MT", "MO", "MZO", "MOPT"})
        for count in (1, 2, 3):
            page.machine_var.set(str(count))
            page._machine_changed(str(count))
            assert not page.results
            previous = len(gantt_windows)
            page.gantt_button.invoke()
            wait_until(lambda previous=previous: len(gantt_windows) == previous + 1)
            assert all(len(r["steps"]) == 4 * count for r in page.results)
            if count == 1:
                assert next(r for r in page.results if r["method"] == "MOPT")["sto"] == 80
        for mode in ("total", "per_machine"):
            page.time_mode_var.set(ESM_TIME_MODES[mode])
            page._time_mode_changed(ESM_TIME_MODES[mode])
            assert page.time_mode_code() == mode
            page.gantt_button.invoke()
            wait_until(lambda: bool(page.results))
            assert all(result["time_mode"] == mode for result in page.results)
            duration = next(
                s["processing_time"] for s in page.results[0]["steps"] if s["job_id"] == "Z3"
            )
            assert abs(duration - (100 / 3 if mode == "total" else 100)) < 1e-8
        # A typed path must not silently reuse loaded jobs or old exports.
        page.path_var.set(str(DATA_DIR / "esm" / "article" / "esm_paper_03.csv"))
        assert not page.results and not page.jobs and page._source_dirty
        page.run_analysis()
        assert page._future is None and "Wczytaj" in page.status_var.get()
        assert all(button.cget("state") == "disabled" for button in page.export_buttons)
        with patch.object(engineering_module.messagebox, "showerror") as stale_export:
            page.copy_result_description()
            stale_export.assert_called_once()
        page.path_var.set(str(DATA_DIR / "esm" / "esm_jobs.csv"))
        page.load_selected_data()
        # Controlled failures test the worker/UI state without changing the solver.
        failed = Future()
        failed.set_exception(ValueError("worker test"))
        with (
            patch.object(page._executor, "submit", return_value=failed),
            patch.object(engineering_module.messagebox, "showerror") as worker_error,
        ):
            page.run_analysis()
            wait_until(lambda: page._future is None)
            worker_error.assert_called_once()
        assert page.run_button.cget("state") == "normal" and not page.results
        assert page.progress.winfo_manager() == ""
        # A changed file must invalidate work already running.
        page.run_analysis()
        page.path_var.set(str(DATA_DIR / "esm" / "article" / "esm_paper_03.csv"))
        page.load_selected_data()
        wait_until(lambda: page._future is None)
        assert not page.results and "Pominieto" in page.status_var.get()
        assert page.time_mode_code() == "file" and page.machine_var.get() == "2"
        page.run_analysis()
        wait_until(lambda: bool(page.results))
        assert page.results[0]["sto"] == 1
        # Explicit examples can also switch to more machines without changing the CSV.
        page.machine_var.set("8")
        page._machine_changed("8")
        assert page.time_mode_code() == "total"
        page.run_analysis()
        wait_until(lambda: bool(page.results))
        assert all(len(r["steps"]) == 24 for r in page.results)
        page.path_var.set(
            str(
                Path(__file__).resolve().parents[1]
                / "tests/fixtures/esm/esm_flow_10_eco_components.csv"
            )
        )
        page.load_selected_data()
        for name, variable in page.method_vars.items():
            variable.set(name in {"ECO_WASTE", "COMPONENT_READY_EDD", "ROBUST_MC"})
        page.run_analysis()
        wait_until(lambda: bool(page.results))
        assert all(len(r["steps"]) == 30 for r in page.results)
        robust = next(r for r in page.results if r["method"] == "ROBUST_MC")
        assert robust["risk_validation_summary"]["iterations"] == 1000
        theory = TheoryPage(root)
        theory.pack(fill="both", expand=True)
        page.path_var.set(str(DATA_DIR / "esm" / "esm_jobs.csv"))
        page.load_selected_data()
        with (
            patch.object(
                root, "pages", {"EngineeringModePage": page, "TheoryPage": theory}, create=True
            ),
            patch.object(root, "show", create=True) as navigate,
        ):
            page.show_theory_gantts()
            navigate.assert_called_once_with("TheoryPage")
        comparison = theory.esm_comparison
        assert comparison is not None
        assert comparison.path_var.get() == page.path_var.get()
        assert comparison.machine_var.get() == page.machine_var.get()
        wait_until(lambda: bool(comparison.results))
        assert comparison.canvas is not None and len(comparison.figure.axes) == 4
        assert all(len(r["steps"]) == 12 for r in comparison.results)
        assert all(len(axis.patches) == 12 for axis in comparison.figure.axes)
        comparison.machine_var.set("2")
        comparison._machine_changed("2")
        assert comparison.figure is None and not comparison.results
        comparison.run_analysis()
        wait_until(lambda: bool(comparison.results))
        assert all(len(r["steps"]) == 8 for r in comparison.results)
        comparison.time_mode_var.set(ESM_TIME_MODES["per_machine"])
        comparison._invalidate()
        comparison.run_analysis()
        wait_until(lambda: bool(comparison.results))
        assert all(
            s["processing_time"] == 100
            for s in comparison.results[0]["steps"]
            if s["job_id"] == "Z3"
        )
        theory._set_family("mh")
        assert comparison.winfo_manager() == ""
        assert theory.animation.winfo_manager() == "grid"
        assert {path: path.read_bytes() for path in (DATA_DIR / "esm").rglob("*.csv")} == csv_before
        assert not callback_errors, callback_errors
        print(
            "ENGINEERING_GUI_OK default=esm_jobs.csv 1/2/3_machines=OK button_calculates=OK "
            "manual_time_modes=2 unchanged_csv=OK stale_result=discarded paper3=1 fixture_8_machines=OK "
            "advanced_methods=3 MAIN_BUTTON_2x2=OK MAIN_BUTTON_7_METHODS=OK resize_1920=OK theory_2x2=OK theory_modes=OK "
            "presets=OK clipboard=OK csv_exports=OK export_pages=2 pending_path=blocked worker_failure=recovered render_failure=clean",
            flush=True,
        )
    finally:
        grid_patch.stop()
        chart_patch.stop()
        root.destroy()


if __name__ == "__main__":
    main()
