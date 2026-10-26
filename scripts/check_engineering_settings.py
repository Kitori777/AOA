"""Exercise the settings panel in Tk and optionally leave a preview for visual QA."""

from __future__ import annotations

import argparse
import json
import time
from hashlib import sha256
from pathlib import Path

import customtkinter as ctk

from AOA.config import DATA_DIR
from AOA.core.esm_costs import OBJECTIVES
from AOA.core.esm_project import ESM_TIME_MODES
from AOA.gui.engineering_settings import ACCENT, EngineeringSettingsPanel
from AOA.gui.pages.engineering_mode_page import EngineeringModePage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1] / "output/engineering-settings"
    output.mkdir(parents=True, exist_ok=True)
    before = {
        p: sha256(p.read_bytes()).hexdigest() for p in (DATA_DIR / "esm").rglob("*") if p.is_file()
    }
    ctk.set_appearance_mode("dark")
    ctk.set_widget_scaling(1)
    ctk.set_window_scaling(1)
    root = ctk.CTk()
    root.withdraw()
    errors = []
    root.report_callback_exception = lambda *error: errors.append(
        tuple(str(item) for item in error)
    )
    page = EngineeringModePage(root)
    page.pack(fill="both", expand=True)
    deadline = time.monotonic() + 90

    def wait(predicate):
        while not predicate():
            assert time.monotonic() < deadline, errors
            root.update()
            time.sleep(0.01)
        root.update_idletasks()

    preview = None
    try:
        wait(lambda: bool(page.jobs))
        panel = page.settings_panel
        assert panel.count_var.get() == "Wybrano 4 z 7"
        assert "3,33 min" in panel.example_var.get()
        assert panel.objective_rows["sto"].cget("border_color") == ACCENT
        page.preset_buttons["extra"].invoke()
        assert panel.count_var.get() == "Wybrano 3 z 7"
        page.method_checkboxes["ECO_WASTE"].toggle()
        assert panel.count_var.get() == "Wybrano 2 z 7"
        page.preset_buttons["all"].invoke()
        assert panel.count_var.get() == "Wybrano 7 z 7"
        page.preset_buttons["basic"].invoke()
        page.run_button.invoke()
        wait(lambda: bool(page.results))
        for code, radio in panel.objective_buttons.items():
            generation = page._generation
            radio.invoke()
            assert page.objective_code() == code and page._generation == generation + 1
            assert not page.results and all(
                b.cget("state") == "disabled" for b in page.export_buttons
            )
            assert panel.objective_rows[code].cget("border_color") == ACCENT
        for count in range(1, 9):
            panel.machine_selector._buttons_dict[str(count)].invoke()
            assert page.machine_var.get() == str(count)
        panel.machine_selector._buttons_dict["3"].invoke()
        panel.time_mode_menu.set(ESM_TIME_MODES["per_machine"])
        panel.time_mode_menu.cget("command")(ESM_TIME_MODES["per_machine"])
        assert (
            page.time_mode_code() == "per_machine" and "Łącznie 30 min" in panel.example_var.get()
        )
        page.path_var.set(
            str(
                DATA_DIR
                / "esm/article/costs/DYLEWSKI_2_maszyny/Przyklad_1/DYLEWSKI_Przyklad_1_W3_koszt_16.csv"
            )
        )
        page.load_selected_data()
        assert page.objective_code() == "cost" and page.machine_var.get() == "2"
        assert page.time_mode_code() == "file" and "M2:" in panel.example_var.get()
        page.path_var.set(str(DATA_DIR / "esm/esm_jobs.csv"))
        page.load_selected_data()
        panel.machine_selector._buttons_dict["3"].invoke()

        main_sizes = []
        for root_width, expected_wide in ((1440, True), (900, False)):
            root.geometry(f"{root_width}x850+20+20")
            root.deiconify()
            wait(
                lambda expected_wide=expected_wide: panel._wide == expected_wide
                and page._methods_card_wide == expected_wide
            )
            assert (
                panel.winfo_rootx() + panel.winfo_width() <= root.winfo_rootx() + root.winfo_width()
            )
            assert all(
                int(shell.grid_info()["columnspan"]) == (1 if expected_wide else 2)
                for shell in page._method_shells
            )
            main_sizes.append({"width": root_width, "columns": 2 if expected_wide else 1})
        root.withdraw()

        preview = ctk.CTkToplevel(root)
        preview.title("AOA — Ustawienia inżynierskie — podgląd")
        preview.configure(fg_color="#0c1b28")
        preview.grid_columnconfigure(0, weight=1)
        display = EngineeringSettingsPanel(
            preview,
            machine_var=page.machine_var,
            time_mode_var=page.time_mode_var,
            objective_var=page.objective_var,
            method_vars=page.method_vars,
            on_machine=page._machine_changed,
            on_time_mode=page._time_mode_changed,
            on_objective=page._objective_changed,
            on_costs=page.show_cost_editor,
            on_preset=page.select_method_preset,
        )
        display.grid(row=0, column=0, sticky="ew", padx=24, pady=24)
        display.refresh(page.jobs)
        sizes = []
        for width, wide in ((1400, True), (700, False), (1100, False), (1280, True)):
            preview.geometry(f"{width}x1000+40+30")
            root.update()
            wait(
                lambda wide=wide: abs(
                    display.winfo_width()
                    - (preview.winfo_width() - display._apply_widget_scaling(48))
                )
                <= 2
                and display._wide == wide
            )
            root.update()
            production = display.production_card
            objective = display.objective_card
            if wide:
                assert production.winfo_y() == objective.winfo_y()
                assert production.winfo_x() + production.winfo_width() < objective.winfo_x()
            else:
                assert production.winfo_y() + production.winfo_height() < objective.winfo_y()
            for widget in (
                production,
                objective,
                display.methods_bar,
                display.cost_button,
                display.time_mode_menu,
            ):
                assert widget.winfo_rootx() >= preview.winfo_rootx()
                assert (
                    widget.winfo_rootx() + widget.winfo_width()
                    <= preview.winfo_rootx() + preview.winfo_width()
                )
            sizes.append(
                {
                    "window_width": width,
                    "columns": 2 if wide else 1,
                    "panel_height": display.winfo_height(),
                }
            )
        assert not errors, errors
        assert {p: sha256(p.read_bytes()).hexdigest() for p in before} == before
        (output / "verification.json").write_text(
            json.dumps(
                {
                    "native_gui": "passed",
                    "sizes": sizes,
                    "main_page_sizes": main_sizes,
                    "objectives": list(OBJECTIVES),
                    "machine_counts": list(range(1, 9)),
                    "presets_and_live_count": True,
                    "results_invalidated_on_objective_change": True,
                    "time_example": display.example_var.get(),
                    "unchanged_data_files": len(before),
                    "callback_errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"ENGINEERING_SETTINGS_OK objectives=3 machines=1-8 presets=OK time_examples=OK responsive=4_sizes data={len(before)}_unchanged",
            flush=True,
        )
        if args.preview:
            height = int(display._reverse_widget_scaling(display.winfo_reqheight())) + 48
            preview.geometry(f"1280x{height}+40+30")
            root.after(180_000, root.quit)
            root.mainloop()
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
