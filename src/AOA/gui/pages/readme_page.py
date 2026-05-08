import customtkinter as ctk

from AOA.core.learning_content import GuideStep, get_guide_steps


class ReadmePage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.steps = get_guide_steps()
        self.active_index = 0
        self.step_buttons: list[ctk.CTkButton] = []
        self._build_layout()
        self._show_step(0)

    def _build_layout(self) -> None:
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(
            header, text="Interaktywna instrukcja użytkownika", font=("Arial", 24, "bold")
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            header,
            text="Klikaj kolejne kroki i sprawdzaj: co robi moduł, gdzie kliknąć i po co to jest.",
            font=("Segoe UI", 13),
            text_color="#cbd5e1",
        ).pack(anchor="w", padx=16, pady=(0, 14))

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=20, pady=(6, 20))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.nav_frame = ctk.CTkScrollableFrame(body, width=310, label_text="Kroki pracy")
        self.nav_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        for index, step in enumerate(self.steps):
            button = ctk.CTkButton(
                self.nav_frame,
                text=step.title,
                anchor="w",
                command=lambda i=index: self._show_step(i),
            )
            button.pack(fill="x", padx=8, pady=5)
            self.step_buttons.append(button)

        self.content = ctk.CTkScrollableFrame(body)
        self.content.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)
        self.content.grid_columnconfigure(0, weight=1)

    def _show_step(self, index: int) -> None:
        self.active_index = index
        for child in self.content.winfo_children():
            child.destroy()
        for button_index, button in enumerate(self.step_buttons):
            if button_index == index:
                button.configure(fg_color="#2563eb", hover_color="#1d4ed8")
            else:
                button.configure(fg_color="#334155", hover_color="#475569")
        self._render_step(self.steps[index])

    def _render_step(self, step: GuideStep) -> None:
        ctk.CTkLabel(self.content, text=step.title, font=("Arial", 24, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(18, 8)
        )
        self._info_card("Cel modułu", step.goal, row=1)
        self._list_card("Co kliknąć", step.clicks, row=2, icon="✅")
        self._info_card("Na czym to polega", step.explanation, row=3)
        self._list_card("Warto pamiętać", step.good_to_know, row=4, icon="💡")

        footer = ctk.CTkFrame(self.content, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=18, pady=(8, 18))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            footer,
            text="← Poprzedni krok",
            command=self._previous_step,
            state="normal" if self.active_index > 0 else "disabled",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            footer,
            text="Następny krok →",
            command=self._next_step,
            state="normal" if self.active_index < len(self.steps) - 1 else "disabled",
        ).grid(row=0, column=1, sticky="e")

    def _info_card(self, title: str, text: str, row: int) -> None:
        card = ctk.CTkFrame(self.content, corner_radius=16)
        card.grid(row=row, column=0, sticky="ew", padx=18, pady=8)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=("Arial", 17, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(14, 6)
        )
        ctk.CTkLabel(
            card,
            text=text,
            font=("Segoe UI", 13),
            text_color="#e2e8f0",
            justify="left",
            wraplength=760,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))

    def _list_card(self, title: str, items: tuple[str, ...], row: int, icon: str) -> None:
        card = ctk.CTkFrame(self.content, corner_radius=16)
        card.grid(row=row, column=0, sticky="ew", padx=18, pady=8)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=("Arial", 17, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(14, 6)
        )
        for item_index, item in enumerate(items, start=1):
            ctk.CTkLabel(
                card,
                text=f"{icon} {item}",
                font=("Segoe UI", 13),
                text_color="#e2e8f0",
                justify="left",
                wraplength=760,
                anchor="w",
            ).grid(row=item_index, column=0, sticky="ew", padx=18, pady=3)
        ctk.CTkLabel(card, text="", height=8).grid(row=len(items) + 1, column=0)

    def _previous_step(self) -> None:
        if self.active_index > 0:
            self._show_step(self.active_index - 1)

    def _next_step(self) -> None:
        if self.active_index < len(self.steps) - 1:
            self._show_step(self.active_index + 1)
