import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from AOA.core.learning_content import (
    TheoryModule,
    build_learning_figure,
    find_theory_module,
    get_theory_modules,
)


class TheoryPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.modules = get_theory_modules()
        self.module_titles = [module.title for module in self.modules]
        self.title_to_key = {module.title: module.key for module in self.modules}
        self.selected_module = ctk.StringVar(value=self.module_titles[0])
        self.canvas: FigureCanvasTkAgg | None = None
        self._build_layout()
        self._show_module(self.modules[0])

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(self, corner_radius=18)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="Theory Page — najważniejsze modele i metryki", font=("Arial", 24, "bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))
        ctk.CTkLabel(
            header,
            text="Krótka teoria użytkowa: co robi model, jaki wzór warto znać, jak czytać wynik i kiedy ufać metrykom.",
            font=("Segoe UI", 13),
            text_color="#cbd5e1",
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
        controls = ctk.CTkFrame(self, corner_radius=18)
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 10))
        controls.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(controls, text="Moduł:", font=("Arial", 14, "bold")).grid(
            row=0, column=0, padx=(16, 8), pady=14, sticky="w"
        )
        ctk.CTkOptionMenu(
            controls,
            values=self.module_titles,
            variable=self.selected_module,
            command=self._on_module_selected,
            width=380,
        ).grid(row=0, column=1, padx=8, pady=14, sticky="w")
        ctk.CTkLabel(
            controls,
            text="Wskazówka: teoria ma pomagać w użyciu aplikacji, a nie zastępować dokumentacji ML.",
            text_color="#94a3b8",
            wraplength=700,
            justify="left",
        ).grid(row=0, column=2, padx=10, pady=14, sticky="w")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=6)
        body.grid_columnconfigure(1, weight=7)
        body.grid_rowconfigure(0, weight=1)
        self.text_frame = ctk.CTkScrollableFrame(body, corner_radius=18)
        self.text_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.text_frame.grid_columnconfigure(0, weight=1)
        self.plot_frame = ctk.CTkFrame(body, corner_radius=18)
        self.plot_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.plot_frame.grid_columnconfigure(0, weight=1)
        self.plot_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self.plot_frame, text="Wykres intuicji działania", font=("Arial", 18, "bold")
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

    def _on_module_selected(self, selected_title: str) -> None:
        self._show_module(find_theory_module(self.title_to_key[selected_title]))

    def _show_module(self, module: TheoryModule) -> None:
        for child in self.text_frame.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.text_frame,
            text=module.title,
            font=("Arial", 24, "bold"),
            anchor="w",
            wraplength=620,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        self._text_card("Najważniejszy zapis", module.formula, row=1, monospace=True, height=92)
        self._text_card("Co to znaczy w aplikacji", module.explanation, row=2, height=118)
        self._text_card(
            "Jak tego używać",
            "\n".join(f"• {item}" for item in module.interpretation),
            row=3,
            height=max(110, 36 * len(module.interpretation)),
        )
        self._text_card("Szybka reguła", self._quick_rule(module), row=4, height=92)
        self._draw_figure(module)

    def _quick_rule(self, module: TheoryModule) -> str:
        rules = {
            "regression_metrics": "RMSE/MAE czytaj jako wielkość błędu. R² czytaj jako ogólne dopasowanie — im bliżej 1, tym lepiej.",
            "classification_metrics": "Accuracy pokazuje trafność ogólną, ale przy nierównych klasach patrz przede wszystkim na F1.",
            "overfitting": "Gdy wynik treningowy jest świetny, a testowy słaby, model prawdopodobnie zapamiętał dane zamiast nauczyć się wzorca.",
            "feature_importance": "Wysoka ważność cechy mówi, że model często jej używa, ale nie dowodzi jeszcze przyczyny biznesowej.",
            "quality": "Dobry model jakości powinien mieć mały błąd i punkty blisko linii predykcja = rzeczywistość.",
            "delay": "Dla opóźnień szczególnie pilnuj dużych błędów, bo pojedyncza pomyłka może mocno zmienić kolejność zleceń.",
            "schedule": "Strategia to rekomendacja klasy — warto sprawdzić, czy podobne dane dają podobną decyzję.",
            "sto": "W STO niżej znaczy lepiej: mniejsza suma spóźnień oznacza lepszą kolejność.",
            "priority": "Priorytet jest rankingiem użytkowym, więc jego sens zależy od wag jakości i opóźnienia.",
        }
        return rules.get(
            module.key,
            "Zawsze zaczynaj od danych, potem sprawdzaj metryki i dopiero na końcu podejmuj decyzję.",
        )

    def _text_card(
        self, title: str, text: str, row: int, *, monospace: bool = False, height: int = 110
    ) -> None:
        card = ctk.CTkFrame(self.text_frame, corner_radius=18)
        card.grid(row=row, column=0, sticky="ew", padx=18, pady=8)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=("Arial", 17, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(14, 6)
        )
        box = ctk.CTkTextbox(
            card,
            height=height,
            wrap="word",
            font=("Consolas", 15, "bold") if monospace else ("Segoe UI", 13),
            fg_color="#1f2933",
            border_width=0,
        )
        box.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _draw_figure(self, module: TheoryModule) -> None:
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        fig = build_learning_figure(module.key)
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
