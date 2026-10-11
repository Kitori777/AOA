from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from AOA.config import DATA_DIR
from AOA.core.esm_project import (
    ESM_MAX_MACHINES,
    ESM_METHODS,
    build_mopt_solution_tree,
    esm_method_warnings,
    evaluate_esm_methods,
    list_esm_scenarios,
    load_esm_jobs,
)
from AOA.core.optimization.models import Job
from AOA.gui.engineering_charts import build_esm_gantt_figure, build_mopt_tree_figure
from AOA.gui.theme import COLORS

METHOD_LABELS = {
    "MT": "MT / EDD",
    "MO": "MO / SPT",
    "MZO": "MZO / LPT",
    "MOPT": "MOpt",
    "ECO_WASTE": "ECO Waste",
    "COMPONENT_READY_EDD": "Component Ready + EDD",
    "ROBUST_MC": "Robust Monte Carlo",
}
METHOD_HELP = {
    "MT": "najpierw najblizszy wymagany termin realizacji",
    "MO": "najpierw najkrotszy czas obrobki",
    "MZO": "najpierw najdluzszy czas obrobki",
    "MOPT": "dokladne minimum sumy dodatnich opoznien",
    "ECO_WASTE": "ogranicza odpad i liczbe przezbrojen przy kontroli terminow",
    "COMPONENT_READY_EDD": "uwzglednia gotowosc komponentow, a potem termin realizacji",
    "ROBUST_MC": "porownuje kolejki w powtarzalnych scenariuszach awarii",
}


