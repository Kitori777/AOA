from __future__ import annotations

import customtkinter as ctk

from .animation import ModelAnimationCard
from .data import EXAMPLE_ROWS, JOB_ROWS, TheoryModel, find_theory_model, get_theory_models
from .widgets import BG_CARD, BLUE, BORDER, GREEN, PURPLE, YELLOW, label, make_card, small_badge


class TheoryPage(ctk.CTkFrame):
    """Interaktywna strona teorii modeli ML i heurystyk STO."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="#08111a")
        self.family = "ml"
        self.models = list(get_theory_models("ml"))
        self.selected_key = self.models[0].key
        self.active_step = 0
        self.model_buttons: dict[str, ctk.CTkButton] = {}
        self.family_buttons: dict[str, ctk.CTkButton] = {}
        self.step_cards: list[ctk.CTkFrame] = []
        self.hero_value_labels: dict[str, ctk.CTkLabel] = {}
        self.example_values = {"mt": 0.60, "mo": 0.30, "mzo": 0.10, "gen": 0.20}
        self.example_value_labels: dict[str, ctk.CTkLabel] = {}
        self._build_layout()
        self._show_model(find_theory_model(self.selected_key))

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = make_card(self, radius=16, fg_color="#0d1a26")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)
        label(header, "Teoria modeli — zrozum, jak działają", size=24, weight="bold").grid(
            row=0, column=0, sticky="w", padx=24, pady=(14, 2)
        )
        label(
            header,
            "Oglądaj animacje krok po kroku: od danych wejściowych, przez decyzję modelu, aż do wyniku i porównania metod.",
            size=13,
            color="#cbd5e1",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 14))
        self._build_hero_stats(header)

        top = make_card(self, radius=14, fg_color="#0d1a26")
        top.grid(row=1, column=0, sticky="ew", padx=14, pady=(6, 8))
        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(2, weight=0)
        family_box = ctk.CTkFrame(top, fg_color="transparent")
        family_box.grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self.family_buttons["ml"] = ctk.CTkButton(
            family_box,
            text="ML",
            width=120,
            height=34,
            command=lambda: self._set_family("ml"),
        )
        self.family_buttons["ml"].grid(row=0, column=0, padx=(0, 6))
        self.family_buttons["mh"] = ctk.CTkButton(
            family_box,
            text="Heurystyki",
            width=170,
            height=34,
            command=lambda: self._set_family("mh"),
        )
        self.family_buttons["mh"].grid(row=0, column=1)

        self.model_bar = ctk.CTkScrollableFrame(
            top, fg_color="transparent", orientation="horizontal", height=50
        )
        self.model_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 8))
        self.model_bar.grid_rowconfigure(0, weight=1)

        compare = ctk.CTkFrame(top, fg_color="transparent")
        compare.grid(row=0, column=2, sticky="e", padx=(0, 14), pady=10)
        label(compare, "Porównaj modele:", size=12, weight="bold").grid(row=0, column=0, padx=8)
        ctk.CTkButton(compare, text="Porównaj", width=118, command=self._compare_models).grid(
            row=0, column=1
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        body.grid_columnconfigure(0, weight=17, minsize=250)
        body.grid_columnconfigure(1, weight=58, minsize=660)
        body.grid_columnconfigure(2, weight=25, minsize=360)
        body.grid_rowconfigure(0, weight=1)

        self.left = ctk.CTkScrollableFrame(body, fg_color="transparent", width=245)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left.grid_columnconfigure(0, weight=1)

        self.center = ctk.CTkFrame(body, fg_color="transparent")
        self.center.grid(row=0, column=1, sticky="nsew", padx=4)
        self.center.grid_columnconfigure(0, weight=1)
        self.center.grid_rowconfigure(0, weight=1)
        self.center.grid_rowconfigure(1, weight=0)

        self.right = ctk.CTkScrollableFrame(body, fg_color="transparent", width=340)
        self.right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        self.right.grid_columnconfigure(0, weight=1)

        self.data_card = make_card(self.left)
        self.data_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.info_card = make_card(self.left)
        self.info_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.animation = ModelAnimationCard(self.center, on_step_changed=self._on_step_changed)
        self.animation.grid(row=0, column=0, sticky="nsew")
        self.bind("<Map>", lambda _event: self.animation.start_autoplay())

        self.bottom_bar = make_card(self.center, radius=12, fg_color=BG_CARD)
        self.bottom_bar.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.bottom_bar.configure(height=124)
        self.bottom_bar.grid_propagate(False)
        self.bottom_bar.grid_columnconfigure(0, weight=1)
        label(self.bottom_bar, "Proces krok po kroku", size=13, weight="bold").grid(
            row=0, column=0, sticky="w", padx=14, pady=(8, 2)
        )
        self.steps_frame = ctk.CTkScrollableFrame(
            self.bottom_bar, fg_color="transparent", orientation="horizontal", height=78
        )
        self.steps_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

    def _set_family(self, family: str) -> None:
        self.family = family
        self.models = list(get_theory_models("ml" if family == "ml" else "mh"))
        self.selected_key = self.models[0].key
        self.active_step = 0
        self._show_model(self.models[0])

    def _build_model_buttons(self) -> None:
        for child in self.model_bar.winfo_children():
            child.destroy()
        self.model_buttons.clear()
        label(self.model_bar, "Wybierz model:", size=12, weight="bold").grid(
            row=0, column=0, padx=(2, 10), pady=10
        )
        for index, model in enumerate(self.models, start=1):
            btn = ctk.CTkButton(
                self.model_bar,
                text=model.title,
                width=168,
                height=34,
                fg_color="#111f2d",
                hover_color="#17324d",
                border_width=1,
                border_color="#28384a",
                command=lambda key=model.key: self._select_model(key),
            )
            btn.grid(row=0, column=index, padx=4, pady=10)
            self.model_buttons[model.key] = btn

    def _select_model(self, key: str) -> None:
        self.selected_key = key
        self.active_step = 0
        self._show_model(find_theory_model(key))

    def _show_model(self, model: TheoryModel) -> None:
        self.selected_key = model.key
        self._build_model_buttons()
        self._refresh_family_buttons()
        self._refresh_model_buttons()
        self._update_hero_stats(model)
        self._render_data_card(model)
        self._render_info_card(model)
        self._render_step_cards(model)
        self.animation.set_model(model)
        self.animation.set_example_values(self.example_values)
        self._render_right_panel(model, self.active_step)

    def _build_hero_stats(self, parent: ctk.CTkFrame) -> None:
        stats = ctk.CTkFrame(parent, fg_color="transparent")
        stats.grid(row=0, column=1, rowspan=2, sticky="e", padx=18, pady=12)
        items = [("Tryb", "ML"), ("Model", "-"), ("Kroki", "12")]
        for col, (title, value) in enumerate(items):
            card = ctk.CTkFrame(
                stats,
                fg_color="#102438",
                corner_radius=12,
                border_width=1,
                border_color="#26435f",
            )
            card.grid(row=0, column=col, padx=4)
            label(card, title, size=10, color="#93c5fd").grid(
                row=0, column=0, sticky="w", padx=8, pady=(6, 0)
            )
            out = label(card, value, size=12, weight="bold")
            out.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
            self.hero_value_labels[title] = out

    def _update_hero_stats(self, model: TheoryModel) -> None:
        self.hero_value_labels["Tryb"].configure(text="ML" if model.family == "ml" else "STO")
        self.hero_value_labels["Model"].configure(text=model.short_title[:16])
        self.hero_value_labels["Kroki"].configure(text=str(len(model.steps)))

    def _on_step_changed(self, index: int) -> None:
        self.active_step = index
        model = find_theory_model(self.selected_key)
        self._highlight_step_cards(index)
        self._render_right_panel(model, index)

    def _refresh_family_buttons(self) -> None:
        for key, btn in self.family_buttons.items():
            active = key == self.family
            btn.configure(
                fg_color=BLUE if active else "#111f2d",
                hover_color="#176ab8" if active else "#17324d",
                border_width=1,
                border_color="#5eb1ff" if active else "#28384a",
            )

    def _refresh_model_buttons(self) -> None:
        for key, btn in self.model_buttons.items():
            active = key == self.selected_key
            btn.configure(
                fg_color="#123f78" if active else "#111f2d",
                border_width=1,
                border_color=BLUE if active else "#28384a",
                hover_color="#155ca6" if active else "#17324d",
            )

    def _render_data_card(self, model: TheoryModel) -> None:
        for child in self.data_card.winfo_children():
            child.destroy()
        label(self.data_card, "Przykładowe dane wejściowe", size=15, weight="bold").grid(
            row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(14, 10)
        )
        rows: list[tuple[object, ...]]
        if model.family == "mh":
            headers = ["ID", "Klasa", "p (czas)", "d (termin)", "p/d", "GEN"]
            rows = [
                (row.job_id, row.klass, row.processing_time, row.due_date, row.ratio, row.gen)
                for row in JOB_ROWS
            ]
            note = (
                "Wyjaśnienie kolumn:\n"
                "• Klasa – etykieta / strategia (A, B, C)\n"
                "• p – czas przetwarzania zlecenia\n"
                "• d – termin gotowości (due date)\n"
                "• p/d – wskaźnik pomocniczy do rankingu"
            )
        else:
            headers = ["ID", "Cel", "czas_h", "termin_h", "koszt", "material"]
            rows = [
                (
                    row.row_id,
                    "jakosc",
                    8 + (self.example_values["mt"] if row.row_id == 1 else row.mt) * 6,
                    24 + (self.example_values["mo"] if row.row_id == 1 else row.mo) * 42,
                    100 + (self.example_values["mzo"] if row.row_id == 1 else row.mzo) * 160,
                    self.example_values["gen"] if row.row_id == 1 else row.gen,
                )
                for row in EXAMPLE_ROWS
            ]
            note = (
                "Wyjaśnienie kolumn:\n"
                "• Cel – zadanie modelu: jakosc, opoznienie albo schedule\n"
                "• czas_h, termin_h, koszt – realne cechy produkcyjne dla ML\n"
                "• material – przykladowy sygnal opisujacy rekord\n"
                "• MT/MO/MZO sa osobno w heurystykach/STO, nie jako mechanika ML"
            )
        for col, text in enumerate(headers):
            label(self.data_card, text, size=10, weight="bold", color="#e5eef9").grid(
                row=1, column=col, padx=4, pady=5
            )
        for row_no, row in enumerate(rows, start=2):
            for col, value in enumerate(row):
                if isinstance(value, float):
                    txt = f"{value:.2f}" if value < 1 else f"{value:.1f}"
                else:
                    txt = str(value)
                active_cell = row_no == 2 and col == 2
                cell = ctk.CTkLabel(
                    self.data_card,
                    text=txt,
                    width=38,
                    height=28,
                    fg_color="#123f78" if active_cell else "#111f2d",
                    corner_radius=4,
                    font=("Segoe UI", 9, "bold" if active_cell else "normal"),
                    text_color="#f8fafc",
                )
                cell.grid(row=row_no, column=col, padx=2, pady=2, sticky="ew")
                if model.family == "ml" and row_no == 2 and col in {2, 3, 4, 5}:
                    self.example_value_labels[headers[col].lower()] = cell
        label(self.data_card, note, size=10, color="#cbd5e1", wraplength=218).grid(
            row=8, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 14)
        )
        if model.family == "ml":
            self._render_example_controls(row=9)

    def _render_example_controls(self, row: int) -> None:
        panel = ctk.CTkFrame(self.data_card, fg_color="#0d1a26", corner_radius=8)
        panel.grid(row=row, column=0, columnspan=6, sticky="ew", padx=12, pady=(0, 14))
        panel.grid_columnconfigure(1, weight=1)
        label(panel, "Zmień przykład", size=12, weight="bold").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 4)
        )
        labels = {"mt": "czas", "mo": "termin", "mzo": "koszt", "gen": "material"}
        for idx, key in enumerate(("mt", "mo", "mzo", "gen"), start=1):
            label(panel, labels[key], size=10, weight="bold", color="#dbeafe").grid(
                row=idx, column=0, sticky="w", padx=10, pady=3
            )
            value_label = label(panel, f"{self.example_values[key]:.2f}", size=10, color="#cbd5e1")
            value_label.grid(row=idx, column=2, sticky="e", padx=10, pady=3)
            slider = ctk.CTkSlider(
                panel,
                from_=0.0,
                to=1.0,
                number_of_steps=100,
                command=lambda value, name=key, out=value_label: self._update_example_value(
                    name, float(value), out
                ),
            )
            slider.set(self.example_values[key])
            slider.grid(row=idx, column=1, sticky="ew", padx=8, pady=3)

    def _update_example_value(self, key: str, value: float, value_label: ctk.CTkLabel) -> None:
        self.animation.pause_for_reading()
        self.example_values[key] = round(value, 2)
        value_label.configure(text=f"{self.example_values[key]:.2f}")
        if key in self.example_value_labels:
            self.example_value_labels[key].configure(text=f"{self.example_values[key]:.2f}")
        self.animation.set_example_values(self.example_values)
        self._render_right_panel(find_theory_model(self.selected_key), self.active_step)

    def _render_info_card(self, model: TheoryModel) -> None:
        for child in self.info_card.winfo_children():
            child.destroy()
        label(self.info_card, "Kluczowe informacje o modelu", size=15, weight="bold").grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 10)
        )
        items = [
            ("▣", "Typ", model.model_type),
            ("◈", "Algorytm", model.algorithm),
            ("◎", "Cel", model.goal),
            ("▥", "Metryka", model.metric),
            ("◉", "Na co patrzy", model.focus),
        ]
        for i, (icon, name, value) in enumerate(items, start=1):
            row = ctk.CTkFrame(self.info_card, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=14, pady=5)
            row.grid_columnconfigure(2, weight=1)
            label(row, icon, size=14, color="#dbeafe").grid(
                row=0, column=0, sticky="nw", padx=(0, 8)
            )
            label(row, f"{name}: ", size=12, weight="bold", color="#e5eef9").grid(
                row=0, column=1, sticky="nw"
            )
            label(row, value, size=11, color="#cbd5e1", wraplength=145).grid(
                row=0, column=2, sticky="nw"
            )

    def _render_step_cards(self, model: TheoryModel) -> None:
        for child in self.steps_frame.winfo_children():
            child.destroy()
        self.step_cards = []
        for index, (step, detail) in enumerate(zip(model.steps, model.step_details, strict=True)):
            card = make_card(self.steps_frame, fg_color="#111f2d")
            card.configure(width=246, height=68)
            card.grid_propagate(False)
            card.grid(row=0, column=index, padx=4, pady=2, sticky="nsew")
            card.grid_columnconfigure(1, weight=1)
            small_badge(card, str(index + 1), color=BLUE if index == 0 else "#334155").grid(
                row=0, column=0, rowspan=2, padx=(8, 7), pady=8, sticky="n"
            )
            label(card, step, size=10, weight="bold").grid(
                row=0, column=1, sticky="w", padx=(0, 8), pady=(8, 0)
            )
            label(
                card, self._short_step_detail(detail), size=9, color="#cbd5e1", wraplength=172
            ).grid(row=1, column=1, sticky="nw", padx=(0, 8), pady=(0, 8))
            card.bind(
                "<Button-1>", lambda _event, i=index: self.animation.set_step(i, user_action=True)
            )
            for child in card.winfo_children():
                child.bind(
                    "<Button-1>",
                    lambda _event, i=index: self.animation.set_step(i, user_action=True),
                )
            self.step_cards.append(card)
        self._highlight_step_cards(0)

    @staticmethod
    def _short_step_detail(detail: str, max_chars: int = 82) -> str:
        compact = " ".join(detail.split())
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 1].rstrip() + "…"

    def _highlight_step_cards(self, active_index: int) -> None:
        for i, card in enumerate(self.step_cards):
            active = i == active_index
            card.configure(
                fg_color="#123f78" if active else "#111f2d",
                border_color=BLUE if active else BORDER,
            )
        self.after_idle(lambda index=active_index: self._center_step_card(index))

    def _center_step_card(self, active_index: int) -> None:
        if not (0 <= active_index < len(self.step_cards)):
            return

        canvas = getattr(self.steps_frame, "_parent_canvas", None)
        if canvas is None:
            return

        card = self.step_cards[active_index]
        self.steps_frame.update_idletasks()
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox is None:
            return

        content_width = max(1, bbox[2] - bbox[0])
        viewport_width = max(1, canvas.winfo_width())
        scrollable_width = content_width - viewport_width
        if scrollable_width <= 0:
            canvas.xview_moveto(0)
            return

        card_center = card.winfo_x() + card.winfo_width() / 2
        target = (card_center - viewport_width / 2) / scrollable_width
        canvas.xview_moveto(max(0.0, min(1.0, target)))

    def _render_right_panel(self, model: TheoryModel, step_index: int) -> None:
        for child in self.right.winfo_children():
            child.destroy()
        step_index = max(0, min(len(model.steps) - 1, step_index))
        step = model.steps[step_index]
        detail = model.step_details[step_index]

        card = make_card(self.right)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        label(card, "Co dzieje się w tym kroku?", size=15, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )
        self._render_pipeline_row(card, step_index, len(model.steps))
        label(card, f"Krok {step_index + 1}: {step}", size=13, weight="bold").grid(
            row=2, column=0, sticky="w", padx=16, pady=(2, 6)
        )
        label(card, detail, size=12, color="#cbd5e1", wraplength=292).grid(
            row=3, column=0, sticky="ew", padx=16, pady=(0, 16)
        )

        code_card = make_card(self.right, fg_color="#101923")
        code_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        code_card.grid_columnconfigure(0, weight=1)
        label(code_card, "Mini-pseudokod", size=14, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )
        start = max(0, step_index - 2)
        end = min(len(model.pseudocode), step_index + 3)
        for row_no, code_index in enumerate(range(start, end), start=1):
            active_line = code_index == step_index
            line = ctk.CTkLabel(
                code_card,
                text=f"{code_index + 1:02d}  {model.pseudocode[code_index]}",
                anchor="w",
                justify="left",
                fg_color="#123f78" if active_line else "#0f1720",
                corner_radius=6,
                text_color="#ffffff" if active_line else "#bfdbfe",
                font=("Consolas", 11, "bold" if active_line else "normal"),
                padx=8,
                pady=5,
            )
            line.grid(row=row_no, column=0, sticky="ew", padx=12, pady=2)

        state = make_card(self.right, fg_color="#0d1a26")
        state.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        state.grid_columnconfigure(0, weight=1)
        label(state, "Stan przykładu", size=14, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )
        label(
            state,
            self._state_text(model, step_index),
            size=12,
            color="#cbd5e1",
            wraplength=292,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        variables = self._state_variables(model, step_index)
        for i, (name, value) in enumerate(variables, start=2):
            row = ctk.CTkFrame(state, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=16, pady=2)
            row.grid_columnconfigure(1, weight=1)
            label(row, name, size=11, color="#93c5fd").grid(row=0, column=0, sticky="w")
            label(row, value, size=11, weight="bold").grid(row=0, column=1, sticky="e")

        why = make_card(self.right, fg_color="#111f2d")
        why.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        why.grid_columnconfigure(0, weight=1)
        label(why, "Dlaczego to ważne?", size=14, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )
        label(
            why, self._why_text(model, step_index), size=12, color="#cbd5e1", wraplength=292
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        next_card = make_card(self.right, fg_color="#111f2d")
        next_card.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        next_card.grid_columnconfigure(0, weight=1)
        label(next_card, "Co będzie dalej?", size=14, weight="bold", color="#bbf7d0").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )
        next_items = self._next_items(model, step_index)
        for i, text in enumerate(next_items, start=1):
            label(next_card, f"{i}.  {text}", size=11, color="#cbd5e1", wraplength=286).grid(
                row=i, column=0, sticky="w", padx=18, pady=3
            )

        tip = make_card(self.right, fg_color="#2b2717", border=True)
        tip.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        tip.grid_columnconfigure(0, weight=1)
        label(tip, "Wskazówka", size=13, weight="bold", color="#fde68a").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4)
        )
        label(tip, model.tip, size=11, color="#f5e6b8", wraplength=292).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 14)
        )

    def _render_pipeline_row(self, parent: ctk.CTkFrame, step_index: int, total_steps: int) -> None:
        flow = ctk.CTkFrame(parent, fg_color="#0f1b2a", corner_radius=10)
        flow.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        phases = ("Dane", "Cechy", "Model", "Wynik")
        phase_id = min(3, int((step_index / max(1, total_steps - 1)) * 4))
        for col, phase in enumerate(phases):
            active = col <= phase_id
            chip = ctk.CTkFrame(
                flow,
                fg_color="#123f78" if active else "#1f2937",
                corner_radius=8,
                border_width=1,
                border_color="#5eb1ff" if active else "#374151",
            )
            chip.grid(row=0, column=col * 2, padx=4, pady=6)
            label(chip, phase, size=10, weight="bold", color="#e5eef9").grid(
                row=0, column=0, padx=10, pady=4
            )
            if col < len(phases) - 1:
                label(flow, ">", size=12, color="#64748b").grid(row=0, column=col * 2 + 1, padx=2)

    def _state_text(self, model: TheoryModel, step_index: int) -> str:
        if model.family == "ml":
            states = (
                "Rekord produkcyjny ma cechy, z których model ma przewidzieć cel.",
                "Braki danych są uzupełniane, żeby algorytm dostał pełną tabelę.",
                "Model widzi macierz cech X i cel y; schedule jest klasyfikacją, quality/delay regresją.",
                "W modelach drzewiastych powstają podziały cech, a w logistic powstają wagi klas.",
                "Ten krok pokazuje właściwy mechanizm algorytmu, nie heurystyki MT/MO/MZO.",
                "Model dopasowuje zależności: progi, poprawki błędu albo granicę liniową.",
                "Jedna instancja przechodzi przez wyuczony model.",
                "Wyniki cząstkowe zależą od typu modelu: głosy drzew, poprawki boostingu albo softmax.",
                "Agregacja łączy wiele decyzji w jeden stabilniejszy wynik.",
                "Walidacja sprawdza, czy model działa na nowych danych, nie tylko na treningu.",
                "Predykcja trafia do wyników: jakość, opóźnienie albo strategia schedule.",
                "Zapis modelu pozwala potem użyć tej samej logiki w solve i raportach.",
            )
        else:
            states = (
                "Lista zleceń jest punktem startowym symulacji STO.",
                "Każde zlecenie dostaje wskaźniki pomocnicze.",
                "Reguła sortowania tworzy pierwszą kolejkę.",
                "Kolejka jest gotowa do symulacji czasu.",
                "Pierwsze zlecenie ustawia początek osi czasu.",
                "Czasy zakończenia narastają po kolejnych zleceniach.",
                "Opóźnienia pojawiają się tylko po przekroczeniu terminu.",
                "Suma dodatnich opóźnień staje się wynikiem metody.",
                "Warianty kolejki mogą poprawić wynik bez pełnej enumeracji.",
                "Wszystkie metody są liczone na tych samych danych.",
                "Ranking wybiera najmniejsze STO.",
                "Wybrany wariant trafia do wyników i raportu.",
            )
        return states[min(step_index, len(states) - 1)]

    def _state_variables(self, model: TheoryModel, step_index: int) -> tuple[tuple[str, str], ...]:
        if model.family == "ml":
            signal = (
                self.example_values["mt"] * 0.35
                + self.example_values["mo"] * 0.25
                + self.example_values["mzo"] * 0.15
                + self.example_values["gen"] * 0.25
            )
            history_rows = 25 if step_index >= 1 else 0
            train_rows = 5 + history_rows if step_index >= 2 else 5
            confidence = min(0.95, 0.52 + signal * 0.38 + step_index * 0.01)
            return (
                ("czas_h", f"{8 + self.example_values['mt'] * 6:.1f}"),
                ("termin_h", f"{24 + self.example_values['mo'] * 42:.1f}"),
                ("koszt", f"{100 + self.example_values['mzo'] * 160:.0f}"),
                ("material", f"{self.example_values['gen']:.2f}"),
                ("historia", f"{history_rows} rekordów"),
                ("zbiór uczący", f"{train_rows} rekordów"),
                ("pewność", f"{confidence:.2f}"),
            )
        return (
            ("kolejka", "J3 -> J2 -> J1 -> J4"),
            ("czas", f"{min(step_index * 3, 19)} h"),
            ("T+", "7 h" if step_index >= 7 else "liczone"),
            ("najlepszy wariant", model.short_title if step_index >= 10 else "w trakcie"),
        )

    def _why_text(self, model: TheoryModel, step_index: int) -> str:
        if model.family == "ml":
            texts = (
                "Bez jasnego celu model nie wie, czy ma przewidywać jakość, opóźnienie czy schedule.",
                "Uzupełnienie braków chroni przed błędem technicznym i fałszywym porównaniem modeli.",
                "Rozdzielenie X i y pokazuje, czego model używa, a co ma przewidzieć.",
                "Drzewa, boosting i logistic uczą się zupełnie inaczej, dlatego animacja musi je rozdzielać.",
                "To miejsce odcina ML od STO: MT/MO/MZO są regułami kolejkowania, a nie etapami lasu ani boostingu.",
                "Dopasowanie zależności jest właściwym treningiem modelu.",
                "Przejście jednej instancji pokazuje, co stanie się z nowym zleceniem.",
                "Cząstkowe wyniki pomagają wyjaśnić, skąd bierze się predykcja.",
                "Agregacja zmniejsza ryzyko, że jedna przypadkowa decyzja zdominuje wynik.",
                "Walidacja jest kontrolą jakości modelu na danych niewidzianych.",
                "Końcowa predykcja to wartość widoczna potem w Results, Visual i raportach.",
                "Zapis modelu pozwala odtworzyć wynik i używać go w kolejnych workflow.",
            )
        else:
            texts = (
                "Heurystyka działa tylko tak dobrze, jak dane wejściowe i terminy zleceń.",
                "Wskaźniki zmieniają surowe dane w kolejność łatwą do porównania.",
                "Jawna reguła sprawia, że wynik można łatwo wyjaśnić użytkownikowi.",
                "Kolejność startowa decyduje, które zlecenia mogą opóźnić pozostałe.",
                "Pierwsze zlecenia blokują kolejkę najdłużej, więc ich wybór jest krytyczny.",
                "Czas zakończenia Cj jest podstawą do policzenia opóźnień.",
                "Tj pokazuje, które zlecenia realnie przekroczyły termin.",
                "Suma T+ pozwala ocenić całą kolejkę jedną liczbą.",
                "Korekta wariantu może znaleźć lepszy wynik bez pełnego przeszukiwania wszystkich permutacji.",
                "Porównanie metod chroni przed wyborem pierwszej, ale niekoniecznie najlepszej reguły.",
                "Ranking STO pokazuje, która metoda daje najmniejsze opóźnienie.",
                "Wybrana kolejka jest gotowa do zapisania i dalszego wykorzystania.",
            )
        return texts[min(step_index, len(texts) - 1)]

    def _next_items(self, model: TheoryModel, step_index: int) -> tuple[str, ...]:
        if step_index + 1 < len(model.steps):
            return (
                f"Przejdziemy do kroku {step_index + 2}: {model.steps[step_index + 1]}.",
                "Animacja podświetli kolejny element przepływu danych.",
                "Panel po lewej zostaje punktem odniesienia dla tych samych danych.",
            )
        return (
            "Proces dla tego modelu jest zakończony.",
            "Możesz wrócić suwakiem do dowolnego kroku.",
            "Możesz też porównać ten model z innymi wariantami.",
        )

    def _compare_models(self) -> None:
        self._show_compare_panel()

    def _show_compare_panel(self) -> None:
        model = find_theory_model(self.selected_key)
        for child in self.right.winfo_children():
            child.destroy()
        card = make_card(self.right)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        label(card, "Porównanie modeli", size=15, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 10)
        )
        label(
            card,
            f"Aktywna grupa: {'Modele ML' if self.family == 'ml' else 'Heurystyki'}",
            size=12,
            color="#cbd5e1",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))
        for i, item in enumerate(self.models[:12], start=2):
            active = item.key == model.key
            row = make_card(card, fg_color="#123f78" if active else "#111f2d")
            row.grid(row=i, column=0, sticky="ew", padx=12, pady=4)
            row.grid_columnconfigure(0, weight=1)
            label(row, item.short_title, size=12, weight="bold", color="#ffffff").grid(
                row=0, column=0, sticky="w", padx=10, pady=(8, 1)
            )
            label(row, item.focus, size=10, color="#cbd5e1", wraplength=255).grid(
                row=1, column=0, sticky="w", padx=10, pady=(0, 8)
            )
            score = self._compare_score(item, i)
            bar = ctk.CTkProgressBar(row, height=10, progress_color=self._compare_color(item))
            bar.set(score)
            bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 4))
            explainability = min(0.95, score + (0.08 if item.family == "mh" else 0.0))
            label(row, f"stabilność: {score:.2f}", size=10, color="#cbd5e1").grid(
                row=3, column=0, sticky="w", padx=10, pady=(0, 2)
            )
            label(
                row,
                f"wyjaśnialność: {explainability:.2f} | koszt treningu: {self._training_cost_label(item)}",
                size=10,
                color="#cbd5e1",
            ).grid(row=4, column=0, sticky="w", padx=10, pady=(0, 8))

    def _compare_score(self, model: TheoryModel, index: int) -> float:
        if model.family == "mh":
            return max(0.35, 0.92 - index * 0.04)
        if "Random" in model.algorithm or "Extra" in model.algorithm:
            return 0.84
        if "Hist" in model.algorithm:
            return 0.80
        if "Gradient" in model.algorithm:
            return 0.76
        return 0.68

    def _compare_color(self, model: TheoryModel) -> str:
        if model.family == "mh":
            return GREEN
        if "Gradient" in model.algorithm:
            return YELLOW
        if "Regresja" in model.algorithm:
            return PURPLE
        return BLUE

    def _training_cost_label(self, model: TheoryModel) -> str:
        if model.family == "mh":
            return "brak treningu"
        if "Hist" in model.algorithm or "Extra" in model.algorithm:
            return "średni"
        if "Gradient" in model.algorithm:
            return "wyższy"
        return "średni"
