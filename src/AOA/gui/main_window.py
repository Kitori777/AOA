from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from AOA.core.file_manager_service import (
    delete_managed_file,
    list_managed_files,
    preview_managed_file,
)
from AOA.core.release_segments import (
    data_contract_summary,
    report_template_summary,
    segment_summary,
)
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


ALICE_DIAGRAM_RECIPES: dict[str, str] = {
    "drawio:create_bpmn": "Start zdarzenia -> przyjecie zgloszenia -> walidacja -> bramka decyzji -> akceptacja -> realizacja -> koniec",
    "drawio:create_uml": "User -> ReportBuilder -> Dataset -> ExportService -> PDF/HTML wynik",
    "drawio:create_erd": "customers -> orders -> order_items -> products -> production_batches -> quality_results",
    "drawio:create_network": "Internet -> firewall -> aplikacja GUI -> API ML -> baza danych -> storage raportow",
    "drawio:create_swimlane": "Uzytkownik -> System -> Dane -> model -> raport -> decyzja biznesowa",
    "drawio:create_sequence": "Uzytkownik -> GUI: wybiera dane -> Serwis ML: trenuje -> Results: zapisuje wynik -> Report: generuje raport",
    "drawio:create_org": "Kierownik -> Planista -> Operator -> Kontrola jakosci -> Analityk danych -> Utrzymanie ruchu",
    "drawio:create_mindmap": "Cel analizy -> dane -> modele -> wykresy -> raport -> decyzje -> ryzyka",
    "drawio:create_decision": "Czy dane kompletne? -> jesli nie: czyszczenie -> jesli tak: trening -> czy metryka OK? -> wdrozenie albo poprawa",
    "drawio:create_kanban": "Backlog -> Do zrobienia -> W toku -> Kontrola QC -> Gotowe -> Zablokowane",
    "drawio:create_warehouse": "Przyjecie -> kontrola dostawy -> magazyn -> kompletacja -> bufor wysylki -> transport",
    "drawio:create_quality": "Probka -> pomiar -> limit OK? -> akceptacja -> blokada partii -> raport jakosci",
    "drawio:create_ml_pipeline": "CSV -> walidacja -> feature engineering -> train/test -> model -> metryki -> rejestr modelu -> raport",
    "drawio:create_maintenance": "Alert maszyny -> diagnoza -> priorytet -> naprawa -> test -> powrot do produkcji",
    "drawio:create_vsm": "Dostawca -> magazyn -> produkcja -> kontrola -> wysylka -> klient -> lead time i straty",
    "drawio:create_supply": "Dostawca -> transport -> magazyn centralny -> produkcja -> dystrybucja -> klient",
    "drawio:create_plant": "Wejscie materialu -> strefa magazynu -> linia 1 -> linia 2 -> QC -> pakowanie -> wysylka",
    "drawio:create_andon": "Alarm ANDON -> zatrzymanie linii -> lider zmiany -> analiza przyczyny -> akcja korekcyjna -> restart",
    "drawio:create_inventory": "Stan minimalny -> zamowienie -> dostawa -> przyjecie -> aktualizacja stanu -> kontrola zapasu",
    "drawio:create_energy": "Zasilanie -> rozdzielnia -> maszyny -> pomiar energii -> alarm zuzycia -> raport mediow",
}


