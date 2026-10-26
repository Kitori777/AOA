"""Live engineering comparison, sharing scheduling and chart code with ESM."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from AOA.config import DATA_DIR
from AOA.core.esm_costs import OBJECTIVES, DelayPenalty, with_job_penalties
from AOA.core.esm_project import (
    ESM_COMPARISON_METHODS,
    ESM_TIME_MODES,
    esm_csv_has_costs,
    evaluate_esm_methods,
    list_esm_scenarios,
    load_esm_jobs,
)
from AOA.gui.engineering_charts import build_esm_gantt_comparison_figure


class EsmGanttComparison(ctk.CTkFrame):
    """A 2 x 2 comparison of computed MT, MO, MZO and MOpt schedules."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="#0d1a26", corner_radius=14)
        self.path_var = ctk.StringVar(value=str(DATA_DIR / "esm" / "esm_jobs.csv"))
        self.machine_var = ctk.StringVar(value="3")
        self.time_mode_var = ctk.StringVar(value=ESM_TIME_MODES["total"])
        self.objective_var = ctk.StringVar(value=OBJECTIVES["sto"])
        self._penalty_overrides: dict[str, DelayPenalty] | None = None
        self.status_var = ctk.StringVar(value="Wybierz liczbe maszyn i utworz cztery Gantty.")
        self.scenarios = {s.label: s.path for s in list_esm_scenarios(DATA_DIR / "esm")}
        self.scenario_var = ctk.StringVar(value=next(iter(self.scenarios), "esm_jobs.csv"))
        self.jobs = load_esm_jobs(self.path_var.get())
        self.results: list[dict] = []
        self.figure = None
        self.canvas: FigureCanvasTkAgg | None = None
        self.toolbar = None
        self._generation = 0
        self._future: Future | None = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="esm-theory")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text="Teoria ESM - cztery Gantty na tych samych danych",
            font=("Segoe UI", 19, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=10)
        source = ctk.CTkFrame(self, fg_color="transparent")
        source.grid(row=1, column=0, sticky="ew", padx=14)
        source.grid_columnconfigure(0, weight=1)
        ctk.CTkOptionMenu(
            source,
            variable=self.scenario_var,
            values=list(self.scenarios),
            command=self._select_scenario,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(source, text="Wybierz CSV", width=110, command=self._choose_file).grid(
            row=0, column=1
        )
        ctk.CTkLabel(self, textvariable=self.path_var, anchor="w", text_color="#93c5fd").grid(
            row=2, column=0, sticky="ew", padx=14, pady=4
        )
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=3, column=0, sticky="ew", padx=14, pady=4)
        controls.grid_columnconfigure(1, weight=1)
        ctk.CTkSegmentedButton(
            controls,
            values=[str(m) for m in range(1, 9)],
            variable=self.machine_var,
            command=self._machine_changed,
        ).grid(row=0, column=0, padx=(0, 10))
        self.time_mode_menu = ctk.CTkOptionMenu(
            controls,
            variable=self.time_mode_var,
            values=[ESM_TIME_MODES[k] for k in ("total", "per_machine")],
            command=self._invalidate,
        )
        self.time_mode_menu.grid(row=0, column=1, sticky="ew")
        ctk.CTkOptionMenu(
            controls,
            values=list(OBJECTIVES.values()),
            variable=self.objective_var,
            command=self._invalidate,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)
        self.run_button = ctk.CTkButton(
            self,
            text="UTWORZ CZTERY GANTTY (MT / MO / MZO / MOpt)",
            command=self.run_analysis,
            height=40,
        )
        self.run_button.grid(row=4, column=0, sticky="ew", padx=14, pady=8)
        ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            text_color="#8ddbd1",
            anchor="w",
            wraplength=1150,
            justify="left",
        ).grid(row=5, column=0, sticky="ew", padx=14, pady=4)
        self.toolbar_host = ttk.Frame(self)
        self.toolbar_host.grid(row=6, column=0, sticky="ew", padx=10)
        self.chart_host = ctk.CTkFrame(self, fg_color="#071019", height=600)
        self.chart_host.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 12))
        self.chart_host.grid_propagate(False)
        self.chart_host.grid_rowconfigure(0, weight=1)
        self.chart_host.grid_columnconfigure(0, weight=1)
        self.chart_host.bind("<Configure>", self._resize)

    def time_mode_code(self) -> str:
        return next(
            key for key, label in ESM_TIME_MODES.items() if label == self.time_mode_var.get()
        )

    def set_context(
        self,
        path: str | Path,
        machines: int = 3,
        time_mode: str | None = None,
        *,
        objective: str | None = None,
        penalties: Mapping[str, DelayPenalty] | None = None,
    ) -> None:
        jobs = load_esm_jobs(path)
        self._penalty_overrides = dict(penalties) if penalties is not None else None
        if self._penalty_overrides is not None:
            jobs = with_job_penalties(jobs, self._penalty_overrides)
        criterion = objective or ("cost" if esm_csv_has_costs(Path(path).read_bytes()) else "sto")
        self.objective_var.set(OBJECTIVES[criterion])
        self.jobs = jobs
        self.path_var.set(str(path))
        self.machine_var.set(str(machines))
        mode = time_mode or (
            "file" if all(len(j.machine_times) == machines for j in jobs) else "total"
        )
        self.time_mode_var.set(ESM_TIME_MODES[mode])
        keys = (
            ["total", "per_machine", "file"] if jobs[0].machine_times else ["total", "per_machine"]
        )
        self.time_mode_menu.configure(values=[ESM_TIME_MODES[key] for key in keys])
        self.scenario_var.set(
            next(
                (
                    label
                    for label, value in self.scenarios.items()
                    if value.resolve() == Path(path).resolve()
                ),
                "Plik z Pracy inzynierskiej",
            )
        )
        self._invalidate()

    def _select_scenario(self, label: str) -> None:
        path = self.scenarios[label]
        try:
            jobs = load_esm_jobs(path)
            machines = len(jobs[0].machine_times) or int(self.machine_var.get())
            if not jobs[0].machine_times and esm_csv_has_costs(path.read_bytes()):
                machines = 1
            self.set_context(path, machines)
            self.scenario_var.set(label)
        except (ValueError, OSError) as exc:
            self._invalidate()
            self.status_var.set(str(exc))

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=str(DATA_DIR / "esm"), filetypes=[("CSV", "*.csv")]
        )
        if path:
            try:
                jobs = load_esm_jobs(path)
                machines = len(jobs[0].machine_times) or (
                    1 if esm_csv_has_costs(Path(path).read_bytes()) else int(self.machine_var.get())
                )
                self.set_context(path, machines)
            except (OSError, ValueError) as exc:
                self._invalidate()
                self.status_var.set(str(exc))

    def _machine_changed(self, _value: str) -> None:
        if self.time_mode_code() == "file" and any(
            len(j.machine_times) != int(self.machine_var.get()) for j in self.jobs
        ):
            self.time_mode_var.set(ESM_TIME_MODES["total"])
        self._invalidate()

    def _invalidate(self, _value: str = "") -> None:
        self._generation += 1
        self.results = []
        self._clear_chart()
        self.status_var.set(
            "Ustawienia zmienione. Utworz wykresy ponownie; dane CSV pozostaja bez zmian."
        )

    def _clear_chart(self) -> None:
        if self.figure is not None:
            # Figure.clear updates its navigation toolbar; detach it before Tk
            # destroys the toolbar widgets, including during repeated redraws.
            self.figure.canvas.toolbar = None
            self.figure.clear()
            self.figure = None
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        if self.toolbar is not None:
            self.toolbar.destroy()
            self.toolbar = None

    def run_analysis(self) -> None:
        if self._future is not None:
            self.status_var.set("Trwa obliczanie. Poczekaj na zakonczenie biezacego porownania.")
            return
        try:
            # Re-read so all four methods use a single fresh immutable snapshot.
            self.jobs = load_esm_jobs(self.path_var.get())
            if self._penalty_overrides is not None:
                self.jobs = with_job_penalties(self.jobs, self._penalty_overrides)
            self._invalidate()
            generation = self._generation
            self._future = self._executor.submit(
                evaluate_esm_methods,
                list(self.jobs),
                list(ESM_COMPARISON_METHODS),
                n_machines=int(self.machine_var.get()),
                time_mode=self.time_mode_code(),
                objective=next(
                    key for key, label in OBJECTIVES.items() if label == self.objective_var.get()
                ),
            )
            self.status_var.set("Obliczanie czterech harmonogramow w tle...")
            self.after(50, lambda: self._poll(generation))
        except (ValueError, OSError) as exc:
            self.status_var.set(str(exc))

    def _poll(self, generation: int) -> None:
        if self._future is None:
            return
        if not self._future.done():
            self.after(50, lambda: self._poll(generation))
            return
        future, self._future = self._future, None
        if generation != self._generation:
            self.status_var.set(
                "Pominieto wynik po zmianie danych lub ustawien. Utworz Gantty ponownie."
            )
            return
        try:
            self.results = future.result()
            self.figure = build_esm_gantt_comparison_figure(self.results)
            self.canvas = FigureCanvasTkAgg(self.figure, master=self.chart_host)
            self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_host)
            self.toolbar.update()
            self._resize()
            self.canvas.draw()
            mopt = next(r for r in self.results if r["method"] == "MOPT")
            self.status_var.set(
                f"{len(self.jobs)} zlecen, {self.machine_var.get()} maszyn; "
                f"{ESM_TIME_MODES[self.time_mode_code()]}. MOpt: {mopt['search_status']}. "
                f"Kryterium: {OBJECTIVES[mopt['objective']]}; odpad {mopt['total_waste_kg']:g} kg; koszt {mopt['total_tardiness_cost']:g} j.p.; STO {mopt['sto']:g} min. "
                "Wspolna skala i kolory. Czerwone obramowanie: opoznienie po ostatniej operacji."
            )
        except Exception as exc:
            self.results = []
            self.status_var.set(f"Nie udalo sie utworzyc porownania: {exc}")

    def _resize(self, _event=None) -> None:
        if self.canvas is not None and self.figure is not None:
            width = max(640, self.chart_host.winfo_width())
            height = max(480, min(850, int(width * 0.60)))
            self.chart_host.configure(height=height)
            self.figure.set_size_inches(width / self.figure.dpi, height / self.figure.dpi)
            self.canvas.draw_idle()

    def destroy(self) -> None:
        self._generation += 1
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._clear_chart()
        super().destroy()
