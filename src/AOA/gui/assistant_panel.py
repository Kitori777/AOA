from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from urllib import request

import customtkinter as ctk

from AOA.config import ASSISTANT_ASSETS_DIR, DATA_DIR
from AOA.core.assistant_service import AssistantService
from AOA.core.self_learning import alice_self_learning_loop


@dataclass
class AssistantAction:
    kind: str
    value: str


OPERATOR_TASK_MAP: list[tuple[tuple[str, ...], str]] = [
    (
        (
            "otworz pliki",
            "pokaz pliki",
            "menedzer plikow",
            "zarzadzaj plikami",
            "usun pliki",
            "posprzataj pliki",
            "podglad plikow",
        ),
        "files:open",
    ),
    (
        (
            "release check",
            "sprawdz release",
            "kontrola wydania",
            "check przed github",
            "przed publikacja",
        ),
        "app:release_check",
    ),
    (
        (
            "historia treningow",
            "historia workflowow",
            "historia plikow",
            "pokaz historie",
            "ostatnie pliki",
        ),
        "app:history",
    ),
    (
        (
            "porownaj modele",
            "porownywarka modeli",
            "porownanie modeli",
            "sprawdz modele",
        ),
        "app:model_compare",
    ),
    (
        (
            "pokaz tutoriale",
            "tutoriale krok po kroku",
            "instrukcja krok po kroku",
            "readme krok po kroku",
        ),
        "app:tutorials",
    ),
    (
        (
            "pokaz sample",
            "przykladowe dane",
            "dane przykladowe",
            "sample start",
        ),
        "app:samples",
    ),
    (
        (
            "kolejne segmenty",
            "segmenty rozwoju",
            "roadmap",
            "co dalej rozwijac",
            "co mozemy rozwinac",
        ),
        "app:segments",
    ),
    (
        (
            "szablony raportow",
            "report templates",
            "gotowe raporty",
            "formaty raportow",
        ),
        "app:report_templates",
    ),
    (
        (
            "kontrakt danych",
            "data contract",
            "wymagane kolumny",
            "walidacja danych przed treningiem",
        ),
        "app:data_contract",
    ),
    (
        (
            "ocen diagram",
            "sprawdz diagram",
            "audyt diagramu",
            "ocen raport",
            "sprawdz raport",
            "audyt raportu",
            "ocen wykres",
            "sprawdz wykres",
            "ocen model",
            "sprawdz model",
            "audyt workflow",
            "czy jest git",
        ),
        "app:quality_review",
    ),
    (
        (
            "qa html",
            "sprawdz html",
            "test html",
            "sprawdz wykresy html",
            "kontrola html",
        ),
        "app:html_qa",
    ),
    (("otworz main", "przejdz do main", "pokaz main"), "main:open"),
    (("generuj dane", "wygeneruj dane", "przygotuj dane testowe"), "main:generate"),
    (
        (
            "wczytaj sample do main",
            "zaladuj sample do main",
            "sample do main",
            "przygotuj dane do treningu",
            "dane treningowe sample",
        ),
        "main:sample_data",
    ),
    (("przetestuj main", "test main", "pokaz pipeline main"), "main:test_pipeline"),
    (("wczytaj dane z pliku", "zaladuj dane z pliku", "otworz dane csv"), "main:load_file"),
    (("pokaz parametry danych", "ustawienia danych", "parametry generowania"), "main:focus_data"),
    (("pokaz modele main", "wybor modeli", "panel modeli"), "main:focus_models"),
    (
        (
            "zaznacz quality",
            "wybierz quality",
            "model quality",
            "zaznacz jakosc",
            "model jakosci",
        ),
        "main:select_quality",
    ),
    (
        (
            "zaznacz delay",
            "wybierz delay",
            "model delay",
            "zaznacz opoznienie",
            "model opoznienia",
        ),
        "main:select_delay",
    ),
    (
        (
            "zaznacz schedule",
            "wybierz schedule",
            "model schedule",
            "zaznacz harmonogram",
            "model harmonogramu",
        ),
        "main:select_schedule",
    ),
    (
        ("zaznacz wszystkie ml", "wybierz wszystkie ml", "wszystkie modele ml"),
        "main:select_all_ml",
    ),
    (
        (
            "zaznacz podstawowe ml",
            "wybierz podstawowe ml",
            "quality delay schedule",
            "modele bazowe ml",
        ),
        "main:select_basic_ml",
    ),
    (
        ("zaznacz wszystkie sto", "wybierz wszystkie sto", "wszystkie heurystyki"),
        "main:select_all_sto",
    ),
    (
        ("zaznacz podstawowe sto", "wybierz podstawowe sto", "podstawowe heurystyki"),
        "main:select_basic_sto",
    ),
    (("odznacz modele", "wyczysc modele", "wyzeruj wybor modeli"), "main:clear_models"),
    (
        ("ustaw tabpfn", "backend tabpfn", "wybierz tabpfn", "trenuj tabpfn"),
        "main:backend_tabpfn",
    ),
    (
        ("ustaw classic", "backend classic", "wybierz classic", "klasyczny backend"),
        "main:backend_classic",
    ),
    (("uruchom sto", "analiza sto", "przetestuj sto"), "main:run_sto"),
    (
        ("odswiez visual", "aktualizuj wykres", "narysuj wykres", "zrob mi wykres", "zrob wykres"),
        "visual:draw",
    ),
    (("otworz visual", "przejdz do visual", "pokaz visual"), "visual:open"),
    (
        (
            "wczytaj dane z pliku do visual",
            "wczytaj plik do visual",
            "wczytaj dane do visual",
            "zaladuj plik do visual",
            "otworz csv w visual",
        ),
        "visual:load_file",
    ),
    (
        ("wczytaj sample do visual", "zaladuj sample visual", "sample do wykresu"),
        "visual:load_sample",
    ),
    (
        (
            "dobierz wykres",
            "wybierz wykres za mnie",
            "automatyczny wykres",
            "zrob wykres z opisu",
            "narysuj z opisu",
        ),
        "visual:auto_chart",
    ),
    (("scatter z opisu", "wykres scatter z opisu"), "visual:prompt_scatter"),
    (("histogram z opisu", "wykres histogram z opisu"), "visual:prompt_histogram"),
    (("dashboard z opisu", "wykres dashboard z opisu"), "visual:prompt_dashboard"),
    (("otworz raport d3", "pokaz html visual", "otworz html visual"), "visual:open_d3"),
    (("pokaz wybor wykresu", "ustawienia wykresu", "panel wykresow"), "visual:focus_controls"),
    (
        ("wczytaj sample i narysuj dashboard", "sample dashboard", "pokaz dashboard na sample"),
        "visual:sample_dashboard",
    ),
    (("przetestuj visual", "test visual", "pokaz przykladowy wykres"), "visual:sample_dashboard"),
    (("odswiez results", "odswiez wyniki"), "results:refresh"),
    (("przejdz do results", "otworz results", "pokaz results"), "results:open"),
    (
        (
            "wczytaj plik do results",
            "wczytaj dane do results",
            "zaladuj plik do results",
            "otworz csv w results",
        ),
        "results:load_file",
    ),
    (
        ("wczytaj sample do results", "zaladuj sample results", "sample do results"),
        "results:load_sample",
    ),
    (("pokaz braki danych", "raport brakow", "missing report"), "results:missing_report"),
    (("eksportuj widoczne wyniki", "zapisz widoczne wyniki", "eksport results"), "results:export_visible"),
    (("eksportuj wynik sql", "zapisz wynik sql", "csv sql"), "results:export_sql"),
    (("pokaz filtry results", "filtry results", "panel filtrow"), "results:focus_filters"),
    (("uruchom sql", "wykonaj sql", "przetestuj sql"), "results:sql_run"),
    (
        ("pokaz sql przyklad", "przykladowe sql", "sql sample", "sql pierwsze wiersze"),
        "results:sql_preview",
    ),
    (
        ("sql podsumowanie", "sql statystyki", "pokaz statystyki sql", "agregacja sql"),
        "results:sql_summary",
    ),
    (
        ("sql braki", "braki sql", "pokaz braki sql", "policz braki sql"),
        "results:sql_missing",
    ),
    (
        ("sql top", "najwieksze sql", "top rekordy sql"),
        "results:sql_top",
    ),
    (("reset sql",), "results:sql_reset"),
    (("reset filtry", "wyczysc filtry"), "results:reset_filters"),
    (
        ("otworz report", "przejdz do report", "otworz analytics", "przejdz do analytics", "data analytics"),
        "analytics:open",
    ),
    (
        ("uruchom report", "uruchom analytics", "analiza analytics", "workflow analytics", "workflow report"),
        "analytics:run",
    ),
    (("uruchom wszystkie raporty", "wykonaj wszystko report", "pelna analiza report"), "analytics:run_all"),
    (("wygeneruj html analytics", "raport html analytics", "eksport analytics html"), "analytics:export_full_html"),
    (("pokaz builder raportu", "focus builder raportu", "sekcja builder raportu"), "analytics:focus_builder"),
    (
        ("report builder", "otworz builder", "otworz edytor raportu", "pelny edytor raportu"),
        "analytics:report_builder",
    ),
    (
        ("wczytaj przyklad raportu", "gotowy raport", "szablon raportu", "format raportu"),
        "analytics:example",
    ),
    (
        ("stworz raport", "utworz raport", "napisz raport", "zrob raport", "przygotuj raport"),
        "analytics:create_report",
    ),
    (("dodaj ml do raportu", "sekcja ml raport", "analityka ml do raportu"), "analytics:add_ml"),
    (("dodaj sto do raportu", "sekcja sto raport", "heurystyki do raportu"), "analytics:add_sto"),
    (("dodaj pipeline do raportu", "pipeline do raportu"), "analytics:add_pipeline"),
    (("dodaj kpi do raportu", "kpi do raportu"), "analytics:add_kpi"),
    (("dodaj rekomendacje do raportu", "rekomendacje do raportu"), "analytics:add_recommendations"),
    (("dodaj wykres do raportu", "wykres do raportu"), "analytics:add_chart"),
    (("dodaj plik do raportu", "wstaw plik do raportu", "dodaj asset do raportu"), "analytics:add_asset"),
    (("odswiez pliki raportu", "odswiez biblioteke raportu"), "analytics:refresh_assets"),
    (("stworz raport ml", "raport ml", "przygotuj raport ml"), "analytics:create_ml_report"),
    (("stworz raport sto", "raport sto", "przygotuj raport sto"), "analytics:create_sto_report"),
    (("eksportuj notebook", "zrob notebook", "notebook ipynb"), "analytics:export_notebook"),
    (("eksportuj akcje csv", "csv akcji", "lista akcji csv"), "analytics:export_actions"),
    (("zapisz raport html", "eksport raport html"), "analytics:export_html"),
    (("zapisz raport pdf", "eksport raport pdf"), "analytics:export_pdf"),
    (
        ("przetestuj raport", "test raportu", "pokaz jak zrobic raport", "sprawdz report"),
        "analytics:test",
    ),
    (("podglad pdf", "przetestuj pdf", "pokaz pdf"), "analytics:preview_pdf"),
    (
        (
            "otworz diagrams",
            "otworz diagramy",
            "otworz drawio",
            "otworz draw.io",
            "draw io",
            "drawio",
            "diagramy",
        ),
        "drawio:open",
    ),
    (
        ("wczytaj szablon diagramu", "szablon diagrams", "szablon drawio", "szablon draw.io"),
        "drawio:template",
    ),
    (
        ("diagram z opisu", "madry diagram", "zbuduj diagram", "przetestuj diagram"),
        "drawio:smart_sample",
    ),
    (
        ("stworz diagram procesu", "utworz diagram procesu", "zrob diagram procesu"),
        "drawio:create_process",
    ),
    (
        ("stworz diagram produkcji", "utworz diagram produkcji", "zrob diagram produkcji"),
        "drawio:create_production",
    ),
    (
        ("stworz diagram logistyczny", "utworz diagram logistyczny", "zrob diagram logistyczny"),
        "drawio:create_logistics",
    ),
    (
        ("stworz diagram systemu", "utworz diagram systemu", "zrob diagram systemu"),
        "drawio:create_system",
    ),
    (("dodaj maszyne", "blok maszyna"), "drawio:add_machine"),
    (("dodaj magazyn", "blok magazyn"), "drawio:add_warehouse"),
    (("dodaj kontrole qc", "dodaj qc", "blok qc"), "drawio:add_qc"),
    (("dodaj model ml", "blok model ml"), "drawio:add_ml_model"),
    (("dodaj kpi do diagramu", "blok kpi"), "drawio:add_kpi"),
    (("dodaj notatke", "blok notatka"), "drawio:add_note"),
    (("dodaj kontener", "blok kontener"), "drawio:add_container"),
    (("zapisz diagram html", "eksport diagram html"), "drawio:export_html"),
    (("zapisz diagram svg", "eksport diagram svg"), "drawio:export_svg"),
    (("otworz kreator diagramu", "kreator diagramu", "builder diagramu"), "drawio:smart_builder"),
    (
        ("stworz diagram danych", "diagram danych", "diagram pipeline danych"),
        "drawio:create_data_pipeline",
    ),
    (("stworz diagram bpmn", "diagram bpmn", "proces bpmn"), "drawio:create_bpmn"),
    (("stworz uml", "diagram uml", "uml klas", "diagram klas"), "drawio:create_uml"),
    (("stworz erd", "diagram erd", "baza danych diagram"), "drawio:create_erd"),
    (("diagram sieci", "network diagram", "architektura sieci"), "drawio:create_network"),
    (("diagram swimlane", "swimlane", "odpowiedzialnosci proces"), "drawio:create_swimlane"),
    (("diagram sekwencji", "sequence diagram", "sekwencja systemu"), "drawio:create_sequence"),
    (("schemat organizacji", "org chart", "struktura zespolu"), "drawio:create_org"),
    (("mapa mysli", "mind map", "burza pomyslow"), "drawio:create_mindmap"),
    (("drzewo decyzji diagram", "diagram decyzji", "decision tree diagram"), "drawio:create_decision"),
    (("tablica kanban", "diagram kanban", "kanban board"), "drawio:create_kanban"),
    (("diagram magazynu", "warehouse flow", "przeplyw magazynu"), "drawio:create_warehouse"),
    (("kontrola jakosci diagram", "diagram qc", "quality control diagram"), "drawio:create_quality"),
    (("ml production pipeline", "pipeline ml produkcyjny", "diagram mlops"), "drawio:create_ml_pipeline"),
    (("diagram utrzymania ruchu", "maintenance flow", "utrzymanie ruchu"), "drawio:create_maintenance"),
    (("value stream map", "vsm", "mapa strumienia wartosci"), "drawio:create_vsm"),
    (("supply chain", "lancuch dostaw", "diagram dostaw"), "drawio:create_supply"),
    (("plant layout", "layout hali", "uklad zakladu"), "drawio:create_plant"),
    (("andon incident", "diagram awarii", "incydent andon"), "drawio:create_andon"),
    (("inventory replenishment", "uzupelnianie zapasow", "diagram zapasow"), "drawio:create_inventory"),
    (("energy media flow", "media energia", "diagram energii"), "drawio:create_energy"),
    (("guide diagram", "pomoc diagram", "jak robic diagram"), "drawio:guide"),
    (("auto layout", "uloz diagram", "wyrownaj diagram"), "drawio:auto_layout"),
    (("wyczysc diagram", "nowy pusty diagram"), "drawio:clear"),
    (("otworz theory", "przejdz do theory", "pokaz theory", "otworz teorie"), "theory:open"),
    (("pokaz xgboost", "theory xgboost", "animacja xgboost"), "theory:xgboost"),
    (("pokaz tabpfn", "theory tabpfn", "animacja tabpfn"), "theory:tabpfn"),
    (("pokaz sto", "theory sto", "animacja sto", "heurystyki theory"), "theory:sto"),
    (("pokaz ml", "theory ml", "animacja ml"), "theory:ml"),
    (("pokaz mlp", "theory mlp", "animacja mlp"), "theory:mlp"),
    (("pokaz stacking", "theory stacking", "animacja stacking"), "theory:stacking"),
    (("pokaz schedule", "theory schedule", "animacja schedule"), "theory:schedule"),
    (("lekcja ml", "lekcje ml", "daj lekcje ml", "naucz mnie ml", "sciezka ml"), "learning:ml_path"),
    (
        ("lekcja raportow", "lekcje raportow", "daj lekcje raportow", "naucz mnie raportow", "sciezka raportow"),
        "learning:report_path",
    ),
    (
        ("lekcja diagramow", "lekcje diagramow", "daj lekcje diagramow", "naucz mnie diagramow", "sciezka diagramow"),
        "learning:diagram_path",
    ),
    (("co powinienem kliknac", "prowadz mnie", "pilotuj mnie"), "app:guide_next"),
    (("otworz pomoc", "pokaz pomoc", "help aplikacji"), "app:help"),
    (("wlacz autopokaz", "start autopokaz", "demo aplikacji", "zademonstruj aplikacje"), "theory:autotour"),
    (
        ("stworz demo aplikacji", "przetestuj cala aplikacje", "pokaz caly przeplyw"),
        "app:create_demo",
    ),
    (
        (
            "uruchom trening",
            "trenuj modele",
            "naucz modele",
            "nauczaj modele",
            "wytrenuj modele",
            "uczenie modeli",
        ),
        "main:train",
    ),
    (
        ("trenuj quality", "naucz quality", "wytrenuj jakosc", "trenuj jakosc"),
        "main:train_quality",
    ),
    (
        ("trenuj delay", "naucz delay", "wytrenuj opoznienie", "trenuj opoznienie"),
        "main:train_delay",
    ),
    (
        ("trenuj schedule", "naucz schedule", "wytrenuj harmonogram", "trenuj harmonogram"),
        "main:train_schedule",
    ),
    (
        ("trenuj tabpfn quality", "naucz tabpfn quality", "wytrenuj tabpfn jakosc"),
        "main:train_tabpfn_quality",
    ),
    (("wlacz samonauke", "start samonauki", "selfnauka start"), "selflearn:start"),
    (("wylacz samonauke", "stop samonauki", "selfnauka stop"), "selflearn:stop"),
    (("status samonauki", "selfnauka status"), "selflearn:status"),
    (("raport teraz", "wygeneruj raport teraz", "selfnauka teraz"), "selflearn:now"),
    (("raport samonauki", "co zrobila samonauka", "pokaz raport"), "selflearn:report"),
    (("czego nauczyla sie o algorytmach", "raport teorii", "selfnauka teoria"), "selflearn:theory"),
    (("plan samonauki", "etap samonauki", "selfnauka plan"), "selflearn:plan"),
    (("co sie zmienilo", "zmiany samonauki", "delta samonauki"), "selflearn:changes"),
    (("podsumowanie dnia", "raport dzienny", "daily summary"), "selflearn:daily"),
    (("wzrost wiedzy", "growth", "jak rosnie wiedza"), "selflearn:growth"),
]


