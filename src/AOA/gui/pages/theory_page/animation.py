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
        self.example_values = {"mt": 0.60, "mo": 0.30, "mzo": 0.10, "gen": 0.20}
        self.step_index = 0
        self._after_id: str | None = None
        self._resume_after_id: str | None = None
        self.is_playing = False
        self.autoplay_enabled = True
        self.on_step_changed = on_step_changed
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self) -> None:
        self.title = label(self, "Animacja dzialania modelu", size=16, weight="bold")
        self.title.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))
        self.canvas = tk.Canvas(
            self, height=420, bg="#101922", highlightthickness=1, highlightbackground="#252c34"
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _event: self._draw_canvas())

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        controls.grid_columnconfigure(4, weight=1)
        self.prev_btn = ctk.CTkButton(controls, text="<<", width=38, command=self.previous_step)
        self.prev_btn.grid(row=0, column=0, padx=(0, 6))
        self.play_btn = ctk.CTkButton(controls, text="Play", width=54, command=self.toggle_play)
        self.play_btn.grid(row=0, column=1, padx=6)
        self.next_btn = ctk.CTkButton(controls, text=">>", width=38, command=self.next_step)
        self.next_btn.grid(row=0, column=2, padx=6)
        self.step_label = label(controls, "Krok 1 / 12", size=13, weight="bold")
        self.step_label.grid(row=0, column=3, padx=(16, 8), sticky="w")
        self.slider = ctk.CTkSlider(
            controls, from_=1, to=12, number_of_steps=11, command=self._slider_changed
        )
        self.slider.grid(row=0, column=4, padx=8, sticky="ew")
        label(controls, "Tempo", size=12, weight="bold").grid(row=0, column=5, padx=(14, 6))
        self.speed = ctk.CTkOptionMenu(controls, values=["0.75x", "1.0x", "1.5x"], width=84)
        self.speed.set("1.0x")
        self.speed.grid(row=0, column=6, padx=(0, 2))

    def set_model(self, model: TheoryModel) -> None:
        self.stop(cancel_resume=True)
        self.model = model
        self.step_index = 0
        self._configure_slider()
        self._refresh(emit=True)
        self.start_autoplay()

    def set_example_values(self, values: dict[str, float]) -> None:
        self.example_values.update(values)
        self._draw_canvas()

    @property
    def total_steps(self) -> int:
        return max(1, len(self.model.steps) if self.model is not None else 12)

    def _configure_slider(self) -> None:
        total = self.total_steps
        self.slider.configure(from_=1, to=total, number_of_steps=max(total - 1, 1))

    def set_step(self, index: int, *, emit: bool = True, user_action: bool = False) -> None:
        if user_action:
            self.pause_for_reading()
        self.step_index = max(0, min(self.total_steps - 1, index))
        self._refresh(emit=emit)

    def previous_step(self) -> None:
        self.set_step(self.step_index - 1, user_action=True)

    def next_step(self) -> None:
        self.set_step((self.step_index + 1) % self.total_steps, user_action=True)

    def toggle_play(self) -> None:
        if self.is_playing:
            self.autoplay_enabled = False
            self.stop(cancel_resume=True)
        else:
            self.autoplay_enabled = True
            self.start_autoplay()

    def start_autoplay(self) -> None:
        if self.is_playing or not self.autoplay_enabled:
            return
        self.is_playing = True
        self.play_btn.configure(text="Stop")
        self._schedule_next(initial=True)

    def pause_for_reading(self, delay_ms: int = 4500) -> None:
        if not self.autoplay_enabled:
            return
        self.stop(cancel_resume=False)
        if self._resume_after_id is not None:
            self.after_cancel(self._resume_after_id)
        self._resume_after_id = self.after(delay_ms, self._resume_after_pause)

    def _resume_after_pause(self) -> None:
        self._resume_after_id = None
        self.start_autoplay()

    def stop(self, *, cancel_resume: bool = True) -> None:
        self.is_playing = False
        self.play_btn.configure(text="Play")
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        if cancel_resume and self._resume_after_id is not None:
            self.after_cancel(self._resume_after_id)
            self._resume_after_id = None

    def _schedule_next(self, *, initial: bool = False) -> None:
        delay = {"0.75x": 13000, "1.0x": 10000, "1.5x": 7000}.get(self.speed.get(), 10000)
        self._after_id = self.after(10000 if initial else delay, self._play_tick)

    def _play_tick(self) -> None:
        if not self.is_playing:
            return
        self.set_step((self.step_index + 1) % self.total_steps)
        self._schedule_next()

    def _slider_changed(self, value: float) -> None:
        self.set_step(int(round(value)) - 1, user_action=True)

    def _refresh(self, *, emit: bool = True) -> None:
        if self.model is None:
            return
        self.title.configure(text=f"Animacja dzialania modelu: {self.model.title}")
        self.step_label.configure(text=f"Krok {self.step_index + 1} / {self.total_steps}")
        self.slider.set(self.step_index + 1)
        self._draw_canvas()
        if emit and self.on_step_changed is not None:
            self.on_step_changed(self.step_index)

    def _draw_canvas(self) -> None:
        if self.model is None:
            return
        c = self.canvas
        c.delete("all")
        width = max(c.winfo_width(), 920)
        height = max(c.winfo_height(), 420)
        c.configure(scrollregion=(0, 0, width, height))
        self._draw_stepper(c, width)
        if self.model.family == "mh":
            self._draw_mh(c, width, height)
        else:
            self._draw_ml(c, width, height)

    def _draw_stepper(self, c: tk.Canvas, width: int) -> None:
        assert self.model is not None
        total = self.total_steps
        y = 36
        left = 58
        right = width - 58
        gap = (right - left) / max(total - 1, 1)
        c.create_line(left, y, right, y, fill="#3d4652", width=3)
        c.create_line(left, y, left + gap * self.step_index, y, fill=BLUE, width=3)
        for i in range(total):
            x = left + gap * i
            current = i == self.step_index
            active = i <= self.step_index
            radius = 13 if current else 9
            c.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=BLUE if active else "#4b5563",
                outline="#93c5fd" if current else "#38424c",
                width=2 if current else 1,
            )
        c.create_text(
            width / 2,
            70,
            text=f"Krok {self.step_index + 1}: {self.model.steps[self.step_index]}",
            fill="#f8fafc",
            font=("Segoe UI", 12, "bold"),
        )
        c.create_text(
            width / 2,
            94,
            text=self.model.step_details[self.step_index],
            fill=TEXT_MUTED,
            font=("Segoe UI", 9),
            width=min(780, width - 90),
        )

    @staticmethod
    def _ml_visual_kind(model: TheoryModel) -> str:
        algorithm = model.algorithm.lower()
        if "logist" in algorithm:
            return "logistic"
        if "histgradient" in algorithm:
            return "hist"
        if "gradient" in algorithm:
            return "boost"
        if "extra" in algorithm:
            return "extra"
        return "forest"

    @staticmethod
    def _ml_stage_caption(kind: str) -> str:
        if kind == "logistic":
            return "regresja logistyczna: wagi cech, softmax i prawdopodobienstwa klas"
        if kind == "boost":
            return "Gradient Boosting: kolejne drzewa poprawiaja blad poprzedniej predykcji"
        if kind == "hist":
            return "HistGradient: wartosci trafiaja do koszykow, a boosting poprawia gradient bledu"
        if kind == "extra":
            return "ExtraTrees: wiele drzew z mocniej losowanymi progami podzialu"
        return "Random Forest: wiele drzew na losowych probkach i agregacja wyniku"

    def _draw_ml(self, c: tk.Canvas, width: int, height: int) -> None:
        assert self.model is not None
        active = self.step_index
        top = 104
        panel_h = max(132, height - top - 18)
        kind = self._ml_visual_kind(self.model)
        task = (
            "strategia"
            if self.model.key.startswith("Schedule")
            else ("opoznienie" if self.model.key.startswith("Delay") else "jakosc")
        )

        data_x1, data_x2 = 36, 226
        model_x1, model_x2 = 264, width - 282
        result_x1, result_x2 = width - 244, width - 36

        self._panel(c, data_x1, top, data_x2, top + panel_h, "Rekord danych", active >= 0)
        values = self.example_values
        rows = [
            ("ID", "1"),
            ("Cel", task),
            ("czas_h", f"{8 + values['mt'] * 6:.1f}"),
            ("termin_h", f"{24 + values['mo'] * 42:.1f}"),
            ("koszt", f"{100 + values['mzo'] * 160:.0f}"),
            ("material", f"{values['gen']:.2f}"),
        ]
        for i, (name, value) in enumerate(rows):
            y = top + 38 + i * 22
            if i >= 2:
                c.create_rectangle(
                    data_x1 + 22,
                    y - 10,
                    data_x2 - 22,
                    y + 10,
                    fill="#1f4f85" if 2 <= active <= 4 else "#202831",
                    outline="#314155",
                )
            c.create_text(
                data_x1 + 34,
                y,
                text=name,
                fill="white",
                anchor="w",
                font=("Segoe UI", 9, "bold" if i < 2 else "normal"),
            )
            c.create_text(
                data_x2 - 30, y, text=value, fill="#dbeafe", anchor="e", font=("Segoe UI", 9)
            )
        if active >= 1:
            c.create_rectangle(
                data_x1 + 22,
                top + panel_h - 58,
                data_x2 - 22,
                top + panel_h - 18,
                fill="#172554",
                outline="#3b82f6",
            )
            c.create_text(
                (data_x1 + data_x2) / 2,
                top + panel_h - 45,
                text="train/test",
                fill="#dbeafe",
                font=("Segoe UI", 8, "bold"),
            )
            c.create_text(
                (data_x1 + data_x2) / 2,
                top + panel_h - 30,
                text="walidacja modelu",
                fill="#93c5fd",
                font=("Segoe UI", 7),
            )

        self._draw_ml_token(c, width, top, panel_h, active)
        self._arrow(
            c, data_x2 + 6, top + panel_h / 2, model_x1 - 10, top + panel_h / 2, active >= 2
        )
        self._panel(c, model_x1, top, model_x2, top + panel_h, self.model.algorithm, active >= 3)
        self._draw_ml_core(c, model_x1, model_x2, top, panel_h, active, kind)
        self._arrow(
            c, model_x2 + 8, top + panel_h / 2, result_x1 - 8, top + panel_h / 2, active >= 7
        )
        self._panel(c, result_x1, top, result_x2, top + panel_h, "Wynik modelu", active >= 7)

        for i, (prob_name, prob_value) in enumerate(self.model.probabilities):
            y = top + 46 + i * 38
            bar_w = int((result_x2 - result_x1 - 72) * prob_value)
            color = [BLUE, GREEN, PURPLE][i % 3]
            bar_x1, bar_x2 = result_x1 + 26, result_x2 - 24
            c.create_rectangle(bar_x1, y - 13, bar_x2, y + 13, fill="#202831", outline="#2f3a45")
            c.create_rectangle(
                bar_x1,
                y - 13,
                bar_x1 + bar_w,
                y + 13,
                fill=color if active >= 8 else "#3a4350",
                outline="",
            )
            c.create_text(
                bar_x1 + 8, y, text=prob_name, fill="#f8fafc", anchor="w", font=("Segoe UI", 8)
            )
            c.create_text(
                bar_x2 - 8,
                y,
                text=f"{prob_value:.2f}",
                fill="#f8fafc",
                anchor="e",
                font=("Segoe UI", 8),
            )
        c.create_rectangle(
            result_x1 + 26,
            top + panel_h - 46,
            result_x2 - 24,
            top + panel_h - 16,
            fill="#234a2d" if active >= 10 else "#252c34",
            outline="#31523a",
        )
        c.create_text(
            (result_x1 + result_x2) / 2,
            top + panel_h - 31,
            text=self.model.result,
            fill="#dcfce7",
            font=("Segoe UI", 9, "bold"),
            width=result_x2 - result_x1 - 60,
        )
        if self.step_index >= 3:
            c.create_text(
                (model_x1 + model_x2) / 2,
                top + 48,
                text=self._ml_stage_caption(kind),
                fill="#bfdbfe",
                font=("Segoe UI", 9, "bold"),
                width=model_x2 - model_x1 - 36,
            )

    def _draw_ml_core(
        self, c: tk.Canvas, x1: float, x2: float, top: int, panel_h: int, active: int, kind: str
    ) -> None:
        x_mid = (x1 + x2) / 2
        core_w = max(260, x2 - x1)
        if kind == "logistic":
            axis_left, axis_right = x1 + 42, x2 - 42
            axis_bottom, axis_top = top + panel_h - 72, top + 78
            c.create_line(
                axis_left,
                axis_bottom,
                axis_right,
                axis_bottom,
                fill="#64748b",
                width=2,
                arrow=tk.LAST,
            )
            c.create_line(
                axis_left, axis_bottom, axis_left, axis_top, fill="#64748b", width=2, arrow=tk.LAST
            )
            c.create_line(
                axis_left + 10,
                axis_bottom - 24,
                axis_right - 10,
                axis_top + 22,
                fill=YELLOW,
                width=3,
            )
            for px, py, color in [
                (axis_left + core_w * 0.16, axis_bottom - 42, BLUE),
                (axis_left + core_w * 0.34, axis_bottom - 62, GREEN),
                (axis_left + core_w * 0.56, axis_bottom - 104, PURPLE),
            ]:
                c.create_oval(
                    px - 8,
                    py - 8,
                    px + 8,
                    py + 8,
                    fill=color if active >= 4 else "#475569",
                    outline="",
                )
            if active >= 5:
                c.create_text(
                    x_mid,
                    top + 84,
                    text="softmax -> P(A), P(B), P(C)",
                    fill="#dbeafe",
                    font=("Segoe UI", 9, "bold"),
                )
            if active >= 8:
                c.create_text(
                    x_mid,
                    top + panel_h - 30,
                    text="regularizacja ogranicza zbyt duze wagi",
                    fill="#c4b5fd",
                    font=("Segoe UI", 9, "bold"),
                )
            return

        if kind in {"boost", "hist"}:
            labels = ["start", "blad", "drzewo +", "blad", "drzewo +"]
            item_w = min(72, max(54, (core_w - 78) / len(labels)))
            gap = (core_w - 56 - item_w * len(labels)) / max(1, len(labels) - 1)
            x0 = x1 + 28
            y_box = top + panel_h * 0.46
            for i, text in enumerate(labels):
                x = x0 + i * (item_w + gap)
                fill = [BLUE, "#ef4444", GREEN, "#f97316", PURPLE][i]
                c.create_rectangle(
                    x,
                    y_box - 26,
                    x + item_w,
                    y_box + 26,
                    fill=fill if active >= i + 2 else "#334155",
                    outline="#cbd5e1",
                )
                c.create_text(
                    x + item_w / 2,
                    y_box,
                    text=text,
                    fill="white",
                    font=("Segoe UI", 8, "bold"),
                    width=item_w - 8,
                )
                if i < len(labels) - 1:
                    self._arrow(
                        c, x + item_w + 4, y_box, x + item_w + gap - 4, y_box, active >= i + 3
                    )
            if kind == "hist":
                for i in range(5):
                    bx = x_mid - 112 + i * 56
                    c.create_rectangle(
                        bx,
                        top + 76,
                        bx + 38,
                        top + 108,
                        fill="#1e3a8a" if active >= 2 else "#334155",
                        outline="#93c5fd",
                    )
                c.create_text(
                    x_mid,
                    top + 60,
                    text="koszyki wartosci / histogramy",
                    fill="#bfdbfe",
                    font=("Segoe UI", 9, "bold"),
                )
            if active >= 8:
                c.create_text(
                    x_mid,
                    top + panel_h - 32,
                    text="early stopping: walidacja zatrzymuje uczenie",
                    fill="#fde68a",
                    font=("Segoe UI", 9, "bold"),
                )
            return

        top_y = top + 92
        bottom_y = top + panel_h - 104
        offsets = [-0.34, 0.0, 0.34, -0.18, 0.18]
        y_positions = [top_y, top_y - 12, top_y, bottom_y, bottom_y]
        for i, (offset, y) in enumerate(zip(offsets, y_positions, strict=True)):
            x = x_mid + offset * core_w
            text = f"drzewo {i + 1}" if kind == "forest" else f"losowe {i + 1}"
            c.create_rectangle(
                x - 42,
                y - 22,
                x + 42,
                y + 22,
                fill="#1f2937",
                outline="#93c5fd" if active >= 3 else "#475569",
                width=2,
            )
            c.create_text(x, y, text=text, fill="#dbeafe", font=("Segoe UI", 8, "bold"))
            if active >= 4:
                self._draw_tiny_split(c, x, y + 42, active, random_threshold=(kind == "extra"))
        if active >= 7:
            c.create_rectangle(
                x_mid - 96,
                top + panel_h - 52,
                x_mid + 96,
                top + panel_h - 18,
                fill="#123f78",
                outline="#bfdbfe",
            )
            c.create_text(
                x_mid,
                top + panel_h - 35,
                text="srednia / glosowanie",
                fill="#f8fafc",
                font=("Segoe UI", 9, "bold"),
            )

    def _draw_tiny_split(
        self, c: tk.Canvas, x: float, y: float, active: int, *, random_threshold: bool
    ) -> None:
        color = YELLOW if random_threshold else GREEN
        c.create_line(x, y, x - 22, y + 24, fill=color, width=2)
        c.create_line(x, y, x + 22, y + 24, fill=color, width=2)
        c.create_oval(x - 7, y - 7, x + 7, y + 7, fill=color, outline="")
        if active >= 5:
            c.create_text(
                x,
                y + 38,
                text="losowy prog" if random_threshold else "najlepszy prog",
                fill="#cbd5e1",
                font=("Segoe UI", 7),
            )

    def _draw_ml_token(self, c: tk.Canvas, width: int, top: int, panel_h: int, active: int) -> None:
        route = [
            (125, top + panel_h / 2),
            (125, top + panel_h - 38),
            (250, top + panel_h / 2),
            (width / 2 - 120, top + 130),
            (width / 2 - 55, top + 110),
            (width / 2 + 20, top + 130),
            (width / 2 + 92, top + 130),
            (width / 2, top + panel_h - 42),
            (width - 264, top + panel_h / 2),
            (width - 168, top + 82),
            (width - 132, top + panel_h - 28),
            (width - 88, top + panel_h - 28),
        ]
        x, y = route[max(0, min(active, len(route) - 1))]
        c.create_oval(x - 8, y - 8, x + 8, y + 8, fill=YELLOW, outline="#fff7ad", width=2)
        c.create_text(x, y - 18, text="rekord", fill="#fde68a", font=("Segoe UI", 8, "bold"))

    def _draw_mh(self, c: tk.Canvas, width: int, height: int) -> None:
        assert self.model is not None
        active = self.step_index
        top = 104
        panel_h = max(132, height - top - 18)
        jobs = [("J1", 6, 30), ("J2", 4, 20), ("J3", 2, 12), ("J4", 7, 25)]
        self._panel(c, 36, top, 210, top + panel_h, "Zlecenia STO", active >= 0)
        for i, (job, p, d) in enumerate(jobs):
            y = top + 45 + i * 28
            c.create_rectangle(58, y - 11, 190, y + 11, fill="#202831", outline="#2f3a45")
            c.create_text(72, y, text=job, fill="white", anchor="w", font=("Segoe UI", 9, "bold"))
            c.create_text(126, y, text=f"p={p}", fill="#dbeafe", font=("Segoe UI", 9))
            c.create_text(174, y, text=f"d={d}", fill="#dbeafe", font=("Segoe UI", 9))
        self._arrow(c, 226, top + panel_h / 2, 266, top + panel_h / 2, active >= 2)
        self._panel(c, 282, top, width - 326, top + panel_h, "Regula i symulacja", active >= 2)
        c.create_text(
            width / 2 - 20,
            top + 43,
            text=self.model.algorithm,
            fill="#f8fafc",
            font=("Segoe UI", 14, "bold"),
        )
        c.create_text(
            width / 2 - 20,
            top + 72,
            text=self.model.focus,
            fill="#cbd5e1",
            font=("Segoe UI", 10),
            width=250,
        )
        order = (
            ["J4", "J1", "J2", "J3"]
            if "LPT" in self.model.algorithm or self.model.key in {"MZO", "LPT_EDD"}
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
            for i, (name, value) in enumerate([("Tj", "0 / 0 / 0 / 7"), ("T+", "7"), ("STO", "7")]):
                y = top + panel_h - 62 + i * 18
                c.create_text(
                    width / 2 - 150, y, text=name, fill=TEXT_MUTED, anchor="w", font=("Segoe UI", 9)
                )
                c.create_text(
                    width / 2 + 150,
                    y,
                    text=value,
                    fill="#f8fafc",
                    anchor="e",
                    font=("Segoe UI", 9, "bold"),
                )
        self._arrow(c, width - 310, top + panel_h / 2, width - 268, top + panel_h / 2, active >= 9)
        self._panel(c, width - 252, top, width - 36, top + panel_h, "Ranking STO", active >= 9)
        for i, (name, score) in enumerate(
            [(self.model.short_title, "7"), ("MT / EDD", "9"), ("MO / SPT", "11"), ("GENETIC", "6")]
        ):
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
        route = [
            (128, top + 45),
            (128, top + 74),
            (304, top + panel_h / 2),
            (width / 2 - 120, top + 128),
            (width / 2 - 82, top + 128),
            (width / 2 - 28, top + 160),
            (width / 2 + 45, top + panel_h - 44),
            (width / 2 + 120, top + panel_h - 26),
            (width / 2 + 155, top + 128),
            (width - 290, top + panel_h / 2),
            (width - 145, top + 48),
            (width - 144, top + panel_h - 28),
        ]
        token_x, token_y = route[max(0, min(active, len(route) - 1))]
        c.create_oval(
            token_x - 8,
            token_y - 8,
            token_x + 8,
            token_y + 8,
            fill=YELLOW,
            outline="#fff7ad",
            width=2,
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
        c.create_line(
            x1,
            y1,
            x2,
            y2,
            fill=BLUE if active else "#49525d",
            width=3,
            arrow=tk.LAST,
            arrowshape=(12, 14, 5),
        )
