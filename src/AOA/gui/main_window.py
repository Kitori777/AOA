import customtkinter as ctk

from AOA.gui.pages.readme_page import ReadmePage
from AOA.gui.pages.main_page import MainPage
from AOA.gui.pages.visual_page import VisualPage
from AOA.gui.pages.results_page import ResultsPage
from AOA.gui.pages.theory_page import TheoryPage


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Production Optimization")
        self.geometry("1200x700")

        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.pack(side="left", fill="y")

        self.container = ctk.CTkFrame(self)
        self.container.pack(side="right", fill="both", expand=True)

        self.pages = {}
        for Page in (ReadmePage, MainPage, VisualPage, ResultsPage, TheoryPage):
            page = Page(self.container)
            self.pages[Page.__name__] = page
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.build_sidebar()
        self.show("ReadmePage")

    def show(self, name: str):
        self.pages[name].tkraise()

    def build_sidebar(self):
        ctk.CTkLabel(
            self.sidebar,
            text="MENU",
            font=("Arial", 18, "bold")
        ).pack(pady=20)

        page_names = [
            "ReadmePage",
            "MainPage",
            "VisualPage",
            "ResultsPage",
            "TheoryPage",
        ]

        for name in page_names:
            ctk.CTkButton(
                self.sidebar,
                text=name.replace("Page", ""),
                command=lambda n=name: self.show(n)
            ).pack(fill="x", pady=5, padx=10)