def collect_operator_tasks(prompt: str) -> list[str]:
    matches: list[tuple[int, str]] = []
    for aliases, task_name in OPERATOR_TASK_MAP:
        best_pos = None
        for alias in aliases:
            pos = prompt.find(alias)
            if pos >= 0 and (best_pos is None or pos < best_pos):
                best_pos = pos
        if best_pos is not None:
            matches.append((best_pos, task_name))
    matches.sort(key=lambda item: item[0])
    dedup: list[str] = []
    for _pos, task in matches:
        if task not in dedup:
            dedup.append(task)
    if "analytics:create_ml_report" in dedup and "analytics:create_report" in dedup:
        dedup.remove("analytics:create_report")
    if "analytics:create_sto_report" in dedup and "analytics:create_report" in dedup:
        dedup.remove("analytics:create_report")
    if "theory:mlp" in dedup and "theory:ml" in dedup:
        dedup.remove("theory:ml")
    if "visual:load_file" in dedup and "main:load_file" in dedup:
        dedup.remove("main:load_file")
    if "results:load_file" in dedup and "main:load_file" in dedup:
        dedup.remove("main:load_file")
    if any(task.startswith("visual:prompt_") or task == "visual:auto_chart" for task in dedup):
        if "visual:draw" in dedup:
            dedup.remove("visual:draw")
    if any(task.startswith("main:train_") for task in dedup) and "main:train" in dedup:
        dedup.remove("main:train")
    return dedup


