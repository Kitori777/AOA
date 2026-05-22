import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from AOA.config import DATA_DIR
from AOA.core.services import load_and_prepare_visual_file
from AOA.core.visualization_service import (
    build_d3_dashboard_html_report,
    build_d3_html_report,
    build_figure_from_prompt,
    build_figure_from_request,
    build_visual_report,
)

CHART_TYPES = [
    "Production Dashboard",
    "Dashboard",
    "Diagnostics",
    "Pair Explorer",
    "3D Scatter",
    "3D Surface",
    "Bubble Chart",
    "Heatmap Density",
    "Outlier Map",
    "Step View",
    "Priority Timeline",
    "Missingness Map",
    "Column Ranking",
    "Scatter",
    "Line",
    "Histogram",
    "Boxplot",
    "Gantt",
    "DecisionTree",
    "CorrelationMatrix",
    "SimilarityMatrix",
]


class VisualPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.df_vis = None
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
        control.grid_columnconfigure(7, weight=1)
        self.x_var = ctk.StringVar()
        self.y_var = ctk.StringVar()
        self.z_var = ctk.StringVar()
        self.plot_type = ctk.StringVar(value="Production Dashboard")
        self.command_var = ctk.StringVar()
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
        ctk.CTkButton(control, text="Rysuj raport", command=self.draw_plot, width=135).grid(
            row=0, column=5, padx=6, pady=12
        )
        ctk.CTkButton(control, text="Następny widok", command=self.next_chart, width=135).grid(
            row=0, column=6, padx=6, pady=12
        )
        ctk.CTkLabel(
            control,
            text="3D obracasz myszką w obszarze wykresu; toolbar pozwala przybliżać i zapisywać widok.",
            text_color="#cbd5e1",
        ).grid(row=0, column=7, padx=6, pady=12, sticky="w")
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
        ctk.CTkButton(control, text="Otwórz D3 HTML", command=self.open_d3_report, width=135).grid(
            row=1, column=6, padx=6, pady=(0, 12), sticky="w"
        )

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
        self.report_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.report_frame.grid_propagate(False)
        self.report_frame.grid_columnconfigure(0, weight=1)
        self.report_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self.report_frame, text="Raport dla użytkownika", font=("Arial", 18, "bold")
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
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
            self.draw_plot()
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def draw_plot(self):
        if self.df_vis is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik z danymi")
            return
        try:
            fig = build_figure_from_request(
                self.df_vis,
                self.plot_type.get(),
                self.x_var.get(),
                self.y_var.get(),
                self.z_var.get(),
            )
            self._draw_canvas(fig)
            self._set_report(
                build_visual_report(
                    self.df_vis,
                    self.x_var.get(),
                    self.y_var.get(),
                    self.z_var.get(),
                    self.plot_type.get(),
                )
            )
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def draw_from_prompt(self):
        if self.df_vis is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik z danymi")
            return
        try:
            fig, parsed = build_figure_from_prompt(self.df_vis, self.command_var.get())
            self.plot_type.set(parsed["chart_type"] or self.plot_type.get())
            if parsed["x_col"]:
                self.x_var.set(parsed["x_col"])
            if parsed["y_col"]:
                self.y_var.set(parsed["y_col"])
            if parsed["z_col"]:
                self.z_var.set(parsed["z_col"])
            self._draw_canvas(fig)
            self._set_report(
                build_visual_report(
                    self.df_vis,
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
            safe_chart = "".join(
                char.lower() if char.isalnum() else "_" for char in chart_type
            ).strip("_")
            safe_chart = safe_chart[:40] or "chart"
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if chart_type in {"Production Dashboard", "Dashboard"}:
                output_path = DATA_DIR / f"visual_d3_dashboard_{stamp}.html"
                html = build_d3_dashboard_html_report(
                    self.df_vis,
                    x_col=self.x_var.get(),
                    y_col=self.y_var.get(),
                    z_col=self.z_var.get(),
                )
            else:
                output_path = DATA_DIR / f"visual_d3_{safe_chart}_{stamp}.html"
                html = build_d3_html_report(
                    self.df_vis,
                    x_col=self.x_var.get(),
                    y_col=self.y_var.get(),
                    z_col=self.z_var.get(),
                    chart_type=chart_type,
                )
            output_path.write_text(html, encoding="utf-8")
            webbrowser.open_new_tab(output_path.resolve().as_uri())
            self._set_report(
                build_visual_report(
                    self.df_vis,
                    self.x_var.get(),
                    self.y_var.get(),
                    self.z_var.get(),
                    chart_type,
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
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _set_report(self, text: str):
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("end", text)
        self.report_box.configure(state="disabled")
