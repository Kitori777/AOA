from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .data import TheoryModel
from .widgets import BG_CARD, BLUE, BORDER, GREEN, PURPLE, YELLOW, label


class ModelAnimationCard(ctk.CTkFrame):
    """Jedna, filmowa animacja dla TheoryPage."""

    def __init__(self, parent, on_step_changed: Callable[[int], None] | None = None):
        super().__init__(
            parent, corner_radius=14, fg_color=BG_CARD, border_width=1, border_color=BORDER
        )
        self.model: TheoryModel | None = None
        self.example_values = {"mt": 0.60, "mo": 0.30, "mzo": 0.10, "gen": 0.20}
        self.step_index = 0
        self._autoplay_after_id: str | None = None
        self._motion_after_id: str | None = None
        self._type_after_id: str | None = None
        self._resume_after_id: str | None = None
        self._text_reveal = 0
        self._pulse = 0
        self.is_playing = False
        self.autoplay_enabled = True
        self.on_step_changed = on_step_changed

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self) -> None:
        self.title = label(self, "Animacja działania modelu", size=16, weight="bold")
        self.title.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))

        self.canvas = tk.Canvas(
            self, height=760, bg="#07111c", highlightthickness=1, highlightbackground="#203246"
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _event: self._draw_canvas())

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        controls.grid_columnconfigure(4, weight=1)

        self.prev_btn = ctk.CTkButton(controls, text="<<", width=38, command=self.previous_step)
        self.prev_btn.grid(row=0, column=0, padx=(0, 6))
        self.play_btn = ctk.CTkButton(controls, text="Play", width=56, command=self.toggle_play)
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

    @property
    def total_steps(self) -> int:
        return max(1, len(self.model.steps) if self.model is not None else 12)

    def set_model(self, model: TheoryModel) -> None:
        self.stop(cancel_resume=True)
        self.model = model
        self.step_index = 0
        self.slider.configure(from_=1, to=self.total_steps, number_of_steps=max(self.total_steps - 1, 1))
        self._refresh(emit=True)
        self.start_autoplay()

    def set_example_values(self, values: dict[str, float]) -> None:
        self.example_values.update(values)
        self._draw_canvas()

    def set_step(self, index: int, *, emit: bool = True, user_action: bool = False) -> None:
        if user_action:
            self.pause_for_reading()
        self.step_index = max(0, min(self.total_steps - 1, index))
        self._refresh(emit=emit)
        self._start_motion()

    def previous_step(self) -> None:
        self.set_step(self.step_index - 1, user_action=True)

    def next_step(self) -> None:
        self.set_step((self.step_index + 1) % self.total_steps, user_action=True)

    def toggle_play(self) -> None:
        if self.is_playing:
            self.autoplay_enabled = False
            self.stop(cancel_resume=True)
            return
        self.autoplay_enabled = True
        self.start_autoplay()

    def start_autoplay(self) -> None:
        if self.is_playing or not self.autoplay_enabled:
            return
        self.is_playing = True
        self.play_btn.configure(text="Stop")
        self._start_motion()
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
        for attr in ("_autoplay_after_id", "_motion_after_id", "_type_after_id"):
            after_id = getattr(self, attr)
            if after_id is not None:
                self.after_cancel(after_id)
                setattr(self, attr, None)
        if cancel_resume and self._resume_after_id is not None:
            self.after_cancel(self._resume_after_id)
            self._resume_after_id = None

    def _schedule_next(self, *, initial: bool = False) -> None:
        delay = {"0.75x": 13000, "1.0x": 10000, "1.5x": 7000}.get(self.speed.get(), 10000)
        self._autoplay_after_id = self.after(10000 if initial else delay, self._play_tick)

    def _play_tick(self) -> None:
        self._autoplay_after_id = None
        if not self.is_playing:
            return
        self.set_step((self.step_index + 1) % self.total_steps)
        self._schedule_next()

    def _slider_changed(self, value: float) -> None:
        self.set_step(int(round(value)) - 1, user_action=True)

    def _refresh(self, *, emit: bool = True) -> None:
        if self.model is None:
            return
        self.title.configure(text=f"Animacja działania modelu: {self.model.title}")
        self.step_label.configure(text=f"Krok {self.step_index + 1} / {self.total_steps}")
        self.slider.set(self.step_index + 1)
        self._text_reveal = 0
        self._draw_canvas()
        self._start_typewriter()
        if emit and self.on_step_changed is not None:
            self.on_step_changed(self.step_index)

    def _start_typewriter(self) -> None:
        if self._type_after_id is not None:
            self.after_cancel(self._type_after_id)
        self._type_after_id = self.after(28, self._type_tick)

    def _type_tick(self) -> None:
        self._type_after_id = None
        if self.model is None:
            return
        text_len = len(self.model.step_details[self.step_index])
        self._text_reveal = min(text_len, self._text_reveal + 2)
        self._pulse = (self._pulse + 1) % 120
        self._draw_canvas()
        if self._text_reveal < text_len:
            self._type_after_id = self.after(28, self._type_tick)

    def _start_motion(self) -> None:
        if self._motion_after_id is None:
            self._motion_after_id = self.after(70, self._motion_tick)

    def _motion_tick(self) -> None:
        self._motion_after_id = None
        if self.model is None:
            return
        if not self.is_playing and self._text_reveal >= len(self.model.step_details[self.step_index]):
            return
        self._pulse = (self._pulse + 1) % 120
        self._draw_canvas()
        self._motion_after_id = self.after(70, self._motion_tick)

    def _draw_canvas(self) -> None:
        if self.model is None:
            return
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1120)
        height = max(canvas.winfo_height(), 760)
        canvas.configure(scrollregion=(0, 0, width, height))

        if self.model.family == "mh":
            kind = "sto"
        elif self.model.family == "tabpfn":
            kind = self._modern_visual_kind(self.model)
        else:
            kind = self._ml_visual_kind(self.model)
        task = self._task_name()
        self._draw_background(canvas, width, height)
        self._draw_header(canvas, width, kind, task)
        self._draw_narration(canvas, width)
        self._draw_main_scene(canvas, width, height, kind, task)
        self._draw_footer(canvas, width, height, kind, task)

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
    def _modern_visual_kind(model: TheoryModel) -> str:
        algorithm = model.algorithm.lower()
        if "tabpfn" in algorithm:
            return "tabpfn"
        if "xgboost" in algorithm or "xgb" in algorithm:
            return "xgboost"
        if "mlp" in algorithm or "neural_network" in algorithm:
            return "mlp"
        if "stacking" in algorithm:
            return "stacking"
        return ModelAnimationCard._ml_visual_kind(model)

    def _task_name(self) -> str:
        assert self.model is not None
        if self.model.family == "mh":
            return "STO"
        if self.model.family == "tabpfn":
            if self.model.key.endswith("schedule"):
                return "schedule"
            if self.model.key.endswith("delay"):
                return "opoznienie"
            return "jakosc"
        if self.model.key.startswith("Schedule"):
            return "schedule"
        if self.model.key.startswith("Delay"):
            return "opóźnienie"
        return "jakość"

    @staticmethod
    def _kind_color(kind: str) -> str:
        return {
            "forest": "#38bdf8",
            "extra": "#a78bfa",
            "boost": "#f97316",
            "hist": "#22c55e",
            "logistic": "#facc15",
            "sto": "#22c55e",
            "tabpfn": "#14b8a6",
            "xgboost": "#f97316",
            "mlp": "#a855f7",
            "stacking": "#38bdf8",
        }.get(kind, "#38bdf8")

    @staticmethod
    def _mechanic_name(kind: str) -> str:
        return {
            "forest": "głosowanie wielu drzew",
            "extra": "losowe progi ExtraTrees",
            "boost": "poprawki błędu",
            "hist": "koszyki histogramowe",
            "logistic": "softmax",
            "sto": "symulacja kolejki",
            "tabpfn": "kontekst tabelaryczny",
            "xgboost": "boosting z regularyzacja",
            "mlp": "warstwy neuronowe",
            "stacking": "meta-model z modeli bazowych",
        }.get(kind, "model")

    def _draw_background(self, c: tk.Canvas, width: int, height: int) -> None:
        palette = ["#07111c", "#081522", "#091827", "#0a1b2d", "#0b1d32", "#0c2036"]
        band_h = height / len(palette)
        for i, color in enumerate(palette):
            c.create_rectangle(0, i * band_h, width, (i + 1) * band_h, fill=color, outline="")
        for x in range(54, width, 118):
            c.create_line(x, 108, x, height - 120, fill="#10263a", width=1)
        for y in range(132, int(height - 120), 72):
            c.create_line(40, y, width - 40, y, fill="#0f2438", width=1)

    def _draw_header(self, c: tk.Canvas, width: int, kind: str, task: str) -> None:
        assert self.model is not None
        accent = self._kind_color(kind)
        c.create_text(42, 28, text=self.model.title, fill="#f8fafc", anchor="w", font=("Segoe UI", 20, "bold"))
        subtitle = (
            "Film krok po kroku: zlecenia -> kolejka -> Cj/Tj -> ranking STO"
            if kind == "sto"
            else f"Film krok po kroku: rekord -> cechy -> {self._mechanic_name(kind)} -> predykcja {task}"
        )
        c.create_text(42, 57, text=subtitle, fill="#b7c5d8", anchor="w", font=("Segoe UI", 11))

        c.create_rectangle(width - 250, 22, width - 42, 70, fill="#0b1b2d", outline="#274461")
        c.create_text(width - 232, 46, text="MODEL", fill="#93c5fd", anchor="w", font=("Segoe UI", 8, "bold"))
        c.create_text(width - 178, 46, text=self.model.short_title, fill="#f8fafc", anchor="w", font=("Segoe UI", 12, "bold"))
        c.create_rectangle(width - 78, 30, width - 50, 58, fill=accent, outline="")
        c.create_text(width - 64, 44, text=str(self.step_index + 1), fill="white", font=("Segoe UI", 11, "bold"))

        left, right, y = 44, width - 44, 93
        gap = (right - left) / max(self.total_steps - 1, 1)
        c.create_line(left, y, right, y, fill="#334155", width=5)
        c.create_line(left, y, left + gap * self.step_index, y, fill=accent, width=5)
        for i in range(self.total_steps):
            x = left + gap * i
            current = i == self.step_index
            radius = 11 if current else 7
            c.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=accent if i <= self.step_index else "#536171",
                outline="#dbeafe" if current else "#0f1b2a",
                width=2 if current else 1,
            )

    def _draw_narration(self, c: tk.Canvas, width: int) -> None:
        assert self.model is not None
        x1, y1, x2, y2 = 44, 116, width - 44, 206
        if self.model.family == "mh":
            accent = GREEN
        elif self.model.family == "tabpfn":
            accent = self._kind_color(self._modern_visual_kind(self.model))
        else:
            accent = self._kind_color("forest")
        c.create_rectangle(x1, y1, x2, y2, fill="#0b1623", outline="#274461", width=2)
        c.create_rectangle(x1, y1, x1 + 6, y2, fill=accent, outline="")
        c.create_text(
            x1 + 24,
            y1 + 24,
            text=f"Krok {self.step_index + 1}: {self.model.steps[self.step_index]}",
            fill="#f8fafc",
            anchor="w",
            font=("Segoe UI", 17, "bold"),
        )
        full = self.model.step_details[self.step_index]
        shown = full[: self._text_reveal]
        caret = "|" if self._text_reveal < len(full) or self._pulse % 18 < 9 else ""
        c.create_text(
            x1 + 24,
            y1 + 58,
            text=shown + caret,
            fill="#d8e4f2",
            anchor="nw",
            font=("Segoe UI", 12),
            width=x2 - x1 - 48,
        )

    def _draw_main_scene(self, c: tk.Canvas, width: int, height: int, kind: str, task: str) -> None:
        top = 232
        bottom = height - 225
        if kind in {"forest", "extra"}:
            box = (62, top, width - 62, bottom)
            self._draw_panel(c, *box, "Random Forest flow" if kind == "forest" else "ExtraTrees flow", self._kind_color(kind))
            self._draw_tree_flow(c, box, random_threshold=(kind == "extra"))
            return
        if kind == "tabpfn":
            box = (62, top, width - 62, bottom)
            self._draw_panel(c, *box, "TabPFN flow", self._kind_color(kind))
            self._draw_tabpfn_flow(c, box, task)
            return
        if kind == "xgboost":
            box = (62, top, width - 62, bottom)
            self._draw_panel(c, *box, "XGBoost flow", self._kind_color(kind))
            self._draw_xgboost_flow(c, box, task)
            return
        if kind == "mlp":
            box = (62, top, width - 62, bottom)
            self._draw_panel(c, *box, "MLP neural flow", self._kind_color(kind))
            self._draw_mlp_flow(c, box, task)
            return
        if kind == "stacking":
            box = (62, top, width - 62, bottom)
            self._draw_panel(c, *box, "Stacking flow", self._kind_color(kind))
            self._draw_stacking_flow(c, box, task)
            return

        data = (62, top, 298, bottom)
        model = (360, top, width - 360, bottom)
        result = (width - 296, top, width - 62, bottom)
        self._draw_panel(c, *data, "01 dane wejściowe", BLUE)
        self._draw_dataset(c, data, task)
        self._arrow(c, data[2] + 18, (top + bottom) / 2, model[0] - 20, (top + bottom) / 2, self.step_index >= 2)
        self._draw_panel(c, *model, self.model.algorithm if self.model else "model", self._kind_color(kind))
        if kind in {"boost", "hist"}:
            self._draw_boosting_flow(c, model, hist=(kind == "hist"))
        elif kind == "logistic":
            self._draw_logistic_flow(c, model)
        else:
            self._draw_sto_flow(c, model)
        self._arrow(c, model[2] + 20, (top + bottom) / 2, result[0] - 18, (top + bottom) / 2, self.step_index >= 7)
        self._draw_panel(c, *result, "03 wynik", GREEN)
        self._draw_prediction(c, result, task)

    def _draw_panel(
        self, c: tk.Canvas, x1: float, y1: float, x2: float, y2: float, title: str, accent: str
    ) -> None:
        c.create_rectangle(x1 + 7, y1 + 8, x2 + 7, y2 + 8, fill="#050b13", outline="")
        c.create_rectangle(x1, y1, x2, y2, fill="#0a1522", outline="#29425c", width=1)
        c.create_rectangle(x1, y1, x2, y1 + 38, fill="#10263d", outline="")
        c.create_rectangle(x1, y1, x1 + 5, y2, fill=accent, outline="")
        c.create_text(x1 + 20, y1 + 20, text=title, fill="#f8fafc", anchor="w", font=("Segoe UI", 11, "bold"))

    def _draw_tree_flow(
        self, c: tk.Canvas, box: tuple[float, float, float, float], *, random_threshold: bool
    ) -> None:
        x1, y1, x2, y2 = box
        width, height = x2 - x1, y2 - y1
        accent = self._kind_color("extra" if random_threshold else "forest")
        input_node = (x1 + width * 0.08, y1 + height * 0.52)
        sample_nodes = [
            (x1 + width * 0.25, y1 + height * 0.28),
            (x1 + width * 0.25, y1 + height * 0.52),
            (x1 + width * 0.25, y1 + height * 0.76),
        ]
        tree_nodes = [
            (x1 + width * 0.47, y1 + height * 0.20),
            (x1 + width * 0.55, y1 + height * 0.38),
            (x1 + width * 0.48, y1 + height * 0.58),
            (x1 + width * 0.60, y1 + height * 0.74),
        ]
        leaf_nodes = [
            (x1 + width * 0.72, y1 + height * 0.23),
            (x1 + width * 0.78, y1 + height * 0.41),
            (x1 + width * 0.72, y1 + height * 0.59),
            (x1 + width * 0.80, y1 + height * 0.76),
        ]
        aggregate_node = (x1 + width * 0.93, y1 + height * 0.52)

        self._draw_graph_backdrop(c, x1, y1, x2, y2, accent)
        for x, text in [
            (input_node[0], "rekord"),
            (sample_nodes[1][0], "próbki"),
            (tree_nodes[1][0], "drzewa"),
            (leaf_nodes[1][0], "liście"),
            (aggregate_node[0], "agregacja"),
        ]:
            c.create_text(x, y1 + 58, text=text.upper(), fill="#94a3b8", font=("Segoe UI", 8, "bold"))

        if self.step_index >= 2:
            for sample in sample_nodes:
                self._draw_graph_edge(c, input_node, sample, True, accent)
        if self.step_index >= 3:
            tree_routes = [
                (sample_nodes[0], tree_nodes[0]),
                (sample_nodes[0], tree_nodes[1]),
                (sample_nodes[1], tree_nodes[1]),
                (sample_nodes[1], tree_nodes[2]),
                (sample_nodes[2], tree_nodes[2]),
                (sample_nodes[2], tree_nodes[3]),
            ]
            for sample, tree in tree_routes:
                self._draw_graph_edge(c, sample, tree, True, accent)
        if self.step_index >= 4:
            for tree, leaf in zip(tree_nodes, leaf_nodes, strict=False):
                self._draw_graph_edge(c, tree, leaf, True, accent)
        if self.step_index >= 7:
            for leaf in leaf_nodes:
                self._draw_graph_edge(c, leaf, aggregate_node, True, accent)

        self._draw_graph_node(c, *input_node, "x", "rekord", active=True, color=BLUE, radius=24)
        for i, node in enumerate(sample_nodes, start=1):
            self._draw_graph_node(c, *node, f"S{i}", "próbka", active=self.step_index >= 2, color="#38bdf8", radius=20)
        for i, node in enumerate(tree_nodes, start=1):
            self._draw_graph_node(c, *node, f"T{i}", "drzewo", active=self.step_index >= 3, color=accent, radius=23)
            self._draw_decision_mark(c, *node, random_threshold=random_threshold, active=self.step_index >= 4)
        for i, node in enumerate(leaf_nodes, start=1):
            self._draw_graph_node(c, *node, f"ŷ{i}", "liść", active=self.step_index >= 5, color=GREEN, radius=19)
        self._draw_graph_node(
            c,
            *aggregate_node,
            "Σ",
            "średnia" if not random_threshold else "głos",
            active=self.step_index >= 7,
            color=YELLOW,
            radius=28,
        )
        caption = (
            "losowe progi -> wiele drzew -> głosowanie"
            if random_threshold
            else "rekord -> próbki -> drzewa -> liście -> agregacja"
        )
        c.create_rectangle(x1 + width * 0.34, y2 - 44, x1 + width * 0.66, y2 - 14, fill="#0e2a45", outline="#93c5fd")
        c.create_text((x1 + x2) / 2, y2 - 29, text=caption, fill="#f8fafc", font=("Segoe UI", 9, "bold"))

    def _draw_graph_backdrop(
        self, c: tk.Canvas, x1: float, y1: float, x2: float, y2: float, accent: str
    ) -> None:
        c.create_rectangle(x1 + 24, y1 + 48, x2 - 24, y2 - 38, fill="#07111c", outline="#13283d")
        for i, y in enumerate([0.27, 0.52, 0.77]):
            yy = y1 + (y2 - y1) * y
            c.create_line(x1 + 54, yy, x2 - 54, yy, fill="#0e263c" if i == 1 else "#0b2033", width=1)
        c.create_line(x1 + 60, y2 - 46, x2 - 60, y2 - 46, fill=accent, width=2)

    def _draw_graph_edge(
        self,
        c: tk.Canvas,
        start: tuple[float, float],
        end: tuple[float, float],
        active: bool,
        accent: str,
    ) -> None:
        color = accent if active else "#16263a"
        line_w = 4 if active else 1
        control = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + (22 if end[1] >= start[1] else -22))
        points = (start[0], start[1], control[0], control[1], end[0], end[1])
        if not active:
            c.create_line(*points, fill=color, width=line_w, smooth=True)
            return
        c.create_line(*points, fill="#030712", width=line_w + 8, smooth=True)
        if active:
            c.create_line(*points, fill=color, width=line_w + 4, smooth=True)
        c.create_line(*points, fill=color, width=line_w, smooth=True)
        if active:
            phase = (self._pulse % 48) / 48
            px, py = self._quadratic_point(start, control, end, phase)
            c.create_oval(px - 8, py - 8, px + 8, py + 8, fill=color, outline="")
            c.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#f8fafc", outline="")

    @staticmethod
    def _quadratic_point(
        start: tuple[float, float],
        control: tuple[float, float],
        end: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        inv = 1 - t
        return (
            inv * inv * start[0] + 2 * inv * t * control[0] + t * t * end[0],
            inv * inv * start[1] + 2 * inv * t * control[1] + t * t * end[1],
        )

    def _draw_graph_node(
        self,
        c: tk.Canvas,
        x: float,
        y: float,
        title: str,
        subtitle: str,
        *,
        active: bool,
        color: str,
        radius: int,
    ) -> None:
        fill = "#10243a" if active else "#172334"
        outline = "#dbeafe" if active else "#64748b"
        if active:
            pulse = 3 + (self._pulse % 24) / 8
            c.create_oval(x - radius - 16 - pulse, y - radius - 16 - pulse, x + radius + 16 + pulse, y + radius + 16 + pulse, fill=color, outline="")
            c.create_oval(x - radius - 9, y - radius - 9, x + radius + 9, y + radius + 9, fill="#07111c", outline=color, width=2)
        c.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fill, outline=outline, width=2)
        c.create_oval(x - radius * 0.36, y - radius * 0.36, x + radius * 0.36, y + radius * 0.36, fill=color if active else "#475569", outline="")
        c.create_text(x, y, text=title, fill="#f8fafc", font=("Segoe UI", 11, "bold"))
        c.create_rectangle(x - 34, y + radius + 8, x + 34, y + radius + 24, fill="#07111c", outline="")
        c.create_text(x, y + radius + 16, text=subtitle, fill="#cbd5e1", font=("Segoe UI", 7, "bold"))

    def _draw_decision_mark(
        self, c: tk.Canvas, x: float, y: float, *, random_threshold: bool, active: bool
    ) -> None:
        if not active:
            return
        color = "#a78bfa" if random_threshold else "#22c55e"
        text = "losowy próg" if random_threshold else "najlepszy próg"
        c.create_line(x - 13, y + 4, x + 13, y - 10, fill=color, width=2)
        c.create_text(x, y + 43, text=text, fill=color, font=("Segoe UI", 7, "bold"))

    def _draw_dataset(self, c: tk.Canvas, box: tuple[float, float, float, float], task: str) -> None:
        x1, y1, x2, _y2 = box
        values = self.example_values
        rows = [
            ("cel", task),
            ("czas_h", f"{8 + values['mt'] * 6:.1f}"),
            ("termin_h", f"{24 + values['mo'] * 42:.1f}"),
            ("koszt", f"{100 + values['mzo'] * 160:.0f}"),
            ("materiał", f"{values['gen']:.2f}"),
        ]
        active_row = min(max(self.step_index - 1, 0), len(rows) - 1)
        for i, (name, value) in enumerate(rows):
            y = y1 + 68 + i * 34
            active = i == active_row
            c.create_rectangle(x1 + 24, y - 14, x2 - 24, y + 14, fill="#123f78" if active else "#10243a", outline="#7dd3fc" if active else "#31506d")
            c.create_oval(x1 + 33, y - 5, x1 + 43, y + 5, fill="#38bdf8" if active else "#64748b", outline="")
            c.create_text(x1 + 54, y, text=name, fill="#dbeafe", anchor="w", font=("Segoe UI", 9, "bold"))
            c.create_text(x2 - 38, y, text=value, fill="#f8fafc", anchor="e", font=("Segoe UI", 10, "bold"))

    def _draw_prediction(self, c: tk.Canvas, box: tuple[float, float, float, float], task: str) -> None:
        assert self.model is not None
        x1, y1, x2, _y2 = box
        for i, (name, value) in enumerate(self.model.probabilities):
            y = y1 + 70 + i * 42
            bar_x1, bar_x2 = x1 + 28, x2 - 28
            c.create_rectangle(bar_x1, y - 13, bar_x2, y + 13, fill="#10243a", outline="#274461")
            c.create_rectangle(bar_x1, y - 13, bar_x1 + (bar_x2 - bar_x1) * value, y + 13, fill=GREEN if self.step_index >= 8 else "#475569", outline="")
            c.create_text(bar_x1 + 8, y, text=name, fill="#f8fafc", anchor="w", font=("Segoe UI", 8, "bold"))
            c.create_text(bar_x2 - 8, y, text=f"{value:.2f}", fill="#f8fafc", anchor="e", font=("Segoe UI", 8))
        result = self.model.result if self.step_index >= 10 else f"liczę {task}..."
        c.create_rectangle(x1 + 28, y1 + 220, x2 - 28, y1 + 262, fill="#123f2a" if self.step_index >= 10 else "#10243a", outline="#86efac" if self.step_index >= 10 else "#31523a", width=2 if self.step_index >= 10 else 1)
        c.create_text((x1 + x2) / 2, y1 + 241, text=result, fill="#dcfce7", font=("Segoe UI", 12, "bold"))

    def _draw_boosting_flow(
        self, c: tk.Canvas, box: tuple[float, float, float, float], *, hist: bool
    ) -> None:
        x1, y1, x2, y2 = box
        stages = [
            ("F0", "start", "prosta\npredykcja", BLUE),
            ("e1", "błąd", "y - F0", "#ef4444"),
            ("h1", "drzewo", "uczy się\nbłędu", "#22c55e"),
            ("F1", "update", "F0 + ηh1", "#f97316"),
            ("h2", "drzewo", "kolejna\npoprawka", PURPLE),
            ("ŷ", "wynik", "predykcja\npo poprawkach", GREEN),
        ]
        gap = (x2 - x1 - 160) / (len(stages) - 1)
        y = y1 + (y2 - y1) * 0.56
        if hist:
            hist_x = x1 + 62
            c.create_rectangle(hist_x - 16, y1 + 48, hist_x + 300, y1 + 112, fill="#07111c", outline="#1f4f85")
            for i in range(7):
                bx = hist_x + 18 + i * 38
                bar_h = 18 + (i % 4) * 11
                c.create_rectangle(
                    bx,
                    y1 + 92 - bar_h,
                    bx + 24,
                    y1 + 92,
                    fill="#123f78" if self.step_index >= 2 else "#334155",
                    outline="#93c5fd",
                )
            c.create_text(hist_x + 142, y1 + 105, text="koszyki wartości: szybkie histogramy", fill="#bfdbfe", font=("Segoe UI", 9, "bold"))
        else:
            c.create_rectangle(x1 + 62, y1 + 58, x1 + 350, y1 + 106, fill="#07111c", outline="#1f4f85")
            c.create_text(x1 + 82, y1 + 74, text="boosting = model poprawia własne błędy", fill="#fde68a", anchor="w", font=("Segoe UI", 10, "bold"))
            c.create_text(x1 + 82, y1 + 94, text="kolejne małe drzewa dopasowują residuale", fill="#cbd5e1", anchor="w", font=("Segoe UI", 9))
        for i, (symbol, title, subtitle, color) in enumerate(stages):
            x = x1 + 80 + i * gap
            active = self.step_index >= min(i + 2, 8)
            fill = "#10243a" if active else "#172334"
            outline = color if active else "#475569"
            c.create_rectangle(x - 52, y - 42, x + 52, y + 42, fill=fill, outline=outline, width=2)
            c.create_text(x, y - 18, text=symbol, fill=color if active else "#94a3b8", font=("Segoe UI", 15, "bold"))
            c.create_text(x, y + 2, text=title, fill="#f8fafc", font=("Segoe UI", 9, "bold"))
            c.create_text(x, y + 25, text=subtitle, fill="#cbd5e1", font=("Segoe UI", 8), width=86)
            if i < len(stages) - 1:
                self._arrow(c, x + 58, y, x + gap - 58, y, self.step_index >= i + 3)
        if self.step_index >= 8:
            c.create_rectangle(x1 + 72, y2 - 54, x2 - 72, y2 - 20, fill="#10243a", outline="#f97316")
            c.create_text(
                (x1 + x2) / 2,
                y2 - 37,
                text="F_m(x) = F_{m-1}(x) + η·h_m(x)   |   early stopping pilnuje walidacji",
                fill="#fde68a",
                font=("Consolas", 10, "bold"),
            )

    def _draw_logistic_flow(self, c: tk.Canvas, box: tuple[float, float, float, float]) -> None:
        x1, y1, x2, y2 = box
        left, right = x1 + 70, x2 - 70
        bottom, top = y2 - 68, y1 + 74
        c.create_line(left, bottom, right, bottom, fill="#64748b", width=2, arrow=tk.LAST)
        c.create_line(left, bottom, left, top, fill="#64748b", width=2, arrow=tk.LAST)
        c.create_line(left + 16, bottom - 28, right - 16, top + 32, fill="#facc15", width=4)
        for px, py, color in [(0.18, 0.24, BLUE), (0.36, 0.38, GREEN), (0.62, 0.66, PURPLE), (0.78, 0.48, "#ef4444")]:
            x = left + (right - left) * px
            y = bottom - (bottom - top) * py
            c.create_oval(x - 10, y - 10, x + 10, y + 10, fill=color if self.step_index >= 4 else "#475569", outline="")
        if self.step_index >= 5:
            c.create_rectangle(x1 + 62, y2 - 42, x2 - 62, y2 - 16, fill="#10243a", outline="#facc15")
            c.create_text((x1 + x2) / 2, y2 - 29, text="softmax(X·w+b) -> P(A), P(B), P(C)", fill="#fef3c7", font=("Consolas", 10, "bold"))

    def _draw_tabpfn_flow(self, c: tk.Canvas, box: tuple[float, float, float, float], task: str) -> None:
        x1, y1, x2, y2 = box
        accent = self._kind_color("tabpfn")
        algorithm = self.model.algorithm if self.model is not None else "TabPFN"
        is_tabpfn = "TabPFN" in algorithm
        box_w = x2 - x1
        box_h = y2 - y1
        panel_x1, panel_y1 = x1 + 26, y1 + 42
        panel_x2, panel_y2 = x2 - 26, y2 - 34
        c.create_rectangle(panel_x1, panel_y1, panel_x2, panel_y2, fill="#06131d", outline="#155e75")
        c.create_rectangle(panel_x1, panel_y1, panel_x2, panel_y1 + 40, fill="#0f2a37", outline="")
        c.create_text(
            panel_x1 + 18,
            panel_y1 + 20,
            text=(
                "TabPFN flow: tabela + kontekst -> prior pretrenowany -> predykcja -> walidacja"
                if is_tabpfn
                else "Modern ML flow: tabela -> train/test -> model -> predykcja -> walidacja"
            ),
            fill="#f8fafc",
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )

        lane_y = y1 + box_h * 0.67
        stage_y = y1 + 92
        stages = [
            ("01", "DANE", "kolumny X + cel y"),
            ("02", "KONTEKST" if is_tabpfn else "TRAIN/TEST", "train jako opis zadania" if is_tabpfn else "uczciwy podzial danych"),
            ("03", "TABPFN" if is_tabpfn else "MODEL", "model juz pretrenowany" if is_tabpfn else algorithm.split(".")[-1]),
            ("04", "WYNIK", f"predykcja {task}"),
        ]
        stage_w = box_w * 0.18
        gap = box_w * 0.055
        start_x = x1 + box_w * 0.065
        centers: list[tuple[float, float]] = []
        for idx, (number, title, subtitle) in enumerate(stages):
            sx = start_x + idx * (stage_w + gap)
            sy = stage_y
            active = self.step_index >= idx + 1
            c.create_text(
                sx,
                sy,
                text=f"{number} {title}",
                fill=accent if active else "#64748b",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            )
            c.create_text(
                sx,
                sy + 18,
                text=subtitle,
                fill="#ccfbf1" if active else "#64748b",
                anchor="w",
                font=("Segoe UI", 8),
            )
            centers.append((sx + stage_w / 2, lane_y))
            if idx < len(stages) - 1:
                self._arrow(c, sx + stage_w * 0.72, sy + 10, sx + stage_w + gap - 18, sy + 10, self.step_index >= idx + 2)

        table_x = start_x + 14
        table_y = lane_y - 62
        c.create_text(table_x, table_y - 24, text="mini tabela treningowa", fill="#99f6e4", anchor="w", font=("Segoe UI", 9, "bold"))
        headers = ["czas", "termin", "koszt", "y"]
        for col, header in enumerate(headers):
            x = table_x + col * 54
            c.create_rectangle(x, table_y, x + 50, table_y + 24, fill="#0f3a4a", outline="#2dd4bf")
            c.create_text(x + 25, table_y + 12, text=header, fill="#ecfeff", font=("Segoe UI", 8, "bold"))
        values = [
            ("11.6", "36.6", "116", "0.82"),
            ("10.4", "45.0", "116", "0.71"),
            ("9.2", "32.4", "148", "0.64"),
            ("12.2", "32.4", "116", "?"),
        ]
        for row, items in enumerate(values):
            active = self.step_index >= row
            for col, value in enumerate(items):
                x = table_x + col * 54
                y = table_y + 26 + row * 25
                fill = "#123f78" if active and row == 3 else ("#10243a" if active else "#172334")
                c.create_rectangle(x, y, x + 50, y + 22, fill=fill, outline="#155e75")
                c.create_text(x + 25, y + 11, text=value, fill="#f8fafc", font=("Consolas", 8, "bold"))

        context = (centers[1][0], lane_y)
        model = (centers[2][0], lane_y)
        output = (centers[3][0] + 12, lane_y)
        self._arrow(c, table_x + 230, table_y + 72, context[0] - 64, context[1], self.step_index >= 3)
        for idx, yy in enumerate((context[1] - 46, context[1], context[1] + 46)):
            active = self.step_index >= idx + 3
            c.create_rectangle(context[0] - 62, yy - 18, context[0] + 62, yy + 18, fill="#0b1f2c" if active else "#172334", outline=accent if active else "#334155")
            c.create_text(context[0] - 46, yy, text=f"ctx {idx + 1}", fill="#ccfbf1", anchor="w", font=("Segoe UI", 8, "bold"))
            c.create_oval(context[0] + 32, yy - 7, context[0] + 46, yy + 7, fill=accent if active else "#475569", outline="")
        c.create_rectangle(context[0] - 98, context[1] + 70, context[0] + 98, context[1] + 108, fill="#07111c", outline="#155e75")
        c.create_text(
            context[0],
            context[1] + 89,
            text=(
                "TabPFN czyta kilka rekordow\njak kontekst zadania"
                if is_tabpfn
                else "train/test chroni przed\nladnym, ale falszywym wynikiem"
            ),
            fill="#ccfbf1",
            font=("Segoe UI", 8, "bold"),
        )

        self._arrow(c, context[0] + 86, context[1], model[0] - 72, model[1], self.step_index >= 5)
        for radius, color, width in ((56, accent, 4), (40, "#99f6e4", 2), (24, "#334155", 2)):
            fill = "#07111c" if radius == 56 else ""
            c.create_oval(
                model[0] - radius,
                model[1] - radius,
                model[0] + radius,
                model[1] + radius,
                fill=fill,
                outline=color,
                width=width,
            )
        model_title = "TabPFN" if is_tabpfn else algorithm.split(".")[-1].replace("Regressor", "").replace("Classifier", "")
        c.create_text(model[0], model[1] - 13, text=model_title[:12], fill="#f8fafc", font=("Segoe UI", 13, "bold"))
        c.create_text(
            model[0],
            model[1] + 12,
            text="pretrained prior" if is_tabpfn else "fit + walidacja",
            fill="#99f6e4",
            font=("Segoe UI", 8, "bold"),
        )
        if self.step_index >= 6:
            c.create_line(model[0] - 32, model[1] + 28, model[0] + 28, model[1] - 22, fill=accent, width=4)
            for dx, dy in [(-28, 25), (-8, 8), (13, -9), (30, -24)]:
                c.create_oval(model[0] + dx - 5, model[1] + dy - 5, model[0] + dx + 5, model[1] + dy + 5, fill=accent, outline="#ecfeff")
        if self.step_index >= 6:
            for idx, offset in enumerate((-28, 0, 28)):
                self._arrow(c, model[0] + 64, model[1] + offset, output[0] - 76, output[1] + offset / 2, True)
                dot_x = model[0] + 120 + idx * 54
                c.create_oval(dot_x - 6, model[1] + offset - 6, dot_x + 6, model[1] + offset + 6, fill=accent, outline="#ecfeff")

        c.create_rectangle(output[0] - 92, output[1] - 72, output[0] + 100, output[1] + 84, fill="#07111c", outline=accent, width=2)
        c.create_rectangle(output[0] - 92, output[1] - 72, output[0] + 100, output[1] - 38, fill="#0f2a37", outline="")
        c.create_text(output[0] - 72, output[1] - 55, text="PREDYKCJA", fill="#99f6e4", anchor="w", font=("Segoe UI", 9, "bold"))
        probabilities = self.model.probabilities if self.model is not None else ()
        for idx, (name, value) in enumerate(probabilities):
            y = output[1] - 14 + idx * 31
            c.create_rectangle(output[0] - 64, y, output[0] + 72, y + 18, fill="#10243a", outline="#155e75")
            c.create_rectangle(output[0] - 64, y, output[0] - 64 + 136 * value, y + 18, fill=accent if self.step_index >= 7 else "#475569", outline="")
            c.create_text(output[0] - 58, y + 9, text=name, fill="#f8fafc", anchor="w", font=("Segoe UI", 7, "bold"))
            c.create_text(output[0] + 66, y + 9, text=f"{value:.2f}", fill="#ecfeff", anchor="e", font=("Consolas", 7))
        if self.step_index >= 9:
            c.create_rectangle(x1 + box_w * 0.20, y2 - 60, x2 - box_w * 0.20, y2 - 22, fill="#0f2a37", outline=accent)
            c.create_text(
                (x1 + x2) / 2,
                y2 - 41,
                text=f"ten sam train/test co classic ML -> porownujemy metryki, ryzyko i predykcje {task}",
                fill="#ccfbf1",
                font=("Segoe UI", 10, "bold"),
            )

    def _draw_xgboost_flow(self, c: tk.Canvas, box: tuple[float, float, float, float], task: str) -> None:
        x1, y1, x2, y2 = box
        accent = self._kind_color("xgboost")
        px1, py1, px2, py2 = x1 + 26, y1 + 42, x2 - 26, y2 - 34
        c.create_rectangle(px1, py1, px2, py2, fill="#06131d", outline="#1f3b52")
        c.create_rectangle(px1, py1, px2, py1 + 48, fill="#10263d", outline="")
        c.create_text(
            px1 + 18,
            py1 + 17,
            text="XGBoost flow",
            fill="#fff7ed",
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )
        c.create_text(
            px1 + 18,
            py1 + 36,
            text="kolejne male drzewa poprawiaja blad, a regularyzacja pilnuje zeby model nie przesadzil",
            fill="#fdba74",
            anchor="w",
            font=("Segoe UI", 9),
        )

        panel_x1, panel_x2 = px1 + 28, px2 - 28
        card_y1, card_y2 = py1 + 70, py2 - 42
        gap = 18
        card_w = (panel_x2 - panel_x1 - gap * 3) / 4
        cards = [
            (panel_x1 + idx * (card_w + gap), card_y1, panel_x1 + idx * (card_w + gap) + card_w, card_y2)
            for idx in range(4)
        ]
        titles = [
            ("01 DANE", "mini tabela X + y"),
            ("02 START", "predykcja bazowa"),
            ("03 BOOSTING", "residuale -> drzewa"),
            ("04 WALIDACJA", "metryki i wynik"),
        ]
        for idx, (cx1, cy1, cx2, cy2) in enumerate(cards):
            active = self.step_index >= idx + 1
            outline = accent if active else "#334155"
            c.create_rectangle(cx1, cy1, cx2, cy2, fill="#071522", outline=outline, width=2)
            c.create_rectangle(cx1, cy1, cx2, cy1 + 34, fill="#10243a", outline="")
            c.create_text(cx1 + 14, cy1 + 13, text=titles[idx][0], fill=outline, anchor="w", font=("Segoe UI", 9, "bold"))
            c.create_text(cx1 + 14, cy1 + 27, text=titles[idx][1], fill="#cbd5e1", anchor="w", font=("Segoe UI", 7))

        for idx in range(3):
            self._arrow(
                c,
                cards[idx][2] + 8,
                (card_y1 + card_y2) / 2,
                cards[idx + 1][0] - 8,
                (card_y1 + card_y2) / 2,
                self.step_index >= idx + 2,
            )

        data_x = cards[0][0] + 22
        data_y = cards[0][1] + 62
        self._mini_table(c, data_x, data_y, accent, active_rows=min(self.step_index + 1, 4))

        b1x1, b1y1, b1x2, _ = cards[1]
        c.create_text(b1x1 + 20, b1y1 + 72, text="F0 = mean(y)", fill="#f8fafc", anchor="w", font=("Consolas", 10, "bold"))
        c.create_text(b1x1 + 20, b1y1 + 102, text="residual = y - F0", fill="#fed7aa", anchor="w", font=("Consolas", 10, "bold"))
        for idx, value in enumerate((0.72, 0.38, -0.22, 0.18)):
            y_bar = b1y1 + 136 + idx * 22
            zero = b1x1 + card_w * 0.50
            length = abs(value) * 90
            color = accent if self.step_index >= 3 else "#475569"
            c.create_line(zero - 88, y_bar, zero + 88, y_bar, fill="#334155", width=1)
            if value >= 0:
                c.create_rectangle(zero, y_bar - 6, zero + length, y_bar + 6, fill=color, outline="")
            else:
                c.create_rectangle(zero - length, y_bar - 6, zero, y_bar + 6, fill="#38bdf8", outline="")
            c.create_text(b1x2 - 18, y_bar, text=f"e{idx + 1}", fill="#cbd5e1", anchor="e", font=("Segoe UI", 7, "bold"))

        t1x1, t1y1, t1x2, t1y2 = cards[2]
        tree_positions = [
            (t1x1 + card_w * 0.25, t1y1 + 92),
            (t1x1 + card_w * 0.56, t1y1 + 132),
            (t1x1 + card_w * 0.35, t1y1 + 184),
            (t1x1 + card_w * 0.70, t1y1 + 206),
        ]
        for idx, (tx, ty) in enumerate(tree_positions):
            active = self.step_index >= 4 + idx
            fill = "#2a160c" if active else "#172334"
            outline = accent if active else "#475569"
            c.create_rectangle(tx - 42, ty - 24, tx + 42, ty + 24, fill=fill, outline=outline, width=2)
            c.create_text(tx, ty - 6, text=f"h{idx + 1}", fill="#fff7ed", font=("Segoe UI", 10, "bold"))
            c.create_text(tx, ty + 11, text="gain", fill="#fdba74", font=("Segoe UI", 7, "bold"))
        c.create_rectangle(t1x1 + 18, t1y2 - 50, t1x2 - 18, t1y2 - 18, fill="#120b07", outline=accent)
        c.create_text(
            (t1x1 + t1x2) / 2,
            t1y2 - 34,
            text="kara: Omega(tree) hamuje zbyt zlozone poprawki",
            fill="#ffedd5",
            font=("Segoe UI", 8, "bold"),
        )

        r1x1, r1y1, r1x2, r1y2 = cards[3]
        metrics = [("train", 0.82), ("test", 0.74), ("risk", 0.18)]
        for idx, (name, value) in enumerate(metrics):
            yy = r1y1 + 76 + idx * 34
            c.create_text(r1x1 + 18, yy, text=name, fill="#f8fafc", anchor="w", font=("Segoe UI", 8, "bold"))
            c.create_rectangle(r1x1 + 72, yy - 8, r1x2 - 18, yy + 8, fill="#10243a", outline="#155e75")
            c.create_rectangle(r1x1 + 72, yy - 8, r1x1 + 72 + (r1x2 - r1x1 - 90) * value, yy + 8, fill=accent, outline="")
            c.create_text(r1x2 - 24, yy, text=f"{value:.2f}", fill="#f8fafc", anchor="e", font=("Consolas", 8, "bold"))
        c.create_rectangle(r1x1 + 18, r1y2 - 66, r1x2 - 18, r1y2 - 22, fill="#0f2a37", outline=accent, width=2)
        c.create_text((r1x1 + r1x2) / 2, r1y2 - 50, text="wynik", fill="#99f6e4", font=("Segoe UI", 8, "bold"))
        c.create_text(
            (r1x1 + r1x2) / 2,
            r1y2 - 32,
            text=f"predykcja {task} po walidacji",
            fill="#f8fafc",
            font=("Segoe UI", 9, "bold"),
        )

    def _draw_mlp_flow(self, c: tk.Canvas, box: tuple[float, float, float, float], task: str) -> None:
        x1, y1, x2, y2 = box
        accent = self._kind_color("mlp")
        box_w = x2 - x1
        box_h = y2 - y1
        px1, py1, px2, py2 = x1 + 26, y1 + 42, x2 - 26, y2 - 34
        c.create_rectangle(px1, py1, px2, py2, fill="#07111c", outline="#6b21a8")
        c.create_rectangle(px1, py1, px2, py1 + 42, fill="#221036", outline="")
        c.create_text(px1 + 18, py1 + 21, text="MLP: skalowanie -> warstwy neuronowe -> funkcja aktywacji -> blad -> backprop", fill="#f3e8ff", anchor="w", font=("Segoe UI", 12, "bold"))

        left = x1 + box_w * 0.16
        y_mid = y1 + box_h * 0.58
        layer_x = [x1 + box_w * ratio for ratio in (0.34, 0.50, 0.66)]
        layer_counts = [4, 5, 3]
        c.create_rectangle(left - 88, y_mid - 88, left + 90, y_mid + 82, fill="#0b1f2c", outline=accent)
        c.create_text(left - 68, y_mid - 58, text="01 skalowanie", fill=accent, anchor="w", font=("Segoe UI", 9, "bold"))
        for idx, name in enumerate(("czas", "termin", "koszt", "material")):
            yy = y_mid - 30 + idx * 28
            c.create_rectangle(left - 58, yy - 9, left + 58, yy + 10, fill="#18243a", outline="#475569")
            c.create_text(left, yy, text=f"{name} -> z", fill="#f8fafc", font=("Segoe UI", 8, "bold"))

        prev_nodes = [(left + 90, y_mid - 48 + i * 32) for i in range(4)]
        for lx, count in zip(layer_x, layer_counts, strict=False):
            nodes = [(lx, y_mid - (count - 1) * 18 + i * 36) for i in range(count)]
            for px, py in prev_nodes:
                for nx, ny in nodes:
                    c.create_line(px, py, nx, ny, fill="#334155" if self.step_index < 4 else "#7e22ce", width=1)
            for nx, ny in nodes:
                active = self.step_index >= 3
                c.create_oval(nx - 13, ny - 13, nx + 13, ny + 13, fill=accent if active else "#334155", outline="#f5d0fe")
            prev_nodes = nodes
        out_x = x1 + box_w * 0.84
        for px, py in prev_nodes:
            c.create_line(px, py, out_x - 58, y_mid, fill="#7e22ce" if self.step_index >= 6 else "#334155", width=1)
        self._prediction_box(c, out_x, y_mid, accent, task)
        if self.step_index >= 7:
            c.create_rectangle(x1 + box_w * 0.28, py2 - 70, x2 - box_w * 0.28, py2 - 34, fill="#1f1235", outline=accent)
            c.create_text((x1 + x2) / 2, py2 - 52, text="loss(y, y_hat) -> backprop aktualizuje wagi W", fill="#f3e8ff", font=("Consolas", 10, "bold"))

    def _draw_stacking_flow(self, c: tk.Canvas, box: tuple[float, float, float, float], task: str) -> None:
        x1, y1, x2, y2 = box
        accent = self._kind_color("stacking")
        box_w = x2 - x1
        box_h = y2 - y1
        px1, py1, px2, py2 = x1 + 26, y1 + 42, x2 - 26, y2 - 34
        c.create_rectangle(px1, py1, px2, py2, fill="#06131d", outline="#0369a1")
        c.create_rectangle(px1, py1, px2, py1 + 42, fill="#0b2740", outline="")
        c.create_text(px1 + 18, py1 + 21, text="Stacking: kilka modeli bazowych -> predykcje out-of-fold -> meta-model -> klasa/strategia", fill="#e0f2fe", anchor="w", font=("Segoe UI", 12, "bold"))

        data_x = x1 + box_w * 0.12
        base_x = x1 + box_w * 0.36
        meta_x = x1 + box_w * 0.62
        out_x = x1 + box_w * 0.84
        mid_y = y1 + box_h * 0.58
        c.create_rectangle(data_x - 80, mid_y - 65, data_x + 88, mid_y + 65, fill="#0b1f2c", outline=accent)
        c.create_text(data_x - 58, mid_y - 38, text="foldy train", fill=accent, anchor="w", font=("Segoe UI", 9, "bold"))
        for i in range(4):
            yy = mid_y - 12 + i * 18
            c.create_rectangle(data_x - 50, yy, data_x + 50, yy + 12, fill="#123456" if self.step_index >= i else "#172334", outline="#155e75")
        self._arrow(c, data_x + 102, mid_y, base_x - 94, mid_y, self.step_index >= 2)
        base_models = [("RF", -74), ("HGB", 0), ("LOG", 74)]
        for name, offset in base_models:
            active = self.step_index >= 3
            c.create_rectangle(base_x - 70, mid_y + offset - 26, base_x + 70, mid_y + offset + 26, fill="#0b1f2c" if active else "#172334", outline=accent if active else "#475569", width=2)
            c.create_text(base_x, mid_y + offset - 4, text=name, fill="#f8fafc", font=("Segoe UI", 11, "bold"))
            c.create_text(base_x, mid_y + offset + 13, text="pred oof", fill="#bae6fd", font=("Segoe UI", 8, "bold"))
            self._arrow(c, base_x + 78, mid_y + offset, meta_x - 94, mid_y - 20 + offset / 4, self.step_index >= 5)
        c.create_rectangle(meta_x - 86, mid_y - 52, meta_x + 86, mid_y + 52, fill="#082f49", outline=accent, width=2)
        c.create_text(meta_x, mid_y - 14, text="META", fill="#f8fafc", font=("Segoe UI", 14, "bold"))
        c.create_text(meta_x, mid_y + 14, text="uczy sie z predykcji", fill="#bae6fd", font=("Segoe UI", 8, "bold"))
        self._arrow(c, meta_x + 96, mid_y, out_x - 92, mid_y, self.step_index >= 7)
        self._prediction_box(c, out_x, mid_y, accent, task)

    def _mini_table(self, c: tk.Canvas, x: float, y: float, accent: str, *, active_rows: int) -> None:
        headers = ["czas", "termin", "koszt", "y"]
        values = [
            ("11.6", "36.6", "116", "0.82"),
            ("10.4", "45.0", "116", "0.71"),
            ("9.2", "32.4", "148", "0.64"),
            ("12.2", "32.4", "116", "?"),
        ]
        c.create_text(x, y - 20, text="mini tabela", fill=accent, anchor="w", font=("Segoe UI", 9, "bold"))
        for col, header in enumerate(headers):
            cx = x + col * 54
            c.create_rectangle(cx, y, cx + 50, y + 24, fill="#0f3a4a", outline=accent)
            c.create_text(cx + 25, y + 12, text=header, fill="#ecfeff", font=("Segoe UI", 8, "bold"))
        for row, items in enumerate(values):
            active = row < active_rows
            for col, value in enumerate(items):
                cx = x + col * 54
                cy = y + 26 + row * 25
                c.create_rectangle(cx, cy, cx + 50, cy + 22, fill="#10243a" if active else "#172334", outline="#155e75")
                c.create_text(cx + 25, cy + 11, text=value, fill="#f8fafc", font=("Consolas", 8, "bold"))

    def _prediction_box(self, c: tk.Canvas, x: float, y: float, accent: str, task: str) -> None:
        c.create_rectangle(x - 92, y - 72, x + 100, y + 84, fill="#07111c", outline=accent, width=2)
        c.create_rectangle(x - 92, y - 72, x + 100, y - 38, fill="#0f2a37", outline="")
        c.create_text(x - 72, y - 55, text="PREDYKCJA", fill="#f8fafc", anchor="w", font=("Segoe UI", 9, "bold"))
        probabilities = self.model.probabilities if self.model is not None else ()
        for idx, (name, value) in enumerate(probabilities):
            yy = y - 14 + idx * 31
            c.create_rectangle(x - 64, yy, x + 72, yy + 18, fill="#10243a", outline="#155e75")
            c.create_rectangle(x - 64, yy, x - 64 + 136 * value, yy + 18, fill=accent if self.step_index >= 7 else "#475569", outline="")
            c.create_text(x - 58, yy + 9, text=name, fill="#f8fafc", anchor="w", font=("Segoe UI", 7, "bold"))
            c.create_text(x + 66, yy + 9, text=f"{value:.2f}", fill="#ecfeff", anchor="e", font=("Consolas", 7))
        c.create_text(x, y + 68, text=f"wynik dla: {task}", fill="#cbd5e1", font=("Segoe UI", 8, "bold"))

    def _draw_sto_flow(self, c: tk.Canvas, box: tuple[float, float, float, float]) -> None:
        x1, y1, x2, y2 = box
        accent = GREEN
        jobs = [
            ("J3", 2, 8, BLUE),
            ("J2", 4, 11, GREEN),
            ("J1", 6, 10, YELLOW),
            ("J4", 7, 18, PURPLE),
        ]
        c.create_rectangle(x1 + 28, y1 + 34, x2 - 28, y2 - 28, fill="#07111c", outline="#1f4f85")
        c.create_rectangle(x1 + 28, y1 + 34, x2 - 28, y1 + 72, fill="#10243a", outline="")
        c.create_text(
            x1 + 48,
            y1 + 53,
            text="STO flow: zadania -> reguła sortowania -> oś czasu -> opóźnienia -> wynik",
            fill="#f8fafc",
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )

        input_x = x1 + 58
        input_y = y1 + 98
        c.create_text(input_x, input_y - 18, text="DANE", fill="#93c5fd", anchor="w", font=("Segoe UI", 9, "bold"))
        for index, (job, proc, deadline, color) in enumerate(jobs):
            yy = input_y + index * 34
            active = self.step_index >= 1 + index
            fill = "#0f1b2a" if active else "#111827"
            outline = color if active else "#475569"
            c.create_rectangle(input_x, yy, input_x + 170, yy + 26, fill=fill, outline=outline)
            c.create_oval(input_x + 9, yy + 8, input_x + 19, yy + 18, fill=color if active else "#64748b", outline="")
            c.create_text(input_x + 30, yy + 13, text=job, fill="#f8fafc", anchor="w", font=("Segoe UI", 9, "bold"))
            c.create_text(input_x + 78, yy + 13, text=f"p={proc}", fill="#cbd5e1", anchor="w", font=("Consolas", 9, "bold"))
            c.create_text(input_x + 126, yy + 13, text=f"d={deadline}", fill="#cbd5e1", anchor="w", font=("Consolas", 9, "bold"))

        rank_x = x1 + 300
        rank_y = y1 + 116
        c.create_text(rank_x, rank_y - 36, text="REGUŁA", fill="#93c5fd", anchor="w", font=("Segoe UI", 9, "bold"))
        c.create_rectangle(rank_x, rank_y - 16, rank_x + 230, rank_y + 92, fill="#0f1b2a", outline=accent, width=2)
        rule = "EDD / MT: sortuj po d_j" if self.step_index < 5 else "ranking: J3 -> J1 -> J2 -> J4"
        c.create_text(rank_x + 16, rank_y + 6, text=rule, fill="#dcfce7", anchor="w", font=("Segoe UI", 11, "bold"))
        c.create_text(
            rank_x + 16,
            rank_y + 34,
            text="Każde zadanie dostaje score.\nNajmniejszy score idzie pierwsze.",
            fill="#cbd5e1",
            anchor="nw",
            font=("Segoe UI", 9),
            width=190,
        )

        timeline_x = x1 + 590
        timeline_y = y1 + 122
        c.create_text(timeline_x, timeline_y - 42, text="OŚ CZASU", fill="#93c5fd", anchor="w", font=("Segoe UI", 9, "bold"))
        c.create_line(timeline_x, timeline_y + 70, x2 - 310, timeline_y + 70, fill="#38bdf8", width=2)
        cursor = timeline_x
        completion = 0
        ordered_jobs = [jobs[0], jobs[2], jobs[1], jobs[3]]
        scale = max(16, (x2 - timeline_x - 360) / 21)
        total_tardiness = 0
        for index, (job, proc, deadline, color) in enumerate(ordered_jobs):
            active = self.step_index >= index + 4
            width = proc * scale
            completion += proc
            tardiness = max(0, completion - deadline)
            total_tardiness += tardiness
            fill = color if active else "#334155"
            c.create_rectangle(cursor, timeline_y, cursor + width, timeline_y + 46, fill=fill, outline="#e2e8f0" if active else "#64748b", width=2)
            c.create_text(cursor + width / 2, timeline_y + 16, text=job, fill="#07111c" if active and color == YELLOW else "white", font=("Segoe UI", 10, "bold"))
            if active:
                c.create_text(cursor + width / 2, timeline_y + 35, text=f"C={completion}", fill="#07111c" if color == YELLOW else "white", font=("Consolas", 8, "bold"))
                c.create_line(cursor + width, timeline_y + 52, cursor + width, timeline_y + 78, fill="#e2e8f0", width=1)
                c.create_text(cursor + width, timeline_y + 92, text=str(completion), fill="#cbd5e1", font=("Consolas", 8))
            cursor += width + 6

        score_x = x2 - 250
        score_y = y1 + 98
        c.create_text(score_x, score_y - 18, text="WYNIK", fill="#93c5fd", anchor="w", font=("Segoe UI", 9, "bold"))
        c.create_rectangle(score_x, score_y, x2 - 58, score_y + 150, fill="#0f1b2a", outline=accent, width=2)
        rows = [("C_j", "czas końca"), ("T_j", "spóźnienie"), ("STO", "suma T_j")]
        for idx, (symbol, row_label) in enumerate(rows):
            yy = score_y + 18 + idx * 38
            c.create_rectangle(score_x + 16, yy, score_x + 74, yy + 24, fill="#123456", outline="#1f4f85")
            c.create_text(score_x + 45, yy + 12, text=symbol, fill="#f8fafc", font=("Consolas", 9, "bold"))
            c.create_text(score_x + 88, yy + 12, text=row_label, fill="#cbd5e1", anchor="w", font=("Segoe UI", 9))
        if self.step_index >= 8:
            c.create_rectangle(score_x + 16, score_y + 126, x2 - 78, score_y + 174, fill="#052e1a", outline="#22c55e")
            c.create_text(
                (score_x + x2 - 78) / 2,
                score_y + 150,
                text=f"STO = {total_tardiness}",
                fill="#dcfce7",
                font=("Consolas", 14, "bold"),
            )

        if self.step_index >= 6:
            c.create_rectangle(x1 + 64, y2 - 64, x2 - 64, y2 - 24, fill="#10243a", outline="#22c55e")
            c.create_text(
                (x1 + x2) / 2,
                y2 - 44,
                text="C_j = czas zakończenia | T_j = max(0, C_j - d_j) | STO = ΣT_j | mniejszy STO = lepsza kolejka",
                fill="#dcfce7",
                font=("Consolas", 10, "bold"),
            )

    def _draw_footer(self, c: tk.Canvas, width: int, height: int, kind: str, task: str) -> None:
        assert self.model is not None
        x1, y1, x2, y2 = 44, height - 205, width - 44, height - 24
        accent = self._kind_color(kind)
        c.create_rectangle(x1, y1, x2, y2, fill="#07111c", outline=accent, width=2)
        c.create_rectangle(x1, y1, x1 + 6, y2, fill=accent, outline="")
        c.create_text(
            x1 + 20,
            y1 + 20,
            text="Logika modelu i wzór",
            fill="#f8fafc",
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )
        cards = self._footer_cards(kind, task)
        card_w = (x2 - x1 - 70) / 4
        for i, (name, value) in enumerate(cards):
            cx = x1 + 22 + i * (card_w + 12)
            c.create_rectangle(cx, y1 + 40, cx + card_w, y1 + 94, fill="#0f1b2a", outline="#22364c")
            c.create_text(cx + 12, y1 + 57, text=name, fill="#93c5fd", anchor="w", font=("Segoe UI", 8, "bold"))
            c.create_text(
                cx + 12,
                y1 + 77,
                text=value,
                fill="#f8fafc",
                anchor="w",
                font=("Segoe UI", 9, "bold"),
                width=card_w - 24,
            )
        logic = self._logic_sentence(kind, task)
        c.create_rectangle(x1 + 22, y1 + 108, x2 - 22, y2 - 18, fill="#091827", outline="#1f4f85")
        c.create_text(
            x1 + 36,
            y1 + 123,
            text=logic,
            fill="#dbeafe",
            anchor="nw",
            font=("Segoe UI", 9),
            width=x2 - x1 - 72,
        )

    def _footer_cards(
        self, kind: str, task: str
    ) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str], tuple[str, str]]:
        assert self.model is not None
        if kind == "tabpfn":
            return (
                ("wejscie", "tabela X, cel y"),
                ("mechanizm", "kontekst + prior"),
                ("wzor", "y_hat = f_PFN(train,x)"),
                ("wynik", self.model.result if self.step_index >= 10 else "predykcja w toku"),
            )
        if kind == "sto":
            return (
                ("wejście", "p_j, d_j"),
                ("wzór", "T_j=max(0,C_j-d_j)"),
                ("oznaczenia", "C_j koniec, d_j termin"),
                ("wynik", self.model.result if self.step_index >= 10 else "ranking w toku"),
            )
        return (
            ("wejście", "X -> " + task),
            ("wzór", self._formula_label(kind, task)),
            ("oznaczenia", self._symbol_label(kind)),
            ("wynik", self.model.result if self.step_index >= 10 else "liczone..."),
        )

    @staticmethod
    def _formula_label(kind: str, task: str) -> str:
        if kind == "xgboost":
            return "F_m = F_{m-1}+eta*tree_m"
        if kind == "mlp":
            return "a_l=sigma(W_l*a+b)"
        if kind == "stacking":
            return "y_hat=meta(pred_i)"
        if kind == "tabpfn":
            return "y_hat = PFN(context,x)"
        if kind in {"forest", "extra"}:
            return "ŷ = mean(tree_i(x))"
        if kind in {"boost", "hist"}:
            return "F_m = F_{m-1}+ηh_m"
        if kind == "logistic":
            return "P = softmax(Xw+b)"
        return f"f(x)->{task}"

    @staticmethod
    def _symbol_label(kind: str) -> str:
        if kind == "xgboost":
            return "Omega kara za drzewo"
        if kind == "mlp":
            return "W wagi, sigma aktywacja"
        if kind == "stacking":
            return "pred_i wynik bazowy"
        if kind == "tabpfn":
            return "context=train, x=rekord"
        if kind in {"forest", "extra"}:
            return "x rekord, tree_i drzewo"
        if kind in {"boost", "hist"}:
            return "η krok, h_m poprawka"
        if kind == "logistic":
            return "w wagi, b bias"
        return "p czas, d termin"

    @staticmethod
    def _logic_sentence(kind: str, task: str) -> str:
        if kind == "xgboost":
            return (
                f"Wejscie: cechy X i cel y. XGBoost dodaje kolejne drzewa korekcyjne: "
                "F_m(x)=F_{m-1}(x)+eta*tree_m(x). "
                "Dodatkowo liczy kare Omega(tree), zeby drzewo nie bylo zbyt skomplikowane. "
                f"Wynik to mocna, ale walidowana predykcja {task}."
            )
        if kind == "mlp":
            return (
                "Wejscie: cechy X sa skalowane, bo siec neuronowa jest wrazliwa na skale. "
                "Warstwa liczy a_l=sigma(W_l*a_{l-1}+b_l), a blad wraca przez backprop i aktualizuje wagi. "
                f"Wynik to predykcja {task}, ktora trzeba kontrolowac metrykami train/test."
            )
        if kind == "stacking":
            return (
                "Wejscie: te same cechy X trafiaja do kilku modeli bazowych. "
                "Ich predykcje out-of-fold staja sie nowymi cechami dla meta-modelu. "
                "Wzorowo: y_hat=meta(pred_1(x), pred_2(x), ...). "
                f"Wynik {task} ma sens tylko wtedy, gdy stacking poprawia walidacje, a nie tylko train."
            )
        if kind == "tabpfn":
            return (
                "Wejscie: tabela treningowa X_train z celem y_train oraz nowy rekord x. "
                "TabPFN traktuje trening jako kontekst i korzysta z pretrenowanego priora dla problemow tabelarycznych. "
                "Predykcja ma postac y_hat = f_PFN(X_train, y_train, x). "
                "W praktyce porownujemy ja z classic ML na tych samych metrykach i tym samym podziale testowym."
            )
        if kind == "sto":
            return (
                "Wejście: czasy p_j i terminy d_j. Kolejka daje czasy zakończenia C_j. "
                "Opóźnienie pojedynczego zlecenia: T_j = max(0, C_j - d_j). "
                "Cel STO: minimalizować sumę dodatnich opóźnień, czyli STO = ΣT_j."
            )
        if kind in {"forest", "extra"}:
            return (
                f"Wejście: cechy X rekordu produkcji. Każde drzewo daje własną predykcję {task}. "
                "Regresja liczy średnią: ŷ = (tree_1(x)+...+tree_n(x))/n. "
                "Oznaczenia: x to jeden rekord, tree_i(x) to wynik i-tego drzewa, n to liczba drzew. "
                "Klasyfikacja głosuje klasami albo uśrednia prawdopodobieństwa."
            )
        if kind in {"boost", "hist"}:
            return (
                f"Wejście: cechy X i prawdziwy cel y. Model startuje od prostej predykcji, liczy błąd "
                "i dodaje kolejne małe drzewa: F_m(x)=F_{m-1}(x)+η·h_m(x). "
                "Oznaczenia: F_m to predykcja po m krokach, η to learning_rate, h_m to małe drzewo poprawki. "
                f"Wynik końcowy to poprawiona predykcja {task}."
            )
        if kind == "logistic":
            return (
                "Wejście: cechy X są skalowane, potem model liczy wynik liniowy z = Xw+b. "
                "Softmax zamienia go na prawdopodobieństwa klas: P(class|X). "
                "Wygrywa klasa z największym prawdopodobieństwem."
            )
        return f"Model przekształca cechy X w przewidywany wynik: ŷ = f(X) -> {task}."

    def _arrow(self, c: tk.Canvas, x1: float, y1: float, x2: float, y2: float, active: bool) -> None:
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
