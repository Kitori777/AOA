from __future__ import annotations

import customtkinter as ctk

from AOA.gui.pages.main_page import MainPage
from AOA.gui.pages.readme_page import ReadmePage
from AOA.gui.pages.results_page import ResultsPage
from AOA.gui.pages.theory_page import TheoryPage
from AOA.gui.pages.visual_page import VisualPage

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Główne okno aplikacji z lekkim, zwijanym paskiem bocznym."""

    def __init__(self):
        super().__init__()
        self.title("Production Optimization")
        self.geometry("1560x880")
        self.minsize(1180, 720)
        self.configure(fg_color="#08111a")

        self.sidebar_expanded = False
        self.active_page = "ReadmePage"
        self.nav_buttons: dict[str, ctk.CTkButton] = {}

        self.sidebar = ctk.CTkFrame(
            self,
            width=88,
            corner_radius=0,
            fg_color="#0a1722",
            border_width=1,
            border_color="#1c2a38",
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.container = ctk.CTkFrame(self, fg_color="#08111a")
        self.container.pack(side="right", fill="both", expand=True)

        self.pages = {}
        for Page in (ReadmePage, MainPage, VisualPage, ResultsPage, TheoryPage):
            page = Page(self.container)
            self.pages[Page.__name__] = page
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.build_sidebar()
        self.show("ReadmePage")

    def show(self, name: str) -> None:
        self.active_page = name
        self.pages[name].tkraise()
        self._refresh_sidebar_buttons()

    def build_sidebar(self) -> None:
        for child in self.sidebar.winfo_children():
            child.destroy()
        self.nav_buttons.clear()

        self.toggle_btn = ctk.CTkButton(
            self.sidebar,
            text="☰" if not self.sidebar_expanded else "‹  Menu",
            height=46,
            width=56 if not self.sidebar_expanded else 178,
            fg_color="#132232",
            hover_color="#1a3147",
            border_width=1,
            border_color="#24384b",
            command=self.toggle_sidebar,
        )
        self.toggle_btn.pack(padx=16, pady=(18, 20), fill="x")

        items = [
            ("ReadmePage", "▤", "Readme"),
            ("MainPage", "⌂", "Main"),
            ("VisualPage", "▟", "Visual"),
            ("ResultsPage", "▥", "Results"),
            ("TheoryPage", "✣", "Theory"),
        ]
        for name, icon, text in items:
            label = f"{icon}\n{text}" if not self.sidebar_expanded else f"{icon}   {text}"
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                height=64 if not self.sidebar_expanded else 42,
                width=62 if not self.sidebar_expanded else 178,
                corner_radius=10,
                fg_color="#0e1b28",
                hover_color="#162b3d",
                border_width=1,
                border_color="#183149",
                font=("Segoe UI", 11 if not self.sidebar_expanded else 13, "bold"),
                command=lambda page=name: self.show(page),
            )
            btn.pack(padx=14, pady=6, fill="x")
            self.nav_buttons[name] = btn

        ctk.CTkLabel(self.sidebar, text="", fg_color="transparent").pack(fill="both", expand=True)
        help_text = "?" if not self.sidebar_expanded else "?   Pomoc"
        ctk.CTkButton(
            self.sidebar,
            text=help_text,
            height=40,
            width=62 if not self.sidebar_expanded else 178,
            fg_color="#0e1b28",
            hover_color="#162b3d",
            border_width=1,
            border_color="#24384b",
        ).pack(padx=14, pady=(6, 10), fill="x")

        collapse_text = "»" if not self.sidebar_expanded else "«  Zwiń pasek"
        ctk.CTkButton(
            self.sidebar,
            text=collapse_text,
            height=34,
            width=62 if not self.sidebar_expanded else 178,
            fg_color="#102033",
            hover_color="#18314b",
            command=self.toggle_sidebar,
        ).pack(padx=14, pady=(0, 16), fill="x")
        self._refresh_sidebar_buttons()

    def toggle_sidebar(self) -> None:
        self.sidebar_expanded = not self.sidebar_expanded
        self.sidebar.configure(width=220 if self.sidebar_expanded else 88)
        self.build_sidebar()

    def _refresh_sidebar_buttons(self) -> None:
        for name, btn in self.nav_buttons.items():
            active = name == self.active_page
            btn.configure(
                fg_color="#123f78" if active else "#0e1b28",
                border_color="#1f8fff" if active else "#183149",
                hover_color="#155ca6" if active else "#162b3d",
            )
