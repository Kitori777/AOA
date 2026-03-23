import customtkinter as ctk
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from AOA.config import DATA_DIR
from AOA.core.services import load_and_prepare_visual_file
from AOA.core.visualization_service import build_figure_from_request


class VisualPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.df_vis = None
        self.canvas = None

        ctk.CTkLabel(
            self,
            text="Wizualizacje danych",
            font=("Arial", 20, "bold")
        ).pack(pady=10)

        control = ctk.CTkFrame(self)
        control.pack(fill="x", padx=20, pady=10)

        self.x_var = ctk.StringVar()
        self.y_var = ctk.StringVar()
        self.plot_type = ctk.StringVar(value="Scatter")

        ctk.CTkButton(control, text="📂 Wczytaj CSV", command=self.load_file).grid(row=0, column=0, padx=10)

        self.x_menu = ctk.CTkOptionMenu(control, values=[], variable=self.x_var)
        self.x_menu.grid(row=0, column=1, padx=10)

        self.y_menu = ctk.CTkOptionMenu(control, values=[], variable=self.y_var)
        self.y_menu.grid(row=0, column=2, padx=10)

        self.plot_menu = ctk.CTkOptionMenu(
            control,
            values=[
                "Scatter", "Line", "Histogram", "Boxplot",
                "Gantt", "DecisionTree", "CorrelationMatrix", "SimilarityMatrix"
            ],
            variable=self.plot_type
        )
        self.plot_menu.grid(row=0, column=3, padx=10)

        ctk.CTkButton(control, text="Rysuj", command=self.draw_plot).grid(row=0, column=4, padx=10)

        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def load_file(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            initialdir=str(DATA_DIR),
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return

        try:
            result = load_and_prepare_visual_file(path)
            self.df_vis = result["df"]

            self.x_menu.configure(values=result["columns"])
            self.y_menu.configure(values=result["columns"])

            self.x_var.set(result["x_default"])
            self.y_var.set(result["y_default"])

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def draw_plot(self):
        if self.df_vis is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj CSV")
            return

        try:
            fig = build_figure_from_request(
                df=self.df_vis,
                chart_type=self.plot_type.get(),
                x_col=self.x_var.get(),
                y_col=self.y_var.get()
            )
            self._draw_canvas(fig)

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def _draw_canvas(self, fig):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
