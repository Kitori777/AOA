from __future__ import annotations

import json
import webbrowser
from datetime import datetime
from html import escape
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from AOA.config import DATA_DIR
from AOA.core.data_analytics_service import (
    ANALYTICS_WORKFLOWS,
    AnalyticsResult,
    run_analytics_workflow,
)
from AOA.core.report_composer_service import (
    REPORT_EXAMPLE_TEMPLATES,
    analysis_block,
    build_custom_report_html,
    build_custom_report_pdf,
    chart_block,
    default_report_template,
    file_block,
    kpi_block,
    ml_analytics_block,
    pipeline_block,
    prediction_plan_block,
    recommendation_block,
    render_report_pdf_preview_text,
    report_example_template,
    sto_analytics_block,
)
from AOA.core.services import load_and_prepare_visual_file

REPORT_BUILDER_GUIDE = [
    ("START", r"\title{Tytul} | \maketitle | \tableofcontents", "tytul, karta tytulowa i spis tresci"),
    ("STRUKTURA", r"\section{Nazwa} | \subsection{Nazwa}", "duze sekcje i mniejsze podrozdzialy"),
    ("TEKST", r"\textbf{tekst} | \emph{tekst} | \code{fit()}", "pogrubienie, kursywa i kod w linii"),
    ("LINK", r"\url{https://...}", "klikalny link w HTML"),
    ("WZORY", r"$x=y+z$ | \equation{RMSE = sqrt(mean(e^2))}", "wzor w linii albo osobny blok"),
    ("ODWOLANIA", r"\label{eq:sto} i \ref{eq:sto}", "oznaczenie miejsca i odwolanie w tekscie"),
    ("PODPIS", r"\caption{Opis}", "podpis pod ostatnim obrazem, tabela albo wykresem"),
    ("UKLAD", r"\pagebreak | \footnote{uwaga}", "nowa strona i przypis"),
    ("UWAGA", "::: {.callout-tip} tresc | > cytat", "ramka note/tip/warning/danger albo cytat"),
    ("LISTY", r"\begin{itemize} \item ... \end{itemize}", "lista punktowana w stylu LaTeX"),
    ("CHECKLISTA", "- [ ] zadanie / - [x] zrobione", "lista kontrolna jak w Markdown"),
    ("OBRAZ", r"\includegraphics{plik.png}", "PNG/JPG/SVG, np. wykres albo diagram SVG"),
    ("HTML", r"\includehtml{plik.html}", "interaktywny Visual/Diagrams/raport HTML w iframe"),
    ("KOD", r"\begin{verbatim} ... \end{verbatim}", "kod, logi albo surowy tekst"),
    ("MARKDOWN", "# / ## / ### oraz - punkt", "szybkie naglowki i listy bez komend"),
]

REPORT_BUILDER_SNIPPETS = {
    "Cel": "\\section{Cel raportu}\nOpisz decyzje, ktora ma wspierac raport.\n",
    "Podrozdzial": "\\subsection{Nowy podrozdzial}\nDopisz kontekst i obserwacje.\n",
    "Lista": "\\begin{itemize}\n\\item Pierwszy punkt.\n\\item Drugi punkt.\n\\end{itemize}\n",
    "Pogrubienie": "\\textbf{wazny fragment}",
    "TOC": "\\tableofcontents\n",
    "Wzor": "$STO = \\sum max(0, C_j - d_j)$",
    "Rownanie": "\\equation{STO = \\sum max(0, C_j - d_j)}\n",
    "Podpis": "\\caption{Podpis wykresu albo tabeli.}\n",
    "Callout": "::: {.callout-tip} Najwazniejszy wniosek: wpisz tutaj interpretacje.\n",
    "Cytat": "> Krotka uwaga, zalozenie albo komentarz do wyniku.\n",
    "Checklist": "- [ ] Sprawdz dane.\n- [x] Dodaj wykres.\n- [ ] Dopisz wnioski.\n",
    "Obraz": "\\includegraphics{sciezka/do/obrazu.png}\n",
    "HTML": "\\includehtml{sciezka/do/raportu.html}\n",
    "Kod": "\\begin{verbatim}\nWklej kod, log albo tekst.\n\\end{verbatim}\n",
    "Pagebreak": "\\pagebreak\n",
    "ML analiza": ml_analytics_block(),
    "STO analiza": sto_analytics_block(),
    "Plan predykcji": prediction_plan_block(),
    "Pipeline": pipeline_block(),
    "Ryzyka": (
        "\\section{Ryzyka i ograniczenia}\n"
        "\\begin{itemize}\n"
        "\\item Jakosc danych: braki, duplikaty, nietypowe wartosci.\n"
        "\\item Ryzyko modelu: przeuczenie, drift danych, zbyt mala probka.\n"
        "\\item Ryzyko operacyjne: brak danych w czasie rzeczywistym, opozniona reakcja.\n"
        "\\item Decyzja: co robimy, gdy model ma niska pewnosc.\n"
        "\\end{itemize}\n"
    ),
}


class AnalyticsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.assistant_sections = {}
        self.df_loaded = None
        self.current_result: AnalyticsResult | None = None
        self.workflow_var = ctk.StringVar(value="Index")
        self.metric_var = ctk.StringVar(value="")
        self.dimension_var = ctk.StringVar(value="")
        self.status_var = ctk.StringVar(value="Wczytaj dane albo uruchom Index.")
        self.last_saved_path = None
        self.report_title_var = ctk.StringVar(value="Moj raport AOA")
        self.report_builder_window = None
        self.full_report_editor: ctk.CTkTextbox | None = None
        self.full_report_preview: ctk.CTkTextbox | None = None
        self.report_asset_var = ctk.StringVar(value="Brak plikow")
        self.report_asset_paths: dict[str, Path] = {}
        self.report_asset_menu = None
        first_example = next(iter(REPORT_EXAMPLE_TEMPLATES), "Szybki raport decyzyjny")
        self.report_example_var = ctk.StringVar(value=first_example)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_controls()
        self._build_body()
        self.run_workflow()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=18, fg_color="#0f1d2b")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Report Studio - raporty, KPI, diagnostyka i rekomendacje",
            font=("Arial", 25, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text=(
                "Centrum raportow: gotowe szablony, jakosc danych, dashboardy, KPI, "
                "diagnostyka metryk, ML/STO, market sizing, PDF preview i plan notebooka."
            ),
            text_color="#cbd5e1",
            wraplength=1180,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
        ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            fg_color="#123456",
            corner_radius=12,
            text_color="#dbeafe",
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=18, pady=16)

    def _build_controls(self) -> None:
        controls = ctk.CTkFrame(self, corner_radius=18, fg_color="#111827")
        self.assistant_sections["controls"] = controls
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        controls.grid_columnconfigure(5, weight=1)
        ctk.CTkButton(controls, text="Wczytaj dane", command=self.load_file, width=130).grid(
            row=0, column=0, padx=(12, 6), pady=12
        )
        self.workflow_menu = ctk.CTkOptionMenu(
            controls,
            values=ANALYTICS_WORKFLOWS,
            variable=self.workflow_var,
            width=210,
        )
        self.workflow_menu.grid(row=0, column=1, padx=6, pady=12)
        self.metric_menu = ctk.CTkOptionMenu(
            controls, values=[""], variable=self.metric_var, width=170
        )
        self.metric_menu.grid(row=0, column=2, padx=6, pady=12)
        self.dimension_menu = ctk.CTkOptionMenu(
            controls, values=[""], variable=self.dimension_var, width=170
        )
        self.dimension_menu.grid(row=0, column=3, padx=6, pady=12)
        ctk.CTkButton(controls, text="Uruchom analize", command=self.run_workflow, width=150).grid(
            row=0, column=4, padx=6, pady=12
        )
        ctk.CTkButton(controls, text="Zapisz raport", command=self.save_report, width=130).grid(
            row=0, column=5, padx=6, pady=12, sticky="e"
        )
        ctk.CTkButton(
            controls, text="Otworz HTML", command=self.export_html_report, width=130
        ).grid(row=1, column=0, padx=(12, 6), pady=(0, 10))
        ctk.CTkButton(
            controls, text="Wykonaj wszystko", command=self.run_all_workflows, width=150
        ).grid(row=1, column=1, padx=6, pady=(0, 10))
        ctk.CTkButton(
            controls, text="Notebook .ipynb", command=self.export_notebook, width=140
        ).grid(row=1, column=2, padx=6, pady=(0, 10))
        ctk.CTkButton(controls, text="CSV akcji", command=self.export_actions_csv, width=120).grid(
            row=1, column=3, padx=6, pady=(0, 10)
        )
        ctk.CTkButton(
            controls, text="Report Builder", command=self.focus_report_builder, width=140
        ).grid(row=1, column=4, padx=6, pady=(0, 10))
        ctk.CTkLabel(
            controls,
            text=(
                "Tu testujesz raporty na gotowych formatach, uruchamiasz analize, generujesz HTML, "
                "pelny pakiet workflow, notebook i liste akcji do dalszej pracy."
            ),
            text_color="#94a3b8",
        ).grid(row=2, column=0, columnspan=6, sticky="w", padx=12, pady=(0, 12))

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, corner_radius=18, fg_color="#0b1220")
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)
        self.title_label = ctk.CTkLabel(body, text="", font=("Arial", 22, "bold"))
        self.title_label.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))
        self.output_box = ctk.CTkTextbox(body, wrap="word", font=("Consolas", 13))
        self.output_box.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))

        composer = ctk.CTkFrame(body, corner_radius=16, fg_color="#111827")
        self.assistant_sections["report_builder"] = composer
        composer.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 16), pady=16)
        composer.grid_columnconfigure(0, weight=1)
        composer.grid_rowconfigure(7, weight=1)
        ctk.CTkLabel(
            composer,
            text="Report Builder - pelny edytor",
            font=("Arial", 20, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 4))
        ctk.CTkEntry(
            composer,
            textvariable=self.report_title_var,
            placeholder_text="Tytul raportu",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        ctk.CTkButton(
            composer,
            text="Otworz pelny edytor raportu",
            command=self.open_report_builder_window,
            height=42,
        ).grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        ctk.CTkLabel(
            composer,
            text=(
                "Pisanie raportu jest teraz w osobnym pelnym oknie: edytor po lewej, "
                "podglad strony po prawej, biblioteka plikow i guide obok."
            ),
            text_color="#bfdbfe",
            justify="left",
            wraplength=620,
        ).grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))
        example_frame = ctk.CTkFrame(composer, fg_color="#0b1220", corner_radius=10)
        example_frame.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 10))
        example_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            example_frame,
            text="Gotowe formaty raportow do testowania",
            text_color="#bfdbfe",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))
        ctk.CTkOptionMenu(
            example_frame,
            values=list(REPORT_EXAMPLE_TEMPLATES),
            variable=self.report_example_var,
            width=260,
        ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkButton(
            example_frame,
            text="Wczytaj przyklad",
            command=self.apply_report_example,
            width=140,
        ).grid(row=1, column=1, sticky="e", padx=(6, 10), pady=(0, 10))
        tools = ctk.CTkFrame(composer, fg_color="transparent")
        tools.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 8))
        for idx in range(4):
            tools.grid_columnconfigure(idx, weight=1)
        ctk.CTkButton(tools, text="Dodaj wynik", command=self.add_current_result_to_report).grid(
            row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 6)
        )
        ctk.CTkButton(tools, text="Dodaj plik", command=self.add_file_to_report).grid(
            row=0, column=1, sticky="ew", padx=5, pady=(0, 6)
        )
        ctk.CTkButton(tools, text="Sekcja", command=self.add_report_section).grid(
            row=0, column=2, sticky="ew", padx=5, pady=(0, 6)
        )
        ctk.CTkButton(tools, text="Wyczyść", command=self.reset_report_builder).grid(
            row=0, column=3, sticky="ew", padx=(5, 0), pady=(0, 6)
        )
        ctk.CTkButton(tools, text="Eksport HTML", command=self.export_custom_report_html).grid(
            row=1, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(tools, text="Eksport .tex", command=self.export_custom_report_tex).grid(
            row=1, column=1, sticky="ew", padx=5
        )
        ctk.CTkButton(tools, text="Eksport .md", command=self.export_custom_report_md).grid(
            row=1, column=2, sticky="ew", padx=5
        )
        ctk.CTkButton(tools, text="Podgląd HTML", command=self.preview_custom_report).grid(
            row=1, column=3, sticky="ew", padx=(5, 0)
        )
        ctk.CTkButton(tools, text="KPI", command=self.add_kpi_block).grid(
            row=2, column=0, sticky="ew", padx=(0, 5), pady=(6, 0)
        )
        ctk.CTkButton(tools, text="Wykres", command=self.add_chart_block).grid(
            row=2, column=1, sticky="ew", padx=5, pady=(6, 0)
        )
        ctk.CTkButton(tools, text="Rekomendacje", command=self.add_recommendations_block).grid(
            row=2, column=2, sticky="ew", padx=5, pady=(6, 0)
        )
        ctk.CTkButton(tools, text="Odśwież podgląd", command=self.update_report_preview).grid(
            row=2, column=3, sticky="ew", padx=(5, 0), pady=(6, 0)
        )
        ctk.CTkButton(tools, text="ML analiza", command=self.add_ml_analytics_block).grid(
            row=3, column=0, sticky="ew", padx=(0, 5), pady=(6, 0)
        )
        ctk.CTkButton(tools, text="STO analiza", command=self.add_sto_analytics_block).grid(
            row=3, column=1, sticky="ew", padx=5, pady=(6, 0)
        )
        ctk.CTkButton(tools, text="Plan predykcji", command=self.add_prediction_plan_block).grid(
            row=3, column=2, sticky="ew", padx=5, pady=(6, 0)
        )
        ctk.CTkButton(
            tools, text="Ryzyka", command=lambda: self.insert_report_snippet("Ryzyka")
        ).grid(row=3, column=3, sticky="ew", padx=(5, 0), pady=(6, 0))
        ctk.CTkButton(tools, text="Pipeline", command=self.add_pipeline_block).grid(
            row=4, column=0, sticky="ew", padx=(0, 5), pady=(6, 0)
        )
        ctk.CTkButton(tools, text="Plik z projektu", command=self.add_selected_asset_to_report).grid(
            row=4, column=1, sticky="ew", padx=5, pady=(6, 0)
        )
        ctk.CTkButton(tools, text="PDF preview", command=self.preview_custom_report_pdf).grid(
            row=4, column=2, sticky="ew", padx=5, pady=(6, 0)
        )
        ctk.CTkButton(tools, text="Eksport PDF", command=self.export_custom_report_pdf).grid(
            row=4, column=3, sticky="ew", padx=(5, 0), pady=(6, 0)
        )
        ctk.CTkLabel(
            composer,
            text="Źródło raportu po lewej, podgląd po prawej",
            text_color="#bfdbfe",
        ).grid(row=6, column=0, sticky="w", padx=14, pady=(0, 6))
        editor_grid = ctk.CTkFrame(composer, fg_color="transparent")
        editor_grid.grid(row=7, column=0, sticky="nsew", padx=14, pady=(0, 10))
        editor_grid.grid_remove()
        editor_grid.grid_columnconfigure(0, weight=1)
        editor_grid.grid_columnconfigure(1, weight=1)
        editor_grid.grid_rowconfigure(0, weight=1)
        self.report_editor = ctk.CTkTextbox(editor_grid, wrap="word", font=("Consolas", 12))
        self.report_editor.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.report_editor.insert("end", default_report_template(self.report_title_var.get()))
        self.report_editor.bind("<KeyRelease>", lambda _event: self.update_report_preview())
        self.report_preview = ctk.CTkTextbox(editor_grid, wrap="word", font=("Segoe UI", 12))
        self.report_preview.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.report_preview.configure(state="disabled")
        ctk.CTkLabel(
            composer,
            text=r"Komendy: \section{}, \subsection{}, \item, \textbf{}, \includegraphics{}, \includehtml{}",
            text_color="#94a3b8",
            wraplength=560,
            justify="left",
        ).grid(row=8, column=0, sticky="ew", padx=14, pady=(0, 8))
        self.update_report_preview()

    def load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Wybierz plik z danymi",
            initialdir=str(DATA_DIR),
            filetypes=[
                ("Pliki tabelaryczne", "*.csv *.txt *.tsv"),
                ("CSV", "*.csv"),
                ("TXT", "*.txt"),
                ("TSV", "*.tsv"),
            ],
        )
        if not path:
            return
        try:
            result = load_and_prepare_visual_file(path)
            self.df_loaded = result["df"]
            columns = result["columns"] or [""]
            numeric = self.df_loaded.select_dtypes(include="number").columns.tolist() or columns
            self.metric_menu.configure(values=numeric)
            self.dimension_menu.configure(values=columns)
            self.metric_var.set(numeric[0] if numeric else "")
            self.dimension_var.set(columns[0] if columns else "")
            self.status_var.set(f"Wczytano: {len(self.df_loaded)} wierszy, {len(columns)} kolumn.")
            self.run_workflow()
        except Exception as exc:
            messagebox.showerror("Blad", str(exc))

    def run_workflow(self) -> None:
        result = run_analytics_workflow(
            self.df_loaded,
            self.workflow_var.get(),
            self.metric_var.get(),
            self.dimension_var.get(),
        )
        self.current_result = result
        self.title_label.configure(
            text=f"{result.title} | rekomendowany wykres: {result.recommended_chart}"
        )
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", result.body)
        self.output_box.configure(state="disabled")

    def _ensure_current_result(self) -> AnalyticsResult:
        if self.current_result is None:
            self.run_workflow()
        if self.current_result is None:
            raise RuntimeError("Analytics workflow did not return a result.")
        return self.current_result

    def save_report(self) -> None:
        result = self._ensure_current_result()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / f"analytics_report_{stamp}.md"
        path.write_text(f"# {result.title}\n\n{result.body}\n", encoding="utf-8")
        self.last_saved_path = path
        self.status_var.set(f"Zapisano raport: {path.name}")
        messagebox.showinfo("Gotowe", f"Zapisano raport:\n{path}")

    def focus_report_builder(self) -> None:
        self.open_report_builder_window()

    def open_report_builder_window(self) -> None:
        if self.report_builder_window is not None and self.report_builder_window.winfo_exists():
            self.report_builder_window.lift()
            self.report_builder_window.focus_force()
            if self.full_report_editor is not None:
                self.full_report_editor.focus_set()
            return

        window = ctk.CTkToplevel(self)
        self.report_builder_window = window
        window.title("AOA Report Builder - pelne okno")
        window.geometry("1500x900")
        try:
            window.state("zoomed")
        except Exception:
            pass
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(2, weight=1)
        window.protocol("WM_DELETE_WINDOW", self.close_report_builder_window)

        header = ctk.CTkFrame(window, corner_radius=16, fg_color="#0f1d2b")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            header,
            text="Report Builder - pelne okno jak Overleaf/LaTeX",
            font=("Arial", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))
        ctk.CTkEntry(header, textvariable=self.report_title_var, width=360).grid(
            row=0, column=1, sticky="ew", padx=14, pady=12
        )
        ctk.CTkButton(
            header, text="Zapisz do panelu i zamknij", command=self.close_report_builder_window
        ).grid(row=0, column=2, padx=14, pady=12)
        ctk.CTkLabel(
            header,
            text="Po lewej piszesz raport, w srodku widzisz podglad, po prawej masz przewodnik wszystkich komend.",
            text_color="#cbd5e1",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 12))

        toolbar = ctk.CTkFrame(window, corner_radius=16, fg_color="#111827")
        toolbar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        for idx in range(10):
            toolbar.grid_columnconfigure(idx, weight=1)
        actions = [
            ("Dodaj wynik", self.add_current_result_to_report),
            ("Dodaj plik", self.add_file_to_report),
            ("Sekcja", self.add_report_section),
            ("KPI", self.add_kpi_block),
            ("Wykres", self.add_chart_block),
            ("Rekomendacje", self.add_recommendations_block),
            ("ML", self.add_ml_analytics_block),
            ("STO", self.add_sto_analytics_block),
            ("Plan pred.", self.add_prediction_plan_block),
            ("Pipeline", self.add_pipeline_block),
            ("Ryzyka", lambda: self.insert_report_snippet("Ryzyka")),
            ("Pliki", self.refresh_report_asset_menu),
            ("Podglad HTML", self.preview_custom_report),
            ("Podglad PDF", self.preview_custom_report_pdf),
            ("Eksport PDF", self.export_custom_report_pdf),
            ("Eksport HTML", self.export_custom_report_html),
        ]
        for idx, (label, command) in enumerate(actions):
            ctk.CTkButton(toolbar, text=label, command=command).grid(
                row=idx // 10, column=idx % 10, sticky="ew", padx=5, pady=8
            )
        ctk.CTkLabel(
            toolbar,
            text="Przykladowy format:",
            text_color="#bfdbfe",
            font=("Arial", 12, "bold"),
        ).grid(row=2, column=0, sticky="e", padx=5, pady=(0, 8))
        ctk.CTkOptionMenu(
            toolbar,
            values=list(REPORT_EXAMPLE_TEMPLATES),
            variable=self.report_example_var,
        ).grid(row=2, column=1, columnspan=3, sticky="ew", padx=5, pady=(0, 8))
        ctk.CTkButton(
            toolbar,
            text="Wczytaj przyklad raportu",
            command=self.apply_report_example,
        ).grid(row=2, column=4, columnspan=2, sticky="ew", padx=5, pady=(0, 8))
        ctk.CTkButton(
            toolbar,
            text="Wroc do pustego szablonu",
            command=self.reset_report_builder,
        ).grid(row=2, column=6, columnspan=2, sticky="ew", padx=5, pady=(0, 8))

        workspace = ctk.CTkFrame(window, corner_radius=16, fg_color="#0b1220")
        workspace.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        workspace.grid_columnconfigure(0, weight=5)
        workspace.grid_columnconfigure(1, weight=4)
        workspace.grid_columnconfigure(2, weight=3)
        workspace.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(workspace, text="Źrodlo raportu", font=("Arial", 16, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )
        ctk.CTkLabel(workspace, text="Podglad strony A4 / PDF", font=("Arial", 16, "bold")).grid(
            row=0, column=1, sticky="w", padx=12, pady=(12, 6)
        )
        ctk.CTkLabel(workspace, text="Guide komend", font=("Arial", 16, "bold")).grid(
            row=0, column=2, sticky="w", padx=12, pady=(12, 6)
        )

        self.full_report_editor = ctk.CTkTextbox(workspace, wrap="word", font=("Consolas", 14))
        self.full_report_editor.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        self.full_report_editor.insert("end", self.report_editor.get("1.0", "end").strip())
        self.full_report_editor.bind("<KeyRelease>", lambda _event: self.update_report_preview())

        self.full_report_preview = ctk.CTkTextbox(
            workspace,
            wrap="word",
            font=("Times New Roman", 14),
            fg_color="#f8fafc",
            text_color="#0f172a",
            border_width=10,
            border_color="#d1d5db",
        )
        self.full_report_preview.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 12))
        self.full_report_preview.configure(state="disabled")

        guide_panel = ctk.CTkFrame(workspace, fg_color="#111827", corner_radius=12)
        guide_panel.grid(row=1, column=2, sticky="nsew", padx=(6, 12), pady=(0, 12))
        guide_panel.grid_columnconfigure(0, weight=1)
        guide_panel.grid_rowconfigure(2, weight=1)
        asset_panel = ctk.CTkFrame(guide_panel, fg_color="#0b1220", corner_radius=10)
        asset_panel.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        asset_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            asset_panel,
            text="Pliki do raportu",
            font=("Arial", 13, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))
        self.report_asset_menu = ctk.CTkOptionMenu(
            asset_panel,
            values=["Brak plikow"],
            variable=self.report_asset_var,
            width=260,
        )
        self.report_asset_menu.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        ctk.CTkButton(
            asset_panel,
            text="Wstaw",
            command=self.add_selected_asset_to_report,
            width=82,
        ).grid(row=1, column=1, sticky="e", padx=(4, 10), pady=(0, 8))
        ctk.CTkButton(
            asset_panel,
            text="Odswiez biblioteke: Visual, Diagrams, Analytics, Reports",
            command=self.refresh_report_asset_menu,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        snippets = ctk.CTkFrame(guide_panel, fg_color="transparent")
        snippets.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 10))
        for idx in range(2):
            snippets.grid_columnconfigure(idx, weight=1)
        for idx, label in enumerate(REPORT_BUILDER_SNIPPETS):
            ctk.CTkButton(
                snippets,
                text=label,
                command=lambda key=label: self.insert_report_snippet(key),
                width=120,
            ).grid(row=idx // 2, column=idx % 2, sticky="ew", padx=4, pady=4)

        guide = ctk.CTkTextbox(guide_panel, wrap="word", font=("Segoe UI", 12))
        guide.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        guide.insert("end", self._report_builder_guide_text())
        guide.configure(state="disabled")

        self.update_report_preview()
        self.refresh_report_asset_menu(show_status=False)
        self.full_report_editor.focus_set()

    def close_report_builder_window(self) -> None:
        if self.full_report_editor is not None:
            source = self.full_report_editor.get("1.0", "end").strip()
            self.report_editor.delete("1.0", "end")
            self.report_editor.insert("end", source)
            self.update_report_preview()
        if self.report_builder_window is not None and self.report_builder_window.winfo_exists():
            self.report_builder_window.destroy()
        self.report_builder_window = None
        self.full_report_editor = None
        self.full_report_preview = None
        self.status_var.set("Report Builder zapisany do panelu.")

    def _report_builder_guide_text(self) -> str:
        lines = [
            "JAK PISAC RAPORT",
            "================",
            "Pisz zwykly tekst i dodawaj komendy podobne do LaTeX. Podglad odswieza sie podczas pisania.",
            "",
            "KOMENDY",
            "-------",
        ]
        for group, command, description in REPORT_BUILDER_GUIDE:
            lines.append(f"[{group}] {command}\n  {description}\n")
        lines.extend(
            [
                "PLIKI Z APLIKACJI",
                "----------------",
                "Przycisk Pliki odswieza biblioteke z katalogow data/diagrams, data/visual, data/analytics i data/reports.",
                "Wstaw obiekt, gdy chcesz dolaczyc diagram, wykres HTML, SVG, PNG, CSV albo fragment tekstu.",
                "Obraz trafi jako \\includegraphics{}, a interaktywny HTML jako \\includehtml{}.",
                "",
                "PRZYKLADOWY PRZEPLYW",
                "-------------------",
                "1. Ustaw tytul raportu.",
                "2. Dodaj \\section{Cel raportu}.",
                "3. Kliknij Pipeline, zeby opisac cala droge dane -> decyzja.",
                "4. Kliknij Dodaj wynik, KPI, ML, STO albo Plan predykcji.",
                "5. Wstaw plik z Visual/Diagrams przez biblioteke plikow.",
                "6. Uzyj podgladu PDF-like, potem Podglad HTML lub Podglad PDF.",
                "7. Na koncu dodaj \\section{Wnioski} i liste \\item.",
                "",
                "PRZYDATNE WSTAWKI",
                "----------------",
                "- \\tableofcontents najlepiej wstawic po tytule.",
                "- \\caption{} dawaj po \\includegraphics{} albo tabeli.",
                "- \\pagebreak pomaga ulozyc dlugie raporty PDF.",
                "- checklisty - [ ] i - [x] sa dobre do planu pracy.",
                "",
                "EKSPORT",
                "-------",
                "Eksport HTML zachowuje osadzone HTML jako iframe.",
                "Podglad PDF tworzy plik roboczy i od razu go otwiera.",
                "Eksport PDF daje czytelny raport tekstowy do oddania lub archiwizacji.",
                "Eksport .tex/.md zapisuje zrodlo raportu do dalszej edycji.",
            ]
        )
        return "\n".join(lines)

    def _active_report_editor(self):
        if (
            self.full_report_editor is not None
            and self.report_builder_window is not None
            and self.report_builder_window.winfo_exists()
        ):
            return self.full_report_editor
        return self.report_editor

    def insert_report_snippet(self, key: str) -> None:
        snippet = REPORT_BUILDER_SNIPPETS.get(key)
        if not snippet:
            return
        self._append_to_builder("\n" + snippet + "\n")

    def add_current_result_to_report(self) -> None:
        result = self._ensure_current_result()
        self._append_to_builder(
            "\n" + analysis_block(result.title, result.body, result.recommended_chart) + "\n"
        )
        self.status_var.set("Dodano aktualny wynik do wlasnego raportu.")

    def add_report_section(self) -> None:
        self._append_to_builder("\n\\section{Nowa sekcja}\nWpisz tresc sekcji.\n")
        self.status_var.set("Dodano nowa sekcje raportu.")

    def add_kpi_block(self) -> None:
        self._append_to_builder(
            "\n"
            + kpi_block(self.metric_var.get() or "metryka", "wpisz wartosc", "wpisz interpretacje")
            + "\n"
        )
        self.status_var.set("Dodano blok KPI.")

    def add_chart_block(self) -> None:
        chart = (
            self.current_result.recommended_chart
            if self.current_result is not None
            else "Dashboard"
        )
        self._append_to_builder("\n" + chart_block("Wizualizacja", chart) + "\n")
        self.status_var.set("Dodano blok wykresu.")

    def add_recommendations_block(self) -> None:
        self._append_to_builder("\n" + recommendation_block() + "\n")
        self.status_var.set("Dodano blok rekomendacji.")

    def add_ml_analytics_block(self) -> None:
        self._append_to_builder("\n" + ml_analytics_block() + "\n")
        self.status_var.set("Dodano blok analityki ML.")

    def add_sto_analytics_block(self) -> None:
        self._append_to_builder("\n" + sto_analytics_block() + "\n")
        self.status_var.set("Dodano blok analityki STO.")

    def add_prediction_plan_block(self) -> None:
        self._append_to_builder("\n" + prediction_plan_block() + "\n")
        self.status_var.set("Dodano plan predykcji i wdrozenia.")

    def add_pipeline_block(self) -> None:
        self._append_to_builder("\n" + pipeline_block() + "\n")
        self.status_var.set("Dodano pipeline decyzyjny.")

    def _discover_report_assets(self) -> dict[str, Path]:
        roots = [
            DATA_DIR / "diagrams",
            DATA_DIR / "visual",
            DATA_DIR / "analytics",
            DATA_DIR / "reports",
            DATA_DIR,
        ]
        supported = {
            ".csv",
            ".tsv",
            ".txt",
            ".md",
            ".tex",
            ".json",
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".html",
            ".htm",
            ".pdf",
        }
        assets: list[Path] = []
        seen: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in supported:
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                assets.append(path)
        assets.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True)
        labels: dict[str, Path] = {}
        for path in assets[:80]:
            try:
                rel = path.relative_to(DATA_DIR)
            except ValueError:
                rel = path
            label = str(rel).replace("\\", "/")
            labels[label] = path
        return labels

    def refresh_report_asset_menu(self, show_status: bool = True) -> None:
        self.report_asset_paths = self._discover_report_assets()
        values = list(self.report_asset_paths) or ["Brak plikow"]
        self.report_asset_var.set(values[0])
        if self.report_asset_menu is not None:
            try:
                self.report_asset_menu.configure(values=values)
            except Exception:
                pass
        if show_status:
            self.status_var.set(f"Odswiezono biblioteke plikow: {len(self.report_asset_paths)}.")

    def add_selected_asset_to_report(self) -> None:
        if not self.report_asset_paths:
            self.refresh_report_asset_menu(show_status=False)
        label = self.report_asset_var.get()
        path = self.report_asset_paths.get(label)
        if path is None:
            self.add_file_to_report()
            return
        self._append_to_builder("\n" + file_block(path) + "\n")
        self.status_var.set(f"Wstawiono plik z projektu: {label}")

    def add_file_to_report(self) -> None:
        path = filedialog.askopenfilename(
            title="Dodaj plik do raportu",
            initialdir=str(DATA_DIR),
            filetypes=[
                (
                    "Wszystkie wspierane",
                    "*.csv *.tsv *.txt *.md *.tex *.json *.png *.jpg *.jpeg *.svg *.html",
                ),
                ("Tabele", "*.csv *.tsv"),
                ("Tekst", "*.txt *.md *.tex *.json"),
                ("Wizualizacje", "*.png *.jpg *.jpeg *.svg"),
                ("HTML", "*.html *.htm"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not path:
            return
        self._append_to_builder("\n" + file_block(Path(path)) + "\n")
        self.status_var.set(f"Dodano plik do raportu: {Path(path).name}")

    def apply_report_example(self) -> None:
        name = self.report_example_var.get()
        if not name:
            return
        editor = self._active_report_editor()
        editor.delete("1.0", "end")
        editor.insert("end", report_example_template(name, self.report_title_var.get()))
        self.update_report_preview()
        self.status_var.set(f"Wczytano przykladowy format raportu: {name}.")

    def reset_report_builder(self) -> None:
        if not messagebox.askyesno(
            "Report Builder", "Wyczyscic wlasny raport i wstawic szablon od nowa?"
        ):
            return
        editor = self._active_report_editor()
        editor.delete("1.0", "end")
        editor.insert("end", default_report_template(self.report_title_var.get()))
        self.update_report_preview()
        self.status_var.set("Report Builder wyczyszczony.")

    def preview_custom_report(self) -> None:
        self.export_custom_report_html(open_after=True)

    def preview_custom_report_pdf(self) -> Path:
        source = self._report_source()
        output_dir = DATA_DIR / "reports" / "_preview"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "report_builder_preview.pdf"
        build_custom_report_pdf(source, path, title=self.report_title_var.get())
        self.last_saved_path = path
        self.status_var.set(f"Podglad PDF gotowy: {path.name}")
        try:
            webbrowser.open_new_tab(path.resolve().as_uri())
        except Exception as exc:
            messagebox.showerror("Blad podgladu PDF", str(exc))
        return path

    def export_custom_report_html(self, open_after: bool = True) -> Path | None:
        source = self._report_source()
        output_dir = DATA_DIR / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"custom_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        path.write_text(
            build_custom_report_html(source, title=self.report_title_var.get()),
            encoding="utf-8",
        )
        self.last_saved_path = path
        self.status_var.set(f"Wlasny raport HTML gotowy: {path.name}")
        if open_after:
            webbrowser.open_new_tab(path.resolve().as_uri())
        return path

    def export_custom_report_pdf(self) -> Path:
        source = self._report_source()
        output_dir = DATA_DIR / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"custom_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        build_custom_report_pdf(source, path, title=self.report_title_var.get())
        self.last_saved_path = path
        self.status_var.set(f"Zapisano raport PDF: {path.name}")
        messagebox.showinfo("Gotowe", f"Zapisano raport PDF:\n{path}")
        try:
            webbrowser.open_new_tab(path.resolve().as_uri())
        except Exception:
            pass
        return path

    def export_custom_report_tex(self) -> Path:
        return self._export_custom_text("tex")

    def export_custom_report_md(self) -> Path:
        return self._export_custom_text("md")

    def _export_custom_text(self, ext: str) -> Path:
        output_dir = DATA_DIR / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"custom_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        path.write_text(self._report_source(), encoding="utf-8")
        self.last_saved_path = path
        self.status_var.set(f"Zapisano raport .{ext}: {path.name}")
        messagebox.showinfo("Gotowe", f"Zapisano raport:\n{path}")
        return path

    def _append_to_builder(self, text: str) -> None:
        editor = self._active_report_editor()
        editor.insert("end", text)
        editor.see("end")
        self.update_report_preview()

    def update_report_preview(self) -> None:
        if not hasattr(self, "report_preview"):
            return
        preview = render_report_pdf_preview_text(
            self._report_source(),
            title=self.report_title_var.get(),
        )
        for widget in (
            getattr(self, "report_preview", None),
            getattr(self, "full_report_preview", None),
        ):
            if widget is None:
                continue
            try:
                widget.configure(state="normal")
                widget.delete("1.0", "end")
                widget.insert("end", preview)
                widget.configure(state="disabled")
            except Exception:
                continue

    def _report_source(self) -> str:
        source = self._active_report_editor().get("1.0", "end").strip()
        if "\\title{" not in source and not source.startswith("#"):
            source = f"\\title{{{self.report_title_var.get()}}}\n\n{source}"
        return source

    def export_html_report(self) -> None:
        result = self._ensure_current_result()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = DATA_DIR / "analytics"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"analytics_{stamp}.html"
        html = self._build_html_document([(result.title, result.body, result.recommended_chart)])
        path.write_text(html, encoding="utf-8")
        self.last_saved_path = path
        self.status_var.set(f"HTML gotowy: {path.name}")
        webbrowser.open_new_tab(path.resolve().as_uri())

    def run_all_workflows(self) -> None:
        workflows = [workflow for workflow in ANALYTICS_WORKFLOWS if workflow != "Index"]
        results = [
            run_analytics_workflow(
                self.df_loaded,
                workflow,
                self.metric_var.get(),
                self.dimension_var.get(),
            )
            for workflow in workflows
        ]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = DATA_DIR / "analytics"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"analytics_all_workflows_{stamp}.html"
        path.write_text(
            self._build_html_document(
                [(result.title, result.body, result.recommended_chart) for result in results]
            ),
            encoding="utf-8",
        )
        self.last_saved_path = path
        self.status_var.set(f"Wykonano wszystko: {len(results)} workflow.")
        self.title_label.configure(text="Pelny pakiet Report Studio | HTML zapisany i otwarty")
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert(
            "end",
            "\n\n".join(
                f"## {result.title}\nRekomendowany wykres: {result.recommended_chart}\n\n{result.body}"
                for result in results
            ),
        )
        self.output_box.configure(state="disabled")
        webbrowser.open_new_tab(path.resolve().as_uri())

    def export_notebook(self) -> None:
        result = self._ensure_current_result()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = DATA_DIR / "analytics"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"analytics_notebook_{stamp}.ipynb"
        notebook = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [f"# {result.title}\n", "\n", result.body],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "import pandas as pd\n",
                        "# Wczytaj tutaj swoje dane i kontynuuj analize z aplikacji AOA.\n",
                        f"metric = {self.metric_var.get()!r}\n",
                        f"dimension = {self.dimension_var.get()!r}\n",
                    ],
                },
            ],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "pygments_lexer": "ipython3"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
        self.last_saved_path = path
        self.status_var.set(f"Notebook gotowy: {path.name}")
        messagebox.showinfo("Gotowe", f"Zapisano notebook:\n{path}")

    def export_actions_csv(self) -> None:
        result = self._ensure_current_result()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = DATA_DIR / "analytics"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"analytics_actions_{stamp}.csv"
        lines = [
            "workflow,recommended_chart,action",
            f'"{result.title}","{result.recommended_chart}","Uruchom rekomendowany wykres w Visual"',
            f'"{result.title}","{result.recommended_chart}","Sprawdz metryke {self.metric_var.get()} po wymiarze {self.dimension_var.get()}"',
            f'"{result.title}","{result.recommended_chart}","Zapisz raport HTML i dolacz do wynikow"',
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.last_saved_path = path
        self.status_var.set(f"CSV akcji gotowy: {path.name}")
        messagebox.showinfo("Gotowe", f"Zapisano CSV akcji:\n{path}")

    def _build_html_document(self, sections: list[tuple[str, str, str]]) -> str:
        cards = []
        for title, body, chart in sections:
            body_html = "<br>".join(escape(body).splitlines())
            cards.append(
                "<section class='card'>"
                f"<div class='tag'>Rekomendowany wykres: {escape(chart)}</div>"
                f"<h2>{escape(title)}</h2>"
                f"<p>{body_html}</p>"
                "</section>"
            )
        return (
            "<!doctype html><html lang='pl'><head><meta charset='utf-8'>"
            "<title>AOA Analytics Report</title>"
            "<style>"
            "body{margin:0;background:#eef4fb;color:#0f172a;font-family:Segoe UI,Arial,sans-serif;}"
            "header{background:#0f2a44;color:white;padding:28px 36px;}"
            "main{padding:24px 36px;display:grid;gap:18px;}"
            ".card{background:white;border:2px solid #cbd5e1;border-radius:10px;padding:20px;box-shadow:0 8px 24px #0f172a14;}"
            ".tag{display:inline-block;background:#dbeafe;color:#123f78;padding:7px 10px;border-radius:999px;font-weight:700;}"
            "h1,h2{margin:8px 0 12px;}p{line-height:1.55;white-space:normal;}"
            "</style></head><body><header><h1>AOA Analytics Report</h1>"
            f"<p>Metryka: {escape(self.metric_var.get())} | Wymiar: {escape(self.dimension_var.get())}</p>"
            "</header><main>" + "".join(cards) + "</main></body></html>"
        )

    def focus_section(self, section: str) -> None:
        frame = self.assistant_sections.get(section)
        if frame is None:
            return
        try:
            frame.configure(border_width=2, border_color="#1f8fff")
            self.after(1400, lambda: frame.configure(border_width=0))
        except Exception:
            return
