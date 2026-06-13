# mypy: disable-error-code=attr-defined
from tkinter import messagebox

import customtkinter as ctk

from AOA.core.mh_models import get_mh_model_specs, save_custom_heuristic_config
from AOA.core.ml_models import (
    available_sklearn_estimators,
    get_ml_model_specs,
    parse_params_json,
    save_custom_model_config,
)


class MainPageConfigFormMixin:
    def _build_layout(self):
        self.assistant_sections = {}
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(header, text="ML / Optymalizacja", font=("Arial", 24, "bold")).pack(
            anchor="w", padx=15, pady=(12, 2)
        )
        ctk.CTkLabel(
            header,
            text="Konfiguracja generowania danych, wyboru modeli i analiz STO",
            font=("Arial", 12),
        ).pack(anchor="w", padx=15, pady=(0, 12))

        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=20, pady=10)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkScrollableFrame(content)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        right_panel = ctk.CTkScrollableFrame(content, width=380, label_text="Panel boczny")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        right_panel.grid_columnconfigure(0, weight=1)

        self._build_models_section(left_panel)
        self._build_generation_section(left_panel)
        self._build_actions_section(left_panel)
        self._build_preview_section(left_panel)
        self._build_sto_results_section(left_panel)
        self._build_log_section(left_panel)
        self._build_summary_section(right_panel)
        self._build_status_section(right_panel)
        self._build_right_hint_section(right_panel)

    def _build_models_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=(10, 8))
        self.assistant_sections["models"] = frame
        ctk.CTkLabel(frame, text="Wybór modeli", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )

        ml_frame = ctk.CTkFrame(frame)
        ml_frame.pack(fill="x", padx=10, pady=(0, 8))
        self.ml_frame = ml_frame
        ctk.CTkLabel(ml_frame, text="Modele ML", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        tools = ctk.CTkFrame(ml_frame, fg_color="transparent")
        tools.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkButton(
            tools,
            text="+ Własny model sklearn",
            command=self._open_custom_model_dialog_v3,
            height=32,
        ).pack(side="left", padx=2, pady=2)
        ctk.CTkButton(
            tools,
            text="Odśwież modele",
            command=self._reload_ml_models,
            height=32,
            fg_color="#1f2937",
        ).pack(side="left", padx=8, pady=2)
        self.ml_models_list_frame = ctk.CTkFrame(ml_frame, fg_color="transparent")
        self.ml_models_list_frame.pack(fill="x", padx=0, pady=0)
        for spec in self.ml_model_specs:
            row = ctk.CTkFrame(self.ml_models_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            ctk.CTkCheckBox(
                row,
                text=spec.label,
                variable=self.model_vars[spec.name],
                command=self.render_summary,
            ).pack(anchor="w", padx=2, pady=(2, 0))
            ctk.CTkLabel(
                row,
                text=f"patrzy na: {spec.focus}",
                font=("Arial", 10),
                text_color="#a7b0ba",
                justify="left",
            ).pack(anchor="w", padx=38, pady=(0, 2))

        ctk.CTkLabel(ml_frame, text="Backend ML", font=("Arial", 14, "bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        self.backend_menu = ctk.CTkOptionMenu(
            ml_frame,
            values=["classic", "tabpfn"],
            variable=self.backend_var,
            command=lambda _value: self.render_summary(),
        )
        self.backend_menu.pack(anchor="w", padx=10, pady=(0, 4))
        ctk.CTkLabel(
            ml_frame,
            text=(
                "classic = wybrane estymatory sklearn/xgboost | tabpfn = eksperymentalny "
                "silnik dla każdego zaznaczonego zadania"
            ),
            font=("Arial", 11),
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=10, pady=(0, 10))

        sto_frame = ctk.CTkFrame(frame)
        sto_frame.pack(fill="x", padx=10, pady=(0, 12))
        ctk.CTkLabel(sto_frame, text="Modele heurystyczne STO", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        sto_tools = ctk.CTkFrame(sto_frame, fg_color="transparent")
        sto_tools.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkButton(
            sto_tools,
            text="+ Własna heurystyka STO",
            command=self._open_custom_heuristic_dialog,
            height=32,
        ).pack(side="left", padx=2, pady=2)
        ctk.CTkButton(
            sto_tools,
            text="Odśwież heurystyki",
            command=self._reload_mh_models,
            height=32,
            fg_color="#1f2937",
        ).pack(side="left", padx=8, pady=2)
        self.mh_models_list_frame = ctk.CTkFrame(sto_frame, fg_color="transparent")
        self.mh_models_list_frame.pack(fill="x", padx=0, pady=0)
        for spec in self.mh_model_specs:
            row = ctk.CTkFrame(sto_frame, fg_color="transparent")
            row = ctk.CTkFrame(self.mh_models_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            ctk.CTkCheckBox(
                row,
                text=spec.label,
                variable=self.model_vars[spec.name],
                command=self.render_summary,
            ).pack(anchor="w", padx=2, pady=(2, 0))
            ctk.CTkLabel(
                row,
                text=f"patrzy na: {spec.focus}",
                font=("Arial", 10),
                text_color="#a7b0ba",
                justify="left",
            ).pack(anchor="w", padx=38, pady=(0, 2))

    def _reload_mh_models(self):
        self.mh_model_specs = get_mh_model_specs()
        for spec in self.mh_model_specs:
            if spec.name not in self.model_vars:
                self.model_vars[spec.name] = ctk.BooleanVar(value=False)
        for child in self.mh_models_list_frame.winfo_children():
            child.destroy()
        for spec in self.mh_model_specs:
            row = ctk.CTkFrame(self.mh_models_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            ctk.CTkCheckBox(
                row,
                text=spec.label,
                variable=self.model_vars[spec.name],
                command=self.render_summary,
            ).pack(anchor="w", padx=2, pady=(2, 0))
            ctk.CTkLabel(
                row,
                text=f"patrzy na: {spec.focus}",
                font=("Arial", 10),
                text_color="#a7b0ba",
                justify="left",
            ).pack(anchor="w", padx=38, pady=(0, 2))
        self.render_summary()

    def _reload_ml_models(self):
        self.ml_model_specs = get_ml_model_specs()
        for spec in self.ml_model_specs:
            if spec.name not in self.model_vars:
                self.model_vars[spec.name] = ctk.BooleanVar(value=False)
        for child in self.ml_models_list_frame.winfo_children():
            child.destroy()
        for spec in self.ml_model_specs:
            row = ctk.CTkFrame(self.ml_models_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            ctk.CTkCheckBox(
                row,
                text=spec.label,
                variable=self.model_vars[spec.name],
                command=self.render_summary,
            ).pack(anchor="w", padx=2, pady=(2, 0))
            ctk.CTkLabel(
                row,
                text=f"patrzy na: {spec.focus}",
                font=("Arial", 10),
                text_color="#a7b0ba",
                justify="left",
            ).pack(anchor="w", padx=38, pady=(0, 2))
        self.render_summary()

    def _open_custom_heuristic_dialog(self):
        presets = {
            "Termin / SLA": ("Custom_STO_EDD", "Moja kolejka SLA", "d", "Najpierw elementy z najbliższym terminem albo limitem SLA."),
            "Najkrótsza obsługa": ("Custom_STO_SPT", "Moja szybka kolejka", "p", "Najpierw krótkie zadania, dostawy lub zgłoszenia, żeby szybko odblokować kolejkę."),
            "Najmniejszy zapas": ("Custom_STO_Slack", "Moja Slack", "d - p", "Najpierw elementy z najmniejszym buforem czasu."),
            "Critical ratio": ("Custom_STO_CR", "Moja CR", "d / p", "Relacja terminu do czasu obsługi; niżej oznacza pilniejsze."),
            "Ryzyko opóźnienia": ("Custom_STO_Risk", "Moje ryzyko", "d - 1.5 * p", "Mocniej karze długie elementy blisko terminu."),
            "Priorytet logistyczny": ("Custom_STO_Logistics", "Moja logistyka", "0.65 * d + 0.35 * p", "Miesza termin i czas obsługi, dobre do kolejek logistycznych."),
        }
        dialog = ctk.CTkToplevel(self)
        dialog.title("Własna heurystyka kolejności")
        dialog.geometry("980x720")
        dialog.minsize(820, 620)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=3)
        dialog.grid_columnconfigure(1, weight=2)
        dialog.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            dialog,
            text="Własna heurystyka kolejności",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=22, pady=(18, 8))

        form = ctk.CTkScrollableFrame(dialog)
        form.grid(row=1, column=0, sticky="nsew", padx=(22, 10), pady=(0, 12))
        form.grid_columnconfigure(1, weight=1)
        guide = ctk.CTkTextbox(dialog, wrap="word")
        guide.grid(row=1, column=1, sticky="nsew", padx=(10, 22), pady=(0, 12))

        name_var = ctk.StringVar(value="Custom_STO_EDD")
        label_var = ctk.StringVar(value="Moja heurystyka")
        formula_var = ctk.StringVar(value="d")
        description_var = ctk.StringVar(value="Najpierw elementy z najbliższym terminem albo limitem SLA.")

        def _set_guide() -> None:
            text = (
                "Jak działa własna heurystyka kolejności\n\n"
                "Heurystyka nie trenuje modelu ML. Ona układa kolejkę przez wzór score.\n"
                "Możesz używać jej do produkcji, logistyki, zgłoszeń, operacji serwisowych albo dowolnej listy zadań.\n"
                "Aplikacja liczy score dla każdego elementu i sortuje rosnąco: najmniejszy score idzie pierwszy.\n\n"
                "Dostępne zmienne:\n"
                "- p albo czas: czas obsługi, koszt, wysiłek albo długość zadania.\n"
                "- d albo termin: deadline, limit SLA, termin dostawy albo priorytet liczbowy.\n"
                "- slack: d - p, czyli zapas czasu albo bufor.\n"
                "- cr: d / p, critical ratio.\n"
                "- urgency: p / d, względna pilność.\n"
                "- i: numer elementu w danych, n: liczba elementów.\n\n"
                "Przykłady wzorów:\n"
                "d                 -> najbliższy termin/SLA pierwszy.\n"
                "p                 -> najkrótsza obsługa pierwsza.\n"
                "d - p             -> najmniejszy zapas czasu pierwszy.\n"
                "d / p             -> critical ratio.\n"
                "d - 1.5 * p       -> termin ważny, ale długie elementy robią się pilniejsze.\n"
                "0.7 * d + 0.3 * p -> mieszanka terminu i czasu.\n\n"
                "Po zapisie heurystyka pojawi się na liście heurystyk i będzie porównywana razem z MT, MO, MZO, MOPT itd."
            )
            guide.configure(state="normal")
            guide.delete("1.0", "end")
            guide.insert("1.0", text)
            guide.configure(state="disabled")

        def _apply_preset(key: str) -> None:
            name, label, formula, desc = presets[key]
            name_var.set(name)
            label_var.set(label)
            formula_var.set(formula)
            description_var.set(desc)

        ctk.CTkLabel(form, text="1. Wybierz przykład", font=("Segoe UI", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8)
        )
        preset_frame = ctk.CTkFrame(form, fg_color="transparent")
        preset_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        preset_frame.grid_columnconfigure((0, 1), weight=1)
        for index, key in enumerate(presets):
            ctk.CTkButton(
                preset_frame,
                text=key,
                command=lambda value=key: _apply_preset(value),
                height=34,
            ).grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=4)

        fields = [
            ("2. Nazwij heurystykę", None),
            ("Nazwa techniczna", name_var),
            ("Nazwa na ekranie", label_var),
            ("3. Wpisz wzór score", None),
            ("Wzór", formula_var),
            ("Opis", description_var),
        ]
        row = 2
        for label_text, variable in fields:
            if variable is None:
                ctk.CTkLabel(form, text=label_text, font=("Segoe UI", 17, "bold")).grid(
                    row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6)
                )
            else:
                ctk.CTkLabel(form, text=label_text).grid(row=row, column=0, sticky="w", padx=16, pady=6)
                ctk.CTkEntry(form, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=16, pady=6)
            row += 1

        ctk.CTkLabel(
            form,
            text="Sortowanie jest rosnące: najmniejszy score trafia najwcześniej w kolejce.",
            text_color="#bfdbfe",
            justify="left",
            wraplength=620,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 14))

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", padx=22, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text="Konfiguracja zostanie zapisana do: models/custom_sto_heuristics.json",
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w")

        def _save() -> None:
            try:
                config = save_custom_heuristic_config(
                    name=name_var.get(),
                    label=label_var.get(),
                    formula=formula_var.get(),
                    description=description_var.get(),
                )
                self.log(f"Zapisano własną heurystykę STO: {config.name}")
                dialog.destroy()
                self._reload_mh_models()
            except Exception as exc:
                messagebox.showerror("Błąd heurystyki", str(exc), parent=dialog)

        ctk.CTkButton(footer, text="Anuluj", width=130, command=dialog.destroy).grid(
            row=0, column=1, padx=6
        )
        ctk.CTkButton(footer, text="Zapisz heurystykę", width=170, command=_save).grid(
            row=0, column=2, padx=6
        )
        _set_guide()

    def _open_custom_model_dialog(self):
        task_labels = {
            "quality": "Jakość / regresja",
            "delay": "Opóźnienie / regresja",
            "schedule": "Harmonogram / klasyfikacja",
            "SVR: margines dla regresji": {
                "task": "quality",
                "name": "Custom_SVR",
                "estimator": "sklearn.svm.SVR",
                "scaler": "robust",
                "params": '{\n  "C": 12.0,\n  "epsilon": 0.08,\n  "gamma": "scale"\n}',
                "note": "SVM/SVR dobrze działa przy mniejszych danych i nieliniowej granicy, ale wymaga skalowania.",
            },
            "KNN: podobne przypadki": {
                "task": "delay",
                "name": "Custom_KNN",
                "estimator": "sklearn.neighbors.KNeighborsRegressor",
                "scaler": "robust",
                "params": '{\n  "n_neighbors": 9,\n  "weights": "distance"\n}',
                "note": "KNN porównuje nowe zlecenie do podobnych historycznych przypadków. Wymaga skalowania.",
            },
            "Ridge: prosty baseline": {
                "task": "quality",
                "name": "Custom_Ridge",
                "estimator": "sklearn.linear_model.Ridge",
                "scaler": "standard",
                "params": '{\n  "alpha": 1.4\n}',
                "note": "Prosty model liniowy. Dobry jako punkt odniesienia dla bardziej złożonych modeli.",
            },
            "HistGradient: większe dane": {
                "task": "delay",
                "name": "Custom_HistGradient",
                "estimator": "sklearn.ensemble.HistGradientBoostingRegressor",
                "scaler": "none",
                "params": '{\n  "max_iter": 260,\n  "learning_rate": 0.045,\n  "l2_regularization": 0.04,\n  "random_state": 42\n}',
                "note": "Boosting histogramowy. Dobry przy większych zbiorach i nieliniowych zależnościach.",
            },
            "RandomForestClassifier: klasy": {
                "task": "schedule",
                "name": "Custom_RandomForestSchedule",
                "estimator": "sklearn.ensemble.RandomForestClassifier",
                "scaler": "none",
                "params": '{\n  "n_estimators": 300,\n  "class_weight": "balanced_subsample",\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "note": "Klasyfikator drzewiasty do harmonogramu. Dobry, gdy klasy nie są liniowo rozdzielne.",
            },
        }
        task_by_label = {value: key for key, value in task_labels.items()}

        dialog = ctk.CTkToplevel(self)
        dialog.title("Własny model sklearn")
        dialog.geometry("880x620")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            dialog,
            text="Własny model sklearn",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        body = ctk.CTkFrame(dialog)
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=12)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(5, weight=1)

        name_var = ctk.StringVar(value="Custom_RF")
        label_var = ctk.StringVar(value="Mój RandomForest")
        task_var = ctk.StringVar(value=task_labels["quality"])
        scaler_var = ctk.StringVar(value="auto")
        estimator_var = ctk.StringVar(value="")

        def _estimators_for_task() -> list[str]:
            task = task_by_label[task_var.get()]
            return list(available_sklearn_estimators(task))

        estimators = _estimators_for_task()
        if estimators:
            estimator_var.set(estimators[0])

        ctk.CTkLabel(body, text="Nazwa techniczna").grid(
            row=0, column=0, sticky="w", padx=12, pady=8
        )
        ctk.CTkEntry(body, textvariable=name_var).grid(
            row=0, column=1, sticky="ew", padx=12, pady=8
        )
        ctk.CTkLabel(body, text="Nazwa na ekranie").grid(
            row=1, column=0, sticky="w", padx=12, pady=8
        )
        ctk.CTkEntry(body, textvariable=label_var).grid(
            row=1, column=1, sticky="ew", padx=12, pady=8
        )
        ctk.CTkLabel(body, text="Zadanie").grid(row=2, column=0, sticky="w", padx=12, pady=8)
        task_menu = ctk.CTkOptionMenu(body, values=list(task_labels.values()), variable=task_var)
        task_menu.grid(row=2, column=1, sticky="ew", padx=12, pady=8)
        ctk.CTkLabel(body, text="Estymator sklearn").grid(
            row=3, column=0, sticky="w", padx=12, pady=8
        )
        estimator_menu = ctk.CTkOptionMenu(body, values=estimators, variable=estimator_var)
        estimator_menu.grid(row=3, column=1, sticky="ew", padx=12, pady=8)
        ctk.CTkLabel(body, text="Skalowanie").grid(row=4, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkOptionMenu(
            body,
            values=["auto", "none", "standard", "robust"],
            variable=scaler_var,
        ).grid(row=4, column=1, sticky="w", padx=12, pady=8)

        ctk.CTkLabel(body, text="Parametry JSON").grid(
            row=5, column=0, sticky="nw", padx=12, pady=8
        )
        params_box = ctk.CTkTextbox(body, height=170)
        params_box.grid(row=5, column=1, sticky="nsew", padx=12, pady=8)
        params_box.insert("1.0", '{\n  "random_state": 42\n}')

        info = (
            "Wybierz estymator sklearn pasujący do zadania. Po zapisie model pojawi się "
            "na liście i będzie trenowany razem z innymi modelami."
        )
        ctk.CTkLabel(body, text=info, text_color="#a7b0ba", justify="left", wraplength=620).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 8)
        )

        def _task_changed(_value=None):
            values = _estimators_for_task()
            estimator_menu.configure(values=values)
            if values:
                estimator_var.set(values[0])

        task_menu.configure(command=_task_changed)

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)

        def _save():
            try:
                params = parse_params_json(params_box.get("1.0", "end"))
                config = save_custom_model_config(
                    name=name_var.get(),
                    task=task_by_label[task_var.get()],
                    label=label_var.get(),
                    estimator=estimator_var.get(),
                    params=params,
                    scaler=scaler_var.get(),
                )
                self.log(f"Zapisano własny model ML: {config.name}")
                dialog.destroy()
                self._reload_ml_models()
            except Exception as exc:
                messagebox.showerror("Błąd modelu", str(exc), parent=dialog)

        ctk.CTkButton(footer, text="Anuluj", width=120, command=dialog.destroy).grid(
            row=0, column=1, padx=6, pady=4
        )
        ctk.CTkButton(footer, text="Zapisz model", width=150, command=_save).grid(
            row=0, column=2, padx=6, pady=4
        )

    def _open_custom_model_dialog_v2(self):
        task_labels = {
            "quality": "Jakość / regresja",
            "delay": "Opóźnienie / regresja",
            "schedule": "Harmonogram / klasyfikacja",
        }
        task_by_label = {value: key for key, value in task_labels.items()}
        presets = {
            "RandomForest: najprostszy start": {
                "task": "quality",
                "name": "Custom_RandomForest",
                "estimator": "sklearn.ensemble.RandomForestRegressor",
                "scaler": "none",
                "params": '{\n  "n_estimators": 300,\n  "min_samples_leaf": 2,\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "note": "Dobry pierwszy model do jakości. Stabilny, odporny i nie wymaga skalowania.",
            },
            "ExtraTrees: szybki model": {
                "task": "delay",
                "name": "Custom_ExtraTrees",
                "estimator": "sklearn.ensemble.ExtraTreesRegressor",
                "scaler": "none",
                "params": '{\n  "n_estimators": 400,\n  "max_features": 0.9,\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "note": "Dobry do opóźnień i danych z szumem. Mocniej losuje podziały niż RandomForest.",
            },
            "GradientBoosting: dokładniejsze poprawki": {
                "task": "quality",
                "name": "Custom_GradientBoost",
                "estimator": "sklearn.ensemble.GradientBoostingRegressor",
                "scaler": "none",
                "params": '{\n  "n_estimators": 220,\n  "learning_rate": 0.045,\n  "max_depth": 3,\n  "random_state": 42\n}',
                "note": "Model uczy się seriami: każdy kolejny etap poprawia błąd poprzedniego.",
            },
            "LogisticRegression: harmonogram": {
                "task": "schedule",
                "name": "Custom_LogisticSchedule",
                "estimator": "sklearn.linear_model.LogisticRegression",
                "scaler": "standard",
                "params": '{\n  "max_iter": 1200,\n  "class_weight": "balanced",\n  "random_state": 42\n}',
                "note": "Czytelny model klasyfikacyjny do wyboru strategii harmonogramowania.",
            },
            "SVR: margines dla regresji": {
                "task": "quality",
                "name": "Custom_SVR",
                "estimator": "sklearn.svm.SVR",
                "scaler": "robust",
                "params": '{\n  "C": 12.0,\n  "epsilon": 0.08,\n  "gamma": "scale"\n}',
                "note": "SVM/SVR działa dobrze przy mniejszych danych i wymaga skalowania.",
            },
            "KNN: podobne przypadki": {
                "task": "delay",
                "name": "Custom_KNN",
                "estimator": "sklearn.neighbors.KNeighborsRegressor",
                "scaler": "robust",
                "params": '{\n  "n_neighbors": 9,\n  "weights": "distance"\n}',
                "note": "KNN porównuje nowe zlecenie do podobnych historycznych przypadków.",
            },
            "Ridge: prosty baseline": {
                "task": "quality",
                "name": "Custom_Ridge",
                "estimator": "sklearn.linear_model.Ridge",
                "scaler": "standard",
                "params": '{\n  "alpha": 1.4\n}',
                "note": "Prosty model liniowy jako punkt odniesienia dla bardziej złożonych modeli.",
            },
            "HistGradient: większe dane": {
                "task": "delay",
                "name": "Custom_HistGradient",
                "estimator": "sklearn.ensemble.HistGradientBoostingRegressor",
                "scaler": "none",
                "params": '{\n  "max_iter": 260,\n  "learning_rate": 0.045,\n  "l2_regularization": 0.04,\n  "random_state": 42\n}',
                "note": "Boosting histogramowy do większych danych i nieliniowych zależności.",
            },
            "RandomForestClassifier: klasy": {
                "task": "schedule",
                "name": "Custom_RandomForestSchedule",
                "estimator": "sklearn.ensemble.RandomForestClassifier",
                "scaler": "none",
                "params": '{\n  "n_estimators": 300,\n  "class_weight": "balanced_subsample",\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "note": "Klasyfikator drzewiasty do harmonogramu i wyboru strategii.",
            },
        }

        dialog = ctk.CTkToplevel(self)
        dialog.title("Guide: własny model sklearn")
        dialog.geometry("1120x700")
        dialog.minsize(960, 620)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(14, 8))
        ctk.CTkLabel(
            header,
            text="Guide: własny model sklearn",
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Wybierz przykład albo ustaw model samodzielnie. Środek okna ma suwak, a przyciski zapisu zostają na dole.",
            text_color="#a7b0ba",
            font=("Segoe UI", 13),
        ).pack(anchor="w", pady=(3, 0))

        body = ctk.CTkScrollableFrame(dialog)
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 12))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        form = ctk.CTkFrame(body)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        form.grid_columnconfigure(1, weight=1)
        guide = ctk.CTkFrame(body)
        guide.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        guide.grid_columnconfigure(0, weight=1)

        name_var = ctk.StringVar(value="Custom_RandomForest")
        label_var = ctk.StringVar(value="Mój model ML")
        task_var = ctk.StringVar(value=task_labels["quality"])
        scaler_var = ctk.StringVar(value="none")
        estimator_var = ctk.StringVar(value="sklearn.ensemble.RandomForestRegressor")
        note_var = ctk.StringVar(value=presets["RandomForest: najprostszy start"]["note"])

        def _estimators_for_task() -> list[str]:
            task = task_by_label[task_var.get()]
            values = list(available_sklearn_estimators(task))
            current = estimator_var.get()
            if current and current not in values:
                values.insert(0, current)
            return values

        def _set_params(text: str) -> None:
            params_box.delete("1.0", "end")
            params_box.insert("1.0", text)

        def _logic_text() -> str:
            task = task_by_label[task_var.get()]
            estimator = estimator_var.get().split(".")[-1] or "model"
            scaler = scaler_var.get()
            if task in {"quality", "delay"}:
                target = "jakość produktu" if task == "quality" else "opóźnienie produkcji"
                metric = "RMSE / MAE / R²"
                output = "liczbę"
            else:
                target = "strategię harmonogramowania"
                metric = "accuracy / precision / recall"
                output = "klasę"
            return (
                "LOGIKA MODELU\n"
                "================\n"
                "1. Aplikacja bierze dane produkcji i robi cechy X.\n"
                f"2. Celem y jest: {target}.\n"
                "3. Braki liczbowe są uzupełniane medianą.\n"
                f"4. Skalowanie: {scaler}.\n"
                f"5. Trening: {estimator}.fit(X, y).\n"
                f"6. Predykcja: model.predict(X_new) zwraca {output}.\n"
                f"7. Ocena po treningu: {metric}.\n\n"
                "WZORY\n"
                "ŷ = model(X)\n"
                "błąd = y - ŷ\n"
                "RandomForest/ExtraTrees: ŷ = średnia z wielu drzew\n"
                "Boosting: F_m(x) = F_{m-1}(x) + learning_rate * h_m(x)\n"
                "Klasyfikacja: klasa = argmax(P(klasa | X))\n\n"
                "JAK WYBRAĆ\n"
                "Drzewa: dobry start, mało ustawiania.\n"
                "Boosting: często dokładniejszy, ale bardziej wrażliwy.\n"
                "SVM/SVR: granica z marginesem, użyj skalowania.\n"
                "KNN: podobne historyczne przypadki, użyj skalowania.\n"
                "Ridge/Linear: szybki punkt odniesienia.\n"
                "Logistic/RandomForestClassifier: harmonogram i klasy."
            )

        def _refresh_logic() -> None:
            logic_box.configure(state="normal")
            logic_box.delete("1.0", "end")
            logic_box.insert("1.0", _logic_text())
            logic_box.configure(state="disabled")

        def _apply_preset(name: str) -> None:
            preset = presets[name]
            task_var.set(task_labels[preset["task"]])
            name_var.set(preset["name"])
            label_var.set("Mój model ML")
            scaler_var.set(preset["scaler"])
            estimator_var.set(preset["estimator"])
            note_var.set(preset["note"])
            estimator_menu.configure(values=_estimators_for_task())
            _set_params(preset["params"])
            _refresh_logic()

        ctk.CTkLabel(form, text="1. Wybierz przykład", font=("Segoe UI", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 8)
        )
        preset_frame = ctk.CTkFrame(form, fg_color="transparent")
        preset_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        preset_frame.grid_columnconfigure((0, 1, 2), weight=1)
        for index, preset_name in enumerate(presets):
            ctk.CTkButton(
                preset_frame,
                text=preset_name,
                height=36,
                command=lambda value=preset_name: _apply_preset(value),
            ).grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
        ctk.CTkLabel(
            form,
            textvariable=note_var,
            text_color="#cbd5e1",
            justify="left",
            wraplength=640,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14))

        labels = [
            ("2. Nazwij model", None),
            ("Nazwa techniczna", name_var),
            ("Nazwa na ekranie", label_var),
            ("3. Wybierz zadanie", None),
            ("Zadanie", task_var),
            ("4. Wybierz bibliotekę", None),
            ("Estymator sklearn", estimator_var),
            ("Skalowanie", scaler_var),
        ]
        row = 3
        for text, var in labels:
            if var is None:
                ctk.CTkLabel(form, text=text, font=("Segoe UI", 17, "bold")).grid(
                    row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6)
                )
            elif text == "Zadanie":
                ctk.CTkLabel(form, text=text).grid(row=row, column=0, sticky="w", padx=16, pady=6)
                task_menu = ctk.CTkOptionMenu(form, values=list(task_labels.values()), variable=task_var)
                task_menu.grid(row=row, column=1, sticky="ew", padx=16, pady=6)
            elif text == "Estymator sklearn":
                ctk.CTkLabel(form, text=text).grid(row=row, column=0, sticky="w", padx=16, pady=6)
                estimator_menu = ctk.CTkOptionMenu(
                    form,
                    values=_estimators_for_task(),
                    variable=estimator_var,
                    width=560,
                    command=lambda _value: _refresh_logic(),
                )
                estimator_menu.grid(row=row, column=1, sticky="ew", padx=16, pady=6)
            elif text == "Skalowanie":
                ctk.CTkLabel(form, text=text).grid(row=row, column=0, sticky="w", padx=16, pady=6)
                ctk.CTkOptionMenu(
                    form,
                    values=["auto", "none", "standard", "robust"],
                    variable=scaler_var,
                    command=lambda _value: _refresh_logic(),
                ).grid(row=row, column=1, sticky="w", padx=16, pady=6)
            else:
                ctk.CTkLabel(form, text=text).grid(row=row, column=0, sticky="w", padx=16, pady=6)
                ctk.CTkEntry(form, textvariable=var).grid(row=row, column=1, sticky="ew", padx=16, pady=6)
            row += 1

        ctk.CTkLabel(
            form,
            text="Nazwa na ekranie może zostać jako: Mój model ML. Nazwa techniczna służy do zapisu w pliku.",
            text_color="#94a3b8",
            justify="left",
            wraplength=640,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))
        row += 1
        ctk.CTkLabel(
            form,
            text=(
                "Zadanie to cel predykcji aplikacji: jakość, opóźnienie albo harmonogram. "
                "SVM, KNN, Ridge, lasy i boosting wybierasz niżej jako estymator sklearn."
            ),
            text_color="#bfdbfe",
            justify="left",
            wraplength=640,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))
        row += 1
        ctk.CTkLabel(form, text="5. Parametry JSON", font=("Segoe UI", 17, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6)
        )
        row += 1
        params_box = ctk.CTkTextbox(form, height=165)
        params_box.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=6)
        params_box.insert("1.0", presets["RandomForest: najprostszy start"]["params"])
        row += 1
        ctk.CTkLabel(
            form,
            text='Jeśli nie wiesz co wpisać, nie zmieniaj JSON. Przykład: {"n_estimators": 300, "random_state": 42}.',
            text_color="#94a3b8",
            justify="left",
            wraplength=640,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))

        def _show_step_by_step() -> None:
            tutorial = ctk.CTkToplevel(dialog)
            tutorial.title("Jak dodać własny model krok po kroku")
            tutorial.geometry("760x640")
            tutorial.transient(dialog)
            tutorial.grab_set()
            tutorial.grid_columnconfigure(0, weight=1)
            tutorial.grid_rowconfigure(1, weight=1)
            ctk.CTkLabel(
                tutorial,
                text="Jak dodać własny model krok po kroku",
                font=("Segoe UI", 22, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))
            text = ctk.CTkTextbox(tutorial, wrap="word")
            text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
            text.insert(
                "1.0",
                (
                    "1. Wybierz gotowy przykład.\n"
                    "   Najbezpieczniej zacząć od RandomForest. To model drzewiasty, który zwykle działa dobrze bez strojenia.\n\n"
                    "2. Zostaw nazwę na ekranie jako 'Mój model ML'.\n"
                    "   To jest tylko etykieta widoczna w Main. Nazwa techniczna zapisuje się w pliku JSON.\n\n"
                    "3. Wybierz zadanie.\n"
                    "   Jakość i opóźnienie są regresją, czyli model przewiduje liczbę. Harmonogram jest klasyfikacją, czyli model wybiera klasę/strategię.\n\n"
                    "4. Wybierz estymator sklearn.\n"
                    "   RandomForest/ExtraTrees są dobre na start. SVR i KNN wymagają skalowania. Ridge jest prostym baseline. LogisticRegression i RandomForestClassifier są do klas.\n\n"
                    "5. Zostaw JSON, jeśli nie wiesz co zmienić.\n"
                    "   Parametry JSON są przekazywane bezpośrednio do sklearn, np. n_estimators, max_depth, learning_rate, C albo n_neighbors.\n\n"
                    "6. Kliknij 'Zapisz model'.\n"
                    "   Aplikacja zapisze konfigurację do models/custom_ml_models.json i odświeży listę modeli.\n\n"
                    "7. Zaznacz nowy model w Main i uruchom trening.\n"
                    "   Po treningu model trafi do paczki .pkl razem z metrykami i będzie można używać go w Results oraz Visual.\n\n"
                    "Co dzieje się technicznie:\n"
                    "Dane -> cechy X -> uzupełnienie braków -> opcjonalne skalowanie -> estimator.fit(X, y) -> zapis modelu."
                ),
            )
            text.configure(state="disabled")
            ctk.CTkButton(tutorial, text="Zamknij", command=tutorial.destroy).grid(
                row=2, column=0, sticky="e", padx=18, pady=(0, 16)
            )

        ctk.CTkLabel(guide, text="Jak to zrobić bez wiedzy ML", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )
        ctk.CTkButton(
            guide,
            text="Instrukcja krok po kroku",
            command=_show_step_by_step,
            height=34,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        ctk.CTkLabel(
            guide,
            text=(
                "Najprostsza ścieżka:\n"
                "1. Kliknij RandomForest.\n"
                "2. Zostaw nazwę: Mój model ML.\n"
                "3. Zostaw JSON bez zmian.\n"
                "4. Kliknij Zapisz model.\n"
                "5. Zaznacz model na liście i uruchom trening.\n\n"
                "Kiedy zmieniać preset:\n"
                "- ExtraTrees: szybciej i dobrze przy szumie.\n"
                "- GradientBoosting: dokładniej, ale wrażliwiej.\n"
                "- LogisticRegression: harmonogram/klasy."
            ),
            justify="left",
            text_color="#dbeafe",
            wraplength=390,
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

        ctk.CTkLabel(guide, text="Parametry po ludzku", font=("Segoe UI", 16, "bold")).grid(
            row=3, column=0, sticky="w", padx=16, pady=(8, 6)
        )
        ctk.CTkLabel(
            guide,
            text=(
                "n_estimators - ile drzew/modeli zbudować.\n"
                "learning_rate - jak ostro boosting poprawia błędy.\n"
                "max_depth - jak szczegółowe może być drzewo.\n"
                "min_samples_leaf - hamulec przed przeuczeniem.\n"
                "random_state - powtarzalny wynik.\n"
                "class_weight='balanced' - pomoc przy nierównych klasach."
            ),
            justify="left",
            text_color="#cbd5e1",
            wraplength=390,
        ).grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))

        ctk.CTkLabel(guide, text="Logika i wzory", font=("Segoe UI", 16, "bold")).grid(
            row=5, column=0, sticky="w", padx=16, pady=(8, 6)
        )
        logic_box = ctk.CTkTextbox(guide, height=270, wrap="word")
        logic_box.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 16))

        def _task_changed(_value=None):
            values = _estimators_for_task()
            estimator_menu.configure(values=values)
            if values:
                estimator_var.set(values[0])
            _refresh_logic()

        task_menu.configure(command=_task_changed)
        _refresh_logic()

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text="Konfiguracja zostanie zapisana do: models/custom_ml_models.json",
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w", padx=4)

        def _save():
            try:
                params = parse_params_json(params_box.get("1.0", "end"))
                config = save_custom_model_config(
                    name=name_var.get(),
                    task=task_by_label[task_var.get()],
                    label=label_var.get(),
                    estimator=estimator_var.get(),
                    params=params,
                    scaler=scaler_var.get(),
                )
                self.log(f"Zapisano własny model ML: {config.name}")
                dialog.destroy()
                self._reload_ml_models()
            except Exception as exc:
                messagebox.showerror("Błąd modelu", str(exc), parent=dialog)

        ctk.CTkButton(footer, text="Anuluj", width=130, command=dialog.destroy).grid(
            row=0, column=1, padx=6, pady=4
        )
        ctk.CTkButton(footer, text="Zapisz model", width=170, command=_save).grid(
            row=0, column=2, padx=6, pady=4
        )

    def _open_custom_model_dialog_v3(self):
        task_labels = {
            "quality": "Jakość / regresja",
            "delay": "Opóźnienie / regresja",
            "schedule": "Harmonogram / klasyfikacja",
        }
        task_by_label = {value: key for key, value in task_labels.items()}
        presets = {
            "RandomForest": (
                "quality",
                "Custom_RandomForest",
                "sklearn.ensemble.RandomForestRegressor",
                "none",
                '{\n  "n_estimators": 300,\n  "min_samples_leaf": 2,\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "Najbezpieczniejszy start. Las drzew dobrze działa bez strojenia i zwykle nie wymaga skalowania.",
            ),
            "ExtraTrees": (
                "delay",
                "Custom_ExtraTrees",
                "sklearn.ensemble.ExtraTreesRegressor",
                "none",
                '{\n  "n_estimators": 400,\n  "max_features": 0.9,\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "Szybki model drzewiasty. Dobre do opóźnień i danych z szumem, bo mocniej losuje progi podziałów.",
            ),
            "GradientBoosting": (
                "quality",
                "Custom_GradientBoost",
                "sklearn.ensemble.GradientBoostingRegressor",
                "none",
                '{\n  "n_estimators": 220,\n  "learning_rate": 0.045,\n  "max_depth": 3,\n  "random_state": 42\n}',
                "Dokładniejszy model sekwencyjny. Każde kolejne drzewo poprawia błąd poprzedniego wyniku.",
            ),
            "HistGradient": (
                "delay",
                "Custom_HistGradient",
                "sklearn.ensemble.HistGradientBoostingRegressor",
                "none",
                '{\n  "max_iter": 260,\n  "learning_rate": 0.045,\n  "l2_regularization": 0.04,\n  "random_state": 42\n}',
                "Szybsza wersja boostingu. Dzieli wartości na koszyki histogramowe, więc dobrze działa na większych danych.",
            ),
            "SVR / SVM": (
                "quality",
                "Custom_SVR",
                "sklearn.svm.SVR",
                "robust",
                '{\n  "C": 12.0,\n  "epsilon": 0.08,\n  "gamma": "scale"\n}',
                "SVM/SVR szuka stabilnej granicy z marginesem. Dobre do mniejszych danych, ale wymaga skalowania.",
            ),
            "KNN": (
                "delay",
                "Custom_KNN",
                "sklearn.neighbors.KNeighborsRegressor",
                "robust",
                '{\n  "n_neighbors": 9,\n  "weights": "distance"\n}',
                "Model podobieństwa. Patrzy na najbliższe historyczne rekordy, więc wymaga skalowania cech.",
            ),
            "Ridge": (
                "quality",
                "Custom_Ridge",
                "sklearn.linear_model.Ridge",
                "standard",
                '{\n  "alpha": 1.4\n}',
                "Prosty baseline liniowy. Warto go sprawdzić, żeby wiedzieć, czy bardziej złożone modele faktycznie pomagają.",
            ),
            "LinearRegression": (
                "quality",
                "Custom_LinearRegression",
                "sklearn.linear_model.LinearRegression",
                "standard",
                "{}",
                "Najprostsza regresja liniowa. Dobry punkt odniesienia dla jakości lub opóźnień.",
            ),
            "Polynomial Ridge": (
                "quality",
                "Custom_PolynomialKernel",
                "sklearn.kernel_ridge.KernelRidge",
                "standard",
                '{\n  "alpha": 1.0,\n  "kernel": "polynomial",\n  "degree": 2\n}',
                "Regresja nieliniowa podobna do polynomial regression przez kernel wielomianowy.",
            ),
            "Lasso": (
                "quality",
                "Custom_Lasso",
                "sklearn.linear_model.Lasso",
                "standard",
                '{\n  "alpha": 0.01,\n  "max_iter": 5000,\n  "random_state": 42\n}',
                "Regresja liniowa, która potrafi wyciszać mniej ważne cechy przez karę L1.",
            ),
            "DecisionTree": (
                "delay",
                "Custom_DecisionTree",
                "sklearn.tree.DecisionTreeRegressor",
                "none",
                '{\n  "max_depth": 10,\n  "min_samples_leaf": 2,\n  "random_state": 42\n}',
                "Pojedyncze drzewo decyzyjne. Bardzo czytelne, ale łatwiej się przeucza niż las.",
            ),
            "MLP Neural Net": (
                "quality",
                "Custom_MLPRegressor",
                "sklearn.neural_network.MLPRegressor",
                "standard",
                '{\n  "hidden_layer_sizes": [64, 32],\n  "max_iter": 800,\n  "random_state": 42\n}',
                "Sieć neuronowa sklearn. Wymaga skalowania i zwykle większej ostrożności przy parametrach.",
            ),
            "LogisticRegression": (
                "schedule",
                "Custom_LogisticSchedule",
                "sklearn.linear_model.LogisticRegression",
                "standard",
                '{\n  "max_iter": 1200,\n  "class_weight": "balanced",\n  "random_state": 42\n}',
                "Model do harmonogramu/klas. Liczy prawdopodobieństwa strategii i wybiera najbardziej prawdopodobną.",
            ),
            "SVC / SVM Classifier": (
                "schedule",
                "Custom_SVC",
                "sklearn.svm.SVC",
                "standard",
                '{\n  "C": 2.0,\n  "gamma": "scale",\n  "probability": true,\n  "random_state": 42\n}',
                "SVM do klasyfikacji harmonogramu. Wymaga skalowania i dobrze działa przy mniejszych danych.",
            ),
            "KNN Classifier": (
                "schedule",
                "Custom_KNNClassifier",
                "sklearn.neighbors.KNeighborsClassifier",
                "standard",
                '{\n  "n_neighbors": 7,\n  "weights": "distance"\n}',
                "Klasyfikacja przez podobne przypadki historyczne. Wymaga skalowania.",
            ),
            "Naive Bayes": (
                "schedule",
                "Custom_NaiveBayes",
                "sklearn.naive_bayes.GaussianNB",
                "none",
                "{}",
                "Prosty probabilistyczny klasyfikator. Dobry szybki baseline dla klas.",
            ),
            "MLP Classifier": (
                "schedule",
                "Custom_MLPClassifier",
                "sklearn.neural_network.MLPClassifier",
                "standard",
                '{\n  "hidden_layer_sizes": [64, 32],\n  "max_iter": 800,\n  "random_state": 42\n}',
                "Sieć neuronowa do klasyfikacji. Wymaga skalowania i kontroli przeuczenia.",
            ),
            "RandomForestClassifier": (
                "schedule",
                "Custom_RandomForestSchedule",
                "sklearn.ensemble.RandomForestClassifier",
                "none",
                '{\n  "n_estimators": 300,\n  "class_weight": "balanced_subsample",\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "Drzewiasty klasyfikator do harmonogramu. Dobry, gdy decyzja zależy od nieliniowych relacji w danych.",
            ),
            "XGBoost Regressor": (
                "quality",
                "Custom_XGBoostRegressor",
                "xgboost.XGBRegressor",
                "none",
                '{\n  "n_estimators": 300,\n  "learning_rate": 0.05,\n  "max_depth": 4,\n  "subsample": 0.9,\n  "colsample_bytree": 0.9,\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "XGBoost jest świadomie dopuszczoną opcją eksperymentalną. Mocny boosting drzew do regresji, wymaga zainstalowanego pakietu xgboost.",
            ),
            "XGBoost Classifier": (
                "schedule",
                "Custom_XGBoostClassifier",
                "xgboost.XGBClassifier",
                "none",
                '{\n  "n_estimators": 300,\n  "learning_rate": 0.05,\n  "max_depth": 4,\n  "subsample": 0.9,\n  "colsample_bytree": 0.9,\n  "eval_metric": "mlogloss",\n  "random_state": 42,\n  "n_jobs": -1\n}',
                "XGBoost do klasyfikacji harmonogramu. Dobry przy nieliniowych zależnościach, ale wymaga pakietu xgboost.",
            ),
        }

        dialog = ctk.CTkToplevel(self)
        dialog.title("Guide: własny model sklearn")
        dialog.geometry("1160x720")
        dialog.minsize(980, 640)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(14, 8))
        ctk.CTkLabel(header, text="Guide: własny model sklearn", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Nie wybierasz tu nowego celu aplikacji, tylko algorytm sklearn do celu: jakość, opóźnienie albo harmonogram.",
            text_color="#a7b0ba",
            font=("Segoe UI", 13),
        ).pack(anchor="w", pady=(3, 0))

        body = ctk.CTkScrollableFrame(dialog)
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 12))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        form = ctk.CTkFrame(body)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        form.grid_columnconfigure(1, weight=1)
        guide = ctk.CTkFrame(body)
        guide.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        guide.grid_columnconfigure(0, weight=1)

        name_var = ctk.StringVar(value="Custom_RandomForest")
        label_var = ctk.StringVar(value="Mój model ML")
        task_var = ctk.StringVar(value=task_labels["quality"])
        scaler_var = ctk.StringVar(value="none")
        estimator_var = ctk.StringVar(value="sklearn.ensemble.RandomForestRegressor")
        note_var = ctk.StringVar(value=presets["RandomForest"][5])

        def _set_params(text: str) -> None:
            params_box.delete("1.0", "end")
            params_box.insert("1.0", text)

        def _refresh_logic() -> None:
            task = task_by_label[task_var.get()]
            estimator = estimator_var.get().split(".")[-1] or "model"
            if task == "schedule":
                target = "strategia harmonogramowania"
                metrics = "accuracy, precision, recall"
                pred = "klasa = argmax(P(klasa | X))"
            else:
                target = "jakość produktu" if task == "quality" else "opóźnienie produkcji"
                metrics = "RMSE, MAE, R²"
                pred = "ŷ = model(X)"
            text = (
                f"Cel y: {target}\n"
                f"Pipeline: X -> uzupełnienie braków medianą -> skalowanie: {scaler_var.get()} -> {estimator}\n"
                f"Predykcja: {pred}\n"
                f"Metryki: {metrics}\n\n"
                "Wzory algorytmów:\n"
                "RandomForest/ExtraTrees: ŷ = mean(tree_i(x)) albo głosowanie klas.\n"
                "GradientBoosting/HistGradient: F_m(x)=F_{m-1}(x)+η·h_m(x).\n"
                "SVR/SVM: minimalizuje błąd z marginesem epsilon i karą C.\n"
                "KNN: ŷ = średnia ważona najbliższych sąsiadów.\n"
                "Ridge: min ||y-Xw||² + alpha·||w||².\n"
                "LogisticRegression: P(class|X)=softmax(Xw+b)."
            )
            logic_box.configure(state="normal")
            logic_box.delete("1.0", "end")
            logic_box.insert("1.0", text)
            logic_box.configure(state="disabled")

        def _apply_preset(preset_name: str) -> None:
            task, name, estimator, scaler, params, note = presets[preset_name]
            task_var.set(task_labels[task])
            name_var.set(name)
            label_var.set("Mój model ML")
            estimator_var.set(estimator)
            scaler_var.set(scaler)
            note_var.set(note)
            _set_params(params)
            _refresh_logic()

        def _show_estimator_list() -> None:
            task = task_by_label[task_var.get()]
            values = available_sklearn_estimators(task)
            picker = ctk.CTkToplevel(dialog)
            picker.title("Lista estymatorów sklearn / xgboost")
            picker.geometry("1180x720")
            picker.minsize(980, 620)
            picker.transient(dialog)
            picker.grab_set()
            picker.grid_columnconfigure(0, weight=2)
            picker.grid_columnconfigure(1, weight=2)
            picker.grid_rowconfigure(2, weight=1)
            selected_estimator = ctk.StringVar(value=values[0] if values else "")
            ctk.CTkLabel(
                picker,
                text="Wybierz estymator sklearn / xgboost",
                font=("Segoe UI", 22, "bold"),
            ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 4))
            ctk.CTkLabel(
                picker,
                text="Kliknij pozycję, żeby zobaczyć co robi, czego potrzebuje i kiedy warto jej użyć. Dopiero potem wybierz 'Użyj wybranego'.",
                text_color="#a7b0ba",
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))
            task_mode = "klasyfikatory" if task == "schedule" else "regresory"
            ctk.CTkLabel(
                picker,
                text=f"Aktywne zadanie: {task_var.get()} | pokazuje tylko {task_mode}.",
                text_color="#bfdbfe",
                font=("Segoe UI", 12, "bold"),
            ).grid(row=1, column=1, sticky="e", padx=18, pady=(0, 10))
            list_box = ctk.CTkScrollableFrame(picker)
            list_box.grid(row=2, column=0, sticky="nsew", padx=(18, 8), pady=(0, 12))
            list_box.grid_columnconfigure(0, weight=1)

            details = ctk.CTkTextbox(picker, wrap="word")
            details.grid(row=2, column=1, sticky="nsew", padx=(8, 18), pady=(0, 12))

            def _estimator_info(path: str) -> str:
                name = path.split(".")[-1]
                lower = name.lower()
                task_name = "klasyfikacja" if task == "schedule" else "regresja"
                needs_scaling = any(key in lower for key in ["sv", "knn", "ridge", "lasso", "elastic", "linear", "logistic", "sgd", "perceptron", "kernel"])
                if path.startswith("xgboost.") or "xgb" in lower:
                    idea = "XGBoost buduje kolejne drzewa, które poprawiają błędy poprzednich drzew. To mocny boosting gradientowy z regularyzacją."
                    recommended = "Gdy RandomForest/ExtraTrees są za słabe i chcesz dokładniej złapać nieliniowe zależności. To opcja eksperymentalna, wymaga pakietu xgboost."
                    params = "n_estimators, learning_rate, max_depth, subsample, colsample_bytree, reg_lambda, random_state, n_jobs"
                elif "randomforest" in lower:
                    idea = "Wiele drzew decyzyjnych. Każde drzewo uczy się trochę inaczej, a wynik jest uśredniany albo głosowany."
                    recommended = "Dobry pierwszy wybór, gdy nie wiesz od czego zacząć. Działa dobrze na nieliniowych danych i zwykle nie wymaga skalowania."
                    params = "n_estimators, max_depth, min_samples_leaf, max_features, random_state, n_jobs"
                elif "extratrees" in lower:
                    idea = "Las bardzo losowych drzew. Losuje progi podziału mocniej niż RandomForest."
                    recommended = "Dobre przy szumie, szybkie testowanie i opóźnienia. Zwykle bez skalowania."
                    params = "n_estimators, max_depth, min_samples_leaf, max_features, random_state, n_jobs"
                elif "gradientboost" in lower or "histgradient" in lower or "adaboost" in lower:
                    idea = "Boosting: kolejne modele poprawiają błędy poprzednich. HistGradient używa koszyków histogramowych."
                    recommended = "Gdy prosty las jest za mało dokładny. Warto pilnować learning_rate i przeuczenia."
                    params = "n_estimators/max_iter, learning_rate, max_depth, min_samples_leaf, l2_regularization, random_state"
                elif "sv" in lower:
                    idea = "SVM/SVR szuka stabilnej granicy z marginesem. W regresji SVR toleruje błąd epsilon."
                    recommended = "Dobre przy mniejszych danych i nieliniowych relacjach. Wymaga skalowania standard albo robust."
                    params = "C, epsilon, gamma, kernel"
                elif "kneighbors" in lower or "radiusneighbors" in lower:
                    idea = "KNN przewiduje na podstawie podobnych rekordów historycznych."
                    recommended = "Dobre do prostego testu podobieństwa. Wymaga skalowania, bo używa odległości."
                    params = "n_neighbors, weights, metric, p"
                elif "ridge" in lower or "lasso" in lower or "elastic" in lower or "linear" in lower:
                    idea = "Model liniowy: uczy wagi cech i składa wynik jako kombinację cech."
                    recommended = "Dobry baseline i szybki test, czy zależność jest prosta/liniowa. Najlepiej ze skalowaniem."
                    params = "alpha, fit_intercept, max_iter, tol"
                elif "logistic" in lower:
                    idea = "Klasyfikator liniowy. Liczy prawdopodobieństwa klas przez funkcję logistic/softmax."
                    recommended = "Do harmonogramu i klas, gdy chcesz prosty oraz interpretowalny model. Wymaga skalowania."
                    params = "C, penalty, max_iter, class_weight, random_state"
                elif "dummy" in lower:
                    idea = "Model kontrolny. Udaje prostą strategię, np. średnią albo najczęstszą klasę."
                    recommended = "Użyj tylko jako punkt odniesienia: prawdziwy model powinien go pobić."
                    params = "strategy"
                elif "gaussianprocess" in lower:
                    idea = "Model probabilistyczny. Oprócz predykcji może opisywać niepewność."
                    recommended = "Raczej do mniejszych danych; może być wolny. Wymaga ostrożności i często skalowania."
                    params = "kernel, alpha, normalize_y, random_state"
                else:
                    idea = "Estymator sklearn zgodny z metodami fit(X, y) i predict(X)."
                    recommended = "Wybierz, jeśli wiesz, że pasuje do Twojego celu albo chcesz eksperymentować."
                    params = "Sprawdź dokumentację klasy; najczęściej random_state, max_iter, alpha/C albo parametry modelu."
                scaling = "Tak, ustaw standard albo robust." if needs_scaling else "Zwykle nie, auto/none wystarczy dla modeli drzewiastych."
                return (
                    f"{path}\n\n"
                    f"Typ zadania: {task_name}\n\n"
                    f"Na czym polega:\n{idea}\n\n"
                    f"Kiedy polecane:\n{recommended}\n\n"
                    f"Czego potrzebuje:\n"
                    "- X: tabela cech liczbowych po przygotowaniu danych.\n"
                    "- y: cel, czyli jakość/opóźnienie albo klasa harmonogramu.\n"
                    "- Braki danych: aplikacja uzupełnia medianą.\n"
                    f"- Skalowanie: {scaling}\n\n"
                    f"Typowe parametry JSON:\n{params}\n\n"
                    "Co się stanie po zapisie:\n"
                    "Aplikacja utworzy klasę sklearn, przekaże parametry JSON, uruchomi estimator.fit(X, y), policzy metryki i zapisze model .pkl."
                )

            def _show_details(path: str) -> None:
                selected_estimator.set(path)
                details.configure(state="normal")
                details.delete("1.0", "end")
                details.insert("1.0", _estimator_info(path))
                details.configure(state="disabled")

            for row_no, value in enumerate(values):
                ctk.CTkButton(
                    list_box,
                    text=value,
                    anchor="w",
                    fg_color="#111f2d",
                    hover_color="#17324d",
                    command=lambda selected=value: _show_details(selected),
                ).grid(row=row_no, column=0, sticky="ew", padx=6, pady=2)

            if values:
                _show_details(values[0])

            footer = ctk.CTkFrame(picker, fg_color="transparent")
            footer.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))
            footer.grid_columnconfigure(0, weight=1)

            def _use_selected() -> None:
                selected = selected_estimator.get()
                if selected:
                    estimator_var.set(selected)
                    _refresh_logic()
                picker.destroy()

            ctk.CTkLabel(
                footer,
                textvariable=selected_estimator,
                text_color="#bfdbfe",
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=(0, 10))
            ctk.CTkButton(footer, text="Użyj wybranego", command=_use_selected, width=160).grid(
                row=0, column=1, padx=6
            )
            ctk.CTkButton(footer, text="Zamknij", command=picker.destroy, width=120).grid(
                row=0, column=2, padx=6
            )

        ctk.CTkLabel(form, text="1. Wybierz przykład algorytmu", font=("Segoe UI", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 8)
        )
        preset_frame = ctk.CTkFrame(form, fg_color="transparent")
        preset_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        preset_frame.grid_columnconfigure((0, 1, 2), weight=1)
        for index, preset_name in enumerate(presets):
            ctk.CTkButton(
                preset_frame,
                text=preset_name,
                height=34,
                command=lambda value=preset_name: _apply_preset(value),
            ).grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
        ctk.CTkLabel(form, textvariable=note_var, text_color="#cbd5e1", justify="left", wraplength=650).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14)
        )

        ctk.CTkLabel(form, text="2. Cel i nazwa", font=("Segoe UI", 17, "bold")).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 6)
        )
        ctk.CTkLabel(form, text="Zadanie").grid(row=4, column=0, sticky="w", padx=16, pady=6)
        task_menu = ctk.CTkOptionMenu(
            form,
            values=list(task_labels.values()),
            variable=task_var,
            command=lambda _value: _refresh_logic(),
        )
        task_menu.grid(row=4, column=1, sticky="ew", padx=16, pady=6)
        ctk.CTkLabel(
            form,
            text="Zadanie to cel aplikacji: liczba jakości, liczba opóźnienia albo klasa harmonogramu.",
            text_color="#bfdbfe",
            justify="left",
            wraplength=650,
        ).grid(row=5, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 8))
        ctk.CTkLabel(form, text="Nazwa techniczna").grid(row=6, column=0, sticky="w", padx=16, pady=6)
        ctk.CTkEntry(form, textvariable=name_var).grid(row=6, column=1, sticky="ew", padx=16, pady=6)
        ctk.CTkLabel(form, text="Nazwa na ekranie").grid(row=7, column=0, sticky="w", padx=16, pady=6)
        ctk.CTkEntry(form, textvariable=label_var).grid(row=7, column=1, sticky="ew", padx=16, pady=6)

        ctk.CTkLabel(form, text="3. Estymator i parametry", font=("Segoe UI", 17, "bold")).grid(
            row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6)
        )
        ctk.CTkLabel(form, text="Estymator sklearn/xgboost").grid(row=9, column=0, sticky="w", padx=16, pady=6)
        ctk.CTkEntry(form, textvariable=estimator_var).grid(row=9, column=1, sticky="ew", padx=16, pady=6)
        ctk.CTkButton(
            form,
            text="Pokaż listę estymatorów",
            command=_show_estimator_list,
            height=32,
        ).grid(row=10, column=1, sticky="w", padx=16, pady=(0, 8))
        ctk.CTkLabel(form, text="Skalowanie").grid(row=11, column=0, sticky="w", padx=16, pady=6)
        ctk.CTkOptionMenu(
            form,
            values=["auto", "none", "standard", "robust"],
            variable=scaler_var,
            command=lambda _value: _refresh_logic(),
        ).grid(row=11, column=1, sticky="w", padx=16, pady=6)
        ctk.CTkLabel(form, text="Parametry JSON").grid(row=12, column=0, sticky="nw", padx=16, pady=6)
        params_box = ctk.CTkTextbox(form, height=150)
        params_box.grid(row=12, column=1, sticky="ew", padx=16, pady=6)
        params_box.insert("1.0", presets["RandomForest"][4])
        ctk.CTkLabel(
            form,
            text="Parametry JSON to argumenty sklearn, np. n_estimators, max_depth, C, epsilon, n_neighbors, alpha.",
            text_color="#94a3b8",
            justify="left",
            wraplength=650,
        ).grid(row=13, column=1, sticky="ew", padx=16, pady=(0, 14))

        def _show_step_by_step() -> None:
            tutorial = ctk.CTkToplevel(dialog)
            tutorial.title("Jak dodać własny model krok po kroku")
            tutorial.geometry("980x760")
            tutorial.minsize(820, 640)
            tutorial.transient(dialog)
            tutorial.grab_set()
            tutorial.grid_columnconfigure(0, weight=1)
            tutorial.grid_rowconfigure(1, weight=1)
            ctk.CTkLabel(tutorial, text="Jak dodać własny model krok po kroku", font=("Segoe UI", 22, "bold")).grid(
                row=0, column=0, sticky="w", padx=18, pady=(16, 8)
            )
            text = ctk.CTkTextbox(tutorial, wrap="word")
            text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
            text.insert("1.0", self._custom_model_tutorial_text())
            text.configure(state="disabled")
            ctk.CTkButton(tutorial, text="Zamknij", command=tutorial.destroy).grid(
                row=2, column=0, sticky="e", padx=18, pady=(0, 16)
            )

        ctk.CTkLabel(guide, text="Pomoc i wzory", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )
        ctk.CTkButton(guide, text="Instrukcja krok po kroku", command=_show_step_by_step, height=34).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 12)
        )
        help_box = ctk.CTkTextbox(guide, height=300, wrap="word")
        help_box.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        help_box.insert("1.0", self._custom_model_help_text())
        help_box.configure(state="disabled")
        ctk.CTkLabel(guide, text="Aktualna logika", font=("Segoe UI", 16, "bold")).grid(
            row=3, column=0, sticky="w", padx=16, pady=(8, 6)
        )
        logic_box = ctk.CTkTextbox(guide, height=310, wrap="word")
        logic_box.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        _refresh_logic()

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text="Konfiguracja zostanie zapisana do: models/custom_ml_models.json",
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w", padx=4)

        def _save():
            try:
                params = parse_params_json(params_box.get("1.0", "end"))
                config = save_custom_model_config(
                    name=name_var.get(),
                    task=task_by_label[task_var.get()],
                    label=label_var.get(),
                    estimator=estimator_var.get(),
                    params=params,
                    scaler=scaler_var.get(),
                )
                self.log(f"Zapisano własny model ML: {config.name}")
                dialog.destroy()
                self._reload_ml_models()
            except Exception as exc:
                messagebox.showerror("Błąd modelu", str(exc), parent=dialog)

        ctk.CTkButton(footer, text="Anuluj", width=130, command=dialog.destroy).grid(row=0, column=1, padx=6, pady=4)
        ctk.CTkButton(footer, text="Zapisz model", width=170, command=_save).grid(row=0, column=2, padx=6, pady=4)

    @staticmethod
    def _custom_model_help_text() -> str:
        return (
            "Co wybrać na start?\n"
            "RandomForest - pierwszy wybór dla jakości. Stabilny, odporny, zwykle bez skalowania.\n"
            "ExtraTrees - podobny do lasu, ale szybszy i bardziej losowy. Dobry przy szumie i opóźnieniach.\n"
            "GradientBoosting - gdy chcesz dokładniej poprawiać błędy, ale trzeba uważać na przeuczenie.\n"
            "HistGradient - boosting dla większych danych; koszyki histogramowe przyspieszają trening.\n"
            "XGBoost - mocny boosting eksperymentalny; dobry, gdy chcesz dokładniej łapać nieliniowe zależności i masz zainstalowany pakiet xgboost.\n"
            "SVR / SVM - margines błędu i kara C; dobry przy mniejszych danych, wymaga skalowania.\n"
            "KNN - szuka podobnych rekordów historycznych; prosty do zrozumienia, ale wymaga skalowania.\n"
            "Ridge - prosty model liniowy jako baseline; pokazuje, czy problem jest prawie liniowy.\n"
            "LogisticRegression - klasyfikacja harmonogramu przez prawdopodobieństwa klas.\n"
            "RandomForestClassifier - harmonogram, gdy klasy zależą od nieliniowych relacji.\n\n"
            "Backend ML:\n"
            "classic używa dokładnie wybranego estymatora sklearn/xgboost.\n"
            "tabpfn używa silnika TabPFN dla każdego zaznaczonego zadania; własny model daje wtedy nazwę i cel, ale estymator zastępuje TabPFN.\n\n"
            "Parametry po ludzku:\n"
            "n_estimators = liczba drzew/modeli.\n"
            "max_depth = maksymalna głębokość drzewa.\n"
            "learning_rate = tempo poprawiania błędu.\n"
            "subsample / colsample_bytree = ile rekordów i cech bierze XGBoost w kroku.\n"
            "C = kara w SVM, epsilon = tolerancja błędu.\n"
            "n_neighbors = ilu sąsiadów bierze KNN.\n"
            "alpha = siła regularyzacji Ridge.\n"
            "random_state = powtarzalny wynik."
        )

    @staticmethod
    def _custom_model_tutorial_text() -> str:
        return (
            "JAK WYBRAĆ DOBRY PRZYKŁAD\n"
            "Najpierw wybierz cel, a dopiero potem algorytm.\n\n"
            "1. Jeśli przewidujesz jakość produktu:\n"
            "   - RandomForest: najlepszy pierwszy strzał, bo jest stabilny i nie wymaga skalowania.\n"
            "   - GradientBoosting: spróbuj, gdy RandomForest jest za mało dokładny.\n"
            "   - XGBoost: spróbuj, gdy chcesz mocniejszy boosting i projekt ma zainstalowany pakiet xgboost.\n"
            "   - Ridge: użyj jako prosty punkt odniesienia. Jeśli Ridge działa dobrze, zależność może być prawie liniowa.\n"
            "   - SVR/SVM: spróbuj przy mniejszych danych i nieliniowościach, ale ustaw skalowanie standard albo robust.\n\n"
            "2. Jeśli przewidujesz opóźnienie:\n"
            "   - ExtraTrees: dobry szybki wybór, często odporny na szum.\n"
            "   - HistGradient: dobry przy większych danych, bo używa koszyków histogramowych.\n"
            "   - KNN: dobry do prostego testu podobieństwa, ale musi mieć skalowanie.\n\n"
            "3. Jeśli wybierasz harmonogram/klasę:\n"
            "   - LogisticRegression: prosty klasyfikator, łatwy do interpretacji.\n"
            "   - RandomForestClassifier: mocniejszy klasyfikator, gdy decyzje zależą od wielu nieliniowych warunków.\n\n"
            "KROK PO KROKU W OKNIE\n"
            "1. Kliknij preset. Pola nazwy, estymatora, skalowania i JSON wypełnią się automatycznie.\n"
            "2. Wybierz zadanie: jakość/opóźnienie = regresja, harmonogram = klasyfikacja.\n"
            "3. Nazwa techniczna zapisuje model w pliku. Nazwa na ekranie to etykieta widoczna w Main.\n"
            "4. Estymator sklearn to ścieżka klasy Pythona, np. sklearn.svm.SVR. To nie jest komenda terminala.\n"
            "5. Parametry JSON to argumenty przekazywane do tej klasy, np. n_estimators, max_depth, C, epsilon.\n"
            "6. Skalowanie: drzewa zwykle none; SVR, KNN, Ridge i LogisticRegression zwykle standard albo robust.\n"
            "7. Kliknij Zapisz model. Konfiguracja trafia do models/custom_ml_models.json.\n"
            "8. Zaznacz nowy model w Main i uruchom trening.\n\n"
            "BACKEND CLASSIC A TABPFN\n"
            "classic uruchamia dokładnie wybrany estymator, np. RandomForest, SVR albo XGBoost.\n"
            "tabpfn uruchamia TabPFN na każdym zaznaczonym celu. Własna nazwa zostaje, ale konkretny estymator sklearn/xgboost jest wtedy pomijany.\n\n"
            "CO DZIEJE SIĘ TECHNICZNIE\n"
            "Dane -> cechy X -> uzupełnienie braków medianą -> skalowanie -> estimator.fit(X, y) -> metryki -> zapis .pkl.\n\n"
            "WZORY\n"
            "RandomForest/ExtraTrees: ŷ = mean(tree_i(x)) albo głosowanie klas.\n"
            "GradientBoosting/HistGradient: F_m(x)=F_{m-1}(x)+η·h_m(x).\n"
            "XGBoost: F_m(x)=F_{m-1}(x)+η·tree_m(x), z karą za złożoność drzewa.\n"
            "SVR/SVM: błąd poza marginesem epsilon jest karany przez C.\n"
            "KNN: ŷ = średnia ważona najbliższych sąsiadów.\n"
            "Ridge: min ||y-Xw||² + alpha·||w||².\n"
            "LogisticRegression: P(klasa|X)=softmax(Xw+b)."
        )

    def _build_generation_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=8)
        self.assistant_sections["generation"] = frame
        ctk.CTkLabel(frame, text="Parametry generowania danych", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        grid = ctk.CTkFrame(frame)
        grid.pack(fill="x", padx=10, pady=(0, 10))

        self._entry(grid, "Liczba rekordów", self.n_var, 0, 0)
        self._entry(grid, "Liczba maszyn", self.n_machines_var, 0, 2)
        self._entry(grid, "Test size", self.test_size_var, 1, 0)
        self._entry(grid, "Seed", self.seed_var, 1, 2)
        self._entry(grid, "Czas prod. min [h]", self.prod_min_var, 2, 0)
        self._entry(grid, "Czas prod. max [h]", self.prod_max_var, 2, 2)
        self._entry(grid, "Bufor terminu min [h]", self.deadline_min_var, 3, 0)
        self._entry(grid, "Bufor terminu max [h]", self.deadline_max_var, 3, 2)

        ctk.CTkLabel(
            frame,
            text=(
                "Format parametrow: liczba rekordow, liczba maszyn i seed musza byc calkowite. "
                "Test size to ulamek 0-1, np. 0.2. Czasy i bufory moga byc ulamkowe, ale minimum musi byc mniejsze od maksimum."
            ),
            text_color="#bfdbfe",
            wraplength=860,
            justify="left",
        ).pack(fill="x", padx=15, pady=(0, 8))

        for child in grid.winfo_children():
            if isinstance(child, ctk.CTkEntry):
                child.bind("<KeyRelease>", lambda _e: self.render_summary())

        ctk.CTkLabel(frame, text="Kształty", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=15, pady=(4, 4)
        )
        shapes_frame = ctk.CTkFrame(frame)
        shapes_frame.pack(fill="x", padx=10, pady=(0, 8))
        for name, var in self.ksztalt_vars.items():
            ctk.CTkCheckBox(
                shapes_frame, text=name, variable=var, command=self.render_summary
            ).pack(anchor="w", padx=10, pady=4)

        ctk.CTkLabel(frame, text="Materiały", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=15, pady=(4, 4)
        )
        mat_frame = ctk.CTkFrame(frame)
        mat_frame.pack(fill="x", padx=10, pady=(0, 12))
        for name, var in self.material_vars.items():
            ctk.CTkCheckBox(mat_frame, text=name, variable=var, command=self.render_summary).pack(
                anchor="w", padx=10, pady=4
            )

    def _build_sto_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(frame, text="Wejście ręczne dla STO", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        grid = ctk.CTkFrame(frame)
        grid.pack(fill="x", padx=10, pady=(0, 10))
        self._entry(grid, "Zlecenia", self.sto_jobs_var, 0, 0)
        self._entry(grid, "Czasy", self.sto_times_var, 1, 0)
        self._entry(grid, "Terminy", self.sto_deadlines_var, 2, 0)
        ctk.CTkButton(
            frame, text="Policz tylko STO ręcznie", command=self.run_sto_analysis, height=36
        ).pack(fill="x", padx=15, pady=(0, 12))

    def _build_actions_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=8)
        self.assistant_sections["actions"] = frame
        ctk.CTkLabel(frame, text="Akcje", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 10)
        )
        btns = ctk.CTkFrame(frame)
        btns.pack(fill="x", padx=10, pady=(0, 12))
        self.btn_generate = ctk.CTkButton(btns, text="Generuj dane", command=self.gen, height=38)
        self.btn_generate.pack(fill="x", padx=10, pady=6)
        self.btn_load = ctk.CTkButton(
            btns, text="Wczytaj dane (CSV)", command=self.load_from_disk, height=38
        )
        self.btn_load.pack(fill="x", padx=10, pady=6)
        self.btn_train = ctk.CTkButton(
            btns, text="Uruchom / zapisz wybrane modele", command=self.train, height=38
        )
        self.btn_train.pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(
            btns,
            text="▶ Rozwiąż zapisany model na wybranych danych",
            command=self.solve_existing_models,
            height=38,
        ).pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(
            btns,
            text="Podglad / usuwanie plikow AOA",
            command=self._open_file_manager,
            height=38,
            fg_color="#155e75",
            hover_color="#0e7490",
        ).pack(fill="x", padx=10, pady=6)

    def _open_file_manager(self):
        app = self.winfo_toplevel()
        opener = getattr(app, "open_file_manager_window", None)
        if callable(opener):
            opener()

    def _entry(self, parent, label, var, row, col):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=col, sticky="w", padx=10, pady=6)
        entry = ctk.CTkEntry(parent, textvariable=var, width=160)
        entry.grid(row=row, column=col + 1, sticky="w", padx=10, pady=6)
