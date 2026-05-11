from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .data import TheoryModel
from .widgets import BG_CARD, BLUE, BORDER, GREEN, PURPLE, TEXT_MUTED, YELLOW, label


class ModelAnimationCard(ctk.CTkFrame):
    def __init__(self, parent, on_step_changed: Callable[[int], None] | None = None):
        super().__init__(
            parent, corner_radius=14, fg_color=BG_CARD, border_width=1, border_color=BORDER
        )
        self.model: TheoryModel | None = None
        self.step_index = 0
        self._after_id: str | None = None
        self.is_playing = False
        self.on_step_changed = on_step_changed
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self) -> None:
        self.title = label(self, "Animacja działania modelu", size=16, weight="bold")
        self.title.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))

        self.canvas = tk.Canvas(
            self, height=390, bg="#101922", highlightthickness=1, highlightbackground="#252c34"
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self.canvas.bind("<Configure>", lambda _event: self._draw_canvas())

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        controls.grid_columnconfigure(4, weight=1)
        self.prev_btn = ctk.CTkButton(controls, text="⏮", width=38, command=self.previous_step)
        self.prev_btn.grid(row=0, column=0, padx=(0, 6))
        self.play_btn = ctk.CTkButton(controls, text="▶", width=44, command=self.toggle_play)
        self.play_btn.grid(row=0, column=1, padx=6)
        self.next_btn = ctk.CTkButton(controls, text="⏭", width=38, command=self.next_step)
        self.next_btn.grid(row=0, column=2, padx=6)
        self.step_label = label(controls, "Krok 1 / 12", size=13, weight="bold")
        self.step_label.grid(row=0, column=3, padx=(16, 8), sticky="w")
        self.slider = ctk.CTkSlider(
            controls, from_=1, to=12, number_of_steps=11, command=self._slider_changed
        )
        self.slider.grid(row=0, column=4, padx=8, sticky="ew")
        self.auto_label = label(controls, "Tempo", size=12, weight="bold")
        self.auto_label.grid(row=0, column=5, padx=(14, 6))
        self.speed = ctk.CTkOptionMenu(controls, values=["0.75x", "1.0x", "1.5x"], width=84)
        self.speed.set("1.0x")
        self.speed.grid(row=0, column=6, padx=(0, 2))

    def set_model(self, model: TheoryModel) -> None:
        self.stop()
        self.model = model
        self.step_index = 0
        self._configure_slider()
        self._refresh(emit=True)

    def _configure_slider(self) -> None:
        total = self.total_steps
        self.slider.configure(from_=1, to=total, number_of_steps=max(total - 1, 1))

    @property
    def total_steps(self) -> int:
        return max(1, len(self.model.steps) if self.model is not None else 12)

    def set_step(self, index: int, *, emit: bool = True) -> None:
        self.step_index = max(0, min(self.total_steps - 1, index))
        self._refresh(emit=emit)

    def previous_step(self) -> None:
        self.set_step(self.step_index - 1)

    def next_step(self) -> None:
        self.set_step((self.step_index + 1) % self.total_steps)

    def toggle_play(self) -> None:
        if self.is_playing:
            self.stop()
        else:
            self.is_playing = True
            self.play_btn.configure(text="Ⅱ")
            self._schedule_next()

    def stop(self) -> None:
        self.is_playing = False
        self.play_btn.configure(text="▶")
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _schedule_next(self) -> None:
        factor = {"0.75x": 1500, "1.0x": 1150, "1.5x": 780}.get(self.speed.get(), 1150)
        self._after_id = self.after(factor, self._play_tick)

    def _play_tick(self) -> None:
        if not self.is_playing:
            return
        self.next_step()
        self._schedule_next()

    def _slider_changed(self, value: float) -> None:
        self.set_step(int(round(value)) - 1)

    def _refresh(self, *, emit: bool = True) -> None:
        if self.model is None:
            return
        self.title.configure(text=f"Animacja działania modelu: {self.model.title}")
        self.step_label.configure(text=f"Krok {self.step_index + 1} / {self.total_steps}")
        self.slider.set(self.step_index + 1)
        self._draw_canvas()
        if emit and self.on_step_changed is not None:
            self.on_step_changed(self.step_index)

    def _draw_canvas(self) -> None:
        model = self.model
        if model is None:
            return
        c = self.canvas
        c.delete("all")
        width = max(c.winfo_width(), 820)
        height = max(c.winfo_height(), 390)
        c.configure(scrollregion=(0, 0, width, height))
        self._draw_stepper(c, width)
        if model.family == "mh":
            self._draw_mh(c, width, height)
        else:
            self._draw_ml(c, width, height)

    def _phase(self) -> int:
        return min(3, int(self.step_index / max(1, self.total_steps / 4)))

    def _draw_stepper(self, c: tk.Canvas, width: int) -> None:
        model = self.model
        if model is None:
            return
        total = self.total_steps
        y = 36
        left = 58
        right = width - 58
        gap = (right - left) / max(total - 1, 1)
        c.create_line(left, y, right, y, fill="#3d4652", width=3)
        c.create_line(left, y, left + gap * self.step_index, y, fill=BLUE, width=3)
        for i in range(total):
            x = left + gap * i
            active = i <= self.step_index
            current = i == self.step_index
            radius = 13 if current else 9
            fill = BLUE if active else "#4b5563"
            c.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=fill,
                outline="#93c5fd" if current else "#38424c",
                width=2 if current else 1,
            )
            if current or i in {0, total - 1}:
                c.create_text(x, y, text=str(i + 1), fill="white", font=("Segoe UI", 8, "bold"))
        title = model.steps[self.step_index]
        c.create_text(
            width / 2,
            70,
            text=f"Krok {self.step_index + 1}: {title}",
            fill="#f8fafc",
            font=("Segoe UI", 12, "bold"),
        )
        c.create_text(
            width / 2,
            94,
            text=model.step_details[self.step_index],
            fill=TEXT_MUTED,
            font=("Segoe UI", 9),
            width=min(760, width - 90),
        )

    def _draw_ml(self, c: tk.Canvas, width: int, height: int) -> None:
        active = self.step_index
        phase = self._phase()
        top = 130
        panel_h = max(145, height - top - 18)
        self._panel(c, 36, top, 194, top + panel_h, "Instancja", active >= 0)
        rows = [
            ("ID", "1"),
            ("Klasa", "A"),
            ("MT", "0.60"),
            ("MO", "0.30"),
            ("MZO", "0.10"),
            ("GEN", "0.20"),
        ]
        for i, (k, v) in enumerate(rows):
            y = top + 38 + i * 22
            if i >= 2:
                c.create_rectangle(
                    58,
                    y - 10,
                    172,
                    y + 10,
                    fill="#1f4f85" if 2 <= active <= 4 else "#202831",
                    outline="#314155",
                )
            c.create_text(
                70,
                y,
                text=k,
                fill="white",
                anchor="w",
                font=("Segoe UI", 9, "bold" if i < 2 else "normal"),
            )
            c.create_text(164, y, text=v, fill="#dbeafe", anchor="e", font=("Segoe UI", 9))
        if active >= 2:
            c.create_text(
                115,
                top + panel_h - 22,
                text="cechy po skalowaniu",
                fill="#93c5fd",
                font=("Segoe UI", 8, "bold"),
            )
        self._arrow(c, 210, top + panel_h / 2, 250, top + panel_h / 2, active >= 3)
        self._panel(c, 266, top, width - 300, top + panel_h, "Model uczący się", active >= 3)
        self._draw_tree(c, (width - 34 - 300 + 266) / 2, top + 55, active)
        if active >= 7:
            for offset, label_text in [(-95, "drzewo 1"), (0, "drzewo 2"), (95, "drzewo 3")]:
                c.create_rectangle(
                    (width / 2) + offset - 38,
                    top + panel_h - 50,
                    (width / 2) + offset + 38,
                    top + panel_h - 25,
                    fill="#223149",
                    outline="#3b5f86",
                )
                c.create_text(
                    (width / 2) + offset,
                    top + panel_h - 37,
                    text=label_text,
                    fill="#dbeafe",
                    font=("Segoe UI", 8, "bold"),
                )
        self._arrow(c, width - 284, top + panel_h / 2, width - 246, top + panel_h / 2, active >= 8)
        self._panel(c, width - 230, top, width - 36, top + panel_h, "Wynik", active >= 8)
        model = self.model
        assert model is not None
        for i, (name, value) in enumerate(model.probabilities):
            y = top + 46 + i * 38
            bar_w = int(126 * value)
            color = [BLUE, GREEN, PURPLE][i % 3]
            c.create_rectangle(
                width - 204, y - 13, width - 58, y + 13, fill="#202831", outline="#2f3a45"
            )
            c.create_rectangle(
                width - 204,
                y - 13,
                width - 204 + bar_w,
                y + 13,
                fill=color if active >= 9 else "#3a4350",
                outline="",
            )
            c.create_text(
                width - 196, y, text=name, fill="#f8fafc", anchor="w", font=("Segoe UI", 8)
            )
            c.create_text(
                width - 66, y, text=f"{value:.2f}", fill="#f8fafc", anchor="e", font=("Segoe UI", 8)
            )
        c.create_rectangle(
            width - 204,
            top + panel_h - 42,
            width - 58,
            top + panel_h - 14,
            fill="#234a2d" if active >= 10 else "#252c34",
            outline="#31523a",
        )
        c.create_text(
            width - 131,
            top + panel_h - 28,
            text=model.result,
            fill="#dcfce7",
            font=("Segoe UI", 9, "bold"),
            width=136,
        )
        if phase >= 1:
            c.create_text(
                width / 2,
                top + 28,
                text="model wybiera cechy i progi, które zmniejszają błąd",
                fill="#bfdbfe",
                font=("Segoe UI", 9, "bold"),
            )

    def _draw_mh(self, c: tk.Canvas, width: int, height: int) -> None:
        active = self.step_index
        top = 130
        panel_h = max(145, height - top - 18)
        jobs = [("J1", 6, 30), ("J2", 4, 20), ("J3", 2, 12), ("J4", 7, 25)]
        self._panel(c, 36, top, 210, top + panel_h, "Zlecenia", active >= 0)
        for i, (job, p, d) in enumerate(jobs):
            y = top + 45 + i * 28
            c.create_rectangle(58, y - 11, 190, y + 11, fill="#202831", outline="#2f3a45")
            c.create_text(72, y, text=job, fill="white", anchor="w", font=("Segoe UI", 9, "bold"))
            c.create_text(126, y, text=f"p={p}", fill="#dbeafe", font=("Segoe UI", 9))
            c.create_text(174, y, text=f"d={d}", fill="#dbeafe", font=("Segoe UI", 9))
        self._arrow(c, 226, top + panel_h / 2, 266, top + panel_h / 2, active >= 2)
        self._panel(c, 282, top, width - 326, top + panel_h, "Reguła i symulacja", active >= 2)
        model = self.model
        assert model is not None
        c.create_text(
            width / 2 - 20,
            top + 43,
            text=model.algorithm,
            fill="#f8fafc",
            font=("Segoe UI", 14, "bold"),
        )
        c.create_text(
            width / 2 - 20,
            top + 72,
            text=model.focus,
            fill="#cbd5e1",
            font=("Segoe UI", 10),
            width=250,
        )
        order = (
            ["J4", "J1", "J2", "J3"]
            if "LPT" in model.algorithm or model.key in {"MZO", "LPT_EDD"}
            else ["J3", "J2", "J1", "J4"]
        )
        x = width / 2 - 150
        for i, job in enumerate(order):
            w = [64, 52, 44, 34][i]
            c.create_rectangle(
                x, top + 112, x + w, top + 145, fill=[BLUE, GREEN, YELLOW, PURPLE][i], outline=""
            )
            c.create_text(
                x + w / 2, top + 128, text=job, fill="white", font=("Segoe UI", 9, "bold")
            )
            if active >= 5:
                c.create_text(
                    x + w / 2,
                    top + 160,
                    text=f"C={sum([7, 6, 4, 2][: i + 1])}",
                    fill="#cbd5e1",
                    font=("Segoe UI", 8),
                )
            x += w + 8
        if active >= 6:
            metrics = [("Tj", "0 / 0 / 0 / 7"), ("T+", "7"), ("STO", "7")]
            for i, (k, v) in enumerate(metrics):
                y = top + panel_h - 62 + i * 18
                c.create_text(
                    width / 2 - 150, y, text=k, fill=TEXT_MUTED, anchor="w", font=("Segoe UI", 9)
                )
                c.create_text(
                    width / 2 + 150,
                    y,
                    text=v,
                    fill="#f8fafc",
                    anchor="e",
                    font=("Segoe UI", 9, "bold"),
                )
        self._arrow(c, width - 310, top + panel_h / 2, width - 268, top + panel_h / 2, active >= 9)
        self._panel(c, width - 252, top, width - 36, top + panel_h, "Ranking STO", active >= 9)
        rows = [(model.short_title, "7"), ("MT / EDD", "9"), ("MO / SPT", "11"), ("GENETIC", "6")]
        for i, (name, score) in enumerate(rows):
            y = top + 48 + i * 30
            fill = "#234a2d" if active >= 10 and i == 0 else "#202831"
            c.create_rectangle(
                width - 226, y - 12, width - 62, y + 12, fill=fill, outline="#2f3a45"
            )
            c.create_text(
                width - 216,
                y,
                text=name,
                fill="#f8fafc",
                anchor="w",
                font=("Segoe UI", 8, "bold" if i == 0 else "normal"),
            )
            c.create_text(
                width - 70, y, text=score, fill="#dbeafe", anchor="e", font=("Segoe UI", 8, "bold")
            )
        if active >= 11:
            c.create_rectangle(
                width - 226,
                top + panel_h - 42,
                width - 62,
                top + panel_h - 14,
                fill="#123f2a",
                outline="#31523a",
            )
            c.create_text(
                width - 144,
                top + panel_h - 28,
                text="wybrana kolejka",
                fill="#dcfce7",
                font=("Segoe UI", 9, "bold"),
            )

    def _panel(
        self, c: tk.Canvas, x1: float, y1: float, x2: float, y2: float, title: str, active: bool
    ) -> None:
        c.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill="#181d22",
            outline=BLUE if active else "#34404a",
            width=2 if active else 1,
        )
        c.create_text(
            (x1 + x2) / 2, y1 + 19, text=title, fill="#f8fafc", font=("Segoe UI", 10, "bold")
        )

    def _arrow(
        self, c: tk.Canvas, x1: float, y1: float, x2: float, y2: float, active: bool
    ) -> None:
        color = BLUE if active else "#49525d"
        c.create_line(x1, y1, x2, y2, fill=color, width=3, arrow=tk.LAST, arrowshape=(12, 14, 5))

    def _draw_tree(self, c: tk.Canvas, x: float, y: float, active: int) -> None:
        colors = [BLUE, GREEN, PURPLE, "#9ca3af", "#6b7280"]
        points = [
            (x, y),
            (x - 62, y + 52),
            (x + 62, y + 52),
            (x - 100, y + 102),
            (x - 40, y + 102),
            (x + 40, y + 102),
            (x + 100, y + 102),
        ]
        edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]
        for a, b in edges:
            c.create_line(
                *points[a], *points[b], fill="#6b7280" if active >= 4 else "#374151", width=2
            )
        for i, (px, py) in enumerate(points):
            fill = colors[i % len(colors)] if active >= 4 else "#3d4652"
            radius = 13 if (active >= 5 and i in {1, 4}) else 10
            c.create_oval(
                px - radius, py - radius, px + radius, py + radius, fill=fill, outline="#cbd5e1"
            )
            if active >= 6 and i in {3, 4, 5, 6}:
                c.create_text(px, py + 21, text="głos", fill="#cbd5e1", font=("Segoe UI", 7))