class EngineeringModePage(ctk.CTkFrame):
    """Focused ESM workspace used for the engineering thesis project."""

    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["app_bg"])
        self.scenarios = list_esm_scenarios(DATA_DIR / "esm")
        self.scenario_paths = {scenario.label: scenario.path for scenario in self.scenarios}
        default_path = DATA_DIR / "esm" / "esm_jobs.csv"
        default_label = next(
            (scenario.label for scenario in self.scenarios if scenario.path == default_path),
            "ESM Z1-Z4 (dane z PDF)",
        )
        self.scenario_var = ctk.StringVar(value=default_label)
        self.path_var = ctk.StringVar(value=str(default_path))
        self.machine_var = ctk.StringVar(value="1")
        self.status_var = ctk.StringVar(value="Gotowe. Wczytaj przyklad ESM i uruchom obliczenia.")
        self.method_vars = {
            method: ctk.BooleanVar(value=method in {"MT", "MO", "MZO", "MOPT"})
            for method in ESM_METHODS
        }
        self.jobs: list[Job] = []
        self.results: list[dict] = []
        self.result_by_iid: dict[str, dict] = {}
        self.analysis_warnings: list[str] = []

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
                "Od 1 do 3 maszyn, do 10 zlecen, minimalizacja sumy dodatnich opoznien. "
                "Wynik: porownanie metod, drzewo MOpt i Gantt wybranej metody."
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
        self.input_tree = ttk.Treeview(
            card,
            columns=("job", "processing", "deadline"),
            show="headings",
            height=5,
            style="Esm.Treeview",
        )
        for name, title, width in (
            ("job", "Zlecenie", 180),
            ("processing", "Czas obrobki [min]", 210),
            ("deadline", "Wymagany termin [min]", 240),
        ):
            self.input_tree.heading(name, text=title)
            self.input_tree.column(name, width=width, anchor="center", stretch=True)
        self.input_tree.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(6, 12))

    def _build_methods(self) -> None:
        card = ctk.CTkFrame(self.page, corner_radius=14, fg_color=COLORS["surface"])
        card.grid(row=2, column=0, sticky="ew", padx=18, pady=7)
        card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(card, text="2. Metody", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6)
        )
        machine_bar = ctk.CTkFrame(card, corner_radius=10, fg_color="#0d2a3a")
        machine_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=7, pady=6)
        machine_bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            machine_bar,
            text="Liczba maszyn",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=10)
        ctk.CTkSegmentedButton(
            machine_bar,
            values=[str(value) for value in range(1, ESM_MAX_MACHINES + 1)],
            variable=self.machine_var,
            command=self._machine_changed,
        ).grid(row=0, column=1, sticky="e", padx=12, pady=8)
        for index, method in enumerate(ESM_METHODS):
            row, column = divmod(index, 2)
            shell = ctk.CTkFrame(card, corner_radius=10, fg_color="#102333")
            shell.grid(row=row + 2, column=column, sticky="ew", padx=7, pady=6)
            ctk.CTkCheckBox(
                shell,
                text=METHOD_LABELS[method],
                variable=self.method_vars[method],
                font=("Segoe UI", 13, "bold"),
            ).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(
                shell,
                text=METHOD_HELP[method],
                text_color=COLORS["text_muted"],
                wraplength=500,
                justify="left",
            ).pack(anchor="w", padx=40, pady=(0, 10))
        action_row = 2 + (len(ESM_METHODS) + 1) // 2
        ctk.CTkButton(
            card,
            text="Oblicz i porownaj",
            command=self.run_analysis,
            height=42,
            font=("Segoe UI", 13, "bold"),
        ).grid(
            row=action_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=14,
            pady=(10, 12),
        )

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
                "Tworz wykresy bez szukania dodatkowych opcji. Gantt uzyje wyniku "
                "zaznaczonego w tabeli, a przed pierwszym uzyciem sam uruchomi obliczenia."
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
            text="Pokazuje rozgalezienia, odrzucone warianty i optymalna sciezke.",
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

        ctk.CTkLabel(
            gantt_card,
            text="Harmonogram Gantta",
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            gantt_card,
            text="Rysuje wybrana metode na 1-3 maszynach z terminami i przezbrojeniami.",
            text_color=COLORS["text_muted"],
            justify="left",
            wraplength=520,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
        ctk.CTkButton(
            gantt_card,
            text="UTWORZ WYKRES GANTTA",
            command=self.show_gantt,
            height=44,
            font=("Segoe UI", 13, "bold"),
            fg_color="#155e75",
            hover_color="#164e63",
        ).grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

    def _build_results(self) -> None:
        card = ctk.CTkFrame(self.page, corner_radius=14, fg_color=COLORS["surface"])
        card.grid(row=4, column=0, sticky="ew", padx=18, pady=(7, 16))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="4. Wyniki", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 6)
        )
        self.result_tree = ttk.Treeview(
            card,
            columns=("rank", "method", "order", "sto", "finish", "waste", "p90"),
            show="headings",
            height=7,
            style="Esm.Treeview",
        )
        headings = (
            ("rank", "Miejsce", 75),
            ("method", "Metoda", 120),
            ("order", "Kolejnosc", 330),
            ("sto", "Suma opoznien", 145),
            ("finish", "Koniec [min]", 130),
            ("waste", "Odpad [kg]", 115),
            ("p90", "P90 konca", 115),
        )
        for name, title, width in headings:
            self.result_tree.heading(name, text=title)
            self.result_tree.column(name, width=width, anchor="center", stretch=name == "order")
        self.result_tree.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_selected)
        self.summary = ctk.CTkTextbox(
            card,
            height=105,
            wrap="word",
            fg_color="#101f2d",
            font=("Segoe UI", 11),
        )
        self.summary.grid(row=2, column=0, sticky="ew", padx=14, pady=6)
        self.summary.insert(
            "1.0", "Po obliczeniu tutaj pojawi sie interpretacja najlepszego wyniku."
        )
        self.summary.configure(state="disabled")
        ctk.CTkLabel(
            card,
            textvariable=self.status_var,
            text_color="#8ddbd1",
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=14, pady=(6, 12))

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

    def load_default_data(self) -> None:
        if Path(self.path_var.get()).is_file():
            self.load_selected_data(show_error=False)

    def load_selected_data(self, *, show_error: bool = True) -> None:
        try:
            self.jobs = load_esm_jobs(self.path_var.get())
            self.results = []
            self.result_by_iid = {}
            self.analysis_warnings = []
            self._replace_rows(
                self.input_tree,
                [
                    (job.job_id, f"{job.processing_time:g}", f"{job.deadline:g}")
                    for job in self.jobs
                ],
            )
            self._replace_rows(self.result_tree, [])
            self.status_var.set(f"Wczytano {len(self.jobs)} zlecen. Mozesz uruchomic obliczenia.")
        except Exception as exc:
            self.status_var.set("Nie udalo sie wczytac danych ESM.")
            if show_error:
                messagebox.showerror("Dane ESM", str(exc))

    def run_analysis(self) -> None:
        try:
            if not self.jobs:
                self.jobs = load_esm_jobs(self.path_var.get())
            selected = [method for method in ESM_METHODS if self.method_vars[method].get()]
            self.results = evaluate_esm_methods(
                self.jobs,
                selected,
                n_machines=int(self.machine_var.get()),
            )
            self.analysis_warnings = esm_method_warnings(self.jobs, selected)
            self._replace_rows(self.result_tree, [])
            self.result_by_iid = {}
            for index, result in enumerate(self.results, start=1):
                risk = result.get("risk_summary", {})
                p90 = risk.get("p90_makespan_h")
                iid = self.result_tree.insert(
                    "",
                    "end",
                    values=(
                        index,
                        METHOD_LABELS[result["method"]],
                        " -> ".join(result["order"]),
                        f"{result['sto']:g}",
                        f"{result['completion_total']:g}",
                        f"{result.get('total_waste_kg', 0):g}",
                        "-" if p90 is None else f"{float(p90):.1f}",
                    ),
                )
                self.result_by_iid[iid] = result
            best = self.results[0]
            first_iid = next(iter(self.result_by_iid), "")
            if first_iid:
                self.result_tree.selection_set(first_iid)
            self._set_summary_for_result(best, self.analysis_warnings)
            self.status_var.set(f"Porownano {len(self.results)} metody. Wynik jest gotowy.")
        except Exception as exc:
            messagebox.showerror("Obliczenia ESM", str(exc))
            self.status_var.set("Obliczenia nie zostaly wykonane.")

    def show_mopt_tree(self) -> None:
        try:
            if not self.jobs:
                self.jobs = load_esm_jobs(self.path_var.get())
            nodes = build_mopt_solution_tree(self.jobs)
            figure = build_mopt_tree_figure(nodes)
            note = "Optymalna sciezka jest zielona; odrzucone warianty sa szare."
            if int(self.machine_var.get()) > 1:
                note += " Drzewo pokazuje dokladny problem kolejnosci dla jednej maszyny."
            if any(
                job.components_ready_h > 0
                or job.setup_time > 0
                or job.material
                for job in self.jobs
            ):
                note += (
                    " Drzewo MOpt uwzglednia czasy obrobki i terminy; komponenty, "
                    "przezbrojenia i odpady sa oceniane w rankingu oraz na wykresie Gantta."
                )
            self._show_figure("Drzewo rozwiazania MOpt", figure, note)
        except Exception as exc:
            messagebox.showerror("Drzewo MOpt", str(exc))

    def show_gantt(self) -> None:
        try:
            if not self.results:
                self.run_analysis()
            if not self.results:
                return
            result = self._selected_result()
            figure = build_esm_gantt_figure(result, METHOD_LABELS[result["method"]])
            self._show_figure(
                "Harmonogram Gantta", figure, "Linie kropkowane oznaczaja wymagane terminy zlecen."
            )
        except Exception as exc:
            messagebox.showerror("Wykres Gantta", str(exc))

    def _show_figure(self, title: str, figure: Figure, note: str) -> None:
        window = ctk.CTkToplevel(self)
        window.title(title)
        window.geometry("1180x760")
        window.minsize(900, 600)
        canvas = FigureCanvasTkAgg(figure, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(12, 4))
        ctk.CTkLabel(window, text=note, text_color=COLORS["text_muted"]).pack(pady=(4, 12))
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
            f"Kolejnosc: {' -> '.join(result['order'])}",
            (
                f"STO: {result['sto']:g} min; koniec: {result['completion_total']:g} min; "
                f"odpad: {result.get('total_waste_kg', 0):g} kg."
            ),
        ]
        risk = result.get("risk_summary")
        if risk:
            lines.append(
                "Monte Carlo: "
                f"sredni koniec {float(risk['mean_makespan_h']):.1f} min; "
                f"P90 {float(risk['p90_makespan_h']):.1f} min."
            )
        unscheduled = int(result.get("unscheduled_count", 0))
        if unscheduled:
            lines.append(f"Niezaplanowane zlecenia: {unscheduled}.")
        lines.extend(f"Uwaga: {warning}" for warning in warnings)
        self._set_summary("\n".join(lines))

    def _machine_changed(self, _value: str) -> None:
        self.results = []
        self.result_by_iid = {}
        self.analysis_warnings = []
        self._replace_rows(self.result_tree, [])
        self.status_var.set("Zmieniono liczbe maszyn. Uruchom obliczenia ponownie.")

    @staticmethod
    def _replace_rows(tree: ttk.Treeview, rows: list[tuple]) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", "end", values=row)
