import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from AOA.config import DATA_DIR
from AOA.core.services import load_and_prepare_visual_file
from AOA.core.visualization_service import (
    CHART_TYPES,
    VISUAL_LIBRARIES,
    build_d3_dashboard_html_report,
    build_d3_html_report,
    build_figure_from_prompt,
    build_figure_from_request,
    build_visual_report,
    coerce_chart_for_library,
    get_supported_chart_types,
)


class VisualPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.assistant_sections = {}
        self.df_vis = None
        self._resolved_tree_model = "Auto"
        self.canvas = None
        self.toolbar = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        ctk.CTkLabel(
            header, text="Visual Lab — interaktywna eksploracja danych", font=("Arial", 24, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 2))
        ctk.CTkLabel(
            header,
            text="Wczytaj dowolne dane tabelaryczne, zmieniaj X/Y/Z, obracaj 3D i od razu czytaj raport po prawej.",
            font=("Arial", 12),
            text_color="#cbd5e1",
        ).pack(anchor="w", padx=15, pady=(0, 12))

        control = ctk.CTkFrame(self)
        control.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.assistant_sections["controls"] = control
        control.grid_columnconfigure(8, weight=1)
        self.x_var = ctk.StringVar()
        self.y_var = ctk.StringVar()
        self.z_var = ctk.StringVar()
        self.plot_type = ctk.StringVar(value="Production Dashboard")
        self.chart_library = ctk.StringVar(value="Matplotlib")
        self.command_var = ctk.StringVar()
        self.tree_model_var = ctk.StringVar(value="Auto")
        self.plot_type.trace_add("write", self._on_plot_type_change)
        self.chart_library.trace_add("write", self._on_library_change)
        ctk.CTkButton(control, text="📂 Wczytaj dane", command=self.load_file, width=145).grid(
            row=0, column=0, padx=(12, 8), pady=12
        )
        self.x_menu = ctk.CTkOptionMenu(control, values=[], variable=self.x_var, width=145)
        self.x_menu.grid(row=0, column=1, padx=6, pady=12)
        self.y_menu = ctk.CTkOptionMenu(control, values=[], variable=self.y_var, width=145)
        self.y_menu.grid(row=0, column=2, padx=6, pady=12)
        self.z_menu = ctk.CTkOptionMenu(control, values=[], variable=self.z_var, width=145)
        self.z_menu.grid(row=0, column=3, padx=6, pady=12)
        self.plot_menu = ctk.CTkOptionMenu(
            control,
            values=CHART_TYPES,
            variable=self.plot_type,
            width=170,
        )
        self.plot_menu.grid(row=0, column=4, padx=6, pady=12)
        self.library_menu = ctk.CTkOptionMenu(
            control,
            values=VISUAL_LIBRARIES,
            variable=self.chart_library,
            width=145,
        )
        self.library_menu.grid(row=0, column=5, padx=6, pady=12)
        self.tree_model_menu = None
        ctk.CTkButton(control, text="Rysuj raport", command=self.draw_plot, width=135).grid(
            row=0, column=6, padx=6, pady=12
        )
        html_nav = ctk.CTkFrame(control, fg_color="transparent")
        html_nav.grid(row=0, column=7, rowspan=2, padx=6, pady=12, sticky="nsew")
        html_nav.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            html_nav,
            text="OTWÓRZ HTML",
            command=self.open_d3_report,
            width=170,
            height=36,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=("Arial", 13, "bold"),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkButton(
            html_nav, text="Następny widok", command=self.next_chart, width=170, height=34
        ).grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(
            control,
            text="Tryb drzewa: automatycznie wybierana jest najlepsza metoda STO.",
            text_color="#cbd5e1",
        ).grid(row=2, column=0, columnspan=10, padx=12, pady=(0, 12), sticky="w")
        ctk.CTkLabel(control, text="Wykres z opisu:", font=("Arial", 12, "bold")).grid(
            row=1, column=0, padx=(12, 8), pady=(0, 12), sticky="w"
        )
        self.command_entry = ctk.CTkEntry(
            control,
            textvariable=self.command_var,
            placeholder_text="np. scatter x cena y odpad kolor lateness_h_sim albo histogram cena",
        )
        self.command_entry.grid(row=1, column=1, columnspan=4, padx=6, pady=(0, 12), sticky="ew")
        self.command_entry.bind("<Return>", lambda _event: self.draw_from_prompt())
        ctk.CTkButton(control, text="Rysuj z opisu", command=self.draw_from_prompt, width=135).grid(
            row=1, column=5, padx=6, pady=(0, 12)
        )
        self.draw_current_tree_button = ctk.CTkButton(
            control,
            text="Aktualizuj wykres",
            command=self.draw_plot,
            width=170,
        )
        self.draw_current_tree_button.grid(row=1, column=6, padx=6, pady=(0, 12), sticky="w")
        self.tree_info_label = None
        self._on_plot_type_change()

        body = ctk.CTkFrame(self)
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.plot_frame = ctk.CTkFrame(body)
        self.plot_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.plot_frame.grid_columnconfigure(0, weight=1)
        self.plot_frame.grid_rowconfigure(1, weight=1)
        self.report_frame = ctk.CTkFrame(body, width=360)
        self.assistant_sections["report"] = self.report_frame
        self.report_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.report_frame.grid_propagate(False)
        self.report_frame.grid_columnconfigure(0, weight=1)
        self.report_frame.grid_rowconfigure(1, weight=1)
        report_header = ctk.CTkFrame(self.report_frame, fg_color="transparent")
        report_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        report_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(report_header, text="Raport dla użytkownika", font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(
            report_header,
            text="Otwórz HTML",
            command=self.open_d3_report,
            width=125,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))
        self.report_box = ctk.CTkTextbox(self.report_frame, wrap="word")
        self.report_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self._set_report(
            "Wczytaj plik CSV/TXT/TSV. Możesz użyć danych produkcyjnych albo dowolnej tabeli. "
            "Po narysowaniu wykresu pojawi się raport: zakresy, braki, korelacje, odstające punkty i podpowiedzi interpretacji."
        )

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
            self.df_vis = result["df"]
            columns = result["columns"]
            self.x_menu.configure(values=columns)
            self.y_menu.configure(values=columns)
            self.z_menu.configure(values=columns)
            self.x_var.set(result["x_default"])
            self.y_var.set(result["y_default"])
            self.z_var.set(result.get("z_default", result["y_default"]))
            self._refresh_tree_models()
            self.draw_plot()
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def _refresh_tree_models(self):
        if self.df_vis is None or "sto_model" not in self.df_vis.columns:
            self.tree_model_var.set("Auto")
            return
        self.tree_model_var.set(self._best_sto_model(self.df_vis))

    def _best_sto_model(self, df):
        if df is None or "sto_model" not in df.columns:
            return "Auto"
        metric_candidates = [
            "Kop",
            "kop",
            "sto_kop",
            "lateness_h_sim",
            "pred_delay",
            "odpad",
            "cena",
        ]
        metric = next((col for col in metric_candidates if col in df.columns), None)
        models = df["sto_model"].astype(str).str.strip()
        if metric is None:
            vc = models[models != ""].value_counts()
            return vc.index[0] if not vc.empty else "Auto"
        scored = df.assign(_model=models, _m=pd.to_numeric(df[metric], errors="coerce")).dropna(
            subset=["_m"]
        )
        if scored.empty:
            vc = models[models != ""].value_counts()
            return vc.index[0] if not vc.empty else "Auto"
        best = (
            scored[scored["_model"] != ""]
            .groupby("_model", as_index=False)["_m"]
            .min()
            .sort_values("_m", ascending=True)
        )
        if best.empty:
            return "Auto"
        return str(best.iloc[0]["_model"])

    def _selected_visual_df(self):
        if self.df_vis is None:
            return None
        chart_type = self.plot_type.get()
        selected_model = self.tree_model_var.get()
        self._resolved_tree_model = selected_model
        if chart_type == "SolutionTree" and "sto_model" in self.df_vis.columns:
            if selected_model == "Auto" or not selected_model:
                selected_model = self._best_sto_model(self.df_vis)
                self._resolved_tree_model = selected_model
            filtered = self.df_vis[self.df_vis["sto_model"].astype(str) == selected_model]
            if not filtered.empty:
                return filtered
        return self.df_vis

    def draw_plot(self):
        if self.df_vis is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik z danymi")
            return
        try:
            visual_df = self._selected_visual_df()
            fig = build_figure_from_request(
                visual_df,
                self.plot_type.get(),
                self.x_var.get(),
                self.y_var.get(),
                self.z_var.get(),
                self.chart_library.get(),
            )
            self._draw_canvas(fig)
            self._set_report(
                build_visual_report(
                    visual_df,
                    self.x_var.get(),
                    self.y_var.get(),
                    self.z_var.get(),
                    self.plot_type.get(),
                )
                + (
                    f"\n\nModel drzewa STO: {getattr(self, '_resolved_tree_model', self.tree_model_var.get())}"
                    if self.plot_type.get() == "SolutionTree"
                    else ""
                )
            )
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def load_sample_and_draw_dashboard(self) -> None:
        sample_path = DATA_DIR / "sample" / "sample_table.csv"
        if not sample_path.exists():
            raise FileNotFoundError(f"Brak pliku sample: {sample_path}")
        result = load_and_prepare_visual_file(str(sample_path))
        self.df_vis = result["df"]
        columns = result["columns"]
        self.x_menu.configure(values=columns)
        self.y_menu.configure(values=columns)
        self.z_menu.configure(values=columns)
        self.x_var.set(result["x_default"])
        self.y_var.set(result["y_default"])
        self.z_var.set(result.get("z_default", result["y_default"]))
        self.plot_type.set("Production Dashboard")
        self._refresh_tree_models()
        self.draw_plot()

    def draw_from_prompt(self):
        if self.df_vis is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik z danymi")
            return
        try:
            _fig, parsed = build_figure_from_prompt(self.df_vis, self.command_var.get())
            self.plot_type.set(parsed["chart_type"] or self.plot_type.get())
            if parsed["x_col"]:
                self.x_var.set(parsed["x_col"])
            if parsed["y_col"]:
                self.y_var.set(parsed["y_col"])
            if parsed["z_col"]:
                self.z_var.set(parsed["z_col"])
            visual_df = self._selected_visual_df()
            fig = build_figure_from_request(
                visual_df,
                self.plot_type.get(),
                self.x_var.get(),
                self.y_var.get(),
                self.z_var.get(),
                self.chart_library.get(),
            )
            self._draw_canvas(fig)
            self._set_report(
                build_visual_report(
                    visual_df,
                    parsed["x_col"],
                    parsed["y_col"],
                    parsed["z_col"],
                    parsed["chart_type"],
                )
                + "\n\nPolecenie:\n"
                + self.command_var.get()
            )
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def open_d3_report(self):
        if self.df_vis is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik z danymi")
            return
        try:
            chart_type = self.plot_type.get()
            visual_df = self._selected_visual_df()
            safe_chart = "".join(
                char.lower() if char.isalnum() else "_" for char in chart_type
            ).strip("_")
            safe_chart = safe_chart[:40] or "chart"
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if chart_type in {"Production Dashboard", "Dashboard"}:
                output_path = DATA_DIR / f"visual_d3_dashboard_{stamp}.html"
                html = build_d3_dashboard_html_report(
                    visual_df,
                    x_col=self.x_var.get(),
                    y_col=self.y_var.get(),
                    z_col=self.z_var.get(),
                    chart_library=self.chart_library.get(),
                )
            else:
                output_path = DATA_DIR / f"visual_d3_{safe_chart}_{stamp}.html"
                html = build_d3_html_report(
                    visual_df,
                    x_col=self.x_var.get(),
                    y_col=self.y_var.get(),
                    z_col=self.z_var.get(),
                    chart_type=chart_type,
                    chart_library=self.chart_library.get(),
                )
            output_path.write_text(html, encoding="utf-8")
            webbrowser.open_new_tab(output_path.resolve().as_uri())
            self._set_report(
                build_visual_report(
                    visual_df,
                    self.x_var.get(),
                    self.y_var.get(),
                    self.z_var.get(),
                    chart_type,
                )
                + (
                    f"\n\nModel drzewa STO: {getattr(self, '_resolved_tree_model', self.tree_model_var.get())}"
                    if chart_type == "SolutionTree"
                    else ""
                )
                + f"\n\nD3 HTML zapisany jako świeży plik:\n{output_path}"
                + "\n\nJeśli przeglądarka pokaże komunikat o D3.js, problemem jest blokada CDN lub brak internetu."
            )
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def next_chart(self):
        values = CHART_TYPES
        current = self.plot_type.get()
        next_index = (values.index(current) + 1) % len(values) if current in values else 0
        self.plot_type.set(values[next_index])
        if self.df_vis is not None:
            self.draw_plot()

    def _draw_canvas(self, fig):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        if self.toolbar:
            self.toolbar.destroy()
        is_tree = self.plot_type.get() in {"SolutionTree", "ML Decision Tree"}
        body = self.plot_frame.master
        if body is not None:
            try:
                body.grid_columnconfigure(0, weight=4 if is_tree else 3)
                body.grid_columnconfigure(1, weight=1 if is_tree else 1)
            except Exception:
                pass
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame, pack_toolbar=False)
        self.toolbar.update()
        if is_tree:
            try:
                self.toolbar.pan()
            except Exception:
                pass
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _set_report(self, text: str):
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("end", text)
        self.report_box.configure(state="disabled")

    def focus_section(self, section: str) -> None:
        frame = self.assistant_sections.get(section)
        if frame is None:
            return
        try:
            frame.configure(border_width=2, border_color="#1f8fff")
            self.after(1400, lambda: frame.configure(border_width=0))
        except Exception:
            return

    def _on_plot_type_change(self, *_args):
        chart = self.plot_type.get()
        is_tree = chart == "SolutionTree"
        state = "normal" if is_tree else "disabled"
        try:
            self.draw_current_tree_button.configure(state=state if is_tree else "normal")
        except Exception:
            pass

    def _on_library_change(self, *_args):
        library = self.chart_library.get()
        values = get_supported_chart_types(library)
        current = self.plot_type.get()
        next_chart = coerce_chart_for_library(current, library)
        try:
            self.plot_menu.configure(values=values)
        except Exception:
            return
        if current != next_chart:
            self.plot_type.set(next_chart)
        else:
            self._on_plot_type_change()
        if self.df_vis is not None:
            self.after(50, self.draw_plot)
