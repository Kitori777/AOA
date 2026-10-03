from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd

from AOA.core.production_line import ProductionLineSpec, StationSpec
from AOA.core.production_line_designer import ProductionLineDraft
from AOA.core.services import (
    load_production_line_project,
    run_production_line_flow,
    save_production_line_project,
)

from .machine_configuration_dialog import open_machine_configuration
from .production_line_canvas import ProductionLineCanvas


class ProductionLineDesignerDialog(ctk.CTkToplevel):
    def __init__(self, parent, jobs: pd.DataFrame | None, on_result=None):
        super().__init__(parent)
        self.jobs = jobs
        self.on_result = on_result
        self.draft = ProductionLineDraft()
        self.title("Graficzny projektant linii produkcyjnej")
        self.geometry("1450x860")
        self.minsize(1080, 700)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self.line_id_var = ctk.StringVar(value=self.draft.line_id)
        self.line_name_var = ctk.StringVar(value=self.draft.name)
        self.station_id_var = ctk.StringVar()
        self.station_name_var = ctk.StringVar()
        self.resources_var = ctk.StringVar(value="1")
        self.duration_var = ctk.StringVar(value="czas_produkcji_h")
        self.cost_var = ctk.StringVar(value="0")
        self.waste_var = ctk.StringVar(value="0")
        self.quality_var = ctk.StringVar(value="quality")
        self.status_var = ctk.StringVar(value="")
        self.size_var = ctk.StringVar(value="")

        self._build()
        self._select_station(self.draft.stations[0].station_id)
        self._refresh_project_state()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 8))
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(3, weight=2)
        ctk.CTkLabel(
            header,
            text="Graficzny projektant linii produkcyjnej",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ctk.CTkLabel(header, text="ID linii").grid(row=1, column=0, sticky="w", padx=(0, 8))
        ctk.CTkEntry(header, textvariable=self.line_id_var, width=230).grid(
            row=1, column=1, sticky="w"
        )
        ctk.CTkLabel(header, text="Nazwa").grid(row=1, column=2, sticky="w", padx=(18, 8))
        ctk.CTkEntry(header, textvariable=self.line_name_var).grid(row=1, column=3, sticky="ew")

        workspace = ctk.CTkFrame(self, corner_radius=16)
        workspace.grid(row=1, column=0, sticky="nsew", padx=(20, 8), pady=(0, 10))
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(workspace, fg_color="#111827", corner_radius=12)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        buttons = (
            ("+ Stanowisko", self._new_station, "#2563eb"),
            ("Połącz →", self._begin_connection, "#7c3aed"),
            ("Rozłącz", self._disconnect_selected, "#475569"),
            ("Usuń", self._delete_station, "#991b1b"),
            ("Auto-układ", self._auto_layout, "#155e75"),
            ("Maszyny i trasy", self._open_machine_configuration, "#0f766e"),
            ("−", self._zoom_out, "#334155"),
            ("100%", self._reset_zoom, "#334155"),
            ("+", self._zoom_in, "#334155"),
        )
        for column, (label, command, color) in enumerate(buttons):
            ctk.CTkButton(
                toolbar,
                text=label,
                command=command,
                width=125 if column == 5 else 105 if column < 5 else 55,
                fg_color=color,
            ).grid(row=0, column=column, padx=4, pady=8)
        toolbar.grid_columnconfigure(len(buttons), weight=1)
        ctk.CTkLabel(
            toolbar,
            text="Przeciągaj bloki • kliknij prawe kółko i potem stanowisko docelowe",
            text_color="#94a3b8",
        ).grid(row=0, column=len(buttons), sticky="e", padx=10)

        self.line_canvas = ProductionLineCanvas(
            workspace,
            self.draft,
            on_select=self._on_canvas_select,
            on_change=self._refresh_project_state,
            on_error=self._show_canvas_error,
        )
        self.line_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

        status_frame = ctk.CTkFrame(workspace, fg_color="#0f172a", corner_radius=10)
        status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        status_frame.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            justify="left",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=12, pady=8)

        editor = ctk.CTkScrollableFrame(self, label_text="Właściwości stanowiska")
        editor.grid(row=1, column=1, sticky="nsew", padx=(8, 20), pady=(0, 10))
        editor.grid_columnconfigure(1, weight=1)
        self.selection_label = ctk.CTkLabel(
            editor,
            text="Zaznacz blok na diagramie",
            text_color="#93c5fd",
            font=("Segoe UI", 13, "bold"),
        )
        self.selection_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=10)
        fields = (
            ("ID stanowiska", self.station_id_var),
            ("Nazwa stanowiska", self.station_name_var),
            ("Liczba równoległych maszyn", self.resources_var),
            ("Wzór czasu [h]", self.duration_var),
            ("Wzór kosztu", self.cost_var),
            ("Wzór odpadu", self.waste_var),
            ("Wzór jakości", self.quality_var),
        )
        for row, (label, variable) in enumerate(fields, start=1):
            ctk.CTkLabel(editor, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=7)
            ctk.CTkEntry(editor, textvariable=variable).grid(
                row=row, column=1, sticky="ew", padx=12, pady=7
            )
        ctk.CTkButton(
            editor,
            text="Zapisz właściwości bloku",
            command=self._save_station,
            height=40,
        ).grid(row=8, column=0, columnspan=2, sticky="ew", padx=12, pady=(14, 8))
        ctk.CTkLabel(
            editor,
            text=(
                "Jak połączyć linię:\n"
                "1. Zaznacz blok początkowy.\n"
                "2. Kliknij „Połącz →” albo prawe kółko bloku.\n"
                "3. Kliknij blok docelowy.\n\n"
                "Jedna poprawna linia ma dokładnie jedną ścieżkę bez cykli i rozgałęzień. "
                "Położenie bloków nie zmienia obliczeń — robią to strzałki."
            ),
            justify="left",
            wraplength=390,
            text_color="#cbd5e1",
        ).grid(row=9, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 8))
        ctk.CTkLabel(
            editor,
            text=(
                "Zmienne wzorów: cena, odpad, termin_h, czas_produkcji_h, x, y, z, "
                "job_index, station_index, resource_index, prev_duration, prev_end, "
                "duration, start, end, cost_total, waste_total, quality.\n\n"
                "Funkcje: min, max, abs, round, sqrt, ceil, floor."
            ),
            justify="left",
            wraplength=390,
            text_color="#bfdbfe",
        ).grid(row=10, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 14))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self.size_var, text_color="#94a3b8").grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(
            footer,
            text="Wczytaj projekt",
            command=self._load,
            width=140,
            fg_color="#334155",
        ).grid(row=0, column=1, padx=5)
        ctk.CTkButton(
            footer,
            text="Zapisz projekt",
            command=self._save_project,
            width=140,
            fg_color="#155e75",
        ).grid(row=0, column=2, padx=5)
        self.run_button = ctk.CTkButton(
            footer,
            text="Uruchom symulację",
            command=self._run,
            width=180,
            height=40,
            fg_color="#16a34a",
            hover_color="#15803d",
        )
        self.run_button.grid(row=0, column=3, padx=5)
        ctk.CTkButton(footer, text="Zamknij", command=self.destroy, width=110).grid(
            row=0, column=4, padx=(5, 0)
        )

    def _sync_project_metadata(self) -> None:
        self.draft.line_id = self.line_id_var.get().strip() or "moja_linia"
        self.draft.name = self.line_name_var.get().strip() or "Moja linia produkcyjna"

    def _spec(self) -> ProductionLineSpec:
        self._sync_project_metadata()
        columns = [] if self.jobs is None else [str(column) for column in self.jobs.columns]
        return self.draft.to_spec(columns=columns)

    def _on_canvas_select(self, station_id: str | None) -> None:
        if station_id is None:
            self.selection_label.configure(text="Zaznacz blok na diagramie")
            return
        self._select_station(station_id)

    def _select_station(self, station_id: str) -> None:
        station = self.draft.select_by_id(station_id)
        self.station_id_var.set(station.station_id)
        self.station_name_var.set(station.name)
        self.resources_var.set(str(station.resources))
        self.duration_var.set(station.duration_formula)
        self.cost_var.set(station.cost_formula)
        self.waste_var.set(station.waste_formula)
        self.quality_var.set(station.quality_formula)
        self.selection_label.configure(text=f"Wybrano: {station.name} ({station.station_id})")
        if hasattr(self, "line_canvas"):
            self.line_canvas.redraw()

    def _new_station(self) -> None:
        station = self.draft.new_station_template()
        self.draft.add_station(station, auto_connect=False)
        self._select_station(station.station_id)
        self._refresh_project_state()

    def _save_station(self) -> None:
        try:
            index = self._commit_selected_station()
            saved_station = self.draft.select(index)
            self._select_station(saved_station.station_id)
            self._refresh_project_state()
        except Exception as exc:
            messagebox.showerror("Błąd stanowiska", str(exc), parent=self)

    def _commit_selected_station(self) -> int:
        station = StationSpec(
            self.station_id_var.get(),
            self.station_name_var.get(),
            int(self.resources_var.get()),
            self.duration_var.get(),
            self.cost_var.get(),
            self.waste_var.get(),
            self.quality_var.get(),
        )
        self._sync_project_metadata()
        return self.draft.update_selected_station(
            station,
            columns=[] if self.jobs is None else [str(column) for column in self.jobs.columns],
        )

    def _begin_connection(self) -> None:
        if self.line_canvas.begin_connection():
            station = self.draft.selected_station
            if station:
                self.status_var.set(
                    f"Łączenie od {station.station_id}: kliknij stanowisko docelowe."
                )
                self.status_label.configure(text_color="#c4b5fd")

    def _disconnect_selected(self) -> None:
        self.line_canvas.disconnect_selected()

    def _delete_station(self) -> None:
        self.line_canvas.delete_selected()

    def _auto_layout(self) -> None:
        self.line_canvas.auto_layout()

    def _open_machine_configuration(self) -> None:
        try:
            if self.draft.selected_station is not None:
                self._commit_selected_station()
        except Exception as exc:
            messagebox.showerror("Błąd stanowiska", str(exc), parent=self)
            return
        open_machine_configuration(self, self.draft, on_save=self._configuration_saved)

    def _configuration_saved(self) -> None:
        station = self.draft.selected_station
        if station is not None:
            self._select_station(station.station_id)
        self._refresh_project_state()

    def _zoom_in(self) -> None:
        self.line_canvas.zoom_in()

    def _zoom_out(self) -> None:
        self.line_canvas.zoom_out()

    def _reset_zoom(self) -> None:
        self.line_canvas.reset_zoom()

    def _refresh_project_state(self) -> None:
        valid, message = self.draft.graph_status()
        self.status_var.set(("✓ " if valid else "⚠ ") + message)
        self.status_label.configure(text_color="#86efac" if valid else "#fbbf24")
        self.run_button.configure(state="normal" if valid else "disabled")
        rows = 0 if self.jobs is None else len(self.jobs)
        self.size_var.set(
            f"Dane: {rows:,} zleceń • stanowiska: {len(self.draft.stations)} • "
            f"wynik: {rows * len(self.draft.stations):,} operacji"
        )
        self.line_canvas.redraw()

    def _show_canvas_error(self, message: str) -> None:
        self.status_var.set(f"⚠ {message}")
        self.status_label.configure(text_color="#fca5a5")
        messagebox.showerror("Nie można połączyć", message, parent=self)

    def _save_project(self) -> None:
        try:
            if self.draft.selected_station is not None:
                self._commit_selected_station()
            else:
                self._sync_project_metadata()
            path = save_production_line_project(self.draft)
            messagebox.showinfo("Projekt zapisany", f"Zapisano projekt:\n{path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Błąd projektu", str(exc), parent=self)

    def _load(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Wybierz projekt linii",
            filetypes=[("Projekt linii JSON", "*.json")],
        )
        if not path:
            return
        try:
            project = load_production_line_project(path)
            self.draft = project
            self.line_id_var.set(project.line_id)
            self.line_name_var.set(project.name)
            self.line_canvas.set_draft(project)
            if project.stations:
                self._select_station(project.stations[0].station_id)
            self._refresh_project_state()
        except Exception as exc:
            messagebox.showerror("Błąd projektu", str(exc), parent=self)

    def _run(self) -> None:
        if self.jobs is None or self.jobs.empty:
            messagebox.showerror(
                "Brak danych",
                "Najpierw wygeneruj albo wczytaj dane w Main.",
                parent=self,
            )
            return
        try:
            if self.draft.selected_station is not None:
                self._commit_selected_station()
            spec = self._spec()
        except Exception as exc:
            messagebox.showerror("Linia nie jest gotowa", str(exc), parent=self)
            return
        event_count = len(self.jobs) * len(spec.stations)
        if event_count > 250_000 and not messagebox.askyesno(
            "Duży wynik",
            f"Symulacja utworzy {event_count:,} wierszy. Czy kontynuować?",
            parent=self,
        ):
            return
        try:
            result = run_production_line_flow(spec, self.jobs, project=self.draft)
            if callable(self.on_result):
                self.on_result(result)
            kpis = result["kpis"]
            messagebox.showinfo(
                "Symulacja zakończona",
                f"Zlecenia: {kpis['jobs']}\nCzas całkowity: {kpis['makespan_h']:.3f} h\n"
                f"Opóźnione: {kpis['late_jobs']}\nCSV do Visual:\n{result['visual_path']}\n\n"
                f"Podsumowanie zleceń:\n{result['summary_path']}\n\n"
                f"Efektywność maszyn:\n{result['efficiency_path']}\n\n"
                f"Monte Carlo P90: {result['risk_summary']['p90_makespan_h']:.3f} h",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Błąd symulacji", str(exc), parent=self)


def open_production_line_designer(parent, jobs: pd.DataFrame | None, on_result=None):
    return ProductionLineDesignerDialog(parent, jobs, on_result=on_result)
