from __future__ import annotations

import os
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import customtkinter as ctk
import pandas as pd

from AOA.config import DATA_DIR
from AOA.core.machine_catalog import MachineSpec
from AOA.core.mh_models import get_mh_model_specs
from AOA.core.planning import WeeklyPlan, WeeklyPlanningPolicy, WeeklyPlanStore
from AOA.core.production_line import StationSpec
from AOA.core.production_line_designer import ProductionLineDraft
from AOA.core.queue_machine_config import load_queue_machines, save_queue_machines
from AOA.core.queue_service import (
    QueueEvaluation,
    archive_completed_orders,
    evaluate_queue,
    load_latest_queue_results,
    load_queue_snapshot,
    mark_queue_item_done,
)
from AOA.gui.pages.main_page.machine_configuration_dialog import open_machine_configuration
from AOA.gui.queue_dialogs import (
    QueueDiagnosticsDialog,
    QueueHistoryDialog,
    ScenarioLabDialog,
)
from AOA.settings import load_settings, save_settings


@dataclass(frozen=True)
class QueueRefreshSignature:
    path: str
    mtime_ns: int
    machine_count: int
    methods: tuple[str, ...]
    objective: str
    unavailable_machines: tuple[int, ...]
    component_versions: tuple[int, int]
    planning_mode: str
    current_week_id: str
    weekly_plan: WeeklyPlan | None
    machine_specs: tuple[MachineSpec, ...]


