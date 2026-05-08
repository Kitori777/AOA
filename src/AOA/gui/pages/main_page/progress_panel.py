# mypy: disable-error-code=attr-defined
from tkinter import messagebox

import customtkinter as ctk

from AOA.core.services import (
    build_dataframe_preview_text,
    build_main_page_status,
    build_main_page_summary,
)


class MainPageProgressPanelMixin:
    def _build_preview_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=8)
        ctk.CTkLabel(frame, text="Podgląd danych", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        self.preview_box = ctk.CTkTextbox(frame, height=220)
        self.preview_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.preview_box.configure(state="disabled")

    def _build_log_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=(8, 10))
        ctk.CTkLabel(frame, text="Log", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        self.logbox = ctk.CTkTextbox(frame, height=220)
        self.logbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.logbox.configure(state="disabled")

    def _build_summary_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
        ctk.CTkLabel(frame, text="Podsumowanie wyboru", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        self.summary_box = ctk.CTkTextbox(frame, height=260, wrap="word")
        self.summary_box.pack(fill="x", padx=15, pady=(0, 15))
        self.summary_box.configure(state="disabled")

    def _build_status_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=1, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(frame, text="Szybki status", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        self.status_label = ctk.CTkLabel(
            frame, text="", font=("Arial", 13), justify="left", wraplength=320
        )
        self.status_label.pack(anchor="w", fill="x", padx=15, pady=(0, 12))

    def _build_right_hint_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=2, column=0, sticky="ew", padx=10, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Jak czytać wyniki", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        hint = (
            "Po treningu modeli ML w logu pojawiają się metryki:\n"
            "• RMSE / MAE — im niżej, tym lepiej,\n"
            "• R² — im bliżej 1, tym lepiej.\n\n"
            "Dla STO zapisujesz model algorytmiczny, a później uruchamiasz go na CSV. "
            "Wyniki zapisują się w katalogu data/.\n\n"
            "Dla TabPFN na CPU najlepiej testować mniejsze zbiory, np. 300–1000 rekordów."
        )
        ctk.CTkLabel(frame, text=hint, justify="left", wraplength=320, font=("Arial", 12)).pack(
            anchor="w", fill="x", padx=15, pady=(0, 15)
        )

    def render_summary(self):
        summary = build_main_page_summary(self._ui_config())
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("end", summary)
        self.summary_box.configure(state="disabled")

    def render_status(self):
        self.status_label.configure(text=build_main_page_status(self.df_train, self.df_test))

    def render_preview(self):
        text = build_dataframe_preview_text(
            self.df_full, title="Podgląd pełnego zbioru", max_rows=15
        )
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("end", text)
        self.preview_box.configure(state="disabled")

    def render_sto_report(self, report: str):
        self.sto_box.configure(state="normal")
        self.sto_box.delete("1.0", "end")
        self.sto_box.insert("end", report)
        self.sto_box.configure(state="disabled")

    def _safe_log(self, msg: str):
        self.after(0, lambda: self.log(msg))

    def _safe_showerror(self, title: str, msg: str):
        self.after(0, lambda: messagebox.showerror(title, msg))

    def _safe_render_sto_report(self, report: str):
        self.after(0, lambda: self.render_sto_report(report))

    def log(self, msg: str):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def clear_loaded_data_state(self):
        self.df_train = None
        self.df_test = None
        self.df_full = None
        self.loaded_data_path = None
        self.render_status()
        self.render_preview()

    def _on_train_progress(self, model_name: str, percent: float, detail: str = ""):
        last_percent = self._last_progress_per_model.get(model_name, -1.0)
        should_log = percent >= 100.0 or last_percent < 0 or (percent - last_percent) >= 0.5
        if not should_log:
            return
        self._last_progress_per_model[model_name] = percent
        suffix = f" | {detail}" if detail else ""
        self._safe_log(f"⏳ {model_name}: {percent:.1f}%{suffix}")
