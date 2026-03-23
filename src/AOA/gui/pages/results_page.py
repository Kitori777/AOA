import customtkinter as ctk
from tkinter import filedialog, messagebox, Text, Scrollbar, BOTH

from AOA.config import DATA_DIR
from AOA.core.services import load_and_prepare_visual_file, prepare_results_analysis


class ResultsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        ctk.CTkLabel(
            self,
            text="Wyniki / Dane do ML",
            font=("Arial", 20, "bold")
        ).pack(pady=10)

        self.df_loaded = None
        self.column_vars = {}
        self.target_var = ctk.StringVar(value="")
        self.transformation_var = ctk.StringVar(value="Surowe")

        control = ctk.CTkFrame(self)
        control.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(control, text="📂 Wczytaj plik CSV", command=self.load_file).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(control, text="Przekształcenie:").grid(row=0, column=1, padx=5)

        self.transformation_menu = ctk.CTkOptionMenu(
            control,
            values=[
                "Surowe",
                "MinMax Normalizacja",
                "Standaryzacja",
                "Logarytm",
                "Skalowanie 0-1",
            ],
            variable=self.transformation_var
        )
        self.transformation_menu.grid(row=0, column=2, padx=5)

        self.target_menu = ctk.CTkOptionMenu(control, values=[], variable=self.target_var)
        self.target_menu.grid(row=0, column=3, padx=5)

        ctk.CTkButton(control, text="Regresja", command=lambda: self.show_data("regresja")).grid(row=0, column=4, padx=5)
        ctk.CTkButton(control, text="Klasyfikacja", command=lambda: self.show_data("klasyfikacja")).grid(row=0, column=5, padx=5)

        self.cols_frame = ctk.CTkScrollableFrame(self, height=120)
        self.cols_frame.pack(fill="x", padx=20, pady=10)

        text_frame = ctk.CTkFrame(self)
        text_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.v_scroll = Scrollbar(text_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        self.h_scroll = Scrollbar(text_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")

        self.box = Text(
            text_frame,
            font=("Courier", 10),
            wrap="none",
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set
        )
        self.box.pack(fill=BOTH, expand=True)

        self.v_scroll.config(command=self.box.yview)
        self.h_scroll.config(command=self.box.xview)

    def load_file(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            initialdir=str(DATA_DIR),
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return

        try:
            result = load_and_prepare_visual_file(path)
            self.df_loaded = result["df"]
            columns = result["columns"]

            for widget in self.cols_frame.winfo_children():
                widget.destroy()

            self.column_vars.clear()

            for col in columns:
                var = ctk.BooleanVar(value=True)
                cb = ctk.CTkCheckBox(self.cols_frame, text=col, variable=var)
                cb.pack(anchor="w")
                self.column_vars[col] = var

            self.target_menu.configure(values=columns)
            if columns:
                self.target_var.set(columns[0])

            messagebox.showinfo("OK", f"Wczytano plik: {path}")

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def show_data(self, mode: str):
        if self.df_loaded is None:
            messagebox.showerror("Błąd", "Najpierw wczytaj plik CSV")
            return

        selected_cols = [col for col, var in self.column_vars.items() if var.get()]
        if not selected_cols:
            messagebox.showerror("Błąd", "Zaznacz przynajmniej jedną kolumnę")
            return

        try:
            result = prepare_results_analysis(
                df=self.df_loaded,
                selected_cols=selected_cols,
                transformation=self.transformation_var.get(),
                target=self.target_var.get(),
                mode=mode
            )

            self.box.configure(state="normal")
            self.box.delete("1.0", "end")
            self.box.insert("end", result["text"])
            self.box.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Błąd ML", str(e))
