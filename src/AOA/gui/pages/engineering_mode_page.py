from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from tkinter import TclError, filedialog, messagebox, ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from AOA.config import BASE_DIR, DATA_DIR
from AOA.core.esm_costs import (
    OBJECTIVES,
    DelayPenalty,
    cost_parameters,
    job_penalty,
    with_job_penalties,
)
from AOA.core.esm_project import (
    ESM_DEFAULT_SCENARIO,
    ESM_METHODS,
    ESM_TIME_MODES,
    build_mopt_solution_tree,
    esm_csv_has_costs,
    esm_method_warnings,
    evaluate_esm_methods,
    list_esm_scenarios,
    load_esm_jobs,
    prepare_esm_flow_jobs,
)
from AOA.core.flowshop import FLOW_METHODS
from AOA.core.optimization.models import Job
from AOA.gui.engineering_charts import build_mopt_tree_figure
from AOA.gui.engineering_cost_editor import EngineeringCostEditor
from AOA.gui.engineering_exports import (
    METHOD_LABELS,
    EngineeringContext,
    comparison_rows,
    format_result_description,
    operation_rows,
    write_csv,
)
from AOA.gui.engineering_settings import EngineeringSettingsPanel
from AOA.gui.gantt_window import GanttComparisonWindow
from AOA.gui.theme import COLORS

METHOD_HELP = {
    "MT": "Najpierw zlecenia z najbliższym terminem realizacji.",
    "MO": "Najpierw zlecenia z najkrótszym czasem obróbki.",
    "MZO": "Najpierw zlecenia z najdłuższym czasem obróbki.",
    "MOPT": "Szuka minimum wybranego celu. Wynik pokazuje, czy optimum zostało potwierdzone.",
    "ECO_WASTE": "Ogranicza zmiany materiału i kształtu. Wybierz cel Odpad, aby kg miały pierwszeństwo.",
    "COMPONENT_READY_EDD": "Uwzględnia gotowość komponentów i terminy. Bez kompletu komponentów zlecenie nie ruszy.",
    "ROBUST_MC": "Ocenia kolejności w 1000 symulacji awarii. Kolejne 1000 niezależnie sprawdza wynik.",
}


