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

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._configure_tree_style()
        self._build_header()
        self._build_toolbar()
        self._build_summary_cards()
        self._build_body()
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
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Results Studio — profesjonalny podgląd wyników",
            font=("Arial", 25, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text=(
                "Wczytaj wyniki, filtruj rekordy, sortuj kolumny i sprawdzaj jakość danych "
                "bez wychodzenia z aplikacji."
            ),
            text_color="#cbd5e1",
            wraplength=1120,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
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
        toolbar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        toolbar.grid_columnconfigure(1, weight=2)
        toolbar.grid_columnconfigure(6, weight=1)

        ctk.CTkButton(toolbar, text="📂 Wczytaj dane", command=self.load_file, width=138).grid(
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
        ctk.CTkLabel(
            toolbar,
            text="Kliknij nagłówek tabeli, aby sortować.",
            text_color="#94a3b8",
            justify="left",
        ).grid(row=0, column=7, padx=(6, 12), pady=12, sticky="e")

        loader = ctk.CTkFrame(toolbar, fg_color="#0b1220", corner_radius=14)
        loader.grid(row=1, column=0, columnspan=8, sticky="ew", padx=12, pady=(0, 12))
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
        cards.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        cards.configure(height=118)
        cards.grid_propagate(False)
        cards.grid_rowconfigure(0, weight=1)
        titles = ("Wiersze", "Widoczne", "Kolumny", "Liczbowe", "Braki", "Duplikaty")
        accents = ("#38bdf8", "#22c55e", "#a78bfa", "#f59e0b", "#ef4444", "#64748b")
        for index, (title, accent) in enumerate(zip(titles, accents, strict=True)):
            cards.grid_columnconfigure(index, weight=1)
            card = ctk.CTkFrame(cards, corner_radius=14, fg_color="#0f172a")
            card.grid(row=0, column=index, sticky="nsew", padx=6, pady=10)
            card.configure(height=94)
            card.grid_propagate(False)
            card.grid_columnconfigure(1, weight=1)
            card.grid_rowconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)
            ctk.CTkFrame(card, width=4, fg_color=accent, corner_radius=3).grid(
                row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 8), pady=12
            )
            ctk.CTkLabel(card, text=title, text_color="#94a3b8", font=("Arial", 12)).grid(
                row=0, column=1, sticky="sw", padx=10, pady=(12, 2)
            )
            label = ctk.CTkLabel(card, text="—", font=("Arial", 21, "bold"))
            label.configure(font=("Arial", 24, "bold"), text_color="#f8fafc")
            label.grid(row=1, column=1, sticky="nw", padx=10, pady=(0, 12))
            self.summary_labels[title] = label
            self.summary_cards[title] = card

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=5, minsize=780)
        body.grid_columnconfigure(1, weight=2, minsize=420)
        body.grid_rowconfigure(0, weight=1)

        table_card = ctk.CTkFrame(body, corner_radius=18, fg_color="#111827")
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

        table_shell = ctk.CTkFrame(table_card, fg_color="#0b1220", corner_radius=14)
        table_shell.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        table_shell.grid_columnconfigure(0, weight=1)
        table_shell.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_shell, show="headings", style="Results.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        self.tree.tag_configure("odd", background="#111c2d")
        self.tree.tag_configure("even", background="#0f172a")
        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)
        y_scroll = ttk.Scrollbar(table_shell, orient="vertical", command=self.tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns", pady=(8, 0))
        x_scroll = ttk.Scrollbar(table_shell, orient="horizontal", command=self.tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        report_frame = ctk.CTkFrame(body, corner_radius=18, width=420, fg_color="#111827")
        report_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        report_frame.grid_propagate(False)
        report_frame.grid_columnconfigure(0, weight=1)
        report_frame.grid_rowconfigure(4, weight=1)
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
        self.report_box = ctk.CTkTextbox(
            report_frame,
            wrap="word",
            fg_color="#0b1220",
            text_color="#e5eef9",
            border_width=1,
            border_color="#243244",
        )
        self.report_box.grid(row=4, column=0, sticky="nsew", padx=14, pady=(0, 14))

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
            if columns:
                self.sort_var.set("(brak)")
                self.profile_var.set(columns[0])
            if numeric_columns:
                self.metric_var.set(numeric_columns[0])
            self.status_var.set(f"Wczytano: {len(self.df_loaded)} wierszy, {len(columns)} kolumn")
            self.refresh_view()
            messagebox.showinfo("OK", f"Wczytano plik: {path}")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def refresh_view(self):
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
            self.visible_df = result.df
            self._render_table(result.df)
            self._set_report(result.report)
            self._update_summary(result.df)
            total_rows = len(self.df_loaded) if self.df_loaded is not None else len(result.df)
            if len(result.df) == 0:
                self.status_var.set("Widok gotowy: 0 wierszy po filtrach")
            elif requested_limit > len(result.df) and len(result.df) == total_rows:
                self.status_var.set(
                    f"Widok gotowy: pokazujÄ™ {len(result.df)} z {total_rows} wierszy "
                    f"(plik ma mniej niĹĽ limit {requested_limit})"
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
        if self.visible_df is None or self.visible_df.empty:
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

    def _render_table(self, df: pd.DataFrame) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree_columns = list(df.columns) if df is not None else []
        self.tree.configure(columns=self.tree_columns)
        for column in self.tree_columns:
            width = self._column_width(df, column)
            self.tree.heading(column, text=column, command=self._make_sort_command(column))
            self.tree.column(column, width=width, minwidth=82, stretch=False, anchor="w")
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
            values = {
                "Wiersze": str(profile.rows),
                "Widoczne": str(len(visible_df)) if visible_df is not None else str(profile.rows),
                "Kolumny": str(profile.columns),
                "Liczbowe": str(profile.numeric_columns),
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