class App(ctk.CTk):
    """Główne okno aplikacji z lekkim, zwijanym paskiem bocznym."""

    def __init__(self):
        super().__init__()
        self.title("AOA - Aplikacja Optymalnego Algorytmowania")
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
        self.file_manager_window: ctk.CTkToplevel | None = None
        self._file_manager_selected: Path | None = None

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
            ("AnalyticsPage", "RP", "Report"),
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

    def open_file_manager_window(self) -> None:
        if self.file_manager_window is not None and self.file_manager_window.winfo_exists():
            self.file_manager_window.lift()
            self.file_manager_window.focus_force()
            return

        window = ctk.CTkToplevel(self)
        window.title("AOA - podglad i usuwanie plikow")
        window.geometry("1120x720")
        window.minsize(980, 620)
        window.configure(fg_color="#08111a")
        self.file_manager_window = window
        self._file_manager_selected = None

        header = ctk.CTkFrame(window, fg_color="#0b1b2a", corner_radius=14)
        header.pack(fill="x", padx=18, pady=(18, 10))
        ctk.CTkLabel(
            header,
            text="Menedzer plikow AOA",
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text="Podejrzyj wygenerowane dane, raporty, HTML, wykresy i modele. Usuniecie wymaga potwierdzenia.",
            text_color="#bfdbfe",
            wraplength=980,
        ).pack(anchor="w", padx=18, pady=(0, 14))

        body = ctk.CTkFrame(window, fg_color="#0d1522", corner_radius=14)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(body, fg_color="transparent")
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=14)
        toolbar.grid_columnconfigure(0, weight=1)
        status = ctk.StringVar(value="Wybierz plik z listy.")
        ctk.CTkLabel(toolbar, textvariable=status, text_color="#cbd5e1").grid(
            row=0, column=0, sticky="w"
        )

        file_list = ctk.CTkScrollableFrame(body, fg_color="#101b28", corner_radius=10)
        file_list.grid(row=1, column=0, sticky="nsew", padx=(14, 8), pady=(0, 14))
        preview = ctk.CTkTextbox(body, wrap="word", fg_color="#07111c")
        preview.grid(row=1, column=1, sticky="nsew", padx=(8, 14), pady=(0, 14))

        def _set_preview(text: str) -> None:
            preview.configure(state="normal")
            preview.delete("1.0", "end")
            preview.insert("1.0", text)
            preview.configure(state="disabled")

        def _select(path: Path) -> None:
            self._file_manager_selected = path
            try:
                text = preview_managed_file(path)
            except Exception as exc:
                text = f"Nie udalo sie zrobic podgladu:\n{exc}"
            status.set(f"Wybrano: {path.name}")
            _set_preview(text)

        def _refresh() -> None:
            for child in file_list.winfo_children():
                child.destroy()
            files = list_managed_files()
            if not files:
                ctk.CTkLabel(
                    file_list,
                    text="Brak plikow do pokazania w data/, models/ i docs/.",
                    text_color="#cbd5e1",
                ).pack(fill="x", padx=10, pady=10)
                _set_preview("Brak plikow do podgladu.")
                return
            for item in files:
                ctk.CTkButton(
                    file_list,
                    text=item.label,
                    anchor="w",
                    fg_color="#0b2942",
                    hover_color="#123f78",
                    command=lambda path=item.path: _select(path),
                ).pack(fill="x", padx=8, pady=4)
            status.set(f"Znaleziono plikow: {len(files)}")

        def _open_selected() -> None:
            if self._file_manager_selected is None:
                status.set("Najpierw wybierz plik.")
                return
            try:
                webbrowser.open_new_tab(self._file_manager_selected.resolve().as_uri())
            except Exception as exc:
                status.set(f"Nie udalo sie otworzyc pliku: {exc}")

        def _delete_selected() -> None:
            if self._file_manager_selected is None:
                status.set("Najpierw wybierz plik.")
                return
            path = self._file_manager_selected
            if not messagebox.askyesno(
                "Usunac plik?",
                f"Usunac ten plik z AOA?\n\n{path}\n\nSprawdz podglad przed potwierdzeniem.",
                parent=window,
            ):
                return
            try:
                deleted = delete_managed_file(path)
            except Exception as exc:
                status.set(f"Nie udalo sie usunac: {exc}")
                return
            self._file_manager_selected = None
            status.set(f"Usunieto: {deleted.name}")
            _set_preview("Plik zostal usuniety. Wybierz kolejny albo odswiez liste.")
            _refresh()

        ctk.CTkButton(toolbar, text="Odswiez", command=_refresh, width=120).grid(
            row=0, column=1, padx=6
        )
        ctk.CTkButton(toolbar, text="Otworz", command=_open_selected, width=120).grid(
            row=0, column=2, padx=6
        )
        ctk.CTkButton(
            toolbar,
            text="Usun wybrany",
            command=_delete_selected,
            width=150,
            fg_color="#b91c1c",
            hover_color="#991b1b",
        ).grid(row=0, column=3, padx=6)
        _refresh()

    def open_release_check_window(self) -> None:
        window = ctk.CTkToplevel(self)
        window.title("AOA - release-check i QA")
        window.geometry("1040x720")
        window.minsize(900, 620)
        window.configure(fg_color="#08111a")
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(window, fg_color="#0b1b2a", corner_radius=14)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Release-check AOA",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text=(
                "Jedno miejsce do kontroli przed publikacja: testy, HTML, raporty, "
                "historia artefaktow, sample i wiedza ALICE."
            ),
            text_color="#bfdbfe",
            wraplength=900,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        actions = ctk.CTkFrame(window, fg_color="#111827", corner_radius=14)
        actions.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        for idx in range(5):
            actions.grid_columnconfigure(idx, weight=1)
        buttons = [
            ("Otworz pliki", self.open_file_manager_window),
            ("QA HTML", lambda: self._run_assistant_task("app:html_qa")),
            ("Sample Main", lambda: self._run_assistant_task("main:sample_data")),
            ("Pelny raport", lambda: self._run_assistant_task("analytics:report_builder")),
            ("Tutoriale", lambda: self.show("ReadmePage")),
        ]
        for idx, (label, command) in enumerate(buttons):
            ctk.CTkButton(actions, text=label, command=command, height=38).grid(
                row=0, column=idx, sticky="ew", padx=8, pady=12
            )

        body = ctk.CTkTextbox(window, wrap="word", fg_color="#07111c")
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        files = list_managed_files(40)
        latest = "\n".join(f"- {item.label}" for item in files[:12]) or "- Brak plikow."
        checklist = (
            "CHECKLIST AOA\n"
            "=============\n"
            "1. Testy: uruchom pelny zestaw testow przed publikacja.\n"
            "2. Main: sprawdz generowanie danych, sample, custom ML/STO, TabPFN, XGBoost i trening.\n"
            "3. Visual: otworz HTML/D3, dashboard, SolutionTree, tooltipy, fullscreen i eksport.\n"
            "4. Results: sprawdz sample, SQL preview/statystyki/braki/top i eksport CSV.\n"
            "5. Report: sprawdz pelny builder, PDF preview, pliki, ML/STO analytics i eksporty.\n"
            "6. Diagrams: sprawdz szablony, kolory, auto layout, SVG, Mermaid i HTML.\n"
            "7. Theory: sprawdz ML, heurystyki, TabPFN/nowoczesne ML oraz wzory.\n"
            "8. ALICE: zapytaj 'co umiesz', 'co mozesz w Main', 'release check', 'otworz pliki'.\n"
            "9. Historia: sprawdz najnowsze pliki, modele, raporty i wyniki w menedzerze plikow.\n"
            "10. Dokumentacja: README, docs/guide.md i docs/alice_brain.json musza mowic tym samym jezykiem.\n\n"
            "NAJNOWSZE ARTEFAKTY\n"
            "===================\n"
            f"{latest}\n\n"
            "SAMPLE I TUTORIALE\n"
            "==================\n"
            "- Main: 'wczytaj sample do Main' przygotowuje dane treningowe.\n"
            "- Visual: 'wczytaj sample do Visual' i 'dashboard z opisu' testuja wykresy.\n"
            "- Results: 'wczytaj sample do Results' oraz SQL statystyki/braki/top testuja tabele.\n"
            "- Report: 'przetestuj raport' otwiera gotowy format w pelnym builderze.\n"
            "- Diagrams: 'przetestuj diagram' buduje diagram z opisu.\n"
            "- Theory: 'lekcja ML', 'pokaz XGBoost', 'pokaz TabPFN' prowadza przez animacje.\n"
        )
        body.insert("1.0", checklist)
        body.configure(state="disabled")

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

    def _prepare_report_builder(self, *, with_example: bool = True) -> object | None:
        self.show("AnalyticsPage")
        page = self.pages.get("AnalyticsPage")
        if page is None:
            return None
        if with_example and hasattr(page, "apply_report_example"):
            page.apply_report_example()
        return page

    def _create_smart_diagram(self, description: str) -> str:
        self.show("DrawIOPage")
        page = self.pages.get("DrawIOPage")
        if page is None or not hasattr(page, "_diagram_from_description"):
            return "Nie moge teraz utworzyc diagramu, bo Diagrams Studio nie jest gotowe."
        nodes, edges, template, note = page._diagram_from_description(description)
        page.nodes = nodes
        page.edges = edges
        page.template_var.set(template)
        page.selected_node_id = nodes[0].id if nodes else None
        if hasattr(page, "_refresh_node_menus"):
            page._refresh_node_menus()
        if hasattr(page, "_draw_preview"):
            page._draw_preview()
        if hasattr(page, "status_var"):
            page.status_var.set(f"ALICE zbudowala diagram: {template} | {note}")
        return f"Zbudowalam diagram typu {template}. Mozesz teraz edytowac teksty, kolory i polaczenia."

    def _add_quick_diagram_block(self, block_name: str) -> str:
        self.show("DrawIOPage")
        page = self.pages.get("DrawIOPage")
        if page is None:
            return "Nie moge teraz dodac elementu, bo Diagrams Studio nie jest gotowe."
        if block_name == "Notatka" and hasattr(page, "add_quick_shape"):
            page.add_quick_shape("note")
        elif block_name == "Kontener" and hasattr(page, "add_quick_shape"):
            page.add_quick_shape("container")
        elif hasattr(page, "quick_block_var") and hasattr(page, "add_quick_block"):
            page.quick_block_var.set(block_name)
            page.add_quick_block()
        return f"Dodalam do diagramu blok: {block_name}."

    def _main_page_for_alice(self):
        self.show("MainPage")
        return self.pages.get("MainPage")

    def _main_spec_text(self, spec) -> str:
        parts = [
            getattr(spec, "name", ""),
            getattr(spec, "label", ""),
            getattr(spec, "focus", ""),
            getattr(spec, "description", ""),
            getattr(spec, "task_type", ""),
            getattr(spec, "target", ""),
        ]
        return " ".join(str(part).lower() for part in parts if part)

    def _refresh_main_after_alice(self, page) -> None:
        if page is None:
            return
        for method_name in ("render_summary", "render_status", "render_preview"):
            method = getattr(page, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass

    def _set_main_backend_for_alice(self, backend: str) -> str:
        page = self._main_page_for_alice()
        if page is None or not hasattr(page, "backend_var"):
            return "Main nie jest jeszcze gotowy do ustawienia backendu."
        page.backend_var.set(backend)
        self._refresh_main_after_alice(page)
        label = "TabPFN" if backend == "tabpfn" else "classic ML"
        return f"Ustawilam backend Main na {label}."

    def _select_main_models_for_alice(self, mode: str, *, clear: bool = False) -> str:
        page = self._main_page_for_alice()
        if page is None or not hasattr(page, "model_vars"):
            return "Main nie jest jeszcze gotowy do wyboru modeli."
        if clear:
            for var in page.model_vars.values():
                var.set(False)

        selected: list[str] = []

        def _mark(spec) -> None:
            var = page.model_vars.get(spec.name)
            if var is not None:
                var.set(True)
                selected.append(spec.name)

        if mode == "clear":
            for var in page.model_vars.values():
                var.set(False)
            self._refresh_main_after_alice(page)
            return "Odznaczylam wszystkie modele w Main."

        if mode in {"quality", "delay", "schedule"}:
            keywords = {
                "quality": ("quality", "jakosc", "jakość", "cena", "odpad"),
                "delay": ("delay", "opoz", "opóź", "termin", "late"),
                "schedule": ("schedule", "harmonogram", "class", "strateg"),
            }[mode]
            for spec in getattr(page, "ml_model_specs", []):
                if any(keyword in self._main_spec_text(spec) for keyword in keywords):
                    _mark(spec)
        elif mode == "all_ml":
            for spec in getattr(page, "ml_model_specs", []):
                _mark(spec)
        elif mode == "basic_ml":
            for target in ("quality", "delay", "schedule"):
                before = len(selected)
                self._select_main_models_for_alice(target, clear=False)
                selected = [name for name, var in page.model_vars.items() if var.get()]
                if len(selected) == before:
                    continue
        elif mode == "all_sto":
            for spec in getattr(page, "mh_model_specs", []):
                _mark(spec)
        elif mode == "basic_sto":
            for spec in getattr(page, "mh_model_specs", []):
                if spec.name in {"MT", "MO", "MZO", "MOPT"}:
                    _mark(spec)

        self._refresh_main_after_alice(page)
        if not selected:
            return "Nie znalazlam pasujacego modelu w Main, ale zostawilam ekran modeli otwarty."
        return f"Zaznaczylam w Main: {', '.join(dict.fromkeys(selected))}."

    def _prepare_main_data_for_alice(self) -> str:
        page = self._main_page_for_alice()
        if page is None or not hasattr(page, "gen"):
            return "Main nie jest jeszcze gotowy do przygotowania danych."
        page.gen()
        return "Przygotowalam dane treningowe w Main na podstawie aktualnych parametrow."

    def _train_main_for_alice(self) -> str:
        page = self._main_page_for_alice()
        if page is None or not hasattr(page, "train"):
            return "Main nie jest jeszcze gotowy do treningu."
        if getattr(page, "df_train", None) is None:
            page.gen()
        page.train()
        return "Uruchomilam trening w Main dla aktualnie zaznaczonych modeli."

    def _run_assistant_task(self, task_name: str) -> str:
        try:
            if task_name == "files:open":
                self.open_file_manager_window()
                return (
                    "Otworzylam menedzer plikow AOA. Mozesz podejrzec HTML, CSV, raporty, modele i usunac plik dopiero po potwierdzeniu."
                )
            if task_name == "app:release_check":
                self.open_release_check_window()
                return (
                    "Otworzylam centrum release-check AOA.\n"
                    "1. Uruchom testy jednostkowe i przeplywowe.\n"
                    "2. Sprawdz Main: generowanie danych, custom ML/STO, TabPFN i trening.\n"
                    "3. Sprawdz Visual: kazdy typ HTML, dashboard, SolutionTree i eksport.\n"
                    "4. Sprawdz Results: wczytanie pliku, SQL, filtry i CSV.\n"
                    "5. Sprawdz Report: pelny builder, PDF preview, pliki i eksporty.\n"
                    "6. Sprawdz Diagrams: szablony, kolory, eksport SVG/Mermaid/HTML.\n"
                    "7. Sprawdz Theory: ML, heurystyki i nowoczesne ML.\n"
                    "8. Zapytaj ALICE: 'co umiesz', 'co mozesz w Main', 'co mozesz w Report'."
                )
            if task_name == "app:history":
                self.open_file_manager_window()
                return (
                    "Pokazuje historie artefaktow AOA: dane, modele, raporty, HTML, JSON i notebooki. "
                    "To jest praktyczna historia treningow i workflowow, bo kazdy zapisany wynik trafia do kontrolowanych katalogow."
                )
            if task_name == "app:tutorials":
                self.show("ReadmePage")
                return (
                    "Pokazuje interaktywna instrukcje AOA. Znajdziesz tu kroki pracy, tutoriale modulow, sample i linki do Theory."
                )
            if task_name == "app:samples":
                self.show("MainPage")
                page = self.pages.get("MainPage")
                if page is not None and hasattr(page, "gen"):
                    page.gen()
                return (
                    "Przygotowalam sample w Main. Mozesz teraz poprosic o sample Visual, Results, raport albo diagram."
                )
            if task_name == "app:model_compare":
                self.show("ResultsPage")
                return (
                    "Przenosze do Results. Porownuj modele po metrykach: regresja RMSE/MAE/R2, klasyfikacja accuracy/F1, STO opoznienia/bufor/kolejka."
                )
            if task_name == "app:segments":
                return segment_summary()
            if task_name == "app:report_templates":
                self.show("AnalyticsPage")
                return report_template_summary()
            if task_name == "app:data_contract":
                self.show("MainPage")
                return data_contract_summary()
            if task_name == "app:quality_review":
                return (
                    "Robie szybki audyt aktualnej pracy AOA.\n"
                    "1. Cel: czy wiadomo, jaka decyzje wspiera artefakt.\n"
                    "2. Dane: czy wejscie jest opisane, kompletne i bez podejrzanych brakow.\n"
                    "3. Metoda: czy model, wykres, diagram albo raport pasuje do celu.\n"
                    "4. Czytelnosc: czy teksty, osie, kolory i polaczenia nie nachodza na siebie.\n"
                    "5. Wynik: czy sa metryki, interpretacja, ryzyka i rekomendowany nastepny krok.\n"
                    "Napisz konkretniej: 'ocen diagram', 'ocen raport', 'ocen wykres' albo 'ocen model', a dam checkliste pod ten tryb."
                )
            if task_name == "app:html_qa":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "open_d3_report"):
                    page.open_d3_report()
                return (
                    "Otworzylam Visual i interaktywny HTML do kontroli. Sprawdz fullscreen, eksport, tooltipy, osie, legendy, reset widoku i czy wykres nie wychodzi poza ekran."
                )
            if task_name == "main:open":
                self.show("MainPage")
                return "Jasne, jestem juz w Main. Tu zaczyna sie praca z danymi, ML, TabPFN i STO."
            if task_name == "main:generate":
                self.show("MainPage")
                page = self.pages.get("MainPage")
                if page is not None and hasattr(page, "gen"):
                    page.gen()
                return "Wygenerowalam dane testowe w Main i odswiezylam podsumowanie."
            if task_name == "main:sample_data":
                return self._prepare_main_data_for_alice()
            if task_name == "main:test_pipeline":
                self.show("MainPage")
                page = self.pages.get("MainPage")
                if page is not None and hasattr(page, "gen"):
                    page.gen()
                self.focus_page_section("MainPage", "models")
                return (
                    "Pokazuje testowy pipeline w Main: dane sa przygotowane, a panel modeli jest podswietlony. "
                    "Mozesz teraz uruchomic trening albo poprosic mnie: 'uruchom trening'."
                )
            if task_name == "main:load_file":
                self.show("MainPage")
                page = self.pages.get("MainPage")
                if page is not None and hasattr(page, "load_from_disk"):
                    page.load_from_disk()
                return "Otworzylam wybor pliku danych w Main."
            if task_name == "main:focus_data":
                self.show("MainPage")
                self.focus_page_section("MainPage", "generation")
                return "Pokazuje parametry generowania danych: rekordy, test size, seed, czasy i bufory."
            if task_name == "main:focus_models":
                self.show("MainPage")
                self.focus_page_section("MainPage", "models")
                return "Pokazuje wybor modeli: classic ML, TabPFN, XGBoost, wlasne modele i heurystyki STO."
            if task_name == "main:select_quality":
                return self._select_main_models_for_alice("quality")
            if task_name == "main:select_delay":
                return self._select_main_models_for_alice("delay")
            if task_name == "main:select_schedule":
                return self._select_main_models_for_alice("schedule")
            if task_name == "main:select_all_ml":
                return self._select_main_models_for_alice("all_ml")
            if task_name == "main:select_basic_ml":
                return self._select_main_models_for_alice("basic_ml")
            if task_name == "main:select_all_sto":
                return self._select_main_models_for_alice("all_sto")
            if task_name == "main:select_basic_sto":
                return self._select_main_models_for_alice("basic_sto")
            if task_name == "main:clear_models":
                return self._select_main_models_for_alice("clear")
            if task_name == "main:backend_tabpfn":
                return self._set_main_backend_for_alice("tabpfn")
            if task_name == "main:backend_classic":
                return self._set_main_backend_for_alice("classic")
            if task_name == "main:run_sto":
                self.show("MainPage")
                page = self.pages.get("MainPage")
                if page is not None and hasattr(page, "run_sto_analysis"):
                    page.run_sto_analysis()
                return "Uruchomilam szybka analize STO dla aktualnych zadan."
            if task_name == "visual:open":
                self.show("VisualPage")
                return "Jasne, juz przenioslam Cie do Visual."
            if task_name == "visual:load_file":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "load_file"):
                    page.load_file()
                return "Otworzylam wybor pliku w Visual. Po wczytaniu dobierzemy typ wykresu do kolumn."
            if task_name == "visual:load_sample":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "load_sample_data"):
                    page.load_sample_data()
                    if hasattr(page, "draw_plot"):
                        page.draw_plot()
                return "Wczytalam sample do Visual i narysowalam domyslny wykres."
            if task_name == "visual:auto_chart":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "auto_chart_from_sample"):
                    page.auto_chart_from_sample()
                return "Dobralam wykres do dostepnych kolumn i narysowalam go w Visual."
            if task_name == "visual:prompt_scatter":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "draw_sample_from_prompt"):
                    page.draw_sample_from_prompt("scatter czas termin")
                return "Narysowalam scatter z opisu na danych przykladowych."
            if task_name == "visual:prompt_histogram":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "draw_sample_from_prompt"):
                    page.draw_sample_from_prompt("histogram czas")
                return "Narysowalam histogram z opisu na danych przykladowych."
            if task_name == "visual:prompt_dashboard":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "load_sample_and_draw_dashboard"):
                    page.load_sample_and_draw_dashboard()
                return "Narysowalam dashboard produkcyjny na danych przykladowych."
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
            if task_name == "visual:open_d3":
                self.show("VisualPage")
                page = self.pages.get("VisualPage")
                if page is not None and hasattr(page, "open_d3_report"):
                    page.open_d3_report()
                return "Otworzylam ostatni interaktywny raport HTML/D3 z Visual."
            if task_name == "visual:focus_controls":
                self.show("VisualPage")
                self.focus_page_section("VisualPage", "controls")
                return "Pokazuje ustawienia wykresow: biblioteka, typ wykresu, osie i opcje rysowania."
            if task_name == "results:refresh":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "refresh_view"):
                    page.refresh_view()
                return "Zrobione, odswiezylam widok wynikow."
            if task_name == "results:open":
                self.show("ResultsPage")
                return "Jasne, jestem juz w Results."
            if task_name == "results:load_file":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "load_file"):
                    page.load_file()
                return "Otworzylam wybor pliku w Results. Po wczytaniu moge od razu pokazac SQL."
            if task_name == "results:load_sample":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "load_sample_data"):
                    page.load_sample_data()
                return "Wczytalam sample do Results i pokazuje tabele do filtrowania."
            if task_name == "results:missing_report":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "show_missing_report"):
                    page.show_missing_report()
                return "Pokazuje raport brakow danych i kolumn wymagajacych uwagi."
            if task_name == "results:export_visible":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "export_visible"):
                    page.export_visible()
                return "Otworzylam eksport widocznych wynikow do CSV."
            if task_name == "results:export_sql":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "export_sql_visible"):
                    page.export_sql_visible()
                return "Otworzylam eksport aktualnego wyniku SQL do CSV."
            if task_name == "results:focus_filters":
                self.show("ResultsPage")
                self.focus_page_section("ResultsPage", "toolbar")
                return "Pokazuje filtry Results: plik, model, cel, metryki, SQL i odswiezanie."
            if task_name == "results:sql_preview":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "run_sql_example"):
                    page.run_sql_example("preview")
                return "Pokazuje przykladowe SQL: pierwsze 20 wierszy z tabeli results."
            if task_name == "results:sql_summary":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "run_sql_example"):
                    page.run_sql_example("summary")
                return "Pokazuje przykladowe SQL ze statystykami dla pierwszej kolumny liczbowej."
            if task_name == "results:sql_missing":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "run_sql_example"):
                    page.run_sql_example("missing")
                return "Pokazuje SQL, ktory liczy braki danych w kolumnach."
            if task_name == "results:sql_top":
                self.show("ResultsPage")
                page = self.pages.get("ResultsPage")
                if page is not None and hasattr(page, "run_sql_example"):
                    page.run_sql_example("top")
                return "Pokazuje SQL z rekordami o najwiekszej wartosci pierwszej kolumny liczbowej."
            if task_name == "analytics:open":
                self.show("AnalyticsPage")
                return "Jasne, jestem juz w Report Studio."
            if task_name == "analytics:run":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "run_workflow"):
                    page.run_workflow()
                return "Uruchomilam wybrany workflow Report Studio."
            if task_name == "analytics:run_all":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "run_all_workflows"):
                    page.run_all_workflows()
                return "Uruchomilam wszystkie workflow Report Studio."
            if task_name == "analytics:export_full_html":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "export_html_report"):
                    page.export_html_report()
                return "Wygenerowalam pelny raport HTML z Report Studio."
            if task_name == "analytics:focus_builder":
                self.show("AnalyticsPage")
                self.focus_page_section("AnalyticsPage", "report_builder")
                return "Pokazuje Report Builder: zrodlo raportu, podglad, komendy i pliki do wstawienia."
            if task_name == "analytics:report_builder":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "open_report_builder_window"):
                    page.open_report_builder_window()
                return "Otworzylam pelny Report Builder: po lewej piszesz, po srodku masz podglad, po prawej guide."
            if task_name == "analytics:example":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "apply_report_example"):
                    page.apply_report_example()
                    if hasattr(page, "open_report_builder_window"):
                        page.open_report_builder_window()
                return "Wczytalam gotowy przykladowy raport i otworzylam edytor do testowania."
            if task_name == "analytics:test":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None:
                    if hasattr(page, "run_workflow"):
                        page.run_workflow()
                    if hasattr(page, "apply_report_example"):
                        page.apply_report_example()
                    if hasattr(page, "open_report_builder_window"):
                        page.open_report_builder_window()
                return (
                    "Przetestowalam Report Studio: uruchomilam workflow, wczytalam gotowy format raportu "
                    "i otworzylam pelny edytor z podgladem."
                )
            if task_name == "analytics:create_report":
                page = self._prepare_report_builder(with_example=True)
                if page is not None:
                    for method_name in (
                        "add_ml_analytics_block",
                        "add_sto_analytics_block",
                        "add_pipeline_block",
                        "add_recommendations_block",
                    ):
                        if hasattr(page, method_name):
                            getattr(page, method_name)()
                    if hasattr(page, "open_report_builder_window"):
                        page.open_report_builder_window()
                return (
                    "Stworzylam szkic raportu: cel, dane, ML, STO, pipeline i rekomendacje. "
                    "Otworzylam pelny edytor, zebys mogl dopisac szczegoly."
                )
            if task_name == "analytics:add_ml":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "add_ml_analytics_block"):
                    page.add_ml_analytics_block()
                return "Dodalam sekcje analityki ML do raportu."
            if task_name == "analytics:add_sto":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "add_sto_analytics_block"):
                    page.add_sto_analytics_block()
                return "Dodalam sekcje STO / heurystyk do raportu."
            if task_name == "analytics:add_pipeline":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "add_pipeline_block"):
                    page.add_pipeline_block()
                return "Dodalam pipeline decyzyjny do raportu."
            if task_name == "analytics:add_kpi":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "add_kpi_block"):
                    page.add_kpi_block()
                return "Dodalam blok KPI do raportu."
            if task_name == "analytics:add_recommendations":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "add_recommendations_block"):
                    page.add_recommendations_block()
                return "Dodalam rekomendacje do raportu."
            if task_name == "analytics:add_chart":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "add_chart_block"):
                    page.add_chart_block()
                return "Dodalam blok wykresu do raportu."
            if task_name == "analytics:add_asset":
                page = self._prepare_report_builder(with_example=False)
                if page is not None:
                    if hasattr(page, "refresh_report_asset_menu"):
                        page.refresh_report_asset_menu(show_status=False)
                    if (
                        getattr(page, "report_asset_paths", None)
                        and hasattr(page, "add_selected_asset_to_report")
                    ):
                        page.add_selected_asset_to_report()
                        return "Dodalam najnowszy plik z biblioteki projektu do raportu."
                return "Nie znalazlam jeszcze plikow do wstawienia. Najpierw wygeneruj wykres, diagram albo raport."
            if task_name == "analytics:refresh_assets":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "refresh_report_asset_menu"):
                    page.refresh_report_asset_menu(show_status=True)
                return "Odswiezylam biblioteke plikow do raportow."
            if task_name == "analytics:create_ml_report":
                page = self._prepare_report_builder(with_example=True)
                if page is not None:
                    for method_name in (
                        "add_ml_analytics_block",
                        "add_chart_block",
                        "add_prediction_plan_block",
                        "add_recommendations_block",
                    ):
                        if hasattr(page, method_name):
                            getattr(page, method_name)()
                    if hasattr(page, "open_report_builder_window"):
                        page.open_report_builder_window()
                return "Stworzylam raport ML: predykcja, metryki, wykres, plan uzycia i rekomendacje."
            if task_name == "analytics:create_sto_report":
                page = self._prepare_report_builder(with_example=True)
                if page is not None:
                    for method_name in (
                        "add_sto_analytics_block",
                        "add_kpi_block",
                        "add_pipeline_block",
                        "add_recommendations_block",
                    ):
                        if hasattr(page, method_name):
                            getattr(page, method_name)()
                    if hasattr(page, "open_report_builder_window"):
                        page.open_report_builder_window()
                return "Stworzylam raport STO: heurystyki, KPI, pipeline decyzyjny i rekomendacje."
            if task_name == "analytics:export_notebook":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "export_notebook"):
                    page.export_notebook()
                return "Wygenerowalam notebook .ipynb dla dalszej analizy."
            if task_name == "analytics:export_actions":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None and hasattr(page, "export_actions_csv"):
                    page.export_actions_csv()
                return "Wygenerowalam CSV z lista akcji do dalszej pracy."
            if task_name == "analytics:export_html":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "export_custom_report_html"):
                    page.export_custom_report_html(open_after=True)
                return "Zapisalam raport jako HTML i otworzylam podglad."
            if task_name == "analytics:export_pdf":
                page = self._prepare_report_builder(with_example=False)
                if page is not None and hasattr(page, "export_custom_report_pdf"):
                    page.export_custom_report_pdf()
                return "Zapisalam raport jako PDF."
            if task_name == "analytics:preview_pdf":
                self.show("AnalyticsPage")
                page = self.pages.get("AnalyticsPage")
                if page is not None:
                    if hasattr(page, "apply_report_example"):
                        page.apply_report_example()
                    if hasattr(page, "preview_custom_report_pdf"):
                        page.preview_custom_report_pdf()
                return "Przygotowalam przykladowy raport i otworzylam faktyczny podglad PDF."
            if task_name == "drawio:open":
                self.show("DrawIOPage")
                return "Jasne, jestem juz w Diagrams Studio."
            if task_name == "drawio:template":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "load_template"):
                    page.load_template()
                return "Wczytalam wybrany szablon diagramu."
            if task_name == "drawio:smart_sample":
                return self._create_smart_diagram(
                    "CSV -> walidacja danych -> model ML -> metryki -> diagram procesu -> raport dla kierownika"
                )
            if task_name == "drawio:create_process":
                return self._create_smart_diagram(
                    "Start -> wczytaj dane -> sprawdz jakosc -> decyzja czy OK -> popraw bledy -> wynik -> raport"
                )
            if task_name == "drawio:create_production":
                return self._create_smart_diagram(
                    "Zlecenie -> magazyn materialu -> maszyna -> kontrola QC -> bufor WIP -> pakowanie -> wysylka"
                )
            if task_name == "drawio:create_logistics":
                return self._create_smart_diagram(
                    "Dostawca -> przyjecie -> magazyn -> kompletacja -> transport -> klient -> potwierdzenie"
                )
            if task_name == "drawio:create_system":
                return self._create_smart_diagram(
                    "Uzytkownik -> aplikacja GUI -> serwis ML -> baza danych -> raport HTML/PDF -> dashboard"
                )
            if task_name == "drawio:create_data_pipeline":
                return self._create_smart_diagram(
                    "Plik CSV -> walidacja -> czyszczenie danych -> cechy X -> model ML -> metryki -> raport"
                )
            if task_name in ALICE_DIAGRAM_RECIPES:
                return self._create_smart_diagram(ALICE_DIAGRAM_RECIPES[task_name])
            if task_name == "drawio:add_machine":
                return self._add_quick_diagram_block("Maszyna")
            if task_name == "drawio:add_warehouse":
                return self._add_quick_diagram_block("Magazyn")
            if task_name == "drawio:add_qc":
                return self._add_quick_diagram_block("Kontrola QC")
            if task_name == "drawio:add_ml_model":
                return self._add_quick_diagram_block("Model ML")
            if task_name == "drawio:add_kpi":
                return self._add_quick_diagram_block("KPI")
            if task_name == "drawio:add_note":
                return self._add_quick_diagram_block("Notatka")
            if task_name == "drawio:add_container":
                return self._add_quick_diagram_block("Kontener")
            if task_name == "drawio:export_html":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "export"):
                    page.export("html")
                return "Otworzylam zapis diagramu do HTML."
            if task_name == "drawio:export_svg":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "export"):
                    page.export("svg")
                return "Otworzylam zapis diagramu do SVG."
            if task_name == "drawio:smart_builder":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "show_smart_diagram_builder"):
                    page.show_smart_diagram_builder()
                return "Otworzylam kreator madrego diagramu z opisu."
            if task_name == "drawio:guide":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "show_diagram_guide"):
                    page.show_diagram_guide()
                return "Otworzylam guide: jak wymyslic i zbudowac dowolny diagram."
            if task_name == "drawio:auto_layout":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "auto_layout"):
                    page.auto_layout()
                return "Ulozylam aktualny diagram przez Auto layout."
            if task_name == "drawio:clear":
                self.show("DrawIOPage")
                page = self.pages.get("DrawIOPage")
                if page is not None and hasattr(page, "clear_diagram"):
                    page.clear_diagram()
                return "Wyczyscilam diagram. Mozesz zaczac od pustej planszy albo poprosic mnie o nowy szablon."
            if task_name == "theory:open":
                self.show("TheoryPage")
                return "Jestem w Theory. Tu pokazuje jedna animacje procesu modelu krok po kroku."
            if task_name == "theory:ml":
                self.show("TheoryPage")
                page = self.pages.get("TheoryPage")
                if page is not None and hasattr(page, "_set_family"):
                    page._set_family("ml")
                return "Pokazuje klasyczne ML w Theory: dane, cechy, model, wynik i wzory."
            if task_name == "theory:sto":
                self.show("TheoryPage")
                page = self.pages.get("TheoryPage")
                if page is not None and hasattr(page, "_set_family"):
                    page._set_family("mh")
                return "Pokazuje heurystyki STO w Theory: kolejka zadan, ranking, opoznienia i wzor STO."
            if task_name == "theory:tabpfn":
                self.show("TheoryPage")
                page = self.pages.get("TheoryPage")
                if page is not None and hasattr(page, "_set_family"):
                    page._set_family("tabpfn")
                    if hasattr(page, "_select_model"):
                        page._select_model("tabpfn_quality")
                return "Pokazuje TabPFN w Theory: tabela jako kontekst, prior pretrenowany i predykcja."
            if task_name == "theory:xgboost":
                self.show("TheoryPage")
                page = self.pages.get("TheoryPage")
                if page is not None and hasattr(page, "_set_family"):
                    page._set_family("tabpfn")
                    if hasattr(page, "_select_model"):
                        page._select_model("modern_xgboost_quality")
                return "Pokazuje XGBoost w Theory: baseline, residuale, drzewa korekcyjne, regularyzacja i walidacja."
            if task_name == "theory:mlp":
                self.show("TheoryPage")
                page = self.pages.get("TheoryPage")
                if page is not None and hasattr(page, "_set_family"):
                    page._set_family("tabpfn")
                    if hasattr(page, "_select_model"):
                        page._select_model("modern_mlp_delay")
                return "Pokazuje MLP w Theory: warstwy neuronowe, uczenie wag i predykcje opoznienia."
            if task_name == "theory:stacking":
                self.show("TheoryPage")
                page = self.pages.get("TheoryPage")
                if page is not None and hasattr(page, "_set_family"):
                    page._set_family("tabpfn")
                    if hasattr(page, "_select_model"):
                        page._select_model("modern_stacking_schedule")
                return "Pokazuje Stacking w Theory: kilka modeli bazowych i meta-model laczacy ich decyzje."
            if task_name == "theory:schedule":
                self.show("TheoryPage")
                page = self.pages.get("TheoryPage")
                if page is not None and hasattr(page, "_set_family"):
                    page._set_family("tabpfn")
                    if hasattr(page, "_select_model"):
                        page._select_model("tabpfn_schedule")
                return "Pokazuje Schedule w Theory: klasyfikacje strategii zamiast samej regresji liczbowej."
            if task_name == "app:create_demo":
                messages = [
                    self._run_assistant_task("main:generate"),
                    self._run_assistant_task("visual:sample_dashboard"),
                    self._run_assistant_task("drawio:smart_sample"),
                    self._run_assistant_task("analytics:create_report"),
                    self._run_assistant_task("theory:xgboost"),
                ]
                return "Zrobilam demo przeplywu aplikacji:\n- " + "\n- ".join(messages)
            if task_name == "learning:ml_path":
                messages = [
                    self._run_assistant_task("main:focus_models"),
                    self._run_assistant_task("theory:ml"),
                    self._run_assistant_task("theory:xgboost"),
                ]
                return "Ukladam sciezke nauki ML:\n- " + "\n- ".join(messages)
            if task_name == "learning:report_path":
                messages = [
                    self._run_assistant_task("analytics:focus_builder"),
                    self._run_assistant_task("analytics:create_report"),
                    self._run_assistant_task("analytics:preview_pdf"),
                ]
                return "Ukladam sciezke nauki raportow:\n- " + "\n- ".join(messages)
            if task_name == "learning:diagram_path":
                messages = [
                    self._run_assistant_task("drawio:guide"),
                    self._run_assistant_task("drawio:smart_builder"),
                    self._run_assistant_task("drawio:create_process"),
                ]
                return "Ukladam sciezke nauki diagramow:\n- " + "\n- ".join(messages)
            if task_name == "app:guide_next":
                page = self.active_page
                suggestions = {
                    "MainPage": "Jestes w Main. Najpierw wygeneruj/wczytaj dane, potem wybierz modele i uruchom trening albo STO.",
                    "VisualPage": "Jestes w Visual. Wczytaj sample, wybierz typ wykresu i narysuj dashboard albo SolutionTree.",
                    "ResultsPage": "Jestes w Results. Odswiez wyniki, ustaw filtry, sprawdz SQL i wyeksportuj widoczna tabele.",
                    "AnalyticsPage": "Jestes w Report Studio. Wczytaj gotowy format, dodaj ML/STO/KPI i sprawdz podglad PDF.",
                    "DrawIOPage": "Jestes w Diagrams. Opisz proces slowami albo wybierz szablon, potem uzyj Auto layout.",
                    "TheoryPage": "Jestes w Theory. Wybierz rodzine modeli i przechodz krokami przez jedna animacje.",
                }
                return suggestions.get(page, "Zacznij od Main: przygotuj dane, a potem przejdz do Visual, Results albo Report.")
            if task_name == "app:help":
                self.show_help()
                return "Otworzylam pomoc aplikacji."
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
                return self._train_main_for_alice()
            if task_name == "main:train_quality":
                self._select_main_models_for_alice("quality", clear=True)
                return self._train_main_for_alice()
            if task_name == "main:train_delay":
                self._select_main_models_for_alice("delay", clear=True)
                return self._train_main_for_alice()
            if task_name == "main:train_schedule":
                self._select_main_models_for_alice("schedule", clear=True)
                return self._train_main_for_alice()
            if task_name == "main:train_tabpfn_quality":
                self._set_main_backend_for_alice("tabpfn")
                self._select_main_models_for_alice("quality", clear=True)
                return self._train_main_for_alice()
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
