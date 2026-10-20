"""Resizable, paged 2 x 2 Gantt window for the engineering mode button."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from tkinter import filedialog, messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from AOA.config import BASE_DIR, DATA_DIR
from AOA.core.esm_project import ESM_METHODS
from AOA.gui.engineering_charts import build_esm_gantt_grid_figure


class GanttComparisonWindow(ctk.CTkToplevel):
    def __init__(self, parent, results: list[dict]):
        if not results:
            raise ValueError("Brak wynikow do pokazania na Ganttach.")
        super().__init__(parent)
        self.title("Harmonogramy Gantta - wszystkie wybrane metody (2 x 2)")
        self.geometry("1280x860")
        self.minsize(900, 600)
        by_method = {r["method"]: r for r in results}
        self.results = [by_method[m] for m in ESM_METHODS if m in by_method]
        self.figures = []
        self.canvases: list[FigureCanvasTkAgg] = []
        self.toolbars: list[NavigationToolbar2Tk] = []
        self._layout_timers: dict[int, str] = {}
        self._closed = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=f"Wybrane metody: {len(self.results)} | do czterech Ganttow na zakladke | "
            "wspolna skala i kolory zlecen",
            font=("Segoe UI", 14, "bold"),
            wraplength=780,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.export_button = ctk.CTkButton(
            header, text="Zapisz wszystkie Gantty", command=self.export_all
        )
        self.export_button.grid(row=0, column=1, padx=(10, 0))
        self.tabs = ctk.CTkTabview(self, fg_color="#071019")
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        for start in range(0, len(self.results), 4):
            group = self.results[start : start + 4]
            name = f"Metody {start + 1}-{start + len(group)}"
            frame = self.tabs.add(name)
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(1, weight=1)
            toolbar_frame = ctk.CTkFrame(frame, fg_color="#071019")
            toolbar_frame.grid(row=0, column=0, sticky="ew")
            figure = build_esm_gantt_grid_figure(
                group,
                context_results=self.results,
                title=f"Gantty - metody {start + 1}-{start + len(group)} z {len(self.results)}",
            )
            canvas = FigureCanvasTkAgg(figure, master=frame)
            widget = canvas.get_tk_widget()
            widget.configure(background="#071019", highlightthickness=0)
            widget.grid(row=1, column=0, sticky="nsew")
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
            self.figures.append(figure)
            self.canvases.append(canvas)
            self.toolbars.append(toolbar)
            index = len(self.canvases) - 1
            # Keep Matplotlib's own Configure handler: it resizes the figure to
            # the whole canvas. The extra handler only reflows text afterwards.
            widget.bind(
                "<Configure>", lambda _event, index=index: self._schedule_layout(index), add="+"
            )
            canvas.draw()
        ctk.CTkLabel(
            self,
            text="Kazdy panel to osobna metoda. Czerwone obramowanie: opoznione zlecenie. "
            "Linie kropkowane: terminy. Wykresy przedstawiaja harmonogram nominalny.",
            wraplength=1150,
            text_color="#cbd5e1",
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        self.export_status = ctk.StringVar(value="Eksport zapisze każdą zakładkę w PNG i SVG.")
        ctk.CTkLabel(self, textvariable=self.export_status, anchor="w", wraplength=1100).grid(
            row=3, column=0, sticky="ew", padx=12, pady=(0, 8)
        )
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.lift()

    def export_all(self) -> None:
        selected = filedialog.askdirectory(
            parent=self, title="Wybierz folder na Gantty", initialdir=str(BASE_DIR), mustexist=True
        )
        if not selected:
            return
        self.export_button.configure(state="disabled")
        original_sizes = [tuple(figure.get_size_inches()) for figure in self.figures]
        export_size = max(original_sizes, key=lambda size: size[0] * size[1])
        written: list[Path] = []
        bundle: Path | None = None
        try:
            directory = Path(selected).resolve()
            if directory.is_relative_to((DATA_DIR / "esm").resolve()):
                raise ValueError(
                    "Zapisz wykresy poza data/esm, aby zachować folder danych wejściowych."
                )
            # Render first; a failed render must not leave a half-written export.
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            with TemporaryDirectory(prefix=".esm-gantty-", dir=directory) as temporary:
                staging = Path(temporary)
                for index, figure in enumerate(self.figures):
                    figure.set_size_inches(export_size, forward=False)
                    self._layout(index)
                    for extension in ("png", "svg"):
                        figure.savefig(staging / f"gantty_{index + 1:02d}.{extension}", dpi=150)
                candidate = directory / f"esm_gantty_{stamp}"
                candidate.mkdir()
                bundle = candidate
                for source in sorted(staging.iterdir()):
                    destination = bundle / source.name
                    source.rename(destination)
                    written.append(destination)
            self.export_status.set(f"Zapisano {len(written)} plików: {bundle}")
        except (OSError, ValueError, RuntimeError) as exc:
            for path in written:
                path.unlink(missing_ok=True)
            if bundle is not None and bundle.is_dir():
                bundle.rmdir()
            self.export_status.set("Eksport nie został ukończony.")
            messagebox.showerror("Eksport Ganttów", str(exc), parent=self)
        finally:
            for index, (figure, size) in enumerate(zip(self.figures, original_sizes, strict=True)):
                figure.set_size_inches(size, forward=False)
                self._layout(index)
            self.export_button.configure(state="normal")

    def _schedule_layout(self, index: int) -> None:
        if self._closed:
            return
        previous = self._layout_timers.pop(index, None)
        if previous is not None:
            self.after_cancel(previous)
        self._layout_timers[index] = self.after(100, lambda: self._layout(index))

    def _layout(self, index: int) -> None:
        self._layout_timers.pop(index, None)
        if self._closed:
            return
        self.figures[index].tight_layout(rect=(0, 0.055, 1, 0.95), h_pad=3, w_pad=2)
        self.canvases[index].draw_idle()

    def destroy(self) -> None:
        if self._closed:
            return
        self._closed = True
        for timer in self._layout_timers.values():
            self.after_cancel(timer)
        self._layout_timers.clear()
        for figure in self.figures:
            figure.canvas.toolbar = None
            figure.clear()
        super().destroy()
