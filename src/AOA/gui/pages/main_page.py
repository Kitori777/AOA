import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from AOA.config import (
    DEFAULT_RESULT_FILE,
    MODEL_FILE,
    FULL_DATA_FILE,
    TRAIN_DATA_FILE,
    TEST_DATA_FILE,
)
from AOA.core.data_io import load_csv, save_csv
from AOA.core.services import (
    generate_and_split_data,
    solve_existing_models_service,
    train_models_service,
)


class MainPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        ctk.CTkLabel(
            self,
            text="ML / Optymalizacja",
            font=("Arial", 20, "bold")
        ).pack(pady=10)

        self.model_choice = ctk.StringVar(value="Schedule")
        ctk.CTkLabel(self, text="Który model trenować?").pack()

        ctk.CTkOptionMenu(
            self,
            values=["Quality", "Delay", "Schedule", "Oba"],
            variable=self.model_choice
        ).pack(pady=5)

        ctk.CTkButton(
            self,
            text="Generuj dane",
            command=self.gen
        ).pack(pady=5)

        ctk.CTkButton(
            self,
            text="Wczytaj dane (CSV)",
            command=self.load_from_disk
        ).pack(pady=5)

        ctk.CTkButton(
            self,
            text="Trenuj wybrany model",
            command=self.train
        ).pack(pady=5)

        ctk.CTkButton(
            self,
            text="▶ Rozwiąż istniejące modele",
            command=self.solve_existing_models
        ).pack(pady=5)

        self.logbox = ctk.CTkTextbox(self, height=300)
        self.logbox.pack(fill="x", padx=20, pady=20)

        self.df_train = None
        self.df_test = None

    def log(self, msg: str):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def gen(self):
        try:
            df_full, self.df_train, self.df_test = generate_and_split_data(
                n=5000,
                n_machines=3,
                test_size=0.2,
                seed=42
            )

            save_csv(df_full, FULL_DATA_FILE)
            save_csv(self.df_train, TRAIN_DATA_FILE)
            save_csv(self.df_test, TEST_DATA_FILE)

            self.log("✔ Dane wygenerowane i podzielone na train/test")
            self.log(f"Train: {len(self.df_train)} rekordów")
            self.log(f"Test: {len(self.df_test)} rekordów")
            self.log(f"📄 Zapisano pełny zbiór: {FULL_DATA_FILE}")
            self.log(f"📄 Zapisano train: {TRAIN_DATA_FILE}")
            self.log(f"📄 Zapisano test: {TEST_DATA_FILE}")

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def load_from_disk(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            initialdir=str(FULL_DATA_FILE.parent),
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return

        try:
            df_full = load_csv(path)
            split_index = int(len(df_full) * 0.8)

            self.df_train = df_full.iloc[:split_index].copy()
            self.df_test = df_full.iloc[split_index:].copy()

            self.log(f"✔ Wczytano dane: {path}")
            self.log(f"Train: {len(self.df_train)} rekordów")
            self.log(f"Test: {len(self.df_test)} rekordów")

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def train(self):
        if self.df_train is None:
            messagebox.showerror("Błąd", "Brak danych treningowych")
            return

        threading.Thread(target=self.train_worker, daemon=True).start()

    def train_worker(self):
        try:
            choice = self.model_choice.get()
            self.log(f"⏳ Start treningu: {choice}")

            def progress_callback(progress):
                self.log(f"⏳ ScheduleModel: {progress:.1f}%")

            train_models_service(
                df_train=self.df_train,
                choice=choice,
                model_path=MODEL_FILE,
                progress_callback=progress_callback
            )

            self.log(f"💾 Modele zapisane do: {MODEL_FILE}")
            self.log("✔ Trening zakończony")

        except Exception as e:
            self.log(f"❌ Błąd treningu: {e}")

    def solve_existing_models(self):
        threading.Thread(
            target=self._solve_existing_models_thread,
            daemon=True
        ).start()

    def _solve_existing_models_thread(self):
        try:
            model_path = filedialog.askopenfilename(
                title="Wybierz wytrenowany model",
                initialdir=str(MODEL_FILE.parent),
                filetypes=[("Pickle", "*.pkl")]
            )
            if not model_path:
                return

            data_path = filedialog.askopenfilename(
                title="Wybierz dane do rozwiązania",
                initialdir=str(FULL_DATA_FILE.parent),
                filetypes=[("CSV", "*.csv")]
            )
            if not data_path:
                return

            df_result = solve_existing_models_service(
                model_path=model_path,
                data_path=data_path,
                output_path=DEFAULT_RESULT_FILE
            )

            self.log("🏁 Rozwiązanie gotowe")
            self.log("TOP 10 produktów:")
            self.log(df_result.head(10).to_string())
            self.log(f"📄 Zapisano: {DEFAULT_RESULT_FILE}")

        except Exception as e:
            self.log(f"❌ Błąd rozwiązywania: {e}")
