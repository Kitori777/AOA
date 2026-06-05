# mypy: disable-error-code=attr-defined
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd

from AOA.config import DATA_DIR, MODELS_DIR
from AOA.core.data_io import load_csv
from AOA.core.dataset_ops import split_train_test
from AOA.core.models import load_model_pack
from AOA.core.services import (
    DEFAULT_FIELD_ALIASES,
    analyze_sto_models,
    apply_data_mapping,
    generate_and_store_datasets_from_config,
    required_fields,
    solve_models_flow,
    solve_sto_with_saved_model,
    split_selected_models,
    suggest_mapping,
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
            title="Wybierz plik danych",
            initialdir=str(DATA_DIR),
            filetypes=[("Pliki tabelaryczne", "*.csv *.txt *.tsv"), ("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            cfg = self._ui_config()
            ml_models, sto_models = split_selected_models(cfg["selected_models"])
            require_ml = bool(ml_models)
            require_sto = bool(sto_models)

            df_raw = load_csv(path)
            mapping = self._show_data_mapping_dialog(
                df_raw=df_raw,
                file_path=path,
                require_ml=require_ml,
                require_sto=require_sto,
            )
            if mapping is None:
                self.log("Anulowano mapowanie kolumn.")
                return
            mapped = self._apply_data_mapping(
                df_raw=df_raw,
                mapping=mapping,
                require_ml=require_ml,
                require_sto=require_sto,
            )

            self.clear_loaded_data_state()
            self.log(f"Start wczytywania danych z pliku: {path}")
            self.df_full = mapped["full_df"]
            self.df_train, self.df_test = split_train_test(self.df_full, train_ratio=0.8)
            self.loaded_data_path = path
            for line in mapped["messages"]:
                self.log(line)
            self.log(f"Train: {len(self.df_train)} rekordow")
            self.log(f"Test: {len(self.df_test)} rekordow")
            self.render_status()
            self.render_preview()
        except FileNotFoundError:
            messagebox.showerror("Blad", "Nie znaleziono wskazanego pliku.")
        except ValueError as e:
            messagebox.showerror("Blad danych", str(e))
        except Exception as e:
            log_path = write_exception_log("main_page.load_from_disk", e)
            self.log(f"Nieoczekiwany blad. Szczegoly zapisano w: {log_path}")
            messagebox.showerror("Blad", "Wystapil nieoczekiwany blad podczas wczytywania danych.")

    def _show_data_mapping_dialog(
        self,
        *,
        df_raw: pd.DataFrame,
        file_path: str,
        require_ml: bool,
        require_sto: bool,
    ) -> dict[str, str] | None:
        columns = [str(col) for col in df_raw.columns]
        choices = ["(brak)", *columns]
        required = required_fields(require_ml=require_ml, require_sto=require_sto)

        dialog = ctk.CTkToplevel(self)
        dialog.title("Mapowanie kolumn danych")
        dialog.geometry("980x760")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            dialog,
            text="Konfiguracja danych wejściowych",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))
        ctk.CTkLabel(
            dialog,
            text=f"Plik: {file_path}\nWskaż, które kolumny odpowiadają polom modelu i STO.",
            justify="left",
            text_color="#a7b0ba",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        body = ctk.CTkFrame(dialog, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        mapping_box = ctk.CTkScrollableFrame(body, label_text="Mapowanie pól")
        mapping_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        preview_box = ctk.CTkFrame(body)
        preview_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        preview_box.grid_columnconfigure(0, weight=1)
        preview_box.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(preview_box, text="Podgląd danych", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )
        preview = ctk.CTkTextbox(preview_box, wrap="none")
        preview.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        preview.insert("1.0", df_raw.head(12).to_string(index=False))
        preview.configure(state="disabled")

        variables: dict[str, ctk.StringVar] = {}

        suggested = suggest_mapping(columns, aliases=DEFAULT_FIELD_ALIASES)

        targets = [
            ("cena", "Cena [ML]"),
            ("odpad", "Odpad [ML]"),
            ("termin_h", "Termin [ML/STO]"),
            ("czas_produkcji_h", "Czas trwania [ML/STO]"),
            ("ksztalt", "Kształt [ML]"),
            ("material", "Materiał [ML]"),
            ("x", "Wymiar X [ML]"),
            ("y", "Wymiar Y [ML]"),
            ("z", "Wymiar Z [ML]"),
            ("sto_job_id", "ID zlecenia [STO opcjonalnie]"),
        ]
        for row, (target, label_text) in enumerate(targets):
            is_required = target in required
            ctk.CTkLabel(
                mapping_box,
                text=f"{label_text}{' *' if is_required else ''}",
                text_color="#dbeafe" if is_required else "#cbd5e1",
                font=("Segoe UI", 12, "bold" if is_required else "normal"),
            ).grid(row=row, column=0, sticky="w", padx=10, pady=6)
            var = ctk.StringVar(value=suggested.get(target, "(brak)"))
            variables[target] = var
            ctk.CTkOptionMenu(mapping_box, values=choices, variable=var, width=230).grid(
                row=row, column=1, sticky="e", padx=10, pady=6
            )

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        info = (
            "Wymagane pola zależą od wybranych modeli. "
            "Dla samych heurystyk STO wystarczą termin i czas trwania."
        )
        ctk.CTkLabel(footer, text=info, text_color="#94a3b8", justify="left").grid(
            row=0, column=0, sticky="w", padx=4, pady=6
        )

        result: dict[str, str] = {}

        def _confirm() -> None:
            selected = {key: var.get() for key, var in variables.items()}
            missing = [key for key in required if selected.get(key, "(brak)") == "(brak)"]
            if missing:
                messagebox.showerror(
                    "Brak mapowania",
                    f"Uzupełnij wymagane pola: {', '.join(sorted(missing))}",
                    parent=dialog,
                )
                return
            duplicates = [
                source
                for source in {value for value in selected.values() if value != "(brak)"}
                if list(selected.values()).count(source) > 1
            ]
            if duplicates:
                messagebox.showerror(
                    "Duplikat kolumny",
                    "Ta sama kolumna źródłowa została przypisana do kilku pól. "
                    "Przypisz unikalne kolumny.",
                    parent=dialog,
                )
                return
            result.update(selected)
            dialog.destroy()

        ctk.CTkButton(footer, text="Anuluj", width=120, command=dialog.destroy).grid(
            row=0, column=1, padx=6, pady=6, sticky="e"
        )
        ctk.CTkButton(footer, text="Zastosuj mapowanie", width=180, command=_confirm).grid(
            row=0, column=2, padx=6, pady=6, sticky="e"
        )

        self.wait_window(dialog)
        return result if result else None

    def _apply_data_mapping(
        self,
        *,
        df_raw: pd.DataFrame,
        mapping: dict[str, str],
        require_ml: bool,
        require_sto: bool,
    ) -> dict:
        return apply_data_mapping(
            df_raw,
            mapping,
            require_ml=require_ml,
            require_sto=require_sto,
        )

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
                self._safe_render_sto_report(result["report"] + self._sto_saved_files_text(result))
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
            self.render_sto_report(result["report"] + self._sto_saved_files_text(result))
            self._log_sto_results(result)
        except ValueError as e:
            messagebox.showerror("Błąd STO", str(e))
        except Exception as e:
            log_path = write_exception_log("main_page.run_sto_analysis", e)
            self.log(f"❌ Nieoczekiwany błąd STO.\nSzczegóły zapisano w: {log_path}")
            messagebox.showerror("Błąd STO", "Wystąpił nieoczekiwany błąd podczas analizy STO.")