class AOAAssistantPanel(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        *,
        navigate: Callable[[str], None],
        focus_section: Callable[[str, str], None],
        start_autotour: Callable[[], None],
        current_page: Callable[[], str],
        run_app_task: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.navigate = navigate
        self.focus_section = focus_section
        self.start_autotour = start_autotour
        self.current_page = current_page
        self.run_app_task = run_app_task
        self.assistant = AssistantService()
        self._talk_after_ids: list[str] = []
        self.voice_enabled = ctk.BooleanVar(value=True)
        self.response_profile = ctk.StringVar(value="normal")
        self.voice_names = self._load_system_voice_names()
        self.voice_choice = ctk.StringVar(value=self._default_voice_choice(self.voice_names))
        self.voice_engine = ctk.StringVar(value=os.getenv("AOA_ALICE_VOICE_ENGINE", "Windows"))
        self.voicebox_url = ctk.StringVar(
            value=os.getenv("AOA_VOICEBOX_SPEAK_URL", "http://127.0.0.1:17493/speak")
        )
        self.voicebox_voice = ctk.StringVar(value=os.getenv("AOA_VOICEBOX_VOICE", "female"))
        self.voice_rate = ctk.DoubleVar(value=-1)
        self.voice_volume = ctk.DoubleVar(value=92)
        self.operator_mode = ctk.BooleanVar(value=True)
        self.auto_confirm_heavy = ctk.BooleanVar(value=False)
        self._is_busy = False
        self._last_auto_report_ts = ""
        self._last_auto_report_sig = ""
        self._last_daily_summary_key = ""
        self._chat_log_dir = Path(__file__).resolve().parents[3] / "logs" / "alice_chat"
        self._chat_log_session = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.title("ALICE Assistant")
        self.geometry("620x700")
        self.minsize(520, 560)
        self.configure(fg_color="#071423")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        top.grid_columnconfigure(1, weight=1)

        self.avatar_idle, self.avatar_talk = self._load_alice_avatar()
        self.avatar_label = ctk.CTkLabel(top, text="", image=self.avatar_idle)
        self.avatar_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 8))

        ctk.CTkLabel(top, text="ALICE Assistant", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=1, sticky="w", pady=(2, 0)
        )
        ctk.CTkLabel(
            top,
            text="Pelny chat do pytan o aplikacje, procesy i modele.",
            text_color="#9db4cc",
        ).grid(row=1, column=1, sticky="w", pady=(0, 2))

        self.chat = ctk.CTkTextbox(self, wrap="word", fg_color="#0b1a2d", font=("Segoe UI", 13))
        self.chat.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.chat.configure(state="disabled")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        bottom.grid_columnconfigure(0, weight=1)

        self.input_var = ctk.StringVar(value="")
        entry = ctk.CTkEntry(
            bottom,
            textvariable=self.input_var,
            placeholder_text="Napisz pytanie (np. pokaz caly proces od danych do eksportu)...",
        )
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        entry.bind("<Return>", lambda _event: self._on_send())
        self.send_btn = ctk.CTkButton(bottom, text="Wyslij", width=90, command=self._on_send)
        self.send_btn.grid(row=0, column=1, sticky="e")
        ctk.CTkCheckBox(
            bottom, text="Glos ALICE", variable=self.voice_enabled, onvalue=True, offvalue=False
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ctk.CTkOptionMenu(
            bottom,
            values=["krotko", "normal", "ekspercko"],
            variable=self.response_profile,
            width=120,
        ).grid(row=1, column=1, sticky="e", pady=(8, 0))
        voice_row = ctk.CTkFrame(bottom, fg_color="transparent")
        voice_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        voice_row.grid_columnconfigure(0, weight=1)
        ctk.CTkOptionMenu(
            voice_row,
            values=self.voice_names or ["Auto kobiecy"],
            variable=self.voice_choice,
            width=300,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(voice_row, text="Test glosu", width=110, command=self._test_voice).grid(
            row=0, column=1, sticky="e"
        )
        voicebox_row = ctk.CTkFrame(bottom, fg_color="transparent")
        voicebox_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        voicebox_row.grid_columnconfigure(1, weight=1)
        ctk.CTkOptionMenu(
            voicebox_row,
            values=["Windows", "Voicebox"],
            variable=self.voice_engine,
            width=120,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkEntry(
            voicebox_row,
            textvariable=self.voicebox_url,
            placeholder_text="Voicebox local API URL",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkEntry(
            voicebox_row,
            textvariable=self.voicebox_voice,
            placeholder_text="female / nazwa glosu",
            width=150,
        ).grid(row=0, column=2, sticky="e")
        tuning_row = ctk.CTkFrame(bottom, fg_color="transparent")
        tuning_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        tuning_row.grid_columnconfigure(1, weight=1)
        tuning_row.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(tuning_row, text="Tempo", text_color="#9db4cc").grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkSlider(tuning_row, from_=-5, to=4, number_of_steps=9, variable=self.voice_rate).grid(
            row=0, column=1, sticky="ew", padx=(8, 14)
        )
        ctk.CTkLabel(tuning_row, text="Glosnosc", text_color="#9db4cc").grid(
            row=0, column=2, sticky="w"
        )
        ctk.CTkSlider(
            tuning_row, from_=40, to=100, number_of_steps=12, variable=self.voice_volume
        ).grid(row=0, column=3, sticky="ew", padx=(8, 0))
        ctk.CTkCheckBox(
            bottom,
            text="Tryb operatora",
            variable=self.operator_mode,
            onvalue=True,
            offvalue=False,
        ).grid(row=5, column=0, sticky="w", pady=(8, 0))
        ctk.CTkCheckBox(
            bottom,
            text="Auto-potwierdzaj ciezkie",
            variable=self.auto_confirm_heavy,
            onvalue=True,
            offvalue=False,
        ).grid(row=5, column=1, sticky="e", pady=(8, 0))

        self._append_assistant(
            "Hej. Jestem ALICE Assistant. Zapytaj o cokolwiek w aplikacji, "
            "a odpowiem i moge od razu przeniesc Cie do odpowiedniej sekcji."
        )
        self._start_auto_report_feed()

    def reload_runtime(self) -> None:
        """Reload ALICE knowledge/avatar without restarting whole app."""
        self.assistant = AssistantService()
        self.avatar_idle, self.avatar_talk = self._load_alice_avatar()
        self._set_talking(False)

    def _append_user(self, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"Ty:\n{text}\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")
        self._write_chat_log("user", text)

    def _append_assistant(self, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"ALICE:\n{text}\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")
        self._write_chat_log("assistant", text)

    def _on_send(self) -> None:
        if self._is_busy:
            return
        prompt = self.input_var.get().strip()
        if not prompt:
            return
        self.input_var.set("")
        self._set_talking(True)
        self._set_busy(True)
        self._append_user(prompt)
        lower_prompt = prompt.lower()
        if self.operator_mode.get():
            executed = self._run_operator_queue(lower_prompt)
            if executed is not None:
                self._append_assistant(executed)
                self._speak_async(executed)
                self._set_talking(False)
                self._set_busy(False)
                return

        profile = self.response_profile.get()
        threading.Thread(
            target=self._answer_worker,
            args=(lower_prompt, profile),
            daemon=True,
        ).start()

    def _answer_worker(self, prompt: str, profile: str) -> None:
        try:
            response, actions = self._answer(prompt, profile=profile)
        except Exception:
            response, actions = (
                "Przepraszam, chwilowo nie moge odpowiedziec. Sprobuj ponownie za chwile.",
                [],
            )
        self.after(0, lambda: self._apply_answer(response, actions))

    def _apply_answer(self, response: str, actions: list[AssistantAction]) -> None:
        self._append_assistant(response)
        self._speak_async(response)
        for action in actions:
            self._run_action(action)
        self._set_talking(False)
        self._set_busy(False)

    def _run_action(self, action: AssistantAction) -> None:
        if action.kind == "navigate":
            self.navigate(action.value)
        elif action.kind == "focus":
            page, section = action.value.split(":", 1)
            self.navigate(page)
            self.focus_section(page, section)
        elif action.kind == "demo":
            self.start_autotour()

    def _answer(self, prompt: str, profile: str = "normal") -> tuple[str, list[AssistantAction]]:
        actions: list[AssistantAction] = []

        if any(word in prompt for word in ("demo", "zademonstruj", "pokaz jak dziala")):
            actions.append(AssistantAction("demo", "full"))
            return (
                "Uruchamiam autopokaz: Readme -> Main -> Visual -> Results -> Theory.",
                actions,
            )

        if "gdzie tren" in prompt or "jak tren" in prompt:
            actions.append(AssistantAction("focus", "MainPage:models"))
            actions.append(AssistantAction("focus", "MainPage:actions"))
            return (
                "Trening jest w Main. Kroki: 1) wybierz modele, 2) wczytaj dane, "
                "3) kliknij Uruchom / zapisz wybrane modele.",
                actions,
            )

        if "visual" in prompt or "wykres" in prompt:
            actions.append(AssistantAction("focus", "VisualPage:controls"))
            return "Przenosze do Visual i podswietlam panel sterowania wykresu.", actions

        if "results" in prompt or "wynik" in prompt or "csv" in prompt:
            actions.append(AssistantAction("focus", "ResultsPage:toolbar"))
            return "Przenosze do Results i podswietlam toolbar filtrowania/eksportu.", actions

        task_reply = self._maybe_execute_task(prompt)
        if task_reply:
            return task_reply, actions

        rag_answer, _hits, _from_airi = self.assistant.answer(
            prompt,
            profile=profile,
        )
        return (rag_answer, actions)

    def _set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        try:
            self.send_btn.configure(state="disabled" if busy else "normal")
        except Exception:
            pass

    def _run_operator_queue(self, prompt: str) -> str | None:
        tasks = self._collect_tasks(prompt)
        if not tasks:
            return None
        if not callable(self.run_app_task):
            return "Tryb operatora jest chwilowo niedostepny."

        lines = ["Wykonuje plan operatora:"]
        for index, task_name in enumerate(tasks, start=1):
            if self._is_heavy_task(task_name) and not self.auto_confirm_heavy.get():
                ok = messagebox.askyesno(
                    "Potwierdz akcje",
                    f"Czy na pewno wykonac ciezsza akcje: {task_name} ?",
                    parent=self,
                )
                if not ok:
                    lines.append(f"{index}. Pomijam: {task_name} (anulowane).")
                    continue
            reply = self.run_app_task(task_name)
            lines.append(f"{index}. {reply}")
        return "\n".join(lines)

    @staticmethod
    def _is_heavy_task(task_name: str) -> bool:
        return task_name in {
            "main:train",
            "main:train_quality",
            "main:train_delay",
            "main:train_schedule",
            "main:train_tabpfn_quality",
            "selflearn:start",
        }

    def _collect_tasks(self, prompt: str) -> list[str]:
        return collect_operator_tasks(prompt)

    def _maybe_execute_task(self, prompt: str) -> str | None:
        if not callable(self.run_app_task):
            return None
        tasks = self._collect_tasks(prompt)
        for task_name in tasks[:1]:
            if self._is_heavy_task(task_name) and not self.auto_confirm_heavy.get():
                ok = messagebox.askyesno(
                    "Potwierdz akcje",
                    f"Czy na pewno wykonac ciezsza akcje: {task_name} ?",
                    parent=self,
                )
                if not ok:
                    return "Okej, pomijam te ciezsza akcje."
            return self.run_app_task(task_name)
        return None

    def _load_alice_avatar(self) -> tuple[ctk.CTkImage, ctk.CTkImage]:
        candidates = [
            ASSISTANT_ASSETS_DIR / "alice_white.png",
            ASSISTANT_ASSETS_DIR / "alice_avatar.png",
            DATA_DIR / "assistant_assets" / "alice_white.png",
            DATA_DIR / "assistant_assets" / "airi_avatar.png",
        ]
        preferred = next((p for p in candidates if p.exists()), candidates[0])
        preferred.parent.mkdir(parents=True, exist_ok=True)
        if not preferred.exists():
            from PIL import Image

            img = Image.new("RGBA", (512, 682), (13, 28, 49, 255))
            img.save(preferred)

        from PIL import Image

        base = Image.open(preferred).convert("RGBA")
        idle = ctk.CTkImage(light_image=base, dark_image=base, size=(96, 128))
        talk = ctk.CTkImage(light_image=base, dark_image=base, size=(102, 136))
        return idle, talk

    def _set_talking(self, talking: bool) -> None:
        self.avatar_label.configure(image=self.avatar_talk if talking else self.avatar_idle)

    def _test_voice(self) -> None:
        self._speak_async(
            "Czesc, jestem Alice. Najpierw powiem najwazniejszy wniosek, potem spokojnie wyjasnie, co widzisz i co kliknac dalej."
        )

    def _speak_async(self, text: str) -> None:
        if not self.voice_enabled.get():
            return
        speech = self._prepare_spoken_text(text)
        if not speech:
            return

        def _run() -> None:
            if self.voice_engine.get().lower() == "voicebox" and self._speak_with_voicebox(speech):
                return
            safe = speech.replace("'", "''")
            selected_voice = self.voice_choice.get().replace("'", "''")
            rate = int(round(float(self.voice_rate.get())))
            volume = int(round(float(self.voice_volume.get())))
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$voices = $s.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo }; "
                "$femalePl = $voices | Where-Object { $_.Culture.Name -like 'pl*' -and $_.Gender -eq 'Female' } | Select-Object -First 1; "
                "$femaleAny = $voices | Where-Object { $_.Gender -eq 'Female' } | Select-Object -First 1; "
                f"$chosenName = '{selected_voice}'; "
                "$chosen = $voices | Where-Object { $_.Name -eq $chosenName } | Select-Object -First 1; "
                "$selected = if ($chosen) { $chosen } elseif ($femalePl) { $femalePl } elseif ($femaleAny) { $femaleAny } else { $null }; "
                "if ($selected) { $s.SelectVoice($selected.Name) }; "
                f"$s.Rate = {rate}; $s.Volume = {volume}; "
                f"$s.Speak('{safe}');"
            )
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
            except Exception:
                return

        threading.Thread(target=_run, daemon=True).start()

    def _speak_with_voicebox(self, speech: str) -> bool:
        url = self.voicebox_url.get().strip()
        if not url:
            return False
        payload = {
            "text": speech,
            "voice": self.voicebox_voice.get().strip() or "female",
            "voice_id": self.voicebox_voice.get().strip() or "female",
            "format": "wav",
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "AOA-ALICE/1.0"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as resp:
                content_type = resp.headers.get("Content-Type", "")
                body = resp.read()
        except Exception:
            return False
        if "audio" not in content_type.lower() or not body:
            return True
        try:
            out_dir = DATA_DIR / "alice_voicebox"
            out_dir.mkdir(parents=True, exist_ok=True)
            suffix = ".mp3" if "mpeg" in content_type.lower() else ".wav"
            path = out_dir / f"alice_voicebox_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{suffix}"
            path.write_bytes(body)
            safe_path = str(path).replace("'", "''")
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    f"(New-Object Media.SoundPlayer '{safe_path}').PlaySync();",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception:
            return False
        return True

    @staticmethod
    def _load_system_voice_names() -> list[str]:
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.GetInstalledVoices() | Where-Object { $_.Enabled } | "
            "ForEach-Object { $_.VoiceInfo.Name }"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                check=False,
                capture_output=True,
                text=True,
                timeout=8,
            )
        except Exception:
            return ["Auto kobiecy"]
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return names or ["Auto kobiecy"]

    @staticmethod
    def _default_voice_choice(voices: list[str]) -> str:
        if not voices:
            return "Auto kobiecy"
        preferred_fragments = ("Paulina", "Jenny", "Aria", "Sonia", "Zira", "Female", "Kobieta")
        for fragment in preferred_fragments:
            match = next((voice for voice in voices if fragment.lower() in voice.lower()), None)
            if match:
                return match
        return voices[0]

    @staticmethod
    def _prepare_spoken_text(text: str, max_chars: int = 650) -> str:
        speech = str(text or "").strip()
        if not speech:
            return ""
        if "AUTO MELDUNEK:" in speech or "PODSUMOWANIE DNIA" in speech:
            best = re.search(r"najlepszy=([A-Za-z0-9_]+)\s*\(([^)]+)\)", speech)
            sto = re.search(r"STO best=([A-Za-z0-9_]+)\s*\(([^)]+)\)", speech)
            changes = "Sa nowe zmiany." if "Nowe zmiany:" in speech else "Nie ma istotnych zmian."
            parts = ["Mam nowy raport samonauki."]
            if best:
                parts.append(f"Najlepszy model to {best.group(1)}, wynik {best.group(2)}.")
            if sto:
                parts.append(f"Najlepsza metoda STO to {sto.group(1)}, wynik {sto.group(2)}.")
            parts.append(changes)
            return " ".join(parts)
        speech = AOAAssistantPanel._spoken_digest(speech)
        speech = re.sub(r"https?://\S+", " link ", speech)
        speech = re.sub(r"```.*?```", " fragment kodu ", speech, flags=re.S)
        speech = re.sub(r"[*_`#>|]+", " ", speech)
        speech = speech.replace("->", " do ").replace("/", " albo ")
        speech = AOAAssistantPanel._spoken_replacements(speech)
        speech = re.sub(r"\b[A-Z_]{3,}\b", lambda m: m.group(0).replace("_", " "), speech)
        speech = re.sub(r"\s*-\s+", ". ", speech)
        speech = re.sub(r"\s*\d+\.\s+", ". ", speech)
        speech = re.sub(r"\s+", " ", speech).strip()
        if len(speech) > max_chars:
            cut = speech[:max_chars].rsplit(".", 1)[0].strip()
            speech = (cut or speech[:max_chars]).strip() + ". Pelny tekst masz w oknie rozmowy."
        return speech

    @staticmethod
    def _spoken_digest(text: str) -> str:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        if not lines:
            return ""
        intro: list[str] = []
        how_to_read: list[str] = []
        next_steps: list[str] = []
        mode = "intro"
        for line in lines:
            normalized = line.rstrip(":").lower()
            if normalized in {"co dalej", "nastepne kroki", "następne kroki"}:
                mode = "next"
                continue
            if normalized in {"jak to czytac", "jak to czytać"}:
                mode = "read"
                continue
            if mode == "next":
                next_steps.append(line)
            elif mode == "read":
                how_to_read.append(line)
            else:
                intro.append(line)
        if not how_to_read and not next_steps:
            return text
        picked: list[str] = []
        if intro:
            picked.extend(intro[:3])
        if how_to_read:
            picked.append("Jak to czytac: " + " ".join(how_to_read[:3]))
        if next_steps:
            picked.append("Najwazniejsze kroki: " + " ".join(next_steps[:2]))
        return " ".join(picked) if picked else text

    @staticmethod
    def _spoken_replacements(text: str) -> str:
        phrase_replacements = {
            r"\bworkflow\b": "łork floł",
            r"\bworkflowy\b": "łork floły",
            r"\bworkflowem\b": "łork flołem",
            r"\bWorkflow\b": "Łork floł",
            r"\bWorkflowy\b": "Łork floły",
            r"\b__init__\b": "init",
            r"\brun\b": "ran",
            r"\bResult\b": "rizalt",
            r"\bPipeline\b": "pajp lajn",
            r"\bWorkflowResult\b": "łork floł rizalt",
            r"\bWorkflowPipeline\b": "łork floł pajp lajn",
        }
        for pattern, replacement in phrase_replacements.items():
            text = re.sub(pattern, replacement, text)
        replacements = {
            "HTML": "ha te em el",
            "CSV": "ce es fał",
            "SQL": "es ku el",
            "KPI": "ka pe i",
            "STO": "es te o",
            "ML": "em el",
            "D3": "di trzy",
            "X/Y/Z": "iks, igrek i zet",
            "X": "iks",
            "Y": "igrek",
            "Z": "zet",
        }
        for old, new in replacements.items():
            text = re.sub(rf"\b{re.escape(old)}\b", new, text)
        return text

    def _start_auto_report_feed(self) -> None:
        try:
            day_key, _day_msg = alice_self_learning_loop.daily_summary_digest()
            ts, _msg = alice_self_learning_loop.latest_report_digest()
            sig = alice_self_learning_loop.latest_report_signature()
            self._last_daily_summary_key = day_key or ""
            self._last_auto_report_ts = ts or ""
            self._last_auto_report_sig = sig or ""
        except Exception:
            pass
        self.after(60000, self._auto_report_tick)

    def _auto_report_tick(self) -> None:
        try:
            day_key, day_msg = alice_self_learning_loop.daily_summary_digest()
            if day_key and day_key != self._last_daily_summary_key and self.operator_mode.get():
                self._last_daily_summary_key = day_key
                self._append_assistant(f"Nowe podsumowanie dnia jest gotowe.\n{day_msg}")
            ts, msg = alice_self_learning_loop.latest_report_digest()
            sig = alice_self_learning_loop.latest_report_signature()
            if ts and ts != self._last_auto_report_ts and sig and sig != self._last_auto_report_sig:
                self._last_auto_report_ts = ts
                self._last_auto_report_sig = sig
                auto_msg = f"AUTO MELDUNEK:\n{msg}"
                self._append_assistant(auto_msg)
                if self.voice_enabled.get():
                    self._speak_async(f"Nowy raport samonauki. {msg}")
        except Exception:
            pass
        self.after(60000, self._auto_report_tick)

    def _write_chat_log(self, role: str, text: str) -> None:
        try:
            self._chat_log_dir.mkdir(parents=True, exist_ok=True)
            path = self._chat_log_dir / f"chat_{datetime.now().strftime('%Y%m%d')}.jsonl"
            row = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "session": self._chat_log_session,
                "role": role,
                "text": str(text or ""),
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            return
