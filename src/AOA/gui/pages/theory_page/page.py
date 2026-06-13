from __future__ import annotations

import customtkinter as ctk

from .animation import ModelAnimationCard
from .data import TheoryModel, find_theory_model, get_theory_models
from .widgets import BLUE, BORDER, label, make_card


class TheoryPage(ctk.CTkFrame):
    """Jedna strona teorii: wybór modelu i jedna filmowa animacja."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="#08111a")
        self.family = "ml"
        self.models = list(get_theory_models("ml"))
        self.selected_key = self.models[0].key
        self.model_buttons: dict[str, ctk.CTkButton] = {}
        self.family_buttons: dict[str, ctk.CTkButton] = {}
        self.hero_value_labels: dict[str, ctk.CTkLabel] = {}
        self.example_values = {"mt": 0.60, "mo": 0.30, "mzo": 0.10, "gen": 0.20}

        self._build_layout()
        self._show_model(find_theory_model(self.selected_key))

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        page = ctk.CTkScrollableFrame(self, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        page.grid_columnconfigure(0, weight=1)

        header = make_card(page, radius=16, fg_color="#0d1a26")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)
        label(header, "Teoria modeli — jedna animacja", size=24, weight="bold").grid(
            row=0, column=0, sticky="w", padx=24, pady=(14, 2)
        )
        label(
            header,
            "Wybierz model i oglądaj jeden spójny film: dane, mechanizm, przepływ i wynik.",
            size=13,
            color="#cbd5e1",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 14))
        self._build_hero_stats(header)

        top = make_card(page, radius=14, fg_color="#0d1a26")
        top.grid(row=1, column=0, sticky="ew", padx=14, pady=(6, 8))
        top.grid_columnconfigure(1, weight=1)

        family_box = ctk.CTkFrame(top, fg_color="transparent")
        family_box.grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self.family_buttons["ml"] = ctk.CTkButton(
            family_box, text="ML", width=150, height=34, command=lambda: self._set_family("ml")
        )
        self.family_buttons["ml"].grid(row=0, column=0, padx=(0, 6))
        self.family_buttons["mh"] = ctk.CTkButton(
            family_box,
            text="Heurystyki",
            width=210,
            height=34,
            command=lambda: self._set_family("mh"),
        )
        self.family_buttons["mh"].grid(row=0, column=1)
        self.family_buttons["tabpfn"] = ctk.CTkButton(
            family_box,
            text="Nowoczesne ML",
            width=230,
            height=34,
            command=lambda: self._set_family("tabpfn"),
        )
        self.family_buttons["tabpfn"].grid(row=0, column=2, padx=(6, 0))

        label(top, "Jeden renderer animacji", size=12, weight="bold", color="#93c5fd").grid(
            row=0, column=2, sticky="e", padx=18, pady=10
        )

        self.model_bar = ctk.CTkScrollableFrame(
            top, fg_color="transparent", orientation="horizontal", height=58
        )
        self.model_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 8))
        self.model_bar.grid_rowconfigure(0, weight=1)

        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        body.grid_columnconfigure(0, weight=1)

        self.animation = ModelAnimationCard(body, on_step_changed=self._on_step_changed)
        self.animation.grid(row=0, column=0, sticky="ew")
        self.bind("<Map>", lambda _event: self.animation.start_autoplay())

    def _build_hero_stats(self, parent: ctk.CTkFrame) -> None:
        stats = ctk.CTkFrame(parent, fg_color="transparent")
        stats.grid(row=0, column=1, rowspan=2, sticky="e", padx=18, pady=12)
        for col, (title, value) in enumerate((("Tryb", "ML"), ("Model", "-"), ("Kroki", "12"))):
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

    def _set_family(self, family: str) -> None:
        self.family = family
        self.models = list(get_theory_models(family))
        self.selected_key = self.models[0].key
        self._show_model(self.models[0])

    def _show_model(self, model: TheoryModel) -> None:
        self.selected_key = model.key
        self._build_model_buttons()
        self._refresh_family_buttons()
        self._refresh_model_buttons()
        self._update_hero_stats(model)
        self.animation.set_model(model)
        self.animation.set_example_values(self.example_values)

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
                width=190,
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
        self._show_model(find_theory_model(key))

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
                border_color=BLUE if active else BORDER,
                hover_color="#155ca6" if active else "#17324d",
            )

    def _update_hero_stats(self, model: TheoryModel) -> None:
        mode = {"ml": "ML", "mh": "STO", "tabpfn": "TabPFN"}.get(model.family, "ML")
        self.hero_value_labels["Tryb"].configure(text=mode)
        self.hero_value_labels["Model"].configure(text=model.short_title[:16])
        self.hero_value_labels["Kroki"].configure(text=str(len(model.steps)))

    def _on_step_changed(self, _index: int) -> None:
        return