class QueueDashboardPage(ctk.CTkFrame):
    """Live desktop dashboard backed by one local queue CSV file."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="#071019")
        settings = load_settings()
        default_path = DATA_DIR / "sample" / "schedule.csv"
        self.path_var = ctk.StringVar(value=settings.queue_csv_path or str(default_path))
        self.machine_var = ctk.StringVar(value="4")
        self.objective_labels = {
            "Terminy -> odpad -> czas": "deadline_then_waste",
            "Odpad -> terminy -> czas": "waste_then_deadline",
            "Czas -> terminy -> odpad": "makespan_then_deadline",
            "Zbalansowany": "balanced",
        }
        saved_objective = settings.queue_objective
        saved_label = next(
            (label for label, value in self.objective_labels.items() if value == saved_objective),
            "Terminy -> odpad -> czas",
        )
        self.objective_var = ctk.StringVar(value=saved_label)
        self.status_var = ctk.StringVar(value="Gotowe do wczytania kolejki.")
        self.weekly_status_var = ctk.StringVar(
            value="Tryb ciągły — plan aktualizuje się na bieżąco."
        )
        self.planning_mode_labels = {
            "Ciągły": "continuous",
            "Tygodniowy": "weekly",
        }
        saved_mode_label = next(
            (
                label
                for label, value in self.planning_mode_labels.items()
                if value == settings.queue_planning_mode
            ),
            "Ciągły",
        )
        self.planning_mode_var = ctk.StringVar(value=saved_mode_label)
        self.auto_var = ctk.BooleanVar(value=settings.queue_planning_mode != "weekly")
        self.all_models_var = ctk.BooleanVar(value=True)
        self.machine_state_vars: dict[int, ctk.BooleanVar] = {}
        self._saved_unavailable = {
            int(value)
            for value in settings.queue_unavailable_machines.replace(",", "|").split("|")
            if value.strip().isdigit()
        }
        self.model_vars: dict[str, ctk.BooleanVar] = {}
        self.kpi_labels: dict[str, ctk.CTkLabel] = {}
        self._busy = False
        self._last_evaluation: QueueEvaluation | None = None
        self._last_explanation_text = "Plan nie został jeszcze przeliczony."
        self._last_signature: QueueRefreshSignature | None = None
        self._poll_ms = max(1000, int(settings.queue_poll_seconds * 1000))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.page = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.page.grid(row=0, column=0, sticky="nsew")
        self.page.grid_columnconfigure(0, weight=1)
        self._configure_tree_style()
        self._build_header()
        self._build_controls()
        self._build_models()
        self._build_kpis()
        self._build_tables()
        self._load_cached_results()
        smoke_test = os.getenv("AOA_SMOKE_TEST", "").strip() == "1"
        if not smoke_test and not os.getenv("AOA_SMOKE_MARKER", "").strip():
            self.after(250, lambda: self.refresh(force=True))
            self.after(self._poll_ms, self._poll)

    def _configure_tree_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Queue.Treeview",
            background="#0f172a",
            foreground="#e5eef9",
            fieldbackground="#0f172a",
            rowheight=27,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Queue.Treeview.Heading",
            background="#17263a",
            foreground="#f8fafc",
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Queue.Treeview", background=[("selected", "#2563eb")])

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.page, corner_radius=16, fg_color="#0f1d2b")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 7))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Auto Queue — stale planowanie produkcji",
            font=("Segoe UI", 23, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 1))
        ctk.CTkLabel(
            header,
            text=(
                "Jeden plik CSV zasila kolejke, porownanie wszystkich heurystyk i plan maszyn. "
                "Zlecenia DONE sa automatycznie przenoszone do pliku archiwum."
            ),
            text_color="#a9bed0",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            fg_color="#113f6b",
            corner_radius=10,
            text_color="#d9efff",
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=16, pady=14)

    def _build_controls(self) -> None:
        controls = ctk.CTkFrame(self.page, corner_radius=14, fg_color="#111827")
        controls.grid(row=1, column=0, sticky="ew", padx=18, pady=7)
        controls.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(controls, text="Wybierz CSV", command=self._choose_file, width=110).grid(
            row=0, column=0, padx=(12, 6), pady=11
        )
        ctk.CTkEntry(controls, textvariable=self.path_var).grid(
            row=0, column=1, padx=6, pady=11, sticky="ew"
        )
        ctk.CTkLabel(controls, text="Maszyny:").grid(row=0, column=2, padx=(8, 2), pady=11)
        ctk.CTkOptionMenu(
            controls,
            variable=self.machine_var,
            values=[str(value) for value in range(1, 9)],
            width=72,
            command=self._machine_count_changed,
        ).grid(row=0, column=3, padx=6, pady=11)
        ctk.CTkCheckBox(
            controls,
            text="Auto 2 s",
            variable=self.auto_var,
            width=90,
        ).grid(row=0, column=4, padx=8, pady=11)
        ctk.CTkButton(
            controls,
            text="Odswiez teraz",
            command=lambda: self.refresh(force=True),
            width=116,
        ).grid(row=0, column=5, padx=(6, 12), pady=11)
        tool_row = ctk.CTkFrame(controls, fg_color="transparent")
        tool_row.grid(row=2, column=0, columnspan=6, sticky="ew", padx=12, pady=(0, 10))
        ctk.CTkButton(
            tool_row, text="Scenariusze co-jeśli", command=self._open_scenarios, width=155
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            tool_row, text="Historia i audyt", command=self._open_history, width=135
        ).pack(side="left", padx=8)
        ctk.CTkButton(tool_row, text="Diagnostyka", command=self._open_diagnostics, width=120).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            tool_row,
            text="Profile maszyn",
            command=self._open_machine_profiles,
            width=130,
            fg_color="#0f766e",
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            tool_row,
            text="Wyniki maszyn",
            command=self._open_machine_results,
            width=130,
            fg_color="#155e75",
        ).pack(side="left", padx=8)
        ctk.CTkLabel(
            controls,
            text="Jeden cel optymalizacji (dostepnosc komponentow zawsze jest warunkiem):",
            text_color="#9db4cc",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))
        ctk.CTkOptionMenu(
            controls,
            variable=self.objective_var,
            values=list(self.objective_labels),
            width=220,
            command=self._objective_changed,
        ).grid(row=1, column=2, columnspan=3, sticky="w", padx=6, pady=(0, 10))
        weekly_row = ctk.CTkFrame(controls, fg_color="transparent")
        weekly_row.grid(row=3, column=0, columnspan=6, sticky="ew", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            weekly_row,
            text="Tryb planowania:",
            text_color="#9db4cc",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            weekly_row,
            variable=self.planning_mode_var,
            values=list(self.planning_mode_labels),
            command=self._planning_mode_changed,
            width=130,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            weekly_row,
            text="Przygotuj następny tydzień",
            command=self._create_weekly_draft,
            width=190,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            weekly_row,
            text="Zatwierdź tydzień",
            command=self._approve_weekly_plan,
            width=145,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            weekly_row,
            text="Awaryjnie przeplanuj",
            command=self._emergency_replan,
            width=165,
            fg_color="#9a3412",
            hover_color="#7c2d12",
        ).pack(side="left", padx=4)
        ctk.CTkLabel(
            weekly_row,
            textvariable=self.weekly_status_var,
            text_color="#8ddbd1",
        ).pack(side="left", padx=12)

        machine_row = ctk.CTkFrame(controls, fg_color="transparent")
        machine_row.grid(row=4, column=0, columnspan=6, sticky="ew", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            machine_row,
            text="Stan maszyn (odznacz niedziałającą):",
            text_color="#9db4cc",
        ).pack(side="left", padx=(0, 8))
        self.machine_state_frame = ctk.CTkFrame(machine_row, fg_color="transparent")
        self.machine_state_frame.pack(side="left", fill="x", expand=True)
        self._sync_machine_controls()

    def _sync_machine_controls(self) -> None:
        if not hasattr(self, "machine_state_frame"):
            return
        for child in self.machine_state_frame.winfo_children():
            child.destroy()
        machine_count = int(self.machine_var.get())
        for machine_id in range(1, machine_count + 1):
            variable = self.machine_state_vars.get(machine_id)
            if variable is None:
                variable = ctk.BooleanVar(value=machine_id not in self._saved_unavailable)
                self.machine_state_vars[machine_id] = variable
            ctk.CTkCheckBox(
                self.machine_state_frame,
                text=f"M{machine_id}",
                variable=variable,
                command=self._machine_state_changed,
                width=58,
            ).pack(side="left", padx=4)

    def _unavailable_machines(self) -> tuple[int, ...]:
        machine_count = int(self.machine_var.get())
        return tuple(
            machine_id
            for machine_id in range(1, machine_count + 1)
            if not self.machine_state_vars[machine_id].get()
        )

    def _save_machine_state(self) -> None:
        unavailable = self._unavailable_machines()
        settings = load_settings()
        save_settings(
            replace(
                settings,
                queue_unavailable_machines="|".join(map(str, unavailable)),
            )
        )

    def _machine_count_changed(self, _value: str) -> None:
        self._sync_machine_controls()
        self._save_machine_state()
        self._last_signature = None
        self.refresh(force=True)

    def _machine_state_changed(self) -> None:
        self._save_machine_state()
        self._last_signature = None
        self.refresh(force=True)

    def _build_models(self) -> None:
        shell = ctk.CTkFrame(self.page, corner_radius=14, fg_color="#0c1b28")
        shell.grid(row=2, column=0, sticky="ew", padx=18, pady=7)
        shell.grid_columnconfigure(0, weight=1)
        ctk.CTkCheckBox(
            shell,
            text="Wszystkie modele",
            variable=self.all_models_var,
            command=self._toggle_all_models,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.model_frame = ctk.CTkFrame(
            shell,
            fg_color="#0f2030",
            corner_radius=10,
        )
        self.model_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        for column in range(4):
            self.model_frame.grid_columnconfigure(column, weight=1)
        self._sync_model_controls()

    def _sync_model_controls(self) -> None:
        specs = get_mh_model_specs()
        known = set(self.model_vars)
        for visible_index, spec in enumerate(specs):
            if spec.name in known:
                continue
            variable = ctk.BooleanVar(value=True)
            self.model_vars[spec.name] = variable
            row, column = divmod(visible_index, 4)
            checkbox = ctk.CTkCheckBox(
                self.model_frame,
                text=spec.label,
                variable=variable,
                command=self._model_selection_changed,
                width=118,
            )
            checkbox.grid(row=row * 2, column=column, padx=12, pady=(8, 1), sticky="w")
            ctk.CTkLabel(
                self.model_frame,
                text=spec.focus,
                text_color="#89a4ba",
                font=("Segoe UI", 9),
                justify="left",
                wraplength=250,
            ).grid(row=row * 2 + 1, column=column, padx=12, pady=(0, 8), sticky="nw")

    def _build_kpis(self) -> None:
        kpis = ctk.CTkFrame(self.page, fg_color="transparent")
        kpis.grid(row=3, column=0, sticky="ew", padx=18, pady=7)
        for column in range(3):
            kpis.grid_columnconfigure(column, weight=1)
        cards = (
            ("active", "Aktywne"),
            ("blocked", "Zablokowane"),
            ("models", "Porownane modele"),
            ("best", "Najlepszy model"),
            ("sto", "STO"),
            ("waste", "Odpad kg"),
        )
        for index, (key, title) in enumerate(cards):
            row, column = divmod(index, 3)
            card = ctk.CTkFrame(kpis, corner_radius=13, fg_color="#102333")
            card.grid(row=row, column=column, sticky="ew", padx=4, pady=4)
            ctk.CTkLabel(card, text=title, text_color="#91a7ba", font=("Segoe UI", 10)).pack(
                pady=(8, 1)
            )
            label = ctk.CTkLabel(card, text="—", font=("Segoe UI", 18, "bold"))
            label.pack(pady=(0, 8))
            self.kpi_labels[key] = label

    def _new_tree(self, parent, columns: tuple[str, ...], headings: tuple[str, ...], height: int):
        tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=height,
            style="Queue.Treeview",
        )
        for column, heading in zip(columns, headings, strict=True):
            tree.heading(column, text=heading)
            tree.column(column, width=105, minwidth=70, anchor="center", stretch=True)
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return tree

    def _build_tables(self) -> None:
        body = ctk.CTkFrame(self.page, fg_color="transparent")
        body.grid(row=4, column=0, sticky="ew", padx=18, pady=(7, 14))
        body.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(body, corner_radius=14, fg_color="#0c1b28")
        left.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(left, text="Ranking heurystyk", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        self.ranking_tree = self._new_tree(
            left,
            ("model", "quality", "sto", "makespan", "waste", "missing"),
            ("Model", "Jakosc", "STO", "Koniec h", "Odpad kg", "Braki"),
            7,
        )
        ctk.CTkLabel(
            left,
            text="Kolejka 1 — kompletność komponentów",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=12, pady=(2, 6))
        self.queue_tree = self._new_tree(
            left,
            (
                "id",
                "operation",
                "customer",
                "product",
                "time",
                "due",
                "components",
                "status",
            ),
            (
                "Zlecenie",
                "Operacja",
                "Klient",
                "Produkt",
                "Czas",
                "Termin",
                "Komponenty",
                "Status",
            ),
            7,
        )
        ctk.CTkButton(
            left,
            text="Oznacz wybraną operację jako DONE i archiwizuj",
            command=self._complete_selected,
            height=34,
        ).pack(fill="x", padx=10, pady=(0, 10))

        right = ctk.CTkFrame(body, corner_radius=14, fg_color="#0c1b28")
        right.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(
            right,
            text="Kolejka 2 — dokładne wykonanie na maszynach",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 6))
        self.schedule_tree = self._new_tree(
            right,
            ("lp", "operation", "job", "machine", "start", "end", "delay", "frozen"),
            ("Lp", "Operacja", "Zlecenie", "Maszyna", "Start", "Koniec", "Opozn.", "Blokada"),
            12,
        )
        self.explanation_box = ctk.CTkTextbox(
            right, height=112, wrap="word", fg_color="#101f2d", font=("Segoe UI", 11)
        )
        self.explanation_box.pack(fill="x", padx=10, pady=(0, 8))
        self._set_explanation(
            "Po przeliczeniu tutaj pojawi się uzasadnienie planu i wąskie gardła."
        )
        ctk.CTkLabel(
            right,
            text=(
                "Plik archiwum powstaje obok kolejki jako schedule_archive.csv. "
                "Dopisane zlecenia sa wykrywane automatycznie."
            ),
            text_color="#91a7ba",
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Wybierz plik kolejki CSV",
            filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")],
            initialdir=str(Path(self.path_var.get()).parent),
        )
        if not selected:
            return
        self.path_var.set(selected)
        settings = load_settings()
        save_settings(replace(settings, queue_csv_path=selected))
        self._last_signature = None
        self.refresh(force=True)

    def _open_scenarios(self) -> None:
        try:
            ScenarioLabDialog(
                self,
                queue_path=self.path_var.get(),
                machine_count=int(self.machine_var.get()),
                unavailable_machines=self._unavailable_machines(),
            ).focus_force()
        except Exception as exc:
            self.status_var.set(f"Nie można otworzyć scenariuszy: {exc}")

    def open_scenario_lab(self) -> None:
        self._open_scenarios()

    def _open_history(self) -> None:
        QueueHistoryDialog(self, queue_path=self.path_var.get()).focus_force()

    def open_history(self) -> None:
        self._open_history()

    def _open_diagnostics(self) -> None:
        QueueDiagnosticsDialog(self, queue_path=self.path_var.get()).focus_force()

    def _open_machine_profiles(self) -> None:
        try:
            machine_count = int(self.machine_var.get())
            machines = load_queue_machines(self.path_var.get(), machine_count)
            draft = ProductionLineDraft(
                line_id="auto_queue",
                name="Auto Queue",
                stations=[StationSpec("QUEUE", "Auto Queue", machine_count)],
                machines=list(machines),
            )
        except Exception as exc:
            self.status_var.set(f"Nie można wczytać profili maszyn: {exc}")
            return

        def save_profiles() -> None:
            path = save_queue_machines(self.path_var.get(), draft.machines)
            self._last_signature = None
            self.status_var.set(f"Zapisano profile maszyn: {path.name}")
            self.refresh(force=True)

        open_machine_configuration(
            self,
            draft,
            on_save=save_profiles,
            show_routes=False,
        ).focus_force()

    def _open_machine_results(self) -> None:
        evaluation = self._last_evaluation
        if evaluation is None or not evaluation.machine_efficiency:
            messagebox.showinfo(
                "Brak wyników",
                "Najpierw przelicz kolejkę z przynajmniej jedną wykonalną operacją.",
                parent=self,
            )
            return
        report = pd.DataFrame(list(evaluation.machine_efficiency))
        risk = evaluation.risk_summary
        window = ctk.CTkToplevel(self)
        window.title("Auto Queue — efektywność i ryzyko maszyn")
        window.geometry("1280x720")
        window.minsize(960, 560)
        window.transient(self.winfo_toplevel())
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            window,
            text="Efektywność i ryzyko maszyn Auto Queue",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 8))
        cards = ctk.CTkFrame(window, corner_radius=14)
        cards.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        card_values = (
            ("Maszyny", len(report)),
            ("Śr. wykorzystanie", f"{report['utilization_pct'].mean():.1f}%"),
            ("Szacowane OEE", f"{report['estimated_oee_pct'].mean():.1f}%"),
            ("Śr. przestój", f"{float(risk.get('mean_downtime_h', 0)):.2f} h"),
            ("P90 czasu planu", f"{float(risk.get('p90_makespan_h', 0)):.2f} h"),
            ("Ryzyko awarii", f"{float(risk.get('failure_probability', 0)) * 100:.1f}%"),
        )
        for column, (label, value) in enumerate(card_values):
            cards.grid_columnconfigure(column, weight=1)
            card = ctk.CTkFrame(cards, fg_color="#0f172a", corner_radius=12)
            card.grid(row=0, column=column, sticky="nsew", padx=5, pady=7)
            ctk.CTkLabel(card, text=label, text_color="#94a3b8").pack(pady=(8, 1))
            ctk.CTkLabel(card, text=str(value), font=("Segoe UI", 17, "bold")).pack(pady=(0, 8))
        shell = ctk.CTkFrame(window, corner_radius=14)
        shell.grid(row=2, column=0, sticky="nsew", padx=18, pady=8)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(0, weight=1)
        tree = ttk.Treeview(shell, show="headings", style="Queue.Treeview")
        columns = [str(column) for column in report.columns]
        tree.configure(columns=columns)
        for column_name in columns:
            tree.heading(column_name, text=column_name)
            tree.column(column_name, width=125, minwidth=82, stretch=False)
        for _, row in report.iterrows():
            tree.insert(
                "",
                "end",
                values=[f"{value:.4g}" if isinstance(value, float) else value for value in row],
            )
        tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        y_scroll = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns", pady=(8, 0))
        x_scroll = ttk.Scrollbar(shell, orient="horizontal", command=tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        def export_report() -> None:
            path = filedialog.asksaveasfilename(
                parent=window,
                title="Eksport wyników maszyn",
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv")],
            )
            if path:
                report.to_csv(path, index=False)
                messagebox.showinfo("Zapisano", f"Zapisano raport:\n{path}", parent=window)

        footer = ctk.CTkFrame(window, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text="Monte Carlo: 1000 powtórzeń; P90 pokazuje bezpieczniejszy wariant planistyczny.",
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(footer, text="Eksport CSV", command=export_report).grid(
            row=0, column=1, padx=6
        )
        ctk.CTkButton(footer, text="Zamknij", command=window.destroy).grid(row=0, column=2)

    def open_diagnostics(self) -> None:
        self._open_diagnostics()

    def explain_current_plan(self) -> str:
        return self._last_explanation_text

    def _set_explanation(self, text: str) -> None:
        self._last_explanation_text = text
        self.explanation_box.configure(state="normal")
        self.explanation_box.delete("1.0", "end")
        self.explanation_box.insert("1.0", text)
        self.explanation_box.configure(state="disabled")

    def _toggle_all_models(self) -> None:
        state = self.all_models_var.get()
        for variable in self.model_vars.values():
            variable.set(state)
        self.refresh(force=True)

    def _model_selection_changed(self) -> None:
        self.all_models_var.set(all(variable.get() for variable in self.model_vars.values()))
        self.refresh(force=True)

    def _selected_methods(self) -> tuple[str, ...]:
        return tuple(name for name, variable in self.model_vars.items() if variable.get())

    def _objective(self) -> str:
        return self.objective_labels[self.objective_var.get()]

    def _objective_changed(self, _label: str) -> None:
        settings = load_settings()
        save_settings(replace(settings, queue_objective=self._objective()))
        self._last_signature = None
        self.refresh(force=True)

    def _planning_mode(self) -> str:
        return self.planning_mode_labels[self.planning_mode_var.get()]

    @staticmethod
    def _weekly_policy() -> WeeklyPlanningPolicy:
        settings = load_settings()
        return WeeklyPlanningPolicy(
            timezone=settings.queue_timezone,
            week_start_hour=settings.queue_week_start_hour,
            workdays=settings.queue_workdays,
            workday_hours=settings.queue_workday_hours,
        )

    @staticmethod
    def _weekly_store(path: str | Path) -> WeeklyPlanStore:
        return WeeklyPlanStore(DATA_DIR / "weekly_plans", path)

    def _planning_mode_changed(self, _label: str) -> None:
        settings = load_settings()
        mode = self._planning_mode()
        save_settings(replace(settings, queue_planning_mode=mode))
        self.auto_var.set(mode == "continuous")
        self._last_signature = None
        self.refresh(force=True)

    def _create_weekly_draft(self) -> None:
        evaluation = self._last_evaluation
        if evaluation is None or evaluation.operation_plan is None:
            self.status_var.set("Najpierw przelicz kolejkę, aby przygotować plan tygodniowy.")
            return
        try:
            policy = self._weekly_policy()
            store = self._weekly_store(self.path_var.get())
            active_plan = store.current_plan(policy)
            plan = store.create_draft(
                target_week_start=policy.next_week_start(),
                policy=policy,
                result=evaluation.operation_plan,
                source_queue_hash=evaluation.snapshot.storage_entry.version,
                source_run_id=evaluation.run_id,
                start_offset_h=policy.horizon_hours if active_plan is not None else 0.0,
                exclude_frozen=active_plan is not None,
            )
        except Exception as exc:
            self.status_var.set(f"Nie udało się utworzyć szkicu tygodnia: {exc}")
            return
        self.weekly_status_var.set(
            f"Szkic {plan.plan_id}, wersja {plan.version}, operacje: {len(plan.items)}."
        )
        self.status_var.set("Szkic zapisany. Sprawdź plan i użyj „Zatwierdź tydzień”.")

    def _approve_weekly_plan(self) -> None:
        try:
            policy = self._weekly_policy()
            store = self._weekly_store(self.path_var.get())
            upcoming = store.upcoming_plan(policy)
            if upcoming is None:
                raise FileNotFoundError("Najpierw przygotuj szkic następnego tygodnia.")
            if not messagebox.askyesno(
                "Zatwierdzenie planu",
                f"Zatwierdzić plan {upcoming.plan_id} z {len(upcoming.items)} operacjami?\n\n"
                "Po rozpoczęciu tego tygodnia plan nie zmieni się automatycznie.",
                parent=self,
            ):
                return
            approved = store.approve(upcoming.plan_id, policy=policy)
        except Exception as exc:
            self.status_var.set(f"Nie udało się zatwierdzić tygodnia: {exc}")
            return
        self.weekly_status_var.set(f"Zatwierdzony {approved.plan_id}, wersja {approved.version}.")
        self._last_signature = None
        self.refresh(force=True)

    def _emergency_replan(self) -> None:
        try:
            policy = self._weekly_policy()
            store = self._weekly_store(self.path_var.get())
            active = store.current_plan(policy)
            if active is None or active.effective_status(policy=policy) != "ACTIVE":
                raise ValueError("Brak aktywnego, zatwierdzonego tygodnia.")
        except Exception as exc:
            self.status_var.set(f"Nie można rozpocząć awaryjnego przeplanowania: {exc}")
            return
        reason = simpledialog.askstring(
            "Awaryjne przeplanowanie",
            "Podaj powód zmiany aktywnego tygodnia:",
            parent=self,
        )
        if reason is None:
            return
        if not reason.strip():
            self.status_var.set("Awaryjne przeplanowanie wymaga podania powodu.")
            return
        if not messagebox.askyesno(
            "Potwierdź zmianę",
            "Utworzyć nową, audytowaną wersję aktywnego planu?",
            parent=self,
        ):
            return
        self._busy = True
        self.status_var.set("Tworzę awaryjny wariant planu w tle...")
        signature = self._signature()
        threading.Thread(
            target=self._emergency_replan_worker,
            args=(active, reason.strip(), signature),
            daemon=True,
        ).start()

    def _emergency_replan_worker(
        self,
        active: WeeklyPlan,
        reason: str,
        signature: QueueRefreshSignature,
    ) -> None:
        try:
            path = Path(signature.path)
            evaluation = evaluate_queue(
                load_queue_snapshot(path),
                selected_methods=list(signature.methods),
                n_machines=signature.machine_count,
                objective=signature.objective,
                unavailable_machines=signature.unavailable_machines,
                machine_specs=signature.machine_specs,
            )
            if evaluation.operation_plan is None:
                raise ValueError("Algorytm nie zwrócił planu operacji.")
            policy = self._weekly_policy()
            replacement = self._weekly_store(path).emergency_replan(
                active.plan_id,
                policy=policy,
                result=evaluation.operation_plan,
                reason=reason,
                source_queue_hash=evaluation.snapshot.storage_entry.version,
                source_run_id=evaluation.run_id,
            )
        except Exception as exc:
            message = str(exc)
            self.after(0, lambda: self._show_error(message))
            return
        self.after(0, lambda: self._finish_emergency_replan(replacement))

    def _finish_emergency_replan(self, plan: WeeklyPlan) -> None:
        self._busy = False
        self.weekly_status_var.set(f"Plan awaryjny {plan.plan_id}, wersja {plan.version}.")
        self._last_signature = None
        self.refresh(force=True)

    def _signature(
        self,
    ) -> QueueRefreshSignature:
        path = Path(self.path_var.get()).resolve()
        stat = path.stat()
        bom_path = path.with_name("bom.csv")
        inventory_path = path.with_name("inventory.csv")
        component_versions = (
            bom_path.stat().st_mtime_ns if bom_path.is_file() else -1,
            inventory_path.stat().st_mtime_ns if inventory_path.is_file() else -1,
        )
        mode = self._planning_mode()
        current_week_id = ""
        weekly_plan = None
        if mode == "weekly":
            policy = self._weekly_policy()
            current_week_id = policy.week_id(policy.week_start())
            weekly_plan = self._weekly_store(path).current_plan(policy)
        return QueueRefreshSignature(
            path=str(path),
            mtime_ns=stat.st_mtime_ns,
            machine_count=int(self.machine_var.get()),
            methods=self._selected_methods(),
            objective=self._objective(),
            unavailable_machines=self._unavailable_machines(),
            component_versions=component_versions,
            planning_mode=mode,
            current_week_id=current_week_id,
            weekly_plan=weekly_plan,
            machine_specs=load_queue_machines(path, int(self.machine_var.get())),
        )

    def _poll(self) -> None:
        if self.auto_var.get():
            self.refresh()
        self.after(self._poll_ms, self._poll)

    def refresh(self, force: bool = False) -> None:
        self._sync_model_controls()
        if self._busy:
            return
        methods = self._selected_methods()
        if not methods:
            self.status_var.set("Wybierz przynajmniej jeden model.")
            return
        try:
            signature = self._signature()
        except (OSError, ValueError) as exc:
            self.status_var.set(f"Nie mozna otworzyc CSV: {exc}")
            return
        if not force and signature == self._last_signature:
            return
        self._busy = True
        self.status_var.set("Licze warianty w tle...")
        threading.Thread(
            target=self._evaluate_worker,
            args=(signature,),
            daemon=True,
        ).start()

    def _evaluate_worker(self, signature: QueueRefreshSignature) -> None:
        try:
            path = Path(signature.path)
            archived = archive_completed_orders(path)
            weekly_policy = self._weekly_policy() if signature.planning_mode == "weekly" else None
            evaluation = evaluate_queue(
                load_queue_snapshot(path),
                selected_methods=list(signature.methods),
                n_machines=signature.machine_count,
                objective=signature.objective,
                unavailable_machines=signature.unavailable_machines,
                weekly_policy=weekly_policy,
                weekly_plan=signature.weekly_plan,
                machine_specs=signature.machine_specs,
            )
        except Exception as exc:
            message = str(exc)
            self.after(0, lambda message=message: self._show_error(message))
            return
        self.after(0, lambda: self._apply_evaluation(evaluation, archived, signature))

    def _show_error(self, message: str) -> None:
        self._busy = False
        self.status_var.set(f"Blad kolejki: {message}")

    @staticmethod
    def _clear_tree(tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def _apply_evaluation(
        self,
        evaluation: QueueEvaluation,
        archived: int,
        signature: QueueRefreshSignature,
    ) -> None:
        self._busy = False
        self._last_signature = signature
        self._last_evaluation = evaluation
        snapshot = evaluation.snapshot
        best = evaluation.best
        component_queue = evaluation.component_queue
        admitted_count = len(component_queue.admitted) if component_queue is not None else 0
        component_blocked_count = (
            len(component_queue.unschedulable) if component_queue is not None else 0
        )
        values = {
            "active": str(admitted_count),
            "blocked": str(snapshot.blocked["zlecenie_id"].nunique() + component_blocked_count),
            "models": str(len(evaluation.results)),
            "best": str(best["method"]) if best else "—",
            "sto": (
                f"{evaluation.operation_plan.total_tardiness_h:.2f}"
                if evaluation.operation_plan is not None
                else f"{best['sto']:.2f}"
                if best
                else "0.00"
            ),
            "waste": f"{best['total_waste_kg']:.2f}" if best else "0.00",
        }
        for key, value in values.items():
            self.kpi_labels[key].configure(text=value)

        self._clear_tree(self.ranking_tree)
        for result in evaluation.results:
            self.ranking_tree.insert(
                "",
                "end",
                values=(
                    result["method"],
                    self._quality_label(result.get("optimality_status", "")),
                    f"{result['sto']:.2f}",
                    f"{result['makespan_h']:.2f}",
                    f"{result['total_waste_kg']:.2f}",
                    result["unscheduled_count"],
                ),
            )

        self._clear_tree(self.queue_tree)
        for _, row in snapshot.frame.iterrows():
            queue_id = str(row["queue_item_id"])
            self.queue_tree.insert(
                "",
                "end",
                iid=queue_id,
                values=(
                    row.get("zlecenie_id", ""),
                    row.get("operation_id", ""),
                    row.get("klient", ""),
                    row.get("produkt", ""),
                    row.get("czas_produkcji_h", ""),
                    row.get("termin_h", ""),
                    (
                        component_queue.status_for(row.get("zlecenie_id", ""))
                        if component_queue is not None and str(row.get("status", "")) != "BLOCKED"
                        else "BŁĄD DANYCH"
                    ),
                    row.get("status", ""),
                ),
            )

        self._clear_tree(self.schedule_tree)
        if evaluation.operation_plan is not None:
            for lp, step in enumerate(evaluation.operation_plan.steps, start=1):
                self.schedule_tree.insert(
                    "",
                    "end",
                    values=(
                        lp,
                        step.operation_id,
                        step.order_id,
                        step.machine_id,
                        f"{step.start_h:.2f}",
                        f"{step.end_h:.2f}",
                        f"{step.tardiness_h:.2f}",
                        "TAK" if step.frozen or step.started else "nie",
                    ),
                )
        elif best:
            for legacy_step in best["steps"]:
                self.schedule_tree.insert(
                    "",
                    "end",
                    values=(
                        legacy_step["lp"],
                        legacy_step["job_id"],
                        legacy_step["job_id"],
                        legacy_step["machine_id"],
                        f"{legacy_step['start_time']:.2f}" if legacy_step["scheduled"] else "—",
                        f"{legacy_step['completion_time']:.2f}"
                        if legacy_step["scheduled"]
                        else "—",
                        f"{legacy_step['tardiness_positive']:.2f}",
                        "nie",
                    ),
                )
        if evaluation.explanation is not None:
            explanation_lines = [evaluation.explanation.summary]
            explanation_lines.extend(
                f"Wąskie gardło: {item}" for item in evaluation.explanation.bottlenecks
            )
            explanation_lines.extend(
                f"Zalecenie: {item}" for item in evaluation.explanation.recommendations
            )
            self._set_explanation("\n".join(explanation_lines))
        archive_note = f" Zarchiwizowano: {archived}." if archived else ""
        warning_note = (
            f" {evaluation.persistence_warning}" if evaluation.persistence_warning else ""
        )
        machine_note = (
            " Wyłączone maszyny: "
            + ", ".join(f"M{value}" for value in evaluation.unavailable_machines)
            + "."
            if evaluation.unavailable_machines
            else " Wszystkie maszyny działają."
        )
        weekly_note = ""
        if signature.planning_mode == "weekly":
            if evaluation.weekly_status == "ACTIVE":
                self.weekly_status_var.set(
                    f"Aktywny {evaluation.weekly_plan_id}, wersja "
                    f"{evaluation.weekly_plan_version}; blokady: {evaluation.weekly_locked_count}."
                )
            elif evaluation.weekly_status == "MISSING":
                self.weekly_status_var.set(
                    f"Brak zatwierdzonego planu na {signature.current_week_id}."
                )
            else:
                self.weekly_status_var.set(
                    f"Plan {evaluation.weekly_plan_id}: {evaluation.weekly_status}."
                )
            if evaluation.weekly_alerts:
                weekly_note = " Alerty tygodnia: " + " | ".join(evaluation.weekly_alerts)
        else:
            self.weekly_status_var.set("Tryb ciągły — plan aktualizuje się na bieżąco.")
        self.status_var.set(
            f"Kolejka 1: {admitted_count} dopuszczonych, "
            f"{component_blocked_count} bez kompletu. "
            f"Kolejka 2: {len(evaluation.operation_plan.steps) if evaluation.operation_plan else 0} "
            f"operacji, {len(evaluation.results)} modeli."
            f"{machine_note}"
            f" Przebieg: {evaluation.run_id or 'niezapisany'}."
            f"{archive_note}{warning_note}{weekly_note}"
        )

    @staticmethod
    def _quality_label(status: str) -> str:
        return {
            "OPTIMAL_CONFIRMED": "Optimum",
            "GAP_TO_OPTIMUM": "Luka",
            "BEST_KNOWN": "Najlepszy",
            "CANDIDATE": "Kandydat",
        }.get(status, status or "—")

    def _load_cached_results(self) -> None:
        try:
            ranking, schedule = load_latest_queue_results(self.path_var.get())
        except (OSError, ValueError, FileNotFoundError):
            return
        self._clear_tree(self.ranking_tree)
        for _, row in ranking.iterrows():
            self.ranking_tree.insert(
                "",
                "end",
                values=(
                    row.get("method", ""),
                    self._quality_label(str(row.get("optimality_status", ""))),
                    row.get("sto", ""),
                    row.get("makespan_h", ""),
                    row.get("total_waste_kg", ""),
                    row.get("unscheduled_count", ""),
                ),
            )
        self._clear_tree(self.schedule_tree)
        for _, step in schedule.iterrows():
            scheduled = str(step.get("scheduled", "True")).lower() == "true"
            self.schedule_tree.insert(
                "",
                "end",
                values=(
                    step.get("lp", ""),
                    step.get("operation_id", step.get("job_id", "")),
                    step.get("job_id", ""),
                    step.get("machine_id", ""),
                    step.get("start_time", "") if scheduled else "—",
                    step.get("completion_time", "") if scheduled else "—",
                    step.get("tardiness_positive", ""),
                    "TAK"
                    if str(step.get("frozen", "False")).lower() == "true"
                    or str(step.get("started", "False")).lower() == "true"
                    else "nie",
                ),
            )
        if not ranking.empty:
            first = ranking.iloc[0]
            self.kpi_labels["models"].configure(text=str(len(ranking)))
            self.kpi_labels["best"].configure(text=str(first.get("method", "—")))
            self.kpi_labels["sto"].configure(text=str(first.get("sto", "0.00")))
            self.kpi_labels["waste"].configure(text=str(first.get("total_waste_kg", "0.00")))
            self.status_var.set("Pokazuje ostatnio zapisane wyniki; trwa sprawdzanie kolejki.")

    def _complete_selected(self) -> None:
        selected = self.queue_tree.selection()
        if not selected:
            self.status_var.set("Najpierw wybierz zlecenie w aktywnej kolejce.")
            return
        try:
            mark_queue_item_done(self.path_var.get(), selected[0])
            archived = archive_completed_orders(self.path_var.get())
        except Exception as exc:
            self.status_var.set(f"Nie udalo sie zakonczyc zlecenia: {exc}")
            return
        self.status_var.set(f"Zlecenie zakonczone. Zarchiwizowano: {archived}.")
        self._last_signature = None
        self.refresh(force=True)
