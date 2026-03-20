import customtkinter as ctk
import numpy as np
import pandas as pd

from tkinter import filedialog, messagebox, Text, Scrollbar, BOTH
from AOA.core.data_io import load_csv
from AOA.core.evaluation import (
    append_metrics_row,
    calculate_classification_metrics,
    calculate_regression_metrics,
    fill_missing_values,
    transform_numeric_columns,
)


class ResultsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        ctk.CTkLabel(
            self,
            text="Wyniki / Dane do ML",
            font=("Arial", 20, "bold")
        ).pack(pady=10)

        self.df_loaded = None
        self.column_vars = {}
        self.target_var = ctk.StringVar(value="")
        self.transformation_var = ctk.StringVar(value="Surowe")

        control = ctk.CTkFrame(self)
        control.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            control,
            text="📂 Wczytaj plik CSV",
            command=self.load_file
        ).grid(row=0, column=0, padx=5)

        ctk.CTkLabel(
            control,
            text="Przekształcenie:"
        ).grid(row=0, column=1, padx=5)

        self.transformation_menu = ctk.CTkOptionMenu(
            control,
            values=[
                "Surowe",
                "MinMax Normalizacja",
                "Standaryzacja",
                "Logarytm",
                "Skalowanie 0-1",
            ],
            variable=self.transformation_var
        )
        self.transformation_menu.grid(row=0, column=2, padx=5)

        self.target_menu = ctk.CTkOptionMenu(
            control,
            values=[],
            variable=self.target_var
        )
        self.target_menu.grid(row=0, column=3, padx=5)

        ctk.CTkButton(
            control,
            text="Regresja",
            command=lambda: self.show_data("regresja")
        ).grid(row=0, column=4, padx=5)

        ctk.CTkButton(
            control,
            text="Klasyfikacja",
            command=lambda: self.show_data("klasyfikacja")
        ).grid(row=0, column=5, padx=5)

        self.cols_frame = ctk.CTkScrollableFrame(self, height=120)
        self.cols_frame.pack(fill="x", padx=20, pady=10)

        text_frame = ctk.CTkFrame(self)
        text_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.v_scroll = Scrollbar(text_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        self.h_scroll = Scrollbar(text_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")

        self.box = Text(
            text_frame,
            font=("Courier", 10),
            wrap="none",
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set
        )
        self.box.pack(fill=BOTH, expand=True)

        self.v_scroll.config(command=self.box.yview)
        self.h_scroll.config(command=self.box.xview)

    def load_file(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return

        try:
            self.df_loaded = load_csv(path)
        except Exception as e:
            messagebox.showerror("Błąd", str(e))
            return

        for widget in self.cols_frame.winfo_children():
            widget.destroy()

        self.column_vars.clear()

        for col in self.df_loaded.columns:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.cols_frame, text=col, variable=var)
            cb.pack(anchor="w")
            self.column_vars[col] = var

        self.target_menu.configure(values=list(self.df_loaded.columns))
        if self.df_loaded.columns.tolist():
            self.target_var.set(self.df_loaded.columns[0])

        messagebox.showinfo("OK", f"Wczytano plik: {path}")

    def show_data(self, mode: str):
        if self.df_loaded is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik CSV")
            return

        selected_cols = [col for col, var in self.column_vars.items() if var.get()]
        if not selected_cols:
            messagebox.showerror("Błąd", "Zaznacz przynajmniej jedną kolumnę")
            return

        df_to_show = self.df_loaded[selected_cols].copy()
        df_to_show = fill_missing_values(df_to_show)
        df_to_show = transform_numeric_columns(df_to_show, self.transformation_var.get())

        target = self.target_var.get()
        if target not in df_to_show.columns:
            messagebox.showerror("Błąd", "Nieprawidłowy target")
            return

        try:
            if mode == "regresja":
                metrics = calculate_regression_metrics(df_to_show, target)
            elif mode == "klasyfikacja":
                metrics = calculate_classification_metrics(df_to_show, target)
            else:
                messagebox.showerror("Błąd", "Nieznany tryb analizy")
                return

            df_to_show = append_metrics_row(df_to_show, metrics)

        except Exception as e:
            messagebox.showerror("Błąd ML", str(e))
            return

        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.insert("end", df_to_show.to_string(index=True))
        self.box.configure(state="disabled")
