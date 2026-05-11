# mypy: disable-error-code=attr-defined
import threading
from tkinter import filedialog, messagebox

from AOA.config import DATA_DIR, MODELS_DIR
from AOA.core.models import load_model_pack
from AOA.core.services import (
    analyze_sto_models,
    generate_and_store_datasets_from_config,
    load_training_data,
    solve_models_flow,
    solve_sto_with_saved_model,
    split_selected_models,
    train_models_flow,
    train_sto_models_flow,
)
from AOA.utils.error_utils import write_exception_log


class MainPageStateMixin:
    def _ui_config(self):
        return {
            "selected_models": [name for name, var in self.model_vars.items() if var.get()],
            "selected_ksztalty": [name for name, var in self.ksztalt_vars.items() if var.get()],
            "selected_materialy": [name for name, var in self.material_vars.items() if var.get()],
            "n": self.n_var.get(),
            "n_machines": self.n_machines_var.get(),
            "test_size": self.test_size_var.get(),
            "seed": self.seed_var.get(),
            "prod_min": self.prod_min_var.get(),
            "prod_max": self.prod_max_var.get(),
            "deadline_min": self.deadline_min_var.get(),
            "deadline_max": self.deadline_max_var.get(),
            "backend": self.backend_var.get(),
        }

    def gen(self):
        try:
            cfg = self._ui_config()
            self.clear_loaded_data_state()
            self.log("ℹ Czyszczę poprzednie dane z pamięci...")
            self.log("▶ Start generowania nowych danych...")
            result = generate_and_store_datasets_from_config(cfg)
            self.df_full = result["full_df"]
            self.df_train = result["train_df"]
            self.df_test = result["test_df"]
            self.loaded_data_path = result["full_path"]
            self.last_generation_metadata = {
                "n": int(cfg["n"]),
                "n_machines": int(cfg["n_machines"]),
                "ksztalty": cfg["selected_ksztalty"],
                "materialy": cfg["selected_materialy"],
            }
            for line in result["messages"]:
                self.log(line)
            self.render_status()
            self.render_preview()
        except ValueError as e:
            self.log(f"⚠ Błąd danych: {e}")
            messagebox.showerror("Błąd danych", str(e))
        except Exception as e:
            log_path = write_exception_log("main_page.gen", e)
            self.log(f"❌ Nieoczekiwany błąd.\nSzczegóły zapisano w: {log_path}")
            messagebox.showerror("Błąd", "Wystąpił nieoczekiwany błąd podczas generowania danych.")

    def load_from_disk(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            initialdir=str(DATA_DIR),
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            self.clear_loaded_data_state()
            self.log(f"▶ Wczytywanie danych z pliku: {path}")
            result = load_training_data(path=path, train_ratio=0.8)
            self.df_full = result["full_df"]
            self.df_train = result["train_df"]
            self.df_test = result["test_df"]
            self.loaded_data_path = path
            for line in result["messages"]:
                self.log(line)
            self.render_status()
            self.render_preview()
        except FileNotFoundError:
            messagebox.showerror("Błąd", "Nie znaleziono wskazanego pliku.")
        except ValueError as e:
            messagebox.showerror("Błąd danych", str(e))
        except Exception as e:
            log_path = write_exception_log("main_page.load_from_disk", e)
            self.log(f"❌ Nieoczekiwany błąd.\nSzczegóły zapisano w: {log_path}")
            messagebox.showerror("Błąd", "Wystąpił nieoczekiwany błąd podczas wczytywania danych.")

    def train(self):
        cfg = self._ui_config()
        selected_models = cfg["selected_models"]
        backend = cfg["backend"]
        ml_models, sto_models = split_selected_models(selected_models)
        if not ml_models and not sto_models:
            messagebox.showerror("Błąd", "Wybierz przynajmniej jeden model.")
            return
        if ml_models and self.df_train is None:
            messagebox.showerror("Błąd", "Brak danych treningowych.")
            return
        threading.Thread(
            target=self.train_worker,
            args=(ml_models, sto_models, backend),
            daemon=True,
        ).start()

    def train_worker(self, ml_models, sto_models, backend):
        try:
            self._last_progress_per_model = {}
            if ml_models:
                backend_label = "TabPFN" if backend == "tabpfn" else "Classic"
                self._safe_log(
                    f"▶ Start treningu ML: {', '.join(ml_models)} | backend: {backend_label}"
                )
                result = train_models_flow(
                    df_train=self.df_train,
                    selected_models=ml_models,
                    metadata=self.last_generation_metadata,
                    progress_callback=self._on_train_progress,
                    backend=backend,
                    df_test=self.df_test,
                )
                for line in result["messages"]:
                    self._safe_log(line)
            if sto_models:
                self._safe_log(f"▶ Start zapisu modelu STO: {', '.join(sto_models)}")
                sto_pack_result = train_sto_models_flow(sto_models)
                for line in sto_pack_result["messages"]:
                    self._safe_log(line)
            if ml_models and sto_models:
                self._safe_log("✔ Zapisano razem modele ML i STO")
        except ValueError as e:
            self._safe_log(f"⚠ Błąd danych: {e}")
            self._safe_showerror("Błąd danych", str(e))
        except Exception as e:
            log_path = write_exception_log("main_page.train_worker", e)
            self._safe_log(f"❌ Błąd: {type(e).__name__}: {e}")
            self._safe_log(f"Szczegóły zapisano w: {log_path}")
            self._safe_showerror(
                "Błąd",
                f"Wystąpił błąd podczas uruchamiania modeli:\n\n{type(e).__name__}: {e}",
            )

    def solve_existing_models(self):
        model_path = filedialog.askopenfilename(
            title="Wybierz zapisany model",
            initialdir=str(MODELS_DIR),
            filetypes=[("Pickle", "*.pkl")],
        )
        if not model_path:
            return
        data_path = filedialog.askopenfilename(
            title="Wybierz dane do rozwiązania",
            initialdir=str(DATA_DIR),
            filetypes=[("CSV", "*.csv")],
        )
        if not data_path:
            return
        threading.Thread(
            target=self._solve_existing_models_worker,
            args=(model_path, data_path),
            daemon=True,
        ).start()

    def _solve_existing_models_worker(self, model_path, data_path):
        try:
            pack = load_model_pack(model_path)
            pack_kind = pack.get("pack_kind", "ml")
            self._safe_log(f"▶ Wybrany model: {model_path}")
            self._safe_log(f"▶ Wybrane dane: {data_path}")
            self._safe_log(f"▶ Typ paczki: {pack_kind}")
            if pack_kind == "sto":
                result = solve_sto_with_saved_model(model_path=model_path, data_path=data_path)
                for line in result.get("messages", []):
                    self._safe_log(line)
                self._safe_render_sto_report(result["report"])
                self._log_sto_results(result)
                return
            backend = pack.get("backend", "classic")
            self._safe_log(f"▶ Backend modelu ML: {backend}")
            result = solve_models_flow(model_path=model_path, data_path=data_path)
            for line in result["messages"]:
                self._safe_log(line)
            self._safe_log(f"✔ Plik wynikowy zapisany tutaj: {result['result_path']}")
        except ValueError as e:
            self._safe_log(f"⚠ Błąd danych: {e}")
            self._safe_showerror("Błąd danych", str(e))
        except Exception as e:
            log_path = write_exception_log("main_page.solve_existing_models", e)
            self._safe_log(f"❌ Błąd: {type(e).__name__}: {e}")
            self._safe_log(f"Szczegóły zapisano w: {log_path}")
            self._safe_showerror(
                "Błąd",
                f"Wystąpił błąd podczas rozwiązywania modeli:\n\n{type(e).__name__}: {e}",
            )

    def run_sto_analysis(self):
        selected_models = self._ui_config()["selected_models"]
        _, sto_models = split_selected_models(selected_models)
        if not sto_models:
            messagebox.showinfo("Informacja", "Wybierz przynajmniej jeden model STO.")
            return
        try:
            result = analyze_sto_models(
                job_ids_text=self.sto_jobs_var.get(),
                processing_text=self.sto_times_var.get(),
                deadlines_text=self.sto_deadlines_var.get(),
                selected_methods=sto_models,
            )
            self.render_sto_report(result["report"])
            self._log_sto_results(result)
        except ValueError as e:
            messagebox.showerror("Błąd STO", str(e))
        except Exception as e:
            log_path = write_exception_log("main_page.run_sto_analysis", e)
            self.log(f"❌ Nieoczekiwany błąd STO.\nSzczegóły zapisano w: {log_path}")
            messagebox.showerror("Błąd STO", "Wystąpił nieoczekiwany błąd podczas analizy STO.")
