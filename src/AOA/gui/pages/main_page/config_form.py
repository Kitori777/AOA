# mypy: disable-error-code=attr-defined
import customtkinter as ctk


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
        ctk.CTkLabel(ml_frame, text="Modele ML", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        for spec in self.ml_model_specs:
            row = ctk.CTkFrame(ml_frame, fg_color="transparent")
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
            text="classic = 12 wariantów ML | tabpfn = tryb eksperymentalny dla bazowych Quality/Delay/Schedule",
            font=("Arial", 11),
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 10))

        sto_frame = ctk.CTkFrame(frame)
        sto_frame.pack(fill="x", padx=10, pady=(0, 12))
        ctk.CTkLabel(sto_frame, text="Modele heurystyczne STO", font=("Arial", 15, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        for spec in self.mh_model_specs:
            row = ctk.CTkFrame(sto_frame, fg_color="transparent")
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

    def _entry(self, parent, label, var, row, col):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=col, sticky="w", padx=10, pady=6)
        entry = ctk.CTkEntry(parent, textvariable=var, width=160)
        entry.grid(row=row, column=col + 1, sticky="w", padx=10, pady=6)