class EngineeringModePage(ctk.CTkFrame):
    """Focused ESM workspace used for the engineering thesis project."""

    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["app_bg"])
        self.scenarios = list_esm_scenarios(DATA_DIR / "esm")
        self.scenario_paths = {scenario.label: scenario.path for scenario in self.scenarios}
        default_path = DATA_DIR / "esm" / ESM_DEFAULT_SCENARIO
        default_label = next(
            (scenario.label for scenario in self.scenarios if scenario.path == default_path),
            "START: esm_jobs.csv - jeden czas zlecenia",
        )
        self.scenario_var = ctk.StringVar(value=default_label)
        self.path_var = ctk.StringVar(value=str(default_path))
        self.machine_var = ctk.StringVar(value="3")
        self.time_mode_var = ctk.StringVar(value=ESM_TIME_MODES["total"])
        self.objective_var = ctk.StringVar(value=OBJECTIVES["sto"])
        self.cost_editor: EngineeringCostEditor | None = None
        self.model_var = ctk.StringVar(value="Model: przeplyw M1 -> M2 -> M3")
        self.status_var = ctk.StringVar(value="Gotowe. Wczytaj przyklad ESM i uruchom obliczenia.")
        self.context_var = ctk.StringVar(value="Dane nie zostały jeszcze wczytane.")
        self.activity_var = ctk.StringVar(value="Gotowe do obliczeń.")
        self.method_vars = {
            method: ctk.BooleanVar(value=method in {"MT", "MO", "MZO", "MOPT"})
            for method in ESM_METHODS
        }
        self.jobs: list[Job] = []
        self.results: list[dict] = []
        self.gantt_window: GanttComparisonWindow | None = None
        self.result_by_iid: dict[str, dict] = {}
        self.analysis_warnings: list[str] = []
        self.method_checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="esm")
        self._future: Future | None = None
        self._generation = 0
        self._loaded_path: str | None = None
        self._loaded_sha256 = ""
        self._source_dirty = False
        self._result_context: EngineeringContext | None = None
        self._run_context: EngineeringContext | None = None
        self._analysis_started = 0.0
        self._poll_timer: str | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.page = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.page.grid(row=0, column=0, sticky="nsew")
        self.page.grid_columnconfigure(0, weight=1)
        self._configure_tree_style()
        self._build_header()
        self._build_source()
        self._build_methods()
        self._build_charts()
        self._build_results()
        self._path_trace = self.path_var.trace_add("write", self._source_path_changed)
        self.after(50, self.load_default_data)

    def _configure_tree_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Esm.Treeview",
            background="#0f172a",
            foreground="#e5eef9",
            fieldbackground="#0f172a",
            rowheight=28,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Esm.Treeview.Heading",
            background="#17263a",
            foreground="#f8fafc",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.page, corner_radius=16, fg_color="#0f1d2b")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 7))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Praca inzynierska - szeregowanie zlecen ESM",
            font=("Segoe UI", 24, "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text=(
                "Jeden plik esm_jobs.csv; wybierz 1-8 maszyn, do 10 zlecen. "
                "Wynik: porownanie metod, drzewo MOpt i Gantty metod w ukladzie 2 x 2."
            ),
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
        ctk.CTkLabel(
            header,
            text="ESM  |  lokalnie i offline",
            fg_color="#0f766e",
            corner_radius=12,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=1, rowspan=2, padx=18, pady=16)

    def _build_source(self) -> None:
        card = ctk.CTkFrame(self.page, corner_radius=14, fg_color=COLORS["surface"])
        card.grid(row=1, column=0, sticky="ew", padx=18, pady=7)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="1. Dane projektu", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 6)
        )
        ctk.CTkLabel(card, text="Przyklad:", text_color=COLORS["text_muted"]).grid(
            row=1, column=0, sticky="w", padx=(14, 6), pady=6
        )
        scenario_values = list(self.scenario_paths) or [self.scenario_var.get()]
        ctk.CTkOptionMenu(
            card,
            variable=self.scenario_var,
            values=scenario_values,
            command=self.select_scenario,
        ).grid(row=1, column=1, columnspan=2, sticky="ew", padx=(6, 14), pady=6)
        ctk.CTkButton(card, text="Wybierz CSV", command=self.choose_file, width=115).grid(
            row=2, column=0, padx=(14, 6), pady=6
        )
        ctk.CTkEntry(card, textvariable=self.path_var).grid(
            row=2, column=1, padx=6, pady=6, sticky="ew"
        )
        ctk.CTkButton(card, text="Wczytaj", command=self.load_selected_data, width=100).grid(
            row=2, column=2, padx=(6, 14), pady=6
        )
        ctk.CTkLabel(card, textvariable=self.model_var, text_color="#8ddbd1").grid(
            row=3, column=0, columnspan=3, sticky="w", padx=14, pady=4
        )
        self.input_tree = ttk.Treeview(
            card,
            columns=("job", "processing", "deadline", "ready", "material", "rate", "grace"),
            show="headings",
            height=10,
            style="Esm.Treeview",
        )
        for name, title, width in (
            ("job", "Zlecenie", 180),
            ("processing", "Czas obrobki [min]", 210),
            ("deadline", "Wymagany termin [min]", 240),
            ("ready", "Komponenty od [min]", 160),
            ("material", "Material / ksztalt", 180),
            ("rate", "Stawka [j.p./min]", 130),
            ("grace", "Tolerancja [min]", 130),
        ):
            self.input_tree.heading(name, text=title)
            self.input_tree.column(name, width=width, anchor="center", stretch=True)
        self.input_tree.grid(row=4, column=0, columnspan=3, sticky="ew", padx=14, pady=(6, 12))
        ctk.CTkLabel(
            card,
            textvariable=self.context_var,
            anchor="w",
            justify="left",
            wraplength=1000,
            text_color="#8ddbd1",
        ).grid(row=5, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12))

    def _build_methods(self) -> None:
        card = ctk.CTkFrame(self.page, corner_radius=14, fg_color=COLORS["surface"])
        card.grid(row=2, column=0, sticky="ew", padx=18, pady=7)
        card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(card, text="2. Ustawienia i algorytmy", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6)
        )
        self.settings_panel = EngineeringSettingsPanel(
            card,
            machine_var=self.machine_var,
            time_mode_var=self.time_mode_var,
            objective_var=self.objective_var,
            method_vars=self.method_vars,
            on_machine=self._machine_changed,
            on_time_mode=self._time_mode_changed,
            on_objective=self._objective_changed,
            on_costs=self.show_cost_editor,
            on_preset=self.select_method_preset,
        )
        self.settings_panel.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(8, 10))
        # Keep existing loading, editor and preset entry points on the page.
        self.time_mode_menu = self.settings_panel.time_mode_menu
        self.cost_button = self.settings_panel.cost_button
        self.preset_buttons = self.settings_panel.preset_buttons
        self._method_shells = []
        self._method_notes = []
        for index, method in enumerate(ESM_METHODS):
            row, column = divmod(index, 2)
            shell = ctk.CTkFrame(card, corner_radius=10, fg_color="#102333")
            shell.grid(row=row + 2, column=column, sticky="nsew", padx=7, pady=6)
            self._method_shells.append(shell)
            checkbox = ctk.CTkCheckBox(
                shell,
                text=METHOD_LABELS[method],
                variable=self.method_vars[method],
                command=self._methods_changed,
                font=("Segoe UI", 13, "bold"),
            )
            checkbox.pack(anchor="w", padx=12, pady=(10, 2))
            self.method_checkboxes[method] = checkbox
            note = ctk.CTkLabel(
                shell,
                text=METHOD_HELP[method],
                text_color=COLORS["text_muted"],
                wraplength=500,
                justify="left",
            )
            note.pack(anchor="w", padx=40, pady=(0, 10))
            self._method_notes.append(note)
        action_row = 2 + (len(ESM_METHODS) + 1) // 2
        self.run_button = ctk.CTkButton(
            card,
            text="Oblicz i porownaj",
            command=self.run_analysis,
            height=42,
            font=("Segoe UI", 13, "bold"),
        )
        self.run_button.grid(
            row=action_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=14,
            pady=(10, 12),
        )
        self.progress = ctk.CTkProgressBar(card, mode="indeterminate")
        self.progress.grid(row=action_row + 1, column=0, columnspan=2, sticky="ew", padx=14)
        self.progress.grid_remove()
        self.activity_label = ctk.CTkLabel(card, textvariable=self.activity_var, anchor="w")
        self.activity_label.grid(
            row=action_row + 2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 10)
        )
        self._methods_card_wide: bool | None = None
        card.bind("<Configure>", lambda event: self._layout_methods(event.width))

    def _layout_methods(self, width: int) -> None:
        width = int(self._reverse_widget_scaling(width))
        wide = width >= 1060
        columns = 2 if wide else 1
        if wide != self._methods_card_wide:
            self._methods_card_wide = wide
            for index, shell in enumerate(self._method_shells):
                row, column = divmod(index, columns)
                shell.grid(row=row + 2, column=column, columnspan=1 if wide else 2)
            action_row = 2 + (len(ESM_METHODS) + columns - 1) // columns
            self.run_button.grid(row=action_row)
            progress_visible = bool(self.progress.winfo_manager())
            self.progress.grid_configure(row=action_row + 1)
            if not progress_visible:
                self.progress.grid_remove()
            self.activity_label.grid(row=action_row + 2)
        for note in self._method_notes:
            note.configure(wraplength=max(220, width // columns - 110))

    def _build_charts(self) -> None:
        card = ctk.CTkFrame(self.page, corner_radius=14, fg_color=COLORS["surface"])
        card.grid(row=3, column=0, sticky="ew", padx=18, pady=(7, 16))
        card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(card, text="3. Wykresy", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 2)
        )
        ctk.CTkLabel(
            card,
            text=(
                "Gantty pokazuja wszystkie zaznaczone metody, po cztery na zakladke (2 x 2). "
                "Przed pierwszym uzyciem przycisk sam uruchomi obliczenia."
            ),
            text_color=COLORS["text_muted"],
            justify="left",
            wraplength=1100,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 8))

        tree_card = ctk.CTkFrame(card, corner_radius=12, fg_color="#0d2a3a")
        tree_card.grid(row=2, column=0, sticky="nsew", padx=(14, 7), pady=(4, 14))
        gantt_card = ctk.CTkFrame(card, corner_radius=12, fg_color="#102333")
        gantt_card.grid(row=2, column=1, sticky="nsew", padx=(7, 14), pady=(4, 14))
        for chart_card in (tree_card, gantt_card):
            chart_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tree_card,
            text="Drzewo rozwiazania MOpt",
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            tree_card,
            text="Przeplyw: rzeczywiste decyzje, dolne granice i status najlepszej sciezki.",
            text_color=COLORS["text_muted"],
            justify="left",
            wraplength=520,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
        ctk.CTkButton(
            tree_card,
            text="UTWORZ DRZEWO MOPT",
            command=self.show_mopt_tree,
            height=44,
            font=("Segoe UI", 13, "bold"),
            fg_color="#0f766e",
            hover_color="#115e59",
        ).grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

        ctk.CTkButton(
            card,
            text="POROWNAJ 4 GANTTY W TEORII (2 x 2)",
            command=self.show_theory_gantts,
            height=40,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))

        ctk.CTkLabel(
            gantt_card,
            text="Gantty wszystkich wybranych metod (2 x 2)",
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            gantt_card,
            text="Przeplyw: kazde zlecenie przechodzi przez wszystkie wybrane maszyny (1-8).",
            text_color=COLORS["text_muted"],
            justify="left",
            wraplength=520,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
        self.gantt_button = ctk.CTkButton(
            gantt_card,
            text="UTWORZ WYKRESY GANTTA (2 x 2)",
            command=self.show_gantt,
            height=44,
            font=("Segoe UI", 13, "bold"),
            fg_color="#155e75",
            hover_color="#164e63",
        )
        self.gantt_button.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

    def _build_results(self) -> None:
        card = ctk.CTkFrame(self.page, corner_radius=14, fg_color=COLORS["surface"])
        card.grid(row=4, column=0, sticky="ew", padx=18, pady=(7, 16))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="4. Wyniki", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 6)
        )
        self.result_tree = ttk.Treeview(
            card,
            columns=(
                "rank",
                "method",
                "order",
                "sto",
                "cost",
                "finish",
                "waste",
                "p90",
                "p90_cost",
                "time",
                "proof",
            ),
            show="headings",
            height=7,
            style="Esm.Treeview",
        )
        headings = (
            ("rank", "Miejsce", 75),
            ("method", "Metoda", 120),
            ("order", "Kolejnosc", 270),
            ("sto", "Suma opoznien", 145),
            ("cost", "Koszt [j.p.]", 120),
            ("finish", "Koniec [min]", 130),
            ("waste", "Odpad [kg]", 95),
            ("p90", "P90 konca [min]", 120),
            ("p90_cost", "P90 kosztu [j.p.]", 130),
            ("time", "Obliczenia [s]", 110),
            ("proof", "Optimum", 160),
        )
        for name, title, width in headings:
            self.result_tree.heading(name, text=title)
            self.result_tree.column(name, width=width, anchor="center", stretch=name == "order")
        self.result_tree.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        result_scroll = ttk.Scrollbar(card, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(xscrollcommand=result_scroll.set)
        result_scroll.grid(row=2, column=0, sticky="ew", padx=14)
        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_selected)
        self.summary = ctk.CTkTextbox(
            card,
            height=185,
            wrap="word",
            fg_color="#101f2d",
            font=("Segoe UI", 11),
        )
        self.summary.grid(row=3, column=0, sticky="ew", padx=14, pady=6)
        self.summary.insert(
            "1.0", "Po obliczeniu tutaj pojawi sie interpretacja najlepszego wyniku."
        )
        self.summary.configure(state="disabled")
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=10, pady=6)
        actions.grid_columnconfigure((0, 1, 2), weight=1)
        self.export_buttons = []
        for column, (label, command) in enumerate(
            (
                ("Zapisz porównanie CSV", lambda: self.export_results("comparison")),
                ("Zapisz operacje CSV", lambda: self.export_results("operations")),
                ("Kopiuj opis wyniku", self.copy_result_description),
            )
        ):
            button = ctk.CTkButton(actions, text=label, command=command, state="disabled")
            button.grid(row=0, column=column, sticky="ew", padx=4, pady=4)
            self.export_buttons.append(button)
        ctk.CTkLabel(
            card,
            textvariable=self.status_var,
            text_color="#8ddbd1",
            anchor="w",
        ).grid(row=5, column=0, sticky="ew", padx=14, pady=(6, 12))

    def choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Wybierz dane ESM",
            initialdir=str(DATA_DIR / "esm"),
            filetypes=[("CSV", "*.csv")],
        )
        if selected:
            self.scenario_var.set("Wlasny plik CSV")
            self.path_var.set(selected)
            self.load_selected_data()

    def select_scenario(self, label: str) -> None:
        path = self.scenario_paths.get(label)
        if path is None:
            return
        self.path_var.set(str(path))
        self.load_selected_data()
        if self.jobs and path.resolve().is_relative_to((DATA_DIR / "esm/article").resolve()):
            self.method_vars["MOPT"].set(True)

    def load_default_data(self) -> None:
        if Path(self.path_var.get()).is_file():
            self.load_selected_data(show_error=False)

    def _source_path_changed(self, *_args) -> None:
        self._generation += 1
        self._source_dirty = True
        self.jobs = []
        self._loaded_path = None
        self._loaded_sha256 = ""
        self.settings_panel.refresh([])
        self._clear_results()
        self._replace_rows(self.input_tree, [])
        self.model_var.set("Dane wymagają ponownego wczytania.")
        self.context_var.set("Zmieniono ścieżkę. Kliknij Wczytaj, aby użyć nowego pliku.")
        self.status_var.set("Zmieniono ścieżkę — najpierw wczytaj dane.")

    def _source_ready(self) -> bool:
        if self._source_dirty:
            self.status_var.set("Najpierw kliknij Wczytaj — ścieżka została zmieniona.")
            return False
        if not self.jobs:
            self.load_selected_data()
        return bool(self.jobs)

    def select_method_preset(self, name: str) -> None:
        basic = {"MT", "MO", "MZO", "MOPT"}
        chosen = {"basic": basic, "extra": set(ESM_METHODS) - basic, "all": set(ESM_METHODS)}[name]
        for method, variable in self.method_vars.items():
            variable.set(
                method in chosen and self.method_checkboxes[method].cget("state") != "disabled"
            )
        self._methods_changed()

    def _methods_changed(self) -> None:
        self._generation += 1
        self._clear_results()
        self._update_model_label()
        count = sum(variable.get() for variable in self.method_vars.values())
        self.status_var.set(f"Wybrano {count} metod. Uruchom nowe porównanie.")

    def load_selected_data(self, *, show_error: bool = True, time_mode: str | None = None) -> None:
        try:
            source = Path(self.path_var.get()).resolve()
            source_bytes = source.read_bytes()
            jobs = load_esm_jobs(source)
            if source.read_bytes() != source_bytes:
                raise ValueError("Plik zmienił się podczas wczytywania. Wczytaj go ponownie.")
            self._generation += 1
            self.jobs = jobs
            self._loaded_path = str(source)
            self._loaded_sha256 = sha256(source_bytes).hexdigest()
            self._source_dirty = False
            self.objective_var.set(OBJECTIVES["cost" if esm_csv_has_costs(source_bytes) else "sto"])
            self._clear_results()
            flow = bool(jobs[0].machine_times)
            stages = len(jobs[0].machine_times)
            if flow:
                self.machine_var.set(str(stages))
            elif esm_csv_has_costs(source_bytes):
                self.machine_var.set("1")
            self.time_mode_var.set(ESM_TIME_MODES[time_mode or ("file" if flow else "total")])
            self.time_mode_menu.configure(
                values=[
                    ESM_TIME_MODES[key]
                    for key in (
                        ["total", "per_machine", "file"] if flow else ["total", "per_machine"]
                    )
                ]
            )
            self._update_model_label()
            self.input_tree.heading(
                "processing", text="Czasy M1 / M2 / ... [min]" if flow else "Czas obrobki [min]"
            )
            for method, checkbox in self.method_checkboxes.items():
                enabled = not flow or method in FLOW_METHODS
                checkbox.configure(state="normal" if enabled else "disabled")
                if not enabled:
                    self.method_vars[method].set(False)
            self._replace_rows(
                self.input_tree,
                [
                    (
                        job.job_id,
                        " / ".join(f"{t:g}" for t in job.machine_times)
                        if flow
                        else f"{job.processing_time:g}",
                        f"{job.deadline:g}",
                        "BRAK"
                        if job.stock_status == "UNSCHEDULABLE"
                        else f"{job.components_ready_h:g}",
                        " / ".join(filter(None, (job.material, job.shape))) or "-",
                        f"{job_penalty(job).rate_per_min:g}",
                        f"{job_penalty(job).grace_min:g}",
                    )
                    for job in self.jobs
                ],
            )
            self._replace_rows(self.result_tree, [])
            self.status_var.set(f"Wczytano {len(self.jobs)} zlecen. Mozesz uruchomic obliczenia.")
        except Exception as exc:
            self._generation += 1
            self.jobs = []
            self._loaded_path = None
            self._loaded_sha256 = ""
            self._source_dirty = True
            self._clear_results()
            self._replace_rows(self.input_tree, [])
            self.context_var.set(
                "Brak poprawnie wczytanych danych. Popraw ścieżkę i kliknij Wczytaj."
            )
            self.status_var.set("Nie udalo sie wczytac danych ESM.")
            if show_error:
                messagebox.showerror("Dane ESM", str(exc))

    def _clear_results(self) -> None:
        self.results = []
        self._result_context = None
        self.result_by_iid = {}
        self.analysis_warnings = []
        self._replace_rows(self.result_tree, [])
        self._set_summary(
            "Wczytaj dane i uruchom porownanie. Wynik dotyczy wybranej liczby maszyn."
        )
        for button in self.export_buttons:
            button.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        self.run_button.configure(state="disabled" if busy else "normal")
        if busy:
            self._analysis_started = perf_counter()
            self.progress.grid()
            self.progress.start()
            self.activity_var.set("Obliczenia trwają: 0.0 s — okno pozostaje aktywne.")
        else:
            self.progress.stop()
            self.progress.grid_remove()
            elapsed = perf_counter() - self._analysis_started
            self.activity_var.set(f"Zakończono obliczenia po {elapsed:.1f} s.")

    def _current_result_context(self) -> EngineeringContext:
        context = self._result_context
        if self._future is not None or not self.results or context is None:
            raise ValueError("Najpierw zakończ obliczenia dla bieżących danych.")
        if (
            self._source_dirty
            or str(Path(self.path_var.get()).resolve()) != context.source_path
            or int(self.machine_var.get()) != context.machine_count
            or self.time_mode_code() != context.time_mode
            or self.objective_code() != context.objective
            or json.loads(context.cost_parameters_json) != cost_parameters(self.jobs)
        ):
            raise ValueError("Wyniki dotyczą poprzednich ustawień. Wczytaj dane i oblicz ponownie.")
        return context

    def export_results(self, kind: str) -> None:
        try:
            context = self._current_result_context()
            rows = (comparison_rows if kind == "comparison" else operation_rows)(
                self.results, context
            )
            suffix = "porownanie" if kind == "comparison" else "operacje"
            initial_dir = BASE_DIR / "output"
            selected = filedialog.asksaveasfilename(
                parent=self,
                title="Zapisz wyniki ESM",
                initialdir=str(initial_dir if initial_dir.is_dir() else BASE_DIR),
                initialfile=f"{Path(context.source_path).stem}_{suffix}.csv",
                defaultextension=".csv",
                filetypes=[("CSV dla Excela", "*.csv")],
            )
            if not selected:
                return
            target = Path(selected).resolve()
            if target.is_relative_to((DATA_DIR / "esm").resolve()):
                raise ValueError("Zapisz wyniki poza data/esm, aby zachować dane wejściowe.")
            path = write_csv(target, rows, source_path=context.source_path)
            self.status_var.set(f"Zapisano {len(rows)} wierszy: {path}")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Eksport ESM", str(exc), parent=self)

    def copy_result_description(self) -> None:
        try:
            context = self._current_result_context()
            text = format_result_description(self._selected_result(), context)
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_var.set("Skopiowano opis wybranego wyniku do schowka.")
        except (ValueError, TclError) as exc:
            messagebox.showerror("Opis wyniku", str(exc), parent=self)

    def run_analysis(self, *, then=None, require_mopt: bool = False) -> None:
        if self._future is not None:
            self.status_var.set("Obliczenia trwaja. Poczekaj na zakonczenie biezacego porownania.")
            return
        try:
            if not self._source_ready():
                return
            selected = [method for method in ESM_METHODS if self.method_vars[method].get()]
            if require_mopt and "MOPT" not in selected:
                selected.append("MOPT")
            if not selected:
                raise ValueError("Wybierz przynajmniej jedna metode.")
            self._clear_results()
            generation = self._generation
            prepared = prepare_esm_flow_jobs(
                self.jobs, n_machines=int(self.machine_var.get()), time_mode=self.time_mode_code()
            )
            self.analysis_warnings = esm_method_warnings(prepared, selected)
            self._run_context = EngineeringContext(
                source_path=self._loaded_path or str(Path(self.path_var.get()).resolve()),
                machine_count=int(self.machine_var.get()),
                time_mode=self.time_mode_code(),
                source_sha256=self._loaded_sha256,
                objective=self.objective_code(),
                cost_parameters_json=json.dumps(
                    cost_parameters(self.jobs), ensure_ascii=False, sort_keys=True
                ),
            )
            self._future = self._executor.submit(
                evaluate_esm_methods,
                list(self.jobs),
                selected,
                n_machines=int(self.machine_var.get()),
                time_mode=self.time_mode_code(),
                objective=self.objective_code(),
            )
            self.status_var.set(
                "Obliczanie w tle... MOpt: do 10 s / 100 000 stanow. Okno pozostaje aktywne."
            )
            self._set_busy(True)
            self._poll_timer = self.after(60, lambda: self._poll_analysis(generation, then))
        except Exception as exc:
            messagebox.showerror("Obliczenia ESM", str(exc))
            self.status_var.set("Obliczenia nie zostaly wykonane.")

    def _poll_analysis(self, generation: int, then) -> None:
        self._poll_timer = None
        future = self._future
        if future is None:
            return
        if not future.done():
            self.activity_var.set(
                f"Obliczenia trwają: {perf_counter() - self._analysis_started:.1f} s — "
                "okno pozostaje aktywne."
            )
            self._poll_timer = self.after(60, lambda: self._poll_analysis(generation, then))
            return
        self._future = None
        self._set_busy(False)
        if generation != self._generation:
            self.status_var.set("Pominieto poprzedni wynik po zmianie danych lub liczby maszyn.")
            return
        try:
            self.results = future.result()
            self._result_context = self._run_context
            for index, result in enumerate(self.results, start=1):
                risk = result.get("risk_validation_summary", result.get("risk_summary", {}))
                iid = self.result_tree.insert(
                    "",
                    "end",
                    values=(
                        index,
                        METHOD_LABELS[result["method"]],
                        " -> ".join(result["order"]),
                        f"{result['sto']:g}",
                        f"{result['total_tardiness_cost']:.2f}",
                        f"{result['completion_total']:g}",
                        f"{result.get('total_waste_kg', 0):.2f}",
                        f"{risk['p90_makespan_min']:.2f}" if risk.get("available") else "-",
                        f"{risk['p90_tardiness_cost']:.2f}"
                        if risk.get("available") and "p90_tardiness_cost" in risk
                        else "-",
                        f"{result['elapsed_s']:.3f}" if "elapsed_s" in result else "-",
                        {
                            "OPTIMAL_CONFIRMED": "potwierdzone",
                            "GAP_TO_OPTIMUM": "gorszy wynik",
                            "BEST_KNOWN": "niepotwierdzone",
                            "CANDIDATE": "kandydat",
                            "PARTIAL_PLAN": "plan niepelny",
                            "RISK_ASSESSED": "ocena ryzyka",
                        }.get(result.get("optimality_status", ""), "-"),
                    ),
                )
                self.result_by_iid[iid] = result
            best = self.results[0]
            first_iid = next(iter(self.result_by_iid), "")
            if first_iid:
                self.result_tree.selection_set(first_iid)
            self._set_summary_for_result(best, self.analysis_warnings)
            self.status_var.set(f"Porownano {len(self.results)} metody. Wynik jest gotowy.")
            for button in self.export_buttons:
                button.configure(state="normal")
            if then:
                then()
        except Exception as exc:
            self._clear_results()
            messagebox.showerror("Obliczenia ESM", str(exc))
            self.status_var.set("Obliczenia nie zostaly wykonane.")

    def show_mopt_tree(self) -> None:
        try:
            if not self._source_ready():
                return
            mopt = next((r for r in self.results if r["method"] == "MOPT"), None)
            if mopt is None:
                self.run_analysis(then=self.show_mopt_tree, require_mopt=True)
                return
            solution = mopt["flowshop_solution"]
            nodes = build_mopt_solution_tree(
                list(solution.source_jobs),
                n_machines=int(self.machine_var.get()),
                solution=solution,
                max_nodes=45,
            )
            self._show_figure(
                "Drzewo MOpt - przeplyw",
                build_mopt_tree_figure(nodes),
                f"{mopt['search_status']}; kryterium: {OBJECTIVES[mopt.get('objective', 'sto')]}; "
                f"Odpad={mopt['total_waste_kg']:g} kg; STO={mopt['sto']:g} min; koszt={mopt['total_tardiness_cost']:g} j.p. "
                "Te same operacje i ograniczenia co w rankingu oraz na Gantcie. "
                "Zielone: najlepsza sciezka; zolte: sprawdzone; czerwone: odciecia.",
            )
        except Exception as exc:
            messagebox.showerror("Drzewo MOpt", str(exc))

    def show_gantt(self) -> None:
        try:
            selected = [method for method in ESM_METHODS if self.method_vars[method].get()]
            if not selected:
                raise ValueError("Wybierz przynajmniej jedna metode.")
            available = {result["method"]: result for result in self.results}
            if any(method not in available for method in selected):
                self.run_analysis(then=self.show_gantt)
                return
            self.gantt_window = GanttComparisonWindow(
                self, [available[method] for method in selected]
            )
        except Exception as exc:
            messagebox.showerror("Wykres Gantta", str(exc))

    def _show_figure(self, title: str, figure: Figure, note: str) -> None:
        window = ctk.CTkToplevel(self)
        window.title(title)
        window.geometry("1180x760")
        window.minsize(900, 600)
        toolbar_frame = ttk.Frame(window)
        toolbar_frame.pack(fill="x")
        viewport = ttk.Frame(window)
        viewport.pack(fill="both", expand=True, padx=8, pady=4)
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(0, weight=1)
        from tkinter import Canvas

        scroller = Canvas(viewport, background="#f8fafc", highlightthickness=0)
        scroller.grid(row=0, column=0, sticky="nsew")
        horizontal = ttk.Scrollbar(viewport, orient="horizontal", command=scroller.xview)
        vertical = ttk.Scrollbar(viewport, orient="vertical", command=scroller.yview)
        horizontal.grid(row=1, column=0, sticky="ew")
        vertical.grid(row=0, column=1, sticky="ns")
        scroller.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        host = ttk.Frame(scroller)
        scroller.create_window((0, 0), window=host, anchor="nw")
        canvas = FigureCanvasTkAgg(figure, master=host)
        canvas.draw()
        canvas.get_tk_widget().pack()
        host.bind("<Configure>", lambda _e: scroller.configure(scrollregion=scroller.bbox("all")))

        def center_chart() -> None:
            width = canvas.get_tk_widget().winfo_reqwidth()
            scroller.xview_moveto(max(0.0, 0.5 - scroller.winfo_width() / (2 * width)))

        window.after_idle(center_chart)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        dragging = False

        def start_drag(event) -> None:
            nonlocal dragging
            dragging = not bool(toolbar.mode)
            if dragging:
                scroller.scan_mark(event.x_root, event.y_root)

        def move_drag(event) -> None:
            if dragging and event.state & 0x0100 and not toolbar.mode:
                # Screen coordinates stay stable while the embedded plot moves.
                # Scroll the existing bitmap; do not redraw the Matplotlib tree.
                scroller.scan_dragto(event.x_root, event.y_root, gain=1)

        def stop_drag(_event) -> None:
            nonlocal dragging
            dragging = False

        for widget in (scroller, canvas.get_tk_widget()):
            widget.bind("<ButtonPress-1>", start_drag, add="+")
            widget.bind("<Double-Button-1>", start_drag, add="+")
            widget.bind("<Motion>", move_drag, add="+")
            widget.bind("<ButtonRelease-1>", stop_drag, add="+")
        ctk.CTkLabel(
            window,
            text="Przesuwanie widoku: przytrzymaj lewy przycisk myszy i przeciągnij. " + note,
            text_color=COLORS["text_muted"],
            wraplength=1100,
        ).pack(pady=(4, 12))
        window.lift()

    def _set_summary(self, text: str) -> None:
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", text)
        self.summary.configure(state="disabled")

    def _selected_result(self) -> dict:
        selected = self.result_tree.selection()
        if selected and selected[0] in self.result_by_iid:
            return self.result_by_iid[selected[0]]
        if self.results:
            return self.results[0]
        raise ValueError("Najpierw uruchom porownanie metod.")

    def _on_result_selected(self, _event=None) -> None:
        try:
            self._set_summary_for_result(self._selected_result(), self.analysis_warnings)
        except ValueError:
            return

    def _set_summary_for_result(self, result: dict, warnings: list[str]) -> None:
        lines = [
            f"Metoda: {METHOD_LABELS[result['method']]}",
            f"Kryterium: {OBJECTIVES[result.get('objective', 'sto')]}; koszt: {result.get('total_tardiness_cost', 0):g} j.p.",
            f"Kolejnosc: {' -> '.join(result['order'])}",
            (
                f"STO: {result['sto']:g} min; koniec: {result['completion_total']:g} min; "
                f"odpad: {result.get('total_waste_kg', 0):g} kg."
            ),
        ]
        if result.get("model") == "flowshop":
            proof = result.get("optimality_status") == "OPTIMAL_CONFIRMED"
            lines.append(
                f"Przeplyw przez {result['machine_count']} maszyn; "
                + ("optimum potwierdzone." if proof else "optimum tej metody niepotwierdzone.")
            )
            if "search_states" in result:
                lines.append(
                    f"MOpt: {result['search_states']} stanow, {result['search_pruned']} odciec; "
                    f"{result['elapsed_s']:.3f} s. {result.get('search_stop_reason', '')}"
                )
            lines.append(
                "Suma opoznien po ostatniej maszynie; kolejka wspolna dla wszystkich etapow."
            )
        risk = result.get("risk_summary")
        if risk:
            if risk.get("available"):
                lines.append(
                    f"Monte Carlo ({risk['iterations']} symulacji, ziarno {risk['seed']}): "
                    f"sredni koniec {risk['mean_makespan_min']:.2f} min; P90 {risk['p90_makespan_min']:.2f} min.\n"
                    f"Srednie opoznienie: {risk['mean_lateness_min']:.2f} min; "
                    f"P90 opoznienia: {risk['p90_lateness_min']:.2f} min. "
                    "Gantt przedstawia harmonogram nominalny."
                )
            else:
                lines.append("Monte Carlo: brak dopuszczonych operacji do symulacji.")
        unscheduled = int(result.get("unscheduled_count", 0))
        validation = result.get("risk_validation_summary", {})
        if validation.get("available") and "mean_tardiness_cost" in validation:
            lines.append(
                f"Niezależna weryfikacja kosztu: średnia {validation['mean_tardiness_cost']:.2f} j.p.; "
                f"P90 {validation['p90_tardiness_cost']:.2f} j.p. (ziarno {validation['seed']})."
            )
        if validation.get("available"):
            lines.append(
                f"Niezalezna weryfikacja ({validation['iterations']} symulacji, "
                f"ziarno {validation['seed']}): srednie opoznienie "
                f"{validation['mean_lateness_min']:.2f} min; "
                f"P90 {validation['p90_lateness_min']:.2f} min. "
                "Kolumna P90 przedstawia te serie; nie sluzy ona do ponownego wyboru planu."
            )
            if validation.get("mean_ci_available"):
                low, high = validation["mean_lateness_ci95_min"]
                lines.append(
                    f"Przyblizony przedzial 95% dla sredniego opoznienia: "
                    f"{low:.2f}-{high:.2f} min (nie przedzial pojedynczej realizacji)."
                )
        if unscheduled:
            lines.append(f"Niezaplanowane zlecenia: {unscheduled}.")
            if result.get("blocked_jobs"):
                lines.append("Brak kompletu komponentow: " + ", ".join(result["blocked_jobs"]))
        lines.extend(f"Uwaga: {warning}" for warning in warnings)
        self._set_summary("\n".join(lines))

    def time_mode_code(self) -> str:
        return next(
            key for key, label in ESM_TIME_MODES.items() if label == self.time_mode_var.get()
        )

    def _update_model_label(self) -> None:
        machines = int(self.machine_var.get())
        mode = self.time_mode_code()
        explanation = {
            "total": "Czas zlecenia dzielony na etapy podczas obliczen; CSV bez zmian.",
            "per_machine": "Podany czas wykonywany osobno na kazdej maszynie; CSV bez zmian.",
            "file": "Oryginalne czasy etapow z CSV.",
        }[mode]
        self.model_var.set(f"Przeplyw przez {machines} maszyn. {explanation}")
        self.settings_panel.refresh(self.jobs if not self._source_dirty else [])
        if self._loaded_path is not None and not self._source_dirty:
            self.context_var.set(
                f"Wczytano: {self._loaded_path}\n"
                f"Zlecenia: {len(self.jobs)} | Maszyny: {machines} | {ESM_TIME_MODES[mode]}"
                f" | Kryterium: {OBJECTIVES[self.objective_code()]}"
            )

    def _time_mode_changed(self, _value: str) -> None:
        self._generation += 1
        self._clear_results()
        self._update_model_label()
        self.status_var.set("Zmieniono sposob liczenia czasu. Utworz wykres ponownie.")

    def objective_code(self) -> str:
        return next(key for key, label in OBJECTIVES.items() if label == self.objective_var.get())

    def _objective_changed(self, _value: str) -> None:
        self._generation += 1
        self._clear_results()
        self._update_model_label()
        self.status_var.set("Zmieniono kryterium. Uruchom porównanie ponownie.")

    def show_cost_editor(self) -> None:
        if not self._source_ready():
            return
        if self.cost_editor is not None and self.cost_editor.winfo_exists():
            self.cost_editor.lift()
            return
        generation = self._generation
        self.cost_editor = EngineeringCostEditor(
            self,
            self.jobs,
            lambda parameters: self.apply_cost_parameters(parameters, generation=generation),
        )

    def apply_cost_parameters(
        self, parameters: dict[str, DelayPenalty], *, generation: int | None = None
    ) -> None:
        if (
            self._source_dirty
            or not self.jobs
            or (generation is not None and generation != self._generation)
        ):
            raise ValueError("Zmieniono dane lub ustawienia. Otwórz edytor kosztów ponownie.")
        self.jobs = with_job_penalties(self.jobs, parameters)
        self._generation += 1
        self._clear_results()
        for iid, job in zip(self.input_tree.get_children(), self.jobs, strict=True):
            self.input_tree.set(iid, "rate", f"{job_penalty(job).rate_per_min:g}")
            self.input_tree.set(iid, "grace", f"{job_penalty(job).grace_min:g}")
        self._update_model_label()
        self.status_var.set(
            "Zmieniono parametry kosztów w pamięci. CSV bez zmian; oblicz ponownie."
        )

    def _machine_changed(self, _value: str) -> None:
        if (
            self.jobs
            and self.time_mode_code() == "file"
            and any(len(job.machine_times) != int(self.machine_var.get()) for job in self.jobs)
        ):
            self.time_mode_var.set(ESM_TIME_MODES["total"])
        self._generation += 1
        self._clear_results()
        self._update_model_label()
        self.status_var.set(
            "Zmieniono liczbe maszyn. Czasy przeliczy program; utworz wykres ponownie."
        )

    def show_theory_gantts(self) -> None:
        try:
            if not self._source_ready():
                return
            top = self.winfo_toplevel()
            if hasattr(top, "show") and hasattr(top, "pages"):
                top.show("TheoryPage")
                top.pages["TheoryPage"].show_esm_comparison(
                    self.path_var.get(),
                    int(self.machine_var.get()),
                    self.time_mode_code(),
                    objective=self.objective_code(),
                    penalties={job.job_id: job_penalty(job) for job in self.jobs},
                )
            else:
                from AOA.gui.pages.theory_page.esm_comparison import EsmGanttComparison

                window = ctk.CTkToplevel(self)
                window.title("Teoria ESM - cztery Gantty")
                window.geometry("1280x900")
                comparison = EsmGanttComparison(window)
                comparison.pack(fill="both", expand=True)
                comparison.set_context(
                    self.path_var.get(),
                    int(self.machine_var.get()),
                    self.time_mode_code(),
                    objective=self.objective_code(),
                    penalties={job.job_id: job_penalty(job) for job in self.jobs},
                )
                comparison.run_analysis()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Porownanie Ganttow", str(exc))

    def destroy(self) -> None:
        self._generation += 1
        self.path_var.trace_remove("write", self._path_trace)
        if self._poll_timer is not None:
            self.after_cancel(self._poll_timer)
            self._poll_timer = None
        self.progress.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
        super().destroy()

    @staticmethod
    def _replace_rows(tree: ttk.Treeview, rows: list[tuple]) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", "end", values=row)
