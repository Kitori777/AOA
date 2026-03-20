import customtkinter as ctk
import numpy as np
import pandas as pd
import seaborn as sns

from tkinter import filedialog, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_agg import FigureCanvasAgg
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor, plot_tree
from sklearn.metrics import jaccard_score

from AOA.core.data_io import load_csv


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

        ctk.CTkButton(
            control,
            text="📂 Wczytaj CSV",
            command=self.load_file
        ).grid(row=0, column=0, padx=10)

        self.x_menu = ctk.CTkOptionMenu(control, values=[], variable=self.x_var)
        self.x_menu.grid(row=0, column=1, padx=10)

        self.y_menu = ctk.CTkOptionMenu(control, values=[], variable=self.y_var)
        self.y_menu.grid(row=0, column=2, padx=10)

        self.plot_menu = ctk.CTkOptionMenu(
            control,
            values=[
                "Scatter",
                "Line",
                "Histogram",
                "Boxplot",
                "Gantt",
                "DecisionTree",
                "CorrelationMatrix",
                "SimilarityMatrix",
            ],
            variable=self.plot_type
        )
        self.plot_menu.grid(row=0, column=3, padx=10)

        ctk.CTkButton(
            control,
            text="Rysuj",
            command=self.draw_plot
        ).grid(row=0, column=4, padx=10)

        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return

        try:
            self.df_vis = load_csv(path)
            cols = list(self.df_vis.columns)

            self.x_menu.configure(values=cols)
            self.y_menu.configure(values=cols)

            if cols:
                self.x_var.set(cols[0])
                self.y_var.set(cols[1] if len(cols) > 1 else cols[0])

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def draw_plot(self):
        if self.df_vis is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj CSV")
            return

        kind = self.plot_type.get()
        df = self.df_vis.copy()

        if kind == "DecisionTree":
            self.draw_decision_tree(df)
            return

        fig = Figure(figsize=(9, 5), dpi=100)
        ax = fig.add_subplot(111)

        if kind == "Scatter":
            ax.scatter(df[self.x_var.get()], df[self.y_var.get()])
            ax.set_xlabel(self.x_var.get())
            ax.set_ylabel(self.y_var.get())

        elif kind == "Line":
            x_col = self.x_var.get()
            y_col = self.y_var.get()

            df_line = (
                df[[x_col, y_col]]
                .dropna()
                .sort_values(by=x_col)
                .reset_index(drop=True)
            )

            x = df_line[x_col]
            y = df_line[y_col]
            y_smooth = y.rolling(window=5, center=True).mean()

            ax.plot(x, y, linewidth=1, alpha=0.4, label="Dane")
            ax.plot(x, y_smooth, linewidth=3, label="Średnia krocząca (5)")
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title("Wykres liniowy – wygładzony")
            ax.grid(True, alpha=0.3)
            ax.legend()

        elif kind == "Histogram":
            col = self.x_var.get()
            ax.hist(df[col].dropna(), bins=30)
            ax.set_xlabel(col)
            ax.set_ylabel("Liczność")

        elif kind == "Boxplot":
            col = self.y_var.get()
            ax.boxplot(df[col].dropna())
            ax.set_ylabel(col)

        elif kind == "Gantt":
            required_cols = {"ksztalt", "czas_produkcji_h"}
            if not required_cols.issubset(df.columns):
                messagebox.showerror(
                    "Błąd",
                    "Gantt wymaga kolumn 'ksztalt' i 'czas_produkcji_h'"
                )
                return

            df_g = df[["ksztalt", "czas_produkcji_h"]].dropna()
            starts = df_g["czas_produkcji_h"].cumsum() - df_g["czas_produkcji_h"]

            ax.barh(
                df_g["ksztalt"],
                df_g["czas_produkcji_h"],
                left=starts
            )
            ax.set_xlabel("Czas [h]")

        elif kind == "CorrelationMatrix":
            corr = df.select_dtypes(include=np.number).corr()
            sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
            ax.set_title("Macierz korelacji")

        elif kind == "SimilarityMatrix":
            bin_df = pd.DataFrame()

            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    bin_df[col] = (df[col] >= df[col].median()).astype(int)
                else:
                    bin_df[col] = LabelEncoder().fit_transform(df[col].astype(str))

            n = len(bin_df.columns)
            sim = np.zeros((n, n))

            for i in range(n):
                for j in range(n):
                    sim[i, j] = jaccard_score(
                        bin_df.iloc[:, i],
                        bin_df.iloc[:, j],
                        average="macro"
                    )

            sns.heatmap(
                sim,
                annot=True,
                xticklabels=bin_df.columns,
                yticklabels=bin_df.columns,
                cmap="viridis",
                ax=ax
            )
            ax.set_title("Macierz podobieństw (Jaccard)")

        self._draw_canvas(fig)

    def draw_decision_tree(self, df):
        target = df.columns[-1]
        X = df.drop(columns=[target]).copy()
        y = df[target].copy()

        for col in X.select_dtypes(include=["object", "category"]).columns:
            X[col] = LabelEncoder().fit_transform(X[col].astype(str))

        if pd.api.types.is_numeric_dtype(y):
            y = y.fillna(y.mean())
            model = DecisionTreeRegressor(max_depth=3, random_state=42)
        else:
            y = y.astype(str)
            model = DecisionTreeClassifier(max_depth=3, random_state=42)

        model.fit(X, y)

        fig = Figure(figsize=(14, 6), dpi=100)
        canvas_agg = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)

        plot_tree(
            model,
            feature_names=X.columns,
            filled=True,
            ax=ax
        )

        canvas_agg.draw()
        self._draw_canvas(fig)

    def _draw_canvas(self, fig):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
