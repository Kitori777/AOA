"""Readable, responsive controls for the engineering workspace."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from tkinter import TclError

import customtkinter as ctk

from AOA.core.esm_costs import OBJECTIVES
from AOA.core.esm_project import ESM_MAX_MACHINES, ESM_TIME_MODES, prepare_esm_flow_jobs
from AOA.core.optimization.models import Job
from AOA.gui.theme import COLORS

ACCENT = "#32c6ad"
SELECTED = "#123a3b"
OBJECTIVE_COPY = {
    "sto": ("Opóźnienia", "Najmniej minut spóźnienia względem terminów."),
    "cost": ("Koszt opóźnień", "Najmniejsza suma kar według stawek zleceń."),
    "waste": ("Odpad", "Najmniej kg odpadu z produkcji i przezbrojeń."),
}
OBJECTIVE_DETAIL = {
    "sto": "Remisy: mniej odpadu, potem wcześniejszy koniec produkcji.",
    "cost": "Kara dotyczy opóźnienia ponad tolerancję. Remisy: odpad, potem koniec produkcji.",
    "waste": "Odpad ma pierwszeństwo. Remisy: mniej opóźnień, potem wcześniejszy koniec.",
}


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


class EngineeringSettingsPanel(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        *,
        machine_var: ctk.StringVar,
        time_mode_var: ctk.StringVar,
        objective_var: ctk.StringVar,
        method_vars: Mapping[str, ctk.BooleanVar],
        on_machine: Callable[[str], None],
        on_time_mode: Callable[[str], None],
        on_objective: Callable[[str], None],
        on_costs: Callable[[], None],
        on_preset: Callable[[str], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.machine_var = machine_var
        self.time_mode_var = time_mode_var
        self.objective_var = objective_var
        self.method_vars = method_vars
        self._on_objective = on_objective
        self._jobs: tuple[Job, ...] = ()
        self._wide: bool | None = None
        self._traces: list[tuple[ctk.Variable, str]] = []
        self.grid_columnconfigure((0, 1), weight=1, uniform="settings")
        self.production_card = self._card()
        self.objective_card = self._card()
        self._heading(
            self.production_card, "Produkcja", "Każde zlecenie przechodzi przez wszystkie maszyny."
        )
        self._heading(
            self.objective_card,
            "Co chcesz minimalizować?",
            "Jeden cel dla obliczeń, rankingu i wykresów.",
        )

        ctk.CTkLabel(
            self.production_card, text="Liczba maszyn", font=("Segoe UI", 13, "bold")
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(14, 5))
        machine_row = ctk.CTkFrame(self.production_card, fg_color="transparent")
        machine_row.grid(row=3, column=0, sticky="w", padx=18)
        self.machine_selector = ctk.CTkSegmentedButton(
            machine_row,
            values=[str(i) for i in range(1, ESM_MAX_MACHINES + 1)],
            variable=machine_var,
            command=on_machine,
            height=36,
            width=300,
            fg_color=COLORS["app_bg"],
            unselected_color=COLORS["surface_raised"],
            unselected_hover_color=COLORS["surface_hover"],
            selected_color="#17685e",
            selected_hover_color="#1c7c6f",
            font=("Segoe UI", 13),
        )
        self.machine_selector.pack(side="left")
        ctk.CTkLabel(machine_row, text="1–8", text_color=COLORS["text_muted"], width=40).pack(
            side="left", padx=(8, 0)
        )
        ctk.CTkLabel(
            self.production_card, text="Jak rozłożyć czas zlecenia?", font=("Segoe UI", 13, "bold")
        ).grid(row=4, column=0, sticky="w", padx=18, pady=(16, 5))
        self.time_mode_menu = ctk.CTkOptionMenu(
            self.production_card,
            variable=time_mode_var,
            values=list(ESM_TIME_MODES.values()),
            command=on_time_mode,
            height=36,
            width=320,
            fg_color=COLORS["surface_raised"],
            button_color=COLORS["surface_hover"],
            button_hover_color=COLORS["border"],
            dropdown_fg_color=COLORS["surface_raised"],
            dropdown_hover_color=COLORS["surface_hover"],
            font=("Segoe UI", 13),
        )
        self.time_mode_menu.grid(row=5, column=0, sticky="ew", padx=18)
        example = ctk.CTkFrame(self.production_card, fg_color=COLORS["app_bg"], corner_radius=8)
        example.grid(row=6, column=0, sticky="ew", padx=18, pady=(14, 18))
        example.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            example,
            text="TAK ZOSTANIE POLICZONY CZAS",
            font=("Segoe UI", 10, "bold"),
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
        self.example_var = ctk.StringVar()
        self.example_label = ctk.CTkLabel(
            example,
            textvariable=self.example_var,
            text_color="#b7e9df",
            justify="left",
            anchor="w",
            wraplength=400,
        )
        self.example_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        self.objective_buttons: dict[str, ctk.CTkRadioButton] = {}
        self.objective_rows: dict[str, ctk.CTkFrame] = {}
        self.objective_descriptions: list[ctk.CTkLabel] = []
        for index, (code, (label, description)) in enumerate(OBJECTIVE_COPY.items()):
            shell = ctk.CTkFrame(
                self.objective_card,
                fg_color=COLORS["surface"],
                corner_radius=8,
                border_width=1,
                border_color=COLORS["border_soft"],
            )
            shell.grid(
                row=index + 2, column=0, sticky="ew", padx=18, pady=(8 if index == 0 else 6, 0)
            )
            shell.grid_columnconfigure(0, weight=1)
            radio = ctk.CTkRadioButton(
                shell,
                text=label,
                value=OBJECTIVES[code],
                variable=objective_var,
                command=lambda code=code: on_objective(OBJECTIVES[code]),
                fg_color=ACCENT,
                hover_color="#17685e",
                border_color=COLORS["text_muted"],
                font=("Segoe UI", 13, "bold"),
                radiobutton_width=18,
                radiobutton_height=18,
            )
            radio.grid(row=0, column=0, sticky="w", padx=12, pady=(9, 0))
            note = ctk.CTkLabel(
                shell,
                text=description,
                text_color=COLORS["text_muted"],
                anchor="w",
                justify="left",
                wraplength=400,
            )
            note.grid(row=1, column=0, sticky="ew", padx=(42, 12), pady=(0, 8))
            for widget in (shell, note):
                widget.bind("<Button-1>", lambda _event, code=code: self.select_objective(code))
            self.objective_rows[code] = shell
            self.objective_buttons[code] = radio
            self.objective_descriptions.append(note)
        self.cost_button = ctk.CTkButton(
            self.objective_rows["cost"],
            text="Stawki i tolerancje…",
            command=on_costs,
            height=28,
            width=160,
            fg_color=COLORS["surface_hover"],
            hover_color=COLORS["border"],
            font=("Segoe UI", 12),
        )
        self.cost_button.grid(row=0, column=1, rowspan=2, padx=(0, 10), pady=9)
        self.detail_var = ctk.StringVar()
        self.detail_label = ctk.CTkLabel(
            self.objective_card,
            textvariable=self.detail_var,
            text_color=COLORS["text_muted"],
            justify="left",
            anchor="w",
            wraplength=440,
        )
        self.detail_label.grid(row=5, column=0, sticky="ew", padx=18, pady=(8, 12))

        self.methods_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.methods_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        self.methods_bar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.methods_bar, text="Algorytmy do porównania", font=("Segoe UI", 15, "bold")
        ).grid(row=0, column=0, sticky="w")
        self.count_var = ctk.StringVar()
        self.count_label = ctk.CTkLabel(
            self.methods_bar,
            textvariable=self.count_var,
            text_color=ACCENT,
            font=("Segoe UI", 12, "bold"),
        )
        self.count_label.grid(row=0, column=1, sticky="e")
        self.methods_note = ctk.CTkLabel(
            self.methods_bar,
            text="Podstawowe: MT, MO, MZO, MOpt. Rozszerzone: ECO, Komponenty, Robust.",
            text_color=COLORS["text_muted"],
            justify="left",
            anchor="w",
            wraplength=900,
        )
        self.methods_note.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        presets = ctk.CTkFrame(self.methods_bar, fg_color="transparent")
        presets.grid(row=2, column=0, columnspan=2, sticky="w")
        self.preset_buttons = {}
        for index, (code, label) in enumerate(
            (("basic", "Podstawowe · 4"), ("extra", "Rozszerzone · 3"), ("all", "Wszystkie · 7"))
        ):
            button = ctk.CTkButton(
                presets,
                text=label,
                width=140,
                height=32,
                border_width=1,
                command=lambda code=code: on_preset(code),
                fg_color=COLORS["surface_raised"],
                hover_color=COLORS["surface_hover"],
                border_color=COLORS["border"],
            )
            button.grid(row=0, column=index, padx=(0, 8))
            self.preset_buttons[code] = button

        self._wrapped_labels = [self.example_label, self.detail_label, *self.objective_descriptions]
        self.bind("<Configure>", self._resize)
        for variable in (machine_var, time_mode_var, objective_var, *method_vars.values()):
            token = variable.trace_add("write", lambda *_: self.refresh())
            self._traces.append((variable, token))
        self._layout(False)
        self.refresh()

    def _card(self) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface_raised"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=12,
        )
        card.grid_columnconfigure(0, weight=1)
        return card

    @staticmethod
    def _heading(card, title: str, note: str) -> None:
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 16, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 0)
        )
        label = ctk.CTkLabel(
            card,
            text=note,
            text_color=COLORS["text_muted"],
            justify="left",
            anchor="w",
            wraplength=420,
        )
        label.grid(row=1, column=0, sticky="ew", padx=18)
        card.bind(
            "<Configure>",
            lambda event: label.configure(
                wraplength=max(180, card._reverse_widget_scaling(event.width) - 36)
            ),
        )

    def select_objective(self, code: str) -> None:
        self.objective_var.set(OBJECTIVES[code])
        self._on_objective(OBJECTIVES[code])

    def _layout(self, wide: bool) -> None:
        if wide == self._wide:
            return
        self._wide = wide
        self.production_card.grid(
            row=0, column=0, columnspan=1 if wide else 2, sticky="nsew", padx=(0, 8) if wide else 0
        )
        self.objective_card.grid(
            row=0 if wide else 1,
            column=1 if wide else 0,
            columnspan=1 if wide else 2,
            sticky="nsew",
            padx=(8, 0) if wide else 0,
            pady=0 if wide else (12, 0),
        )
        self.methods_bar.grid(row=1 if wide else 2)

    def _resize(self, event) -> None:
        width = self._reverse_widget_scaling(event.width)
        self._layout(width >= 1060)
        card_width = (width - 16) // 2 if self._wide else width
        for label in self._wrapped_labels:
            cost_row = label is self.objective_descriptions[1]
            label.configure(wraplength=max(140, card_width - (245 if cost_row else 80)))
        self.methods_note.configure(wraplength=max(250, width - 20))

    def refresh(self, jobs: Sequence[Job] | None = None) -> None:
        if jobs is not None:
            self._jobs = tuple(jobs)
        objective = next(
            (key for key, label in OBJECTIVES.items() if label == self.objective_var.get()), "sto"
        )
        for code, shell in self.objective_rows.items():
            shell.configure(
                fg_color=SELECTED if code == objective else COLORS["surface"],
                border_color=ACCENT if code == objective else COLORS["border_soft"],
            )
        self.detail_var.set(OBJECTIVE_DETAIL[objective])
        selected = {method for method, variable in self.method_vars.items() if variable.get()}
        self.count_var.set(f"Wybrano {len(selected)} z {len(self.method_vars)}")
        basic = {"MT", "MO", "MZO", "MOPT"}
        groups = {
            "basic": basic,
            "extra": set(self.method_vars) - basic,
            "all": set(self.method_vars),
        }
        for code, button in self.preset_buttons.items():
            active = selected == groups[code]
            button.configure(
                fg_color=SELECTED if active else COLORS["surface_raised"],
                border_color=ACCENT if active else COLORS["border"],
            )
        if not self._jobs:
            self.example_var.set(
                "Po wczytaniu danych zobaczysz tutaj przykład z pierwszego zlecenia."
            )
            return
        mode = next(
            (key for key, label in ESM_TIME_MODES.items() if label == self.time_mode_var.get()),
            "total",
        )
        machines = int(self.machine_var.get())
        sample = self._jobs[0]
        try:
            times = prepare_esm_flow_jobs([sample], n_machines=machines, time_mode=mode)[
                0
            ].machine_times
        except ValueError:
            self.example_var.set("Dopasuj sposób liczenia czasu do wybranej liczby maszyn.")
            return
        if mode == "total":
            text = f"{sample.job_id}: {_number(sum(times))} min ÷ {machines} = {_number(times[0])} min na każdej maszynie."
        elif mode == "per_machine":
            text = f"{sample.job_id}: {_number(times[0])} min na każdej z {machines} maszyn. Łącznie {_number(sum(times))} min obróbki."
        else:
            text = f"{sample.job_id}: " + " → ".join(
                f"M{i + 1}: {_number(t)} min" for i, t in enumerate(times)
            )
        self.example_var.set(text + " Bez czasu oczekiwania i przezbrojeń.")

    def destroy(self) -> None:
        for variable, token in self._traces:
            try:
                variable.trace_remove("write", token)
            except TclError:
                pass
        super().destroy()
