import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from AOA.config import DATA_DIR, MODELS_DIR
from AOA.core.services import (
    generate_and_store_datasets,
    load_training_data,
    solve_models_flow,
    train_models_flow,
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
            values=["Quality", "Delay", "Schedule"],
            variable=self.model_choice
        ).pack(pady=5)

        ctk.CTkButton(self, text="Generuj dane", command=self.gen).pack(pady=5)
        ctk.CTkButton(self, text="Wczytaj dane (CSV)", command=self.load_from_disk).pack(pady=5)
        ctk.CTkButton(self, text="Trenuj wybrany model", command=self.train).pack(pady=5)
        ctk.CTkButton(self, text="▶ Rozwiąż istniejące modele", command=self.solve_existing_models).pack(pady=5)

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
            result = generate_and_store_datasets(
                n=5000,
                n_machines=1,
                test_size=0.2,
                seed=42
            )

            self.df_train = result["train_df"]
            self.df_test = result["test_df"]

            for line in result["messages"]:
                self.log(line)

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def load_from_disk(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            initialdir=str(DATA_DIR),
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return

        try:
            result = load_training_data(path=path, train_ratio=0.8)
            self.df_train = result["train_df"]
            self.df_test = result["test_df"]

            for line in result["messages"]:
                self.log(line)

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def train(self):
        if self.df_train is None:
            messagebox.showerror("Błąd", "Brak danych treningowych")
            return

        threading.Thread(target=self.train_worker, daemon=True).start()

    def train_worker(self):
        try:
            result = train_models_flow(
                df_train=self.df_train,
                choice=self.model_choice.get(),
                progress_callback=lambda p: self.log(f"⏳ ScheduleModel: {p:.1f}%")
            )

            for line in result["messages"]:
                self.log(line)

        except Exception as e:
            self.log(f"❌ Błąd treningu: {e}")

    def solve_existing_models(self):
        threading.Thread(target=self._solve_existing_models_thread, daemon=True).start()

    def _solve_existing_models_thread(self):
        try:
            model_path = filedialog.askopenfilename(
                title="Wybierz wytrenowany model",
                initialdir=str(MODELS_DIR),
                filetypes=[("Pickle", "*.pkl")]
            )
            if not model_path:
                return

            data_path = filedialog.askopenfilename(
                title="Wybierz dane do rozwiązania",
                initialdir=str(DATA_DIR),
                filetypes=[("CSV", "*.csv")]
            )
            if not data_path:
                return

            result = solve_models_flow(model_path=model_path, data_path=data_path)

            for line in result["messages"]:
                self.log(line)

        except Exception as e:
            self.log(f"❌ Błąd rozwiązywania: {e}")
