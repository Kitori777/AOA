from tkinter import BOTH, Scrollbar, Text, filedialog, messagebox

import customtkinter as ctk

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
        self.limit_var = ctk.StringVar(value="200")
        self.desc_var = ctk.BooleanVar(value=False)
        self.summary_labels: dict[str, ctk.CTkLabel] = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_header()
        self._build_toolbar()
        self._build_summary_cards()
        self._build_body()
        self._set_text("Wczytaj plik, aby zobaczyć dane.")
        self._set_report("Tu pojawi się podsumowanie pliku, profil kolumny i wskazówki do analizy.")

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=18)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Results Studio — viewer, filtr i raport danych",
            font=("Arial", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(12, 2))
        ctk.CTkLabel(
            header,
            text=(
                "Nowoczesny podgląd wyników: wczytaj tabelę, filtruj, sortuj, "
                "sprawdzaj profil kolumn i eksportuj widoczny wycinek."
            ),
            text_color="#cbd5e1",
            wraplength=1120,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self, corner_radius=18)
        toolbar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        toolbar.grid_columnconfigure(8, weight=1)
        ctk.CTkButton(toolbar, text="📂 Wczytaj dane", command=self.load_file, width=135).grid(
            row=0, column=0, padx=(12, 6), pady=10
        )
        ctk.CTkEntry(
            toolbar,
            textvariable=self.filter_var,
            placeholder_text="Szukaj w całej tabeli...",
            width=210,
        ).grid(row=0, column=1, padx=6, pady=10)
        self.sort_menu = ctk.CTkOptionMenu(toolbar, values=[], variable=self.sort_var, width=150)
        self.sort_menu.grid(row=0, column=2, padx=6, pady=10)
        ctk.CTkCheckBox(toolbar, text="malejąco", variable=self.desc_var, width=90).grid(
            row=0, column=3, padx=6, pady=10
        )
        ctk.CTkEntry(toolbar, textvariable=self.limit_var, placeholder_text="Limit", width=80).grid(
            row=0, column=4, padx=6, pady=10
        )
        self.profile_menu = ctk.CTkOptionMenu(
            toolbar, values=[], variable=self.profile_var, width=150
        )
        self.profile_menu.grid(row=0, column=5, padx=6, pady=10)
        ctk.CTkButton(toolbar, text="Odśwież", command=self.refresh_view, width=100).grid(
            row=0, column=6, padx=6, pady=10
        )
        ctk.CTkButton(toolbar, text="Eksport widoku", command=self.export_visible, width=125).grid(
            row=0, column=7, padx=6, pady=10
        )
        ctk.CTkLabel(
            toolbar,
            text="Filtr działa na wszystkie kolumny. Profil po prawej aktualizuje się dla wybranej kolumny.",
            text_color="#94a3b8",
            wraplength=460,
            justify="left",
        ).grid(row=0, column=8, padx=8, pady=10, sticky="w")

    def _build_summary_cards(self) -> None:
        cards = ctk.CTkFrame(self, corner_radius=18)
        cards.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        for index in range(6):
            cards.grid_columnconfigure(index, weight=1)
        titles = ("Wiersze", "Widoczne", "Kolumny", "Liczbowe", "Braki", "Duplikaty")
        for index, title in enumerate(titles):
            card = ctk.CTkFrame(cards, corner_radius=14)
            card.grid(row=0, column=index, sticky="ew", padx=6, pady=10)
            ctk.CTkLabel(card, text=title, text_color="#94a3b8", font=("Arial", 12)).pack(
                anchor="w", padx=12, pady=(8, 0)
            )
            label = ctk.CTkLabel(card, text="—", font=("Arial", 19, "bold"))
            label.pack(anchor="w", padx=12, pady=(0, 8))
            self.summary_labels[title] = label

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=7)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)
        table_card = ctk.CTkFrame(body, corner_radius=18)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(table_card, text="Tabela wynikowa", font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 8)
        )
        text_frame = ctk.CTkFrame(table_card, fg_color="transparent")
        text_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.v_scroll = Scrollbar(text_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll = Scrollbar(text_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")
        self.box = Text(
            text_frame,
            font=("Consolas", 10),
            wrap="none",
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
            bg="#f8fafc",
            fg="#0f172a",
            insertbackground="#0f172a",
        )
        self.box.pack(fill=BOTH, expand=True)
        self.v_scroll.config(command=self.box.yview)
        self.h_scroll.config(command=self.box.xview)
        report_frame = ctk.CTkFrame(body, corner_radius=18, width=370)
        report_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        report_frame.grid_propagate(False)
        report_frame.grid_columnconfigure(0, weight=1)
        report_frame.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(report_frame, text="Raport / profil danych", font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 8)
        )
        action_row = ctk.CTkFrame(report_frame, fg_color="transparent")
        action_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(action_row, text="Raport braków", command=self.show_missing_report).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(action_row, text="Reset filtra", command=self.reset_filters).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        self.report_box = ctk.CTkTextbox(report_frame, wrap="word", fg_color="#161b22")
        self.report_box.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))

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
            self.sort_menu.configure(values=["(brak)", *columns])
            self.profile_menu.configure(values=columns)
            if columns:
                self.sort_var.set("(brak)")
                self.profile_var.set(columns[0])
            self.refresh_view()
            messagebox.showinfo("OK", f"Wczytano plik: {path}")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def refresh_view(self):
        if self.df_loaded is None:
            self._set_text("Wczytaj plik, aby zobaczyć dane.")
            self._update_summary(None)
            return
        try:
            limit = int(self.limit_var.get() or "200")
            sort_column = self.sort_var.get()
            if sort_column == "(brak)":
                sort_column = None
            result = build_viewer_result(
                self.df_loaded,
                query=self.filter_var.get(),
                sort_column=sort_column,
                descending=self.desc_var.get(),
                limit=limit,
                profile_column=self.profile_var.get(),
            )
            self.visible_df = result.df
            self._set_text(result.text)
            self._set_report(result.report)
            self._update_summary(result.df)
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
        self.limit_var.set("200")
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

    def _update_summary(self, visible_df) -> None:
        if self.df_loaded is None:
            values = {key: "—" for key in self.summary_labels}
        else:
            profile = build_dataset_profile(self.df_loaded)
            values = {
                "Wiersze": str(profile.rows),
                "Widoczne": str(len(visible_df)) if visible_df is not None else str(profile.rows),
                "Kolumny": str(profile.columns),
                "Liczbowe": str(profile.numeric_columns),
                "Braki": str(profile.missing_values),
                "Duplikaty": str(profile.duplicate_rows),
            }
        for key, value in values.items():
            self.summary_labels[key].configure(text=value)

    def _set_text(self, text: str):
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.insert("end", text)
        self.box.configure(state="disabled")

    def _set_report(self, text: str):
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("end", text)
        self.report_box.configure(state="disabled")
