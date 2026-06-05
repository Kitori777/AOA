from __future__ import annotations

import os
from pathlib import Path

import customtkinter as ctk

from AOA.core.self_learning import alice_self_learning_loop
from AOA.gui.assistant_panel import AOAAssistantPanel
from AOA.gui.pages.analytics_page import AnalyticsPage
from AOA.gui.pages.drawio_page import DrawIOPage
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
        self.assistant_panel: AOAAssistantPanel | None = None
        self.assistant_toggle: ctk.CTkButton | None = None
        self._assistant_ready = False
        self._autotour_after_ids: list[str] = []
        self._toggle_margin_x = 14
        self._toggle_margin_y = 16
        self._hotreload_state: dict[str, float] = {}
        self._hotreload_after_id: str | None = None

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
        for Page in (
            ReadmePage,
            MainPage,
            VisualPage,
            ResultsPage,
            AnalyticsPage,
            DrawIOPage,
            TheoryPage,
        ):
            page = Page(self.container)
            self.pages[Page.__name__] = page
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.build_sidebar()
        self._build_assistant_toggle()
        self.bind("<Configure>", self._on_window_resize)
        self.show("ReadmePage")
        self.after(1200, self._preload_assistant_in_background)
        if self._auto_self_learning_enabled():
            self.after(2500, self._start_self_learning_background)
        self.after(3000, self._start_runtime_hot_reload)

    def show(self, name: str) -> None:
        self.active_page = name
        self.pages[name].tkraise()
        self._place_assistant_toggle()
        if name == "TheoryPage" and hasattr(self.pages[name], "animation"):
            self.pages[name].animation.start_autoplay()
        self._refresh_sidebar_buttons()

    def build_sidebar(self) -> None:
        for child in self.sidebar.winfo_children():
            child.destroy()
        self.nav_buttons.clear()

        self.toggle_btn = ctk.CTkButton(
            self.sidebar,
            text="Menu" if not self.sidebar_expanded else "<  Menu",
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
            ("ReadmePage", "RD", "Readme"),
            ("MainPage", "MN", "Main"),
            ("VisualPage", "VS", "Visual"),
            ("ResultsPage", "RS", "Results"),
            ("AnalyticsPage", "AN", "Analytics"),
            ("DrawIOPage", "DG", "Diagrams"),
            ("TheoryPage", "TH", "Theory"),
        ]
        for name, icon, text in items:
            label = f"{icon}\n{text}" if not self.sidebar_expanded else f"{icon}  {text}"
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
            command=self.show_help,
        ).pack(padx=14, pady=(6, 10), fill="x")

        collapse_text = ">>" if not self.sidebar_expanded else "<<  Zwin pasek"
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

    def show_help(self) -> None:
        self.show("ReadmePage")

    def _build_assistant_toggle(self) -> None:
        self.assistant_toggle = ctk.CTkButton(
            self.container,
            text="ALICE",
            width=84,
            height=40,
            fg_color="#1f8fff",
            hover_color="#176ab8",
            command=self._toggle_assistant_window,
        )
        self._place_assistant_toggle()
        self.assistant_toggle.lift()

    def _build_assistant_window(self) -> None:
        if self.assistant_panel is not None and self.assistant_panel.winfo_exists():
            return
        self.assistant_panel = AOAAssistantPanel(
            self,
            navigate=self.show,
            focus_section=self.focus_page_section,
            start_autotour=self.start_autotour,
            current_page=lambda: self.active_page,
            run_app_task=self._run_assistant_task,
        )
        self._assistant_ready = True

    def _place_assistant_toggle(self) -> None:
        if self.assistant_toggle is None or not self.assistant_toggle.winfo_exists():
            return
        self.assistant_toggle.place(
            relx=1.0,
            rely=1.0,
            x=-self._toggle_margin_x,
            y=-self._toggle_margin_y,
            anchor="se",
        )
        self.assistant_toggle.lift()

    def _on_window_resize(self, _event=None) -> None:
        self._place_assistant_toggle()

    def _toggle_assistant_window(self) -> None:
        if self.assistant_panel is None or not self.assistant_panel.winfo_exists():
            self._build_assistant_window()
            return
        if str(self.assistant_panel.state()) == "withdrawn":
            self.assistant_panel.deiconify()
            self.assistant_panel.lift()
            self.assistant_panel.focus_force()
            return
        self.assistant_panel.lift()
        self.assistant_panel.focus_force()

    def _preload_assistant_in_background(self) -> None:
        try:
            self._build_assistant_window()
            if self.assistant_panel is not None and self.assistant_panel.winfo_exists():
                self.assistant_panel.withdraw()
            if self.assistant_toggle is not None and self.assistant_toggle.winfo_exists():
                self.assistant_toggle.configure(text="ALICE")
                self.assistant_toggle.lift()
        except Exception:
            # Keep app boot robust even if assistant preload fails.
            self._assistant_ready = False

    def _start_self_learning_background(self) -> None:
        try:
            alice_self_learning_loop.start(interval_seconds=900, initial_delay_seconds=30)
        except Exception:
            return

    @staticmethod
    def _auto_self_learning_enabled() -> bool:
        value = os.getenv("AOA_ALICE_AUTO_SELF_LEARNING", "0").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _start_runtime_hot_reload(self) -> None:
        self._scan_runtime_files(initialize=True)
        self._schedule_runtime_hot_reload()

    def _schedule_runtime_hot_reload(self) -> None:
        self._hotreload_after_id = self.after(5000, self._runtime_hot_reload_tick)

    def _runtime_hot_reload_tick(self) -> None:
        changed = self._scan_runtime_files(initialize=False)
        if changed and self.assistant_panel is not None and self.assistant_panel.winfo_exists():
            try:
                self.assistant_panel.reload_runtime()
            except Exception:
                pass
        self._schedule_runtime_hot_reload()

    def _scan_runtime_files(self, initialize: bool) -> bool:
        root = Path(__file__).resolve().parents[3]
        watched = [
            root / "docs" / "guide.md",
            root / "docs" / "theory.md",
            root / "src" / "AOA" / "core" / "assistant_service.py",
            root / "src" / "AOA" / "assets" / "assistant" / "model_pack.json",
            root / "src" / "AOA" / "assets" / "assistant" / "alice_white.png",
            root / "src" / "AOA" / "assets" / "assistant" / "alice2.png",
            root / "src" / "AOA" / "assets" / "assistant" / "alice3.png",
            root / "src" / "AOA" / "assets" / "assistant" / "alice4.png",
            root / "src" / "AOA" / "assets" / "assistant" / "alice5.png",
            root / "src" / "AOA" / "assets" / "assistant" / "alice6.png",
        ]
        changed = False
        for path in watched:
            if not path.exists():
                continue
            key = str(path)
            mtime = path.stat().st_mtime
            prev = self._hotreload_state.get(key)
            if initialize or prev is None:
                self._hotreload_state[key] = mtime
                continue
            if mtime != prev:
                self._hotreload_state[key] = mtime
                changed = True
        return changed

    def focus_page_section(self, page_name: str, section: str) -> None:
        page = self.pages.get(page_name)
        if page is None:
            return
        focus_method = getattr(page, "focus_section", None)
        if callable(focus_method):
            focus_method(section)

    def start_autotour(self) -> None:
        for aid in self._autotour_after_ids:
            try:
                self.after_cancel(aid)
            except Exception:
                pass
        self._autotour_after_ids = []
        steps = [
            ("ReadmePage", ""),
            ("MainPage", "models"),
            ("MainPage", "actions"),
            ("VisualPage", "controls"),
            ("ResultsPage", "toolbar"),
            ("AnalyticsPage", "controls"),
            ("DrawIOPage", "controls"),
            ("TheoryPage", ""),
        ]
        for idx, (page, section) in enumerate(steps):
            delay = idx * 1700
            self._autotour_after_ids.append(
                self.after(delay, lambda p=page, s=section: self._autotour_step(p, s))
            )

    def _autotour_step(self, page: str, section: str) -> None:
        self.show(page)
        if section:
            self.focus_page_section(page, section)

    def _run_assistant_task(self, task_name: str) -> str:
        try:
            if task_name == "visual:open":
                self.show("VisualPage")
                return "Jasne, juz przenioslam Cie do Visual."
            if task_name == "visual:draw":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "draw_plot"):
                    page.draw_plot()
                return "Gotowe, odswiezylam wykres w Visual."
            if task_name == "visual:sample_dashboard":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "load_sample_and_draw_dashboard"):
                    page.load_sample_and_draw_dashboard()
                return "Wczytalam sample i narysowalam Production Dashboard."
            if task_name == "results:refresh":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "refresh_view"):
                    page.refresh_view()
                return "Zrobione, odswiezylam widok wynikow."
            if task_name == "results:open":
                self.show("ResultsPage")
                return "Jasne, jestem juz w Results."
            if task_name == "analytics:open":
                self.show("AnalyticsPage")
                return "Jasne, jestem juz w Analytics."
            if task_name == "analytics:run":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "run_workflow"):
                    page.run_workflow()
                return "Uruchomilam wybrany workflow Data Analytics."
            if task_name == "drawio:open":
                self.show("DrawIOPage")
                return "Jasne, jestem juz w Diagrams Studio."
            if task_name == "drawio:template":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "load_template"):
                    page.load_template()
                return "Wczytalam wybrany szablon diagramu."
            if task_name == "results:sql_run":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "run_sql_query"):
                    page.run_sql_query()
                return "Uruchomilam zapytanie SQL."
            if task_name == "results:sql_reset":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "reset_sql_query"):
                    page.reset_sql_query()
                return "Wyzerowalam pole SQL."
            if task_name == "results:reset_filters":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "reset_filters"):
                    page.reset_filters()
                return "Filtry zostaly wyczyszczone."
            if task_name == "theory:autotour":
                self.start_autotour()
                return "Startuje autopokaz krok po kroku."
            if task_name == "main:train":
                self.show("MainPage")
                page = self.pages.get("MainPage")
                if page is not None and hasattr(page, "train"):
                    page.train()
                return "Uruchomilam trening modeli z aktualnymi ustawieniami."
            if task_name == "selflearn:start":
                return alice_self_learning_loop.start(interval_seconds=900)
            if task_name == "selflearn:stop":
                return alice_self_learning_loop.stop()
            if task_name == "selflearn:status":
                status_line = alice_self_learning_loop.status()
                report_line = alice_self_learning_loop.latest_report_summary()
                return f"{status_line}\n\n{report_line}"
            if task_name == "selflearn:now":
                return alice_self_learning_loop.run_once_now(reason="alice_operator")
            if task_name == "selflearn:report":
                return alice_self_learning_loop.latest_report_summary()
            if task_name == "selflearn:theory":
                return alice_self_learning_loop.latest_theory_summary()
            if task_name == "selflearn:plan":
                return alice_self_learning_loop.learning_plan_summary()
            if task_name == "selflearn:changes":
                return alice_self_learning_loop.changes_since_previous_summary()
            if task_name == "selflearn:daily":
                return alice_self_learning_loop.daily_summary_digest()[1]
            if task_name == "selflearn:growth":
                return alice_self_learning_loop.changes_since_previous_summary()
            return "Nie znam jeszcze tej akcji, ale moge to dodac."
        except Exception:
            return "Nie udalo sie wykonac tej akcji. Sprawdz, czy potrzebne dane sa juz wczytane."
