import sqlite3
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd

from AOA.config import DATA_DIR
from AOA.core.result_viewer_service import (
    build_dataset_profile,
    build_missing_report,
    build_viewer_result,
)
from AOA.core.services import load_and_prepare_visual_file


class ResultsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.assistant_sections = {}
        self.df_loaded = None
        self.visible_df = None
        self.filter_var = ctk.StringVar(value="")
        self.sort_var = ctk.StringVar(value="")
        self.profile_var = ctk.StringVar(value="")
        self.metric_var = ctk.StringVar(value="")
        self.top_mode_var = ctk.StringVar(value="Wszystkie")
        self.limit_var = ctk.StringVar(value="Wszystkie")
        self.custom_limit_var = ctk.StringVar(value="")
        self.desc_var = ctk.BooleanVar(value=False)
        self.status_var = ctk.StringVar(value="Wczytaj plik, aby rozpocząć analizę.")
        self.summary_labels: dict[str, ctk.CTkLabel] = {}
        self.summary_cards: dict[str, ctk.CTkFrame] = {}
        self.tree_columns: list[str] = []
        self.column_vars: dict[str, ctk.BooleanVar] = {}
        self.column_selector_frame = None
        self.view_mode_var = ctk.StringVar(value="Tabela")
        self.table_shell = None
        self.sql_shell = None
        self.sql_query_box = None
        self.sql_tree = None
        self.sql_table_status = None
        self.sql_visible_df = None
        self.sql_history: list[str] = []
        self.sql_history_index: int = -1
        self.sql_hint_var = ctk.StringVar(value="")
        self.header_frame = None
        self.toolbar_frame = None
        self.loader_frame = None
        self.summary_frame = None
        self.body_frame = None
        self.table_card = None
        self.report_frame = None
        self.header_subtitle = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._configure_tree_style()
        self._build_header()
        self._build_toolbar()
        self._build_summary_cards()
        self._build_body()
        self._set_view_mode()
        self._set_text("Wczytaj plik, aby zobaczyć dane.")
        self._set_report("Tu pojawi się podsumowanie pliku, profil kolumny i wskazówki do analizy.")
        self._update_summary(None)

    def _configure_tree_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Results.Treeview",
            background="#0f172a",
            foreground="#e5eef9",
            fieldbackground="#0f172a",
            rowheight=30,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Results.Treeview.Heading",
            background="#17263a",
            foreground="#f8fafc",
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Results.Treeview",
            background=[("selected", "#2563eb")],
            foreground=[("selected", "#ffffff")],
        )

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=18, fg_color="#0f1d2b")
        self.header_frame = header
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Results Studio — profesjonalny podgląd wyników",
            font=("Arial", 25, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        self.header_subtitle = ctk.CTkLabel(
            header,
            text=(
                "Wczytaj wyniki, filtruj rekordy, sortuj kolumny i sprawdzaj jakość danych "
                "bez wychodzenia z aplikacji."
            ),
            text_color="#cbd5e1",
            wraplength=1120,
            justify="left",
        )
        self.header_subtitle.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
        self.status_chip = ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            fg_color="#123456",
            corner_radius=12,
            text_color="#dbeafe",
        )
        self.status_chip.grid(row=0, column=1, rowspan=2, sticky="e", padx=18, pady=16)

    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self, corner_radius=18, fg_color="#111827")
        self.toolbar_frame = toolbar
        self.assistant_sections["toolbar"] = toolbar
        toolbar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        toolbar.grid_columnconfigure(1, weight=2)
        toolbar.grid_columnconfigure(6, weight=1)

        ctk.CTkButton(toolbar, text="Wczytaj dane", command=self.load_file, width=138).grid(
            row=0, column=0, padx=(12, 6), pady=12
        )
        ctk.CTkEntry(
            toolbar,
            textvariable=self.filter_var,
            placeholder_text="Szukaj w całej tabeli...",
        ).grid(row=0, column=1, padx=6, pady=12, sticky="ew")
        self.sort_menu = ctk.CTkOptionMenu(toolbar, values=[], variable=self.sort_var, width=150)
        self.sort_menu.grid(row=0, column=2, padx=6, pady=12)
        ctk.CTkCheckBox(toolbar, text="malejąco", variable=self.desc_var, width=94).grid(
            row=0, column=3, padx=6, pady=12
        )
        self.profile_menu = ctk.CTkOptionMenu(
            toolbar, values=[], variable=self.profile_var, width=150
        )
        self.profile_menu.grid(row=0, column=4, padx=6, pady=12)
        ctk.CTkButton(toolbar, text="Odśwież", command=self.refresh_view, width=98).grid(
            row=0, column=5, padx=6, pady=12
        )
        ctk.CTkButton(toolbar, text="Eksport CSV", command=self.export_visible, width=116).grid(
            row=0, column=6, padx=6, pady=12, sticky="e"
        )
        ctk.CTkSegmentedButton(
            toolbar,
            values=["Tabela", "SQL"],
            variable=self.view_mode_var,
            command=lambda _value: self._set_view_mode(),
            width=162,
        ).grid(row=0, column=7, padx=6, pady=12, sticky="e")
        ctk.CTkLabel(
            toolbar,
            text="Kliknij nagłówek tabeli, aby sortować.",
            text_color="#94a3b8",
            justify="left",
        ).grid(row=0, column=8, padx=(6, 12), pady=12, sticky="e")

        loader = ctk.CTkFrame(toolbar, fg_color="#0b1220", corner_radius=14)
        self.loader_frame = loader
        loader.grid(row=1, column=0, columnspan=9, sticky="ew", padx=12, pady=(0, 12))
        loader.grid_columnconfigure(8, weight=1)
        ctk.CTkLabel(
            loader, text="1. Tryb:", text_color="#cbd5e1", font=("Arial", 12, "bold")
        ).grid(row=0, column=0, padx=(12, 6), pady=10)
        self.top_menu = ctk.CTkOptionMenu(
            loader,
            values=["Wszystkie", "Największe", "Najmniejsze"],
            variable=self.top_mode_var,
            width=125,
        )
        self.top_menu.grid(row=0, column=1, padx=6, pady=10)
        ctk.CTkLabel(
            loader, text="2. Kolumna:", text_color="#cbd5e1", font=("Arial", 12, "bold")
        ).grid(row=0, column=2, padx=(10, 2), pady=10)
        self.metric_menu = ctk.CTkOptionMenu(loader, values=[], variable=self.metric_var, width=145)
        self.metric_menu.grid(row=0, column=3, padx=6, pady=10)
        ctk.CTkLabel(
            loader, text="3. Wiersze:", text_color="#cbd5e1", font=("Arial", 12, "bold")
        ).grid(row=0, column=4, padx=(12, 4), pady=10)
        self.limit_menu = ctk.CTkOptionMenu(
            loader,
            values=["Wszystkie", "10", "20", "50"],
            variable=self.limit_var,
            width=112,
        )
        self.limit_menu.grid(row=0, column=5, padx=6, pady=10)
        ctk.CTkButton(loader, text="Zastosuj", command=self.refresh_view, width=92).grid(
            row=0, column=6, padx=6, pady=10
        )
        ctk.CTkButton(loader, text="Wyczyść", command=self.reset_filters, width=92).grid(
            row=0, column=7, padx=6, pady=10
        )
        ctk.CTkLabel(
            loader,
            text="Masz 4 wybory: tryb, kolumna, preset liczby wierszy albo własna liczba niżej.",
            text_color="#94a3b8",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=8, padx=(8, 12), pady=10, sticky="w")
        ctk.CTkLabel(
            loader,
            text="4. Własna liczba wierszy:",
            text_color="#cbd5e1",
            font=("Arial", 12, "bold"),
        ).grid(row=1, column=0, columnspan=2, padx=(12, 6), pady=(0, 10), sticky="w")
        self.custom_limit_entry = ctk.CTkEntry(
            loader,
            textvariable=self.custom_limit_var,
            placeholder_text="np. 37",
            width=96,
        )
        self.custom_limit_entry.grid(row=1, column=2, padx=6, pady=(0, 10), sticky="w")
        self.custom_limit_entry.bind("<Return>", lambda _event: self.refresh_view())
        ctk.CTkLabel(
            loader,
            text="Np. wpisz 20 i kliknij Zastosuj. Jeśli plik ma tylko 10 rekordów, zobaczysz 10 i dostaniesz jasny komunikat.",
            text_color="#94a3b8",
            wraplength=720,
            justify="left",
        ).grid(row=1, column=3, columnspan=7, padx=(8, 12), pady=(0, 10), sticky="w")

    def _build_summary_cards(self) -> None:
        cards = ctk.CTkFrame(self, corner_radius=18, fg_color="#111827")
        self.summary_frame = cards
        cards.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        cards.configure(height=90)
        cards.grid_propagate(False)
        cards.grid_rowconfigure(0, weight=1)
        titles = ("Wiersze", "Widoczne", "Kolumny", "Liczbowe", "Braki", "Duplikaty")
        accents = ("#38bdf8", "#22c55e", "#a78bfa", "#f59e0b", "#ef4444", "#64748b")
        for index, (title, accent) in enumerate(zip(titles, accents, strict=True)):
            cards.grid_columnconfigure(index, weight=1)
            card = ctk.CTkFrame(cards, corner_radius=14, fg_color="#0f172a")
            card.grid(row=0, column=index, sticky="nsew", padx=6, pady=7)
            card.configure(height=74)
            card.grid_propagate(False)
            card.grid_columnconfigure(1, weight=1)
            card.grid_rowconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)
            ctk.CTkFrame(card, width=4, fg_color=accent, corner_radius=3).grid(
                row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 8), pady=8
            )
            ctk.CTkLabel(card, text=title, text_color="#94a3b8", font=("Arial", 11)).grid(
                row=0, column=1, sticky="sw", padx=10, pady=(7, 0)
            )
            label = ctk.CTkLabel(card, text="—", font=("Arial", 17, "bold"))
            label.configure(font=("Arial", 19, "bold"), text_color="#f8fafc")
            label.grid(row=1, column=1, sticky="nw", padx=10, pady=(0, 7))
            self.summary_labels[title] = label
            self.summary_cards[title] = card

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame = body
        body.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=5, minsize=780)
        body.grid_columnconfigure(1, weight=2, minsize=420)
        body.grid_rowconfigure(0, weight=1)

        table_card = ctk.CTkFrame(body, corner_radius=18, fg_color="#111827")
        self.table_card = table_card
        self.assistant_sections["table"] = table_card
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(table_card, text="Tabela wynikowa", font=("Arial", 19, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 2)
        )
        self.table_status = ctk.CTkLabel(
            table_card,
            text="Brak danych",
            text_color="#94a3b8",
            justify="left",
        )
        self.table_status.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.table_shell = ctk.CTkFrame(table_card, fg_color="#0b1220", corner_radius=14)
        self.table_shell.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.table_shell.grid_columnconfigure(0, weight=1)
        self.table_shell.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(self.table_shell, show="headings", style="Results.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        self.tree.tag_configure("odd", background="#111c2d")
        self.tree.tag_configure("even", background="#0f172a")
        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)
        y_scroll = ttk.Scrollbar(self.table_shell, orient="vertical", command=self.tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns", pady=(8, 0))
        x_scroll = ttk.Scrollbar(self.table_shell, orient="horizontal", command=self.tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.sql_shell = ctk.CTkFrame(table_card, fg_color="#0b1220", corner_radius=14)
        self.sql_shell.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.sql_shell.grid_columnconfigure(0, weight=1)
        self.sql_shell.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            self.sql_shell,
            text="Tryb SQL (tabela: results)",
            font=("Arial", 14, "bold"),
            text_color="#dbeafe",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        top_sql = ctk.CTkFrame(self.sql_shell, fg_color="transparent")
        top_sql.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        top_sql.grid_columnconfigure(0, weight=1)
        self.sql_query_box = ctk.CTkTextbox(
            top_sql,
            height=62,
            fg_color="#0f172a",
            text_color="#dbeafe",
            border_width=1,
            border_color="#24384b",
        )
        self.sql_query_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.sql_query_box.insert("1.0", "SELECT * FROM results LIMIT 20;")
        self.sql_query_box.bind("<Up>", self._sql_history_prev)
        self.sql_query_box.bind("<Down>", self._sql_history_next)
        self.sql_query_box.bind("<Tab>", self._sql_autocomplete)
        ctk.CTkButton(top_sql, text="Wykonaj SQL", width=120, command=self.run_sql_query).grid(
            row=0, column=1, sticky="n"
        )
        ctk.CTkButton(top_sql, text="Reset", width=120, command=self.reset_sql_query).grid(
            row=0, column=2, sticky="n", padx=(6, 0)
        )
        ctk.CTkButton(
            top_sql, text="Eksport SQL CSV", width=120, command=self.export_sql_visible
        ).grid(row=0, column=3, sticky="n", padx=(6, 0))
        ctk.CTkLabel(
            self.sql_shell,
            textvariable=self.sql_hint_var,
            text_color="#93b3ce",
            justify="left",
        ).grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 4))
        sql_table_shell = ctk.CTkFrame(self.sql_shell, fg_color="#0f172a", corner_radius=12)
        sql_table_shell.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        sql_table_shell.grid_columnconfigure(0, weight=1)
        sql_table_shell.grid_rowconfigure(0, weight=1)
        self.sql_tree = ttk.Treeview(sql_table_shell, show="headings", style="Results.Treeview")
        self.sql_tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        sql_y = ttk.Scrollbar(sql_table_shell, orient="vertical", command=self.sql_tree.yview)
        sql_y.grid(row=0, column=1, sticky="ns", pady=(8, 0))
        sql_x = ttk.Scrollbar(sql_table_shell, orient="horizontal", command=self.sql_tree.xview)
        sql_x.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.sql_tree.configure(yscrollcommand=sql_y.set, xscrollcommand=sql_x.set)
        self.sql_table_status = ctk.CTkLabel(
            self.sql_shell,
            text="Brak wyników SQL.",
            text_color="#9fb4c8",
            justify="left",
        )
        self.sql_table_status.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))
        self.sql_shell.grid_remove()

        report_frame = ctk.CTkFrame(body, corner_radius=18, width=420, fg_color="#111827")
        self.report_frame = report_frame
        self.assistant_sections["report"] = report_frame
        report_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        report_frame.grid_propagate(False)
        report_frame.grid_columnconfigure(0, weight=1)
        report_frame.grid_rowconfigure(5, weight=1)
        ctk.CTkLabel(report_frame, text="Profil i jakość danych", font=("Arial", 19, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 4)
        )
        self.quality_label = ctk.CTkLabel(
            report_frame,
            text="Jakość danych: —",
            text_color="#cbd5e1",
            justify="left",
        )
        self.quality_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 4))
        self.quality_bar = ctk.CTkProgressBar(report_frame, height=12, progress_color="#22c55e")
        self.quality_bar.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.quality_bar.set(0)

        action_row = ctk.CTkFrame(report_frame, fg_color="transparent")
        action_row.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 8))
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(action_row, text="Raport braków", command=self.show_missing_report).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(action_row, text="Reset filtra", command=self.reset_filters).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        column_panel = ctk.CTkFrame(report_frame, fg_color="#0b1220", corner_radius=14)
        column_panel.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 10))
        column_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            column_panel,
            text="Kolumny w tabeli i eksporcie",
            font=("Arial", 13, "bold"),
            text_color="#e5eef9",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        column_buttons = ctk.CTkFrame(column_panel, fg_color="transparent")
        column_buttons.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        column_buttons.grid_columnconfigure(0, weight=1)
        column_buttons.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            column_buttons, text="Zaznacz wszystkie", command=self.select_all_columns
        ).grid(row=0, column=0, sticky="ew", padx=4, pady=2)
        ctk.CTkButton(
            column_buttons, text="Odznacz wszystkie", command=self.clear_all_columns
        ).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.column_selector_frame = ctk.CTkScrollableFrame(
            column_panel,
            height=150,
            fg_color="#111827",
        )
        self.column_selector_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 10))
        self.report_box = ctk.CTkTextbox(
            report_frame,
            wrap="word",
            fg_color="#0b1220",
            text_color="#e5eef9",
            border_width=1,
            border_color="#243244",
        )
        self.report_box.grid(row=5, column=0, sticky="nsew", padx=14, pady=(0, 14))

    def load_file(self):
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
            columns = result["columns"]
            numeric_columns = self.df_loaded.select_dtypes(include="number").columns.tolist()
            self.sort_menu.configure(values=["(brak)", *columns])
            self.profile_menu.configure(values=columns)
            self.metric_menu.configure(values=numeric_columns or columns)
            self._init_column_selector(columns)
            if columns:
                self.sort_var.set("(brak)")
                self.profile_var.set(columns[0])
            if numeric_columns:
                self.metric_var.set(numeric_columns[0])
            self.status_var.set(f"Wczytano: {len(self.df_loaded)} wierszy, {len(columns)} kolumn")
            self.refresh_view()
            if self.view_mode_var.get() == "SQL":
                self.run_sql_query()
            messagebox.showinfo("OK", f"Wczytano plik: {path}")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def refresh_view(self):
        if self.view_mode_var.get() == "SQL":
            if self.df_loaded is not None:
                self.run_sql_query()
            return
        if self.df_loaded is None:
            self.visible_df = None
            self._set_text("Wczytaj plik, aby zobaczyć dane.")
            self._set_report("Tu pojawi się podsumowanie pliku, profil kolumny i wskazówki.")
            self._update_summary(None)
            return
        try:
            limit = self._selected_limit()
            requested_limit = limit
            sort_column = self.sort_var.get()
            if sort_column == "(brak)":
                sort_column = None
            numeric_column = self.metric_var.get() or None
            result = build_viewer_result(
                self.df_loaded,
                query=self.filter_var.get(),
                sort_column=sort_column,
                descending=self.desc_var.get(),
                limit=limit,
                profile_column=self.profile_var.get(),
                numeric_column=numeric_column,
                min_value=None,
                max_value=None,
                top_mode=self._top_mode_key(),
            )
            display_df = self._apply_column_selection(result.df)
            self.visible_df = display_df
            self._render_table(display_df)
            self._set_report(result.report)
            self._update_summary(display_df)
            total_rows = len(self.df_loaded) if self.df_loaded is not None else len(result.df)
            if len(result.df) == 0:
                self.status_var.set("Widok gotowy: 0 wierszy po filtrach")
            elif requested_limit > len(result.df) and len(result.df) == total_rows:
                self.status_var.set(
                    f"Widok gotowy: pokazuję {len(result.df)} z {total_rows} wierszy "
                    f"(plik ma mniej niż limit {requested_limit})"
                )
            elif requested_limit > len(result.df):
                self.status_var.set(f"Widok gotowy: {len(result.df)} wierszy po filtrach")
            else:
                self.status_var.set(f"Widok gotowy: {len(result.df)} widocznych wierszy")
        except Exception as e:
            messagebox.showerror("Błąd widoku", str(e))

    def show_missing_report(self) -> None:
        if self.df_loaded is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik")
            return
        self._set_report(build_missing_report(self.df_loaded))

    def reset_filters(self) -> None:
        self.filter_var.set("")
        self.sort_var.set("(brak)")
        self.desc_var.set(False)
        self.top_mode_var.set("Wszystkie")
        self.limit_var.set("Wszystkie")
        self.custom_limit_var.set("")
        self.refresh_view()

    def export_visible(self) -> None:
        if self.visible_df is None:
            messagebox.showerror("Błąd", "Brak widocznych danych do eksportu")
            return
        if len(self.visible_df.columns) == 0:
            messagebox.showerror("Błąd", "Wybierz przynajmniej jedną kolumnę do eksportu")
            return
        if self.visible_df.empty:
            messagebox.showerror("Błąd", "Brak widocznych danych do eksportu")
            return
        path = filedialog.asksaveasfilename(
            title="Zapisz widoczny widok",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            self.visible_df.to_csv(path, index=False)
            messagebox.showinfo("OK", f"Zapisano widok: {path}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", str(e))

    def _sort_by_column(self, column: str) -> None:
        if self.sort_var.get() == column:
            self.desc_var.set(not self.desc_var.get())
        else:
            self.sort_var.set(column)
            self.desc_var.set(False)
        self.profile_var.set(column)
        self.refresh_view()

    def _make_sort_command(self, column: str):
        return lambda: self._sort_by_column(column)

    def _on_row_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected or self.visible_df is None or self.visible_df.empty:
            return
        values = self.tree.item(selected[0], "values")
        if not values:
            return
        preview = " | ".join(str(value) for value in values[:4])
        self.table_status.configure(text=f"Zaznaczony wiersz: {preview}")

    def _init_column_selector(self, columns: list[str]) -> None:
        if self.column_selector_frame is None:
            return
        for child in self.column_selector_frame.winfo_children():
            child.destroy()
        self.column_vars = {column: ctk.BooleanVar(value=True) for column in columns}
        for index, column in enumerate(columns):
            checkbox = ctk.CTkCheckBox(
                self.column_selector_frame,
                text=column,
                variable=self.column_vars[column],
                command=self.refresh_view,
            )
            checkbox.grid(row=index, column=0, sticky="w", padx=8, pady=3)

    def _selected_columns(self) -> list[str]:
        if not self.column_vars:
            return list(self.df_loaded.columns) if self.df_loaded is not None else []
        return [column for column, var in self.column_vars.items() if var.get()]

    def _apply_column_selection(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None:
            return pd.DataFrame()
        selected = [column for column in self._selected_columns() if column in df.columns]
        return df.loc[:, selected].copy()

    def select_all_columns(self) -> None:
        for var in self.column_vars.values():
            var.set(True)
        self.refresh_view()

    def clear_all_columns(self) -> None:
        for var in self.column_vars.values():
            var.set(False)
        self.refresh_view()

    def _render_table(self, df: pd.DataFrame) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree_columns = list(df.columns) if df is not None else []
        self.tree.configure(columns=self.tree_columns)
        for column in self.tree_columns:
            width = self._column_width(df, column)
            self.tree.heading(column, text=column, command=self._make_sort_command(column))
            self.tree.column(column, width=width, minwidth=82, stretch=False, anchor="w")
        if df is not None and len(df.columns) == 0:
            self.table_status.configure(text="Nie wybrano kolumn do pokazania.")
            return
        if df is None or df.empty:
            self.table_status.configure(text="Brak wierszy po filtrze.")
            return
        for index, (_, row) in enumerate(df.iterrows()):
            tag = "even" if index % 2 == 0 else "odd"
            values = [self._format_cell(row[column]) for column in self.tree_columns]
            self.tree.insert("", "end", values=values, tags=(tag,))
        self.table_status.configure(
            text=f"Pokazuję {len(df)} wierszy i {len(self.tree_columns)} kolumn. Nagłówki sortują dane."
        )

    @staticmethod
    def _format_cell(value) -> str:
        if pd.isna(value):
            return "—"
        if isinstance(value, float):
            return f"{value:.4g}"
        return str(value)

    @staticmethod
    def _column_width(df: pd.DataFrame, column: str) -> int:
        sample = [str(column), *[str(value) for value in df[column].head(30).tolist()]]
        longest = max((len(value) for value in sample), default=10)
        return max(92, min(180, longest * 8 + 24))

    def _top_mode_key(self) -> str:
        return {
            "Największe": "largest",
            "Najmniejsze": "smallest",
        }.get(self.top_mode_var.get(), "all")

    def _selected_limit(self) -> int:
        raw_value = self.custom_limit_var.get().strip() or self.limit_var.get().strip()
        if not raw_value or raw_value.lower() in {"wszystkie", "all"}:
            return len(self.df_loaded) if self.df_loaded is not None else 200
        try:
            limit = int(raw_value)
        except ValueError:
            raise ValueError("Limit wierszy musi być liczbą albo wartością 'Wszystkie'.") from None
        if limit <= 0:
            raise ValueError("Limit wierszy musi być większy od zera.")
        return limit

    @staticmethod
    def _optional_float(raw_value: str, label: str) -> float | None:
        value = raw_value.strip()
        if not value:
            return None
        try:
            return float(value.replace(",", "."))
        except ValueError:
            raise ValueError(f"Wartość {label} musi być liczbą.") from None

    def _update_summary(self, visible_df) -> None:
        if self.df_loaded is None:
            values = {key: "—" for key in self.summary_labels}
            quality = 0.0
            quality_text = "Jakość danych: —"
        else:
            profile = build_dataset_profile(self.df_loaded)
            total_cells = max(profile.rows * profile.columns, 1)
            quality = max(0.0, 1.0 - (profile.missing_values / total_cells))
            visible_columns = len(visible_df.columns) if visible_df is not None else profile.columns
            if visible_df is not None and len(visible_df.columns) > 0:
                visible_numeric = len(visible_df.select_dtypes(include="number").columns)
            else:
                visible_numeric = 0 if visible_df is not None else profile.numeric_columns
            values = {
                "Wiersze": str(profile.rows),
                "Widoczne": str(len(visible_df)) if visible_df is not None else str(profile.rows),
                "Kolumny": f"{visible_columns}/{profile.columns}",
                "Liczbowe": f"{visible_numeric}/{profile.numeric_columns}",
                "Braki": str(profile.missing_values),
                "Duplikaty": str(profile.duplicate_rows),
            }
            quality_text = f"Jakość danych: {quality * 100:.1f}% kompletności"
        for key, value in values.items():
            self.summary_labels[key].configure(text=value)
        color = "#22c55e" if quality >= 0.95 else "#f59e0b" if quality >= 0.8 else "#ef4444"
        self.quality_bar.configure(progress_color=color)
        self.quality_bar.set(quality)
        self.quality_label.configure(text=quality_text)

    def _set_text(self, text: str):
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(columns=[])
        self.table_status.configure(text=text)

    def _set_report(self, text: str):
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("end", text)
        self.report_box.configure(state="disabled")

    def _set_view_mode(self) -> None:
        if self.view_mode_var.get() == "SQL":
            if self.table_shell is not None:
                self.table_shell.grid_remove()
            if self.sql_shell is not None:
                self.sql_shell.grid()
            if self.summary_frame is not None:
                self.summary_frame.grid_remove()
            if self.report_frame is not None:
                self.report_frame.grid_remove()
            if self.loader_frame is not None:
                self.loader_frame.grid_remove()
            if self.body_frame is not None:
                self.body_frame.grid_columnconfigure(0, weight=1, minsize=0)
                self.body_frame.grid_columnconfigure(1, weight=0, minsize=0)
            if self.table_card is not None:
                self.table_card.grid_configure(padx=(0, 0))
            self.status_var.set("Tryb SQL aktywny (tabela: results).")
        else:
            if self.sql_shell is not None:
                self.sql_shell.grid_remove()
            if self.table_shell is not None:
                self.table_shell.grid()
            if self.summary_frame is not None:
                self.summary_frame.grid()
            if self.report_frame is not None:
                self.report_frame.grid()
            if self.loader_frame is not None:
                self.loader_frame.grid()
            if self.body_frame is not None:
                self.body_frame.grid_columnconfigure(0, weight=5, minsize=780)
                self.body_frame.grid_columnconfigure(1, weight=2, minsize=420)
            if self.table_card is not None:
                self.table_card.grid_configure(padx=(0, 10))
            if self.df_loaded is not None:
                self.refresh_view()

    def reset_sql_query(self) -> None:
        if self.sql_query_box is None:
            return
        self.sql_query_box.delete("1.0", "end")
        self.sql_query_box.insert("1.0", "SELECT * FROM results LIMIT 20;")
        self.sql_hint_var.set("")

    def run_sql_query(self) -> None:
        if self.df_loaded is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik z danymi.")
            return
        if self.sql_query_box is None:
            return
        sql = self.sql_query_box.get("1.0", "end").strip()
        if not sql:
            messagebox.showerror("Błąd", "Wpisz zapytanie SQL.")
            return
        if not self.sql_history or self.sql_history[-1] != sql:
            self.sql_history.append(sql)
        self.sql_history_index = len(self.sql_history)
        conn = sqlite3.connect(":memory:")
        try:
            self.df_loaded.to_sql("results", conn, index=False, if_exists="replace")
            first_token = sql.split(None, 1)[0].lower() if sql else ""
            if first_token in {"select", "with", "pragma"}:
                query_df = pd.read_sql_query(sql, conn)
                self.sql_visible_df = query_df
                self._render_sql_table(query_df)
                self._set_report(f"SQL OK\n\n{sql}")
                self._update_summary(query_df)
                self.status_var.set(f"SQL OK: {len(query_df)} wierszy")
            else:
                conn.executescript(sql)
                query_df = pd.read_sql_query("SELECT * FROM results", conn)
                self.sql_visible_df = query_df
                self._render_sql_table(query_df)
                self._set_report(f"SQL wykonano\n\n{sql}")
                self._update_summary(query_df)
                self.status_var.set(f"SQL wykonano: {len(query_df)} wierszy po zmianie")
        except Exception as e:
            messagebox.showerror("Błąd SQL", str(e))
        finally:
            conn.close()

    def _render_sql_table(self, df: pd.DataFrame) -> None:
        if self.sql_tree is None:
            return
        self.sql_tree.delete(*self.sql_tree.get_children())
        sql_cols = list(df.columns) if df is not None else []
        self.sql_tree.configure(columns=sql_cols)
        for column in sql_cols:
            width = self._column_width(df, column)
            self.sql_tree.heading(column, text=column)
            self.sql_tree.column(column, width=width, minwidth=82, stretch=False, anchor="w")
        if df is None or df.empty:
            if self.sql_table_status is not None:
                self.sql_table_status.configure(text="Brak wynikow SQL.")
            return
        for index, (_, row) in enumerate(df.iterrows()):
            tag = "even" if index % 2 == 0 else "odd"
            values = [self._format_cell(row[column]) for column in sql_cols]
            self.sql_tree.insert("", "end", values=values, tags=(tag,))
        if self.sql_table_status is not None:
            self.sql_table_status.configure(text=f"SQL: {len(df)} wierszy, {len(sql_cols)} kolumn.")

    def export_sql_visible(self) -> None:
        if self.sql_visible_df is None or self.sql_visible_df.empty:
            messagebox.showerror("Błąd", "Brak wynikow SQL do eksportu.")
            return
        path = filedialog.asksaveasfilename(
            title="Zapisz wynik SQL",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            self.sql_visible_df.to_csv(path, index=False)
            messagebox.showinfo("OK", f"Zapisano wynik SQL: {path}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", str(e))

    def _sql_history_prev(self, _event=None):
        if not self.sql_history or self.sql_query_box is None:
            return "break"
        self.sql_history_index = max(0, self.sql_history_index - 1)
        self.sql_query_box.delete("1.0", "end")
        self.sql_query_box.insert("1.0", self.sql_history[self.sql_history_index])
        return "break"

    def _sql_history_next(self, _event=None):
        if not self.sql_history or self.sql_query_box is None:
            return "break"
        self.sql_history_index = min(len(self.sql_history), self.sql_history_index + 1)
        self.sql_query_box.delete("1.0", "end")
        if self.sql_history_index < len(self.sql_history):
            self.sql_query_box.insert("1.0", self.sql_history[self.sql_history_index])
        return "break"

    def _sql_autocomplete(self, _event=None):
        if self.sql_query_box is None:
            return "break"
        query = self.sql_query_box.get("1.0", "end")
        cursor = self.sql_query_box.index("insert")
        row, col = map(int, cursor.split("."))
        lines = query.splitlines() or [""]
        line = lines[row - 1] if row - 1 < len(lines) else ""
        token = line[:col].split()[-1].strip('",')
        if not token:
            self.sql_hint_var.set("TAB: wpisz poczatek nazwy kolumny.")
            return "break"
        cols = list(self.df_loaded.columns) if self.df_loaded is not None else []
        matches = [c for c in cols if c.lower().startswith(token.lower())]
        if len(matches) == 1:
            full = matches[0]
            self.sql_query_box.insert("insert", full[len(token) :])
            self.sql_hint_var.set(f"Auto: {full}")
        elif len(matches) > 1:
            self.sql_hint_var.set("Podpowiedzi: " + ", ".join(matches[:8]))
        else:
            self.sql_hint_var.set("Brak podpowiedzi.")
        return "break"

    def focus_section(self, section: str) -> None:
        frame = self.assistant_sections.get(section)
        if frame is None:
            return
        try:
            frame.configure(border_width=2, border_color="#1f8fff")
            self.after(1400, lambda: frame.configure(border_width=0))
        except Exception:
            return
