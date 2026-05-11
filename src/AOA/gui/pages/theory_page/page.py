from __future__ import annotations

import customtkinter as ctk

from .animation import ModelAnimationCard
from .data import EXAMPLE_ROWS, JOB_ROWS, TheoryModel, find_theory_model, get_theory_models
from .widgets import BG_CARD, BLUE, BORDER, label, make_card, small_badge


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

        top = make_card(self, radius=14, fg_color="#0d1a26")
        top.grid(row=1, column=0, sticky="ew", padx=14, pady=(6, 8))
        top.grid_columnconfigure(1, weight=1)
        family_box = ctk.CTkFrame(top, fg_color="transparent")
        family_box.grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self.family_buttons["ml"] = ctk.CTkButton(
            family_box,
            text="⚙  Modele ML",
            width=120,
            height=34,
            command=lambda: self._set_family("ml"),
        )
        self.family_buttons["ml"].grid(row=0, column=0, padx=(0, 6))
        self.family_buttons["mh"] = ctk.CTkButton(
            family_box,
            text="✣  Modele heurystyczne",
            width=170,
            height=34,
            command=lambda: self._set_family("mh"),
        )
        self.family_buttons["mh"].grid(row=0, column=1)

        self.model_bar = ctk.CTkScrollableFrame(
            top, fg_color="transparent", orientation="horizontal", height=56
        )
        self.model_bar.grid(row=0, column=1, sticky="ew", padx=(10, 12), pady=8)
        self.model_bar.grid_rowconfigure(0, weight=1)

        compare = ctk.CTkFrame(top, fg_color="transparent")
        compare.grid(row=0, column=2, sticky="e", padx=(0, 14), pady=10)
        label(compare, "Porównaj modele:", size=12, weight="bold").grid(row=0, column=0, padx=8)
        ctk.CTkButton(compare, text="▥  Porównaj", width=118, command=self._compare_models).grid(
            row=0, column=1
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        body.grid_columnconfigure(0, weight=16, minsize=235)
        body.grid_columnconfigure(1, weight=64, minsize=660)
        body.grid_columnconfigure(2, weight=20, minsize=330)
        body.grid_rowconfigure(0, weight=1)

        self.left = ctk.CTkScrollableFrame(body, fg_color="transparent", width=245)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left.grid_columnconfigure(0, weight=1)

        self.center = ctk.CTkFrame(body, fg_color="transparent")
        self.center.grid(row=0, column=1, sticky="nsew", padx=4)
        self.center.grid_columnconfigure(0, weight=1)
        self.center.grid_rowconfigure(0, weight=1)

        self.right = ctk.CTkScrollableFrame(body, fg_color="transparent", width=340)
        self.right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        self.right.grid_columnconfigure(0, weight=1)

        self.data_card = make_card(self.left)
        self.data_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.info_card = make_card(self.left)
        self.info_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.animation = ModelAnimationCard(self.center, on_step_changed=self._on_step_changed)
        self.animation.grid(row=0, column=0, sticky="nsew")

        self.bottom_bar = make_card(self.center, radius=14, fg_color=BG_CARD)
        self.bottom_bar.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.bottom_bar.grid_columnconfigure(0, weight=1)
        label(self.bottom_bar, "Jak przebiega proces krok po kroku?", size=15, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 6)
        )
        self.steps_frame = ctk.CTkScrollableFrame(
            self.bottom_bar, fg_color="transparent", orientation="horizontal", height=112
        )
        self.steps_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

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
        self._render_data_card(model)
        self._render_info_card(model)
        self._render_step_cards(model)
        self.animation.set_model(model)
        self._render_right_panel(model, self.active_step)

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
            headers = ["ID", "Klasa", "MT", "MO", "MZO", "GEN"]
            rows = [
                (row.row_id, row.klass, row.mt, row.mo, row.mzo, row.gen) for row in EXAMPLE_ROWS
            ]
            note = (
                "Wyjaśnienie kolumn:\n"
                "• Klasa – etykieta / strategia (A, B, C)\n"
                "• MT, MO, MZO, GEN – cechy opisujące instancję\n"
                "• Wartości znormalizowane w zakresie [0, 1]"
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
        label(self.data_card, note, size=10, color="#cbd5e1", wraplength=218).grid(
            row=8, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 14)
        )

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
            card.grid(row=0, column=index, padx=5, pady=4, sticky="nsew")
            card.grid_columnconfigure(1, weight=1)
            small_badge(card, str(index + 1), color=BLUE if index == 0 else "#334155").grid(
                row=0, column=0, rowspan=2, padx=(10, 8), pady=10, sticky="n"
            )
            label(card, step, size=11, weight="bold").grid(
                row=0, column=1, sticky="w", padx=(0, 10), pady=(10, 2)
            )
            label(card, detail, size=10, color="#cbd5e1", wraplength=205).grid(
                row=1, column=1, sticky="nw", padx=(0, 10), pady=(0, 10)
            )
            card.bind("<Button-1>", lambda _event, i=index: self.animation.set_step(i))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda _event, i=index: self.animation.set_step(i))
            self.step_cards.append(card)
        self._highlight_step_cards(0)

    def _highlight_step_cards(self, active_index: int) -> None:
        for i, card in enumerate(self.step_cards):
            active = i == active_index
            card.configure(
                fg_color="#123f78" if active else "#111f2d",
                border_color=BLUE if active else BORDER,
            )

    def _render_right_panel(self, model: TheoryModel, step_index: int) -> None:
        for child in self.right.winfo_children():
            child.destroy()
        step_index = max(0, min(len(model.steps) - 1, step_index))
        step = model.steps[step_index]
        detail = model.step_details[step_index]

        card = make_card(self.right)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        label(card, "🧠  Co dzieje się w tym kroku?", size=15, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )
        label(card, f"Krok {step_index + 1}: {step}", size=13, weight="bold").grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 6)
        )
        label(card, detail, size=12, color="#cbd5e1", wraplength=292).grid(
            row=2, column=0, sticky="ew", padx=16, pady=(0, 16)
        )

        why = make_card(self.right, fg_color="#111f2d")
        why.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        why.grid_columnconfigure(0, weight=1)
        label(why, "ⓘ  Dlaczego to ważne?", size=14, weight="bold").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )
        label(
            why, self._why_text(model, step_index), size=12, color="#cbd5e1", wraplength=292
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        next_card = make_card(self.right, fg_color="#111f2d")
        next_card.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        next_card.grid_columnconfigure(0, weight=1)
        label(next_card, "➜  Co będzie dalej?", size=14, weight="bold", color="#bbf7d0").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )
        next_items = self._next_items(model, step_index)
        for i, text in enumerate(next_items, start=1):
            label(next_card, f"{i}.  {text}", size=11, color="#cbd5e1", wraplength=286).grid(
                row=i, column=0, sticky="w", padx=18, pady=3
            )

        tip = make_card(self.right, fg_color="#2b2717", border=True)
        tip.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        tip.grid_columnconfigure(0, weight=1)
        label(tip, "💡  Wskazówka", size=13, weight="bold", color="#fde68a").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4)
        )
        label(tip, model.tip, size=11, color="#f5e6b8", wraplength=292).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 14)
        )

    def _why_text(self, model: TheoryModel, step_index: int) -> str:
        if model.family == "ml":
            texts = (
                "Bez dobrze przygotowanych danych model nie ma z czego uczyć zależności.",
                "Jedna instancja pozwala zobaczyć decyzję modelu jak proces, a nie czarną skrzynkę.",
                "Wspólna skala cech stabilizuje analizę i ułatwia porównywanie kolumn.",
                "Model nie patrzy na wszystko jednakowo — szuka cech, które realnie zmniejszają błąd.",
                "Podziały w drzewie tłumaczą, dlaczego podobne rekordy trafiają do podobnych wyników.",
                "Przejście po gałęzi pokazuje, jak konkretne liczby zmieniają decyzję.",
                "Wynik pojedynczego drzewa jest tylko fragmentem całej decyzji.",
                "Wiele estymatorów zmniejsza ryzyko, że przypadkowy błąd jednego drzewa zdominuje wynik.",
                "Łączenie głosów daje bardziej odporną predykcję.",
                "Rozkład pokazuje nie tylko decyzję, ale też poziom pewności.",
                "Końcowa predykcja jest tym, co później widzi użytkownik w wynikach.",
                "Zapis wyniku pozwala użyć modelu w raportach, priorytetach i kolejnych obliczeniach.",
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
