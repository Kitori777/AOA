from __future__ import annotations

import json
import math
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from AOA.config import ASSISTANT_ASSETS_DIR, DATA_DIR
from AOA.core.assistant_service import AssistantService


@dataclass
class AssistantAction:
    kind: str
    value: str


class AOAAssistantDock(ctk.CTkFrame):
    """Ultra-clean companion dock: avatar + bubble + input."""

    def __init__(
        self,
        parent: ctk.CTk,
        *,
        navigate: Callable[[str], None],
        focus_section: Callable[[str, str], None],
        start_autotour: Callable[[], None],
    ) -> None:
        # Tuned for 1920x1080 layout (pixel-perfect baseline)
        self.width_expanded = 452
        self.height_expanded = 218
        self.width_compact = 286
        self.height_compact = 116
        self.avatar_idle_size = 132
        self.avatar_talk_size = 136
        self.bubble_wrap_expanded = 300
        self.bubble_wrap_compact = 158

        super().__init__(
            parent,
            fg_color="#061a31",
            corner_radius=16,
            border_width=1,
            border_color="#2f4f71",
            width=self.width_expanded,
            height=self.height_expanded,
        )
        self.navigate = navigate
        self.focus_section = focus_section
        self.start_autotour = start_autotour
        self.assistant = AssistantService()

        self.compact = False
        self._typing_after_id: str | None = None
        self._bubble_after_id: str | None = None
        self._avatar_after_id: str | None = None
        self._bubble_index = 0
        self._avatar_frame = 0
        self._typing_on = False
        self._typing_tick = 0
        self._wave_after_id: str | None = None
        self._wave_t = 0.0
        self._active_mood = "neutral"
        self._last_answer = "Czego potrzebujesz?"
        self._rotation = [
            "Czego potrzebujesz?",
            "Pokazac, gdzie trenowac model?",
            "Zapytaj o dowolny krok pracy.",
            "ALICE moze uruchomic autopokaz.",
        ]

        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.avatar_idle_frames, self.avatar_talk_frames = self._load_avatar_images()
        self.mood_frames = self._load_mood_frames()
        self.avatar_shadow = ctk.CTkLabel(
            self,
            text="",
            fg_color="#0f2e4f",
            width=96,
            height=16,
            corner_radius=10,
        )
        self.avatar_shadow.grid(row=2, column=0, sticky="s", padx=(10, 8), pady=(0, 8))
        self.avatar_label = ctk.CTkLabel(self, text="", image=self.avatar_idle_frames[0])
        self.avatar_label.grid(row=0, column=0, rowspan=3, sticky="sw", padx=(10, 8), pady=8)

        self.bubble = ctk.CTkLabel(
            self,
            text=self._rotation[0],
            fg_color="#0a2b4c",
            corner_radius=14,
            justify="left",
            wraplength=self.bubble_wrap_expanded,
            font=("Segoe UI", 12, "bold"),
            padx=10,
            pady=8,
        )
        self.bubble.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 6))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))
        row.grid_columnconfigure(0, weight=1)
        self.wave = tk.Canvas(
            row,
            height=14,
            highlightthickness=0,
            bg="#0b2f54",
            bd=0,
        )
        self.wave.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self.input_var = ctk.StringVar(value="")
        self.entry = ctk.CTkEntry(
            row, textvariable=self.input_var, placeholder_text="Np. gdzie trenowac model?"
        )
        self.entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.entry.bind("<Return>", lambda _event: self._on_send())
        self.entry.bind("<Escape>", lambda _event: self.toggle())
        self.avatar_label.bind("<Button-1>", lambda _event: self.entry.focus_set())
        self.send_btn = ctk.CTkButton(row, text=">", width=44, command=self._on_send)
        self.send_btn.grid(row=1, column=1, sticky="e")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))
        bottom.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(bottom, text="ALICE gotowa", text_color="#9bc5eb", anchor="w")
        self.status.grid(row=0, column=0, sticky="w")
        self.toggle_btn = ctk.CTkButton(bottom, text="-", width=28, height=24, command=self.toggle)
        self.toggle_btn.grid(row=0, column=1, sticky="e")

        self._append_hint("Napisz pytanie. Poprowadze Cie krok po kroku.")
        self._animate_bubble_rotation()
        self._animate_avatar()
        self._animate_waveform()

    def toggle(self) -> None:
        self.compact = not self.compact
        if self.compact:
            self._animate_size(self.width_compact, self.height_compact)
            self.wave.grid_remove()
            self.entry.grid_remove()
            self.send_btn.grid_remove()
            self.status.configure(text="ALICE")
            self.bubble.configure(wraplength=self.bubble_wrap_compact)
            self.toggle_btn.configure(text="+")
        else:
            self._animate_size(self.width_expanded, self.height_expanded)
            self.wave.grid()
            self.entry.grid()
            self.send_btn.grid()
            self.status.configure(text="ALICE gotowa")
            self.bubble.configure(wraplength=self.bubble_wrap_expanded)
            self.toggle_btn.configure(text="-")

    def _answer(self, prompt: str) -> tuple[str, list[AssistantAction]]:
        actions: list[AssistantAction] = []
        if "gdzie tren" in prompt or "jak tren" in prompt:
            actions.extend(
                [
                    AssistantAction("focus", "MainPage:models"),
                    AssistantAction("focus", "MainPage:actions"),
                ]
            )
            return (
                "Main: wybierz modele, wczytaj dane, kliknij Uruchom / zapisz wybrane modele.",
                actions,
            )
        if "visual" in prompt or "wykres" in prompt:
            actions.append(AssistantAction("focus", "VisualPage:controls"))
            return "Przenosze do Visual i podswietlam panel.", actions
        if "results" in prompt or "csv" in prompt:
            actions.append(AssistantAction("focus", "ResultsPage:toolbar"))
            return "Przenosze do Results i podswietlam toolbar.", actions
        if "demo" in prompt or "autopokaz" in prompt:
            actions.append(AssistantAction("demo", "full"))
            return "Uruchamiam autopokaz po stronach.", actions

        rag_answer, hits, from_airi = self.assistant.answer(prompt)
        if hits:
            src = ", ".join(chunk.source for chunk in hits[:2])
            engine = "ALICE" if from_airi else "RAG"
            rag_answer = f"{rag_answer}\n[{engine}] {src}"
        return rag_answer, actions

    @staticmethod
    def _mood_for_response(prompt: str, response: str, actions: list[AssistantAction]) -> str:
        p = (prompt or "").lower()
        r = (response or "").lower()
        if any(k in p for k in ("blad", "problem", "nie dziala", "error")) or any(
            k in r for k in ("blad", "problem", "uwaga", "brak")
        ):
            return "alert"
        if any(a.kind == "demo" for a in actions) or "krok" in p or "proces" in p:
            return "guide"
        if any(k in p for k in ("gdzie", "jak", "co kliknac", "co dalej")):
            return "explain"
        if any(k in p for k in ("analiza", "porownaj", "wykres", "dbscan", "pca", "tsne", "lda")):
            return "analysis"
        if any(k in p for k in ("super", "dzieki", "ok", "git")) or any(
            k in r for k in ("gotowe", "zrobione", "uruchamiam")
        ):
            return "success"
        return "neutral"

    def _run_action(self, action: AssistantAction) -> None:
        if action.kind == "focus":
            page, section = action.value.split(":", 1)
            self.navigate(page)
            self.focus_section(page, section)
        elif action.kind == "navigate":
            self.navigate(action.value)
        elif action.kind == "demo":
            self.start_autotour()

    def _on_send(self) -> None:
        prompt = self.input_var.get().strip()
        if not prompt:
            return
        self.input_var.set("")
        self.status.configure(text="ALICE pisze...")
        self._typing_on = True
        self._typing_tick = 0
        self._animate_typing()
        self.after(250, lambda p=prompt: self._resolve_and_render(p))

    def _resolve_and_render(self, prompt: str) -> None:
        response, actions = self._answer(prompt.lower())
        self._active_mood = self._mood_for_response(prompt, response, actions)
        self._last_answer = response
        self._typing_on = False
        self.status.configure(text="ALICE gotowa")
        self.bubble.configure(text=self._trim(response, 120))
        self._pulse_bubble()
        for action in actions:
            self._run_action(action)
        self.after(600, lambda: setattr(self, "_typing_on", False))

    def _animate_typing(self) -> None:
        if not self._typing_on:
            return
        dots = "." * ((self._typing_tick % 3) + 1)
        self.bubble.configure(text=f"Czego potrzebujesz{dots}")
        self._typing_tick += 1
        self._typing_after_id = self.after(320, self._animate_typing)

    def _animate_bubble_rotation(self) -> None:
        if not self._typing_on:
            self.bubble.configure(text=self._rotation[self._bubble_index % len(self._rotation)])
            self._bubble_index += 1
        self._bubble_after_id = self.after(4200, self._animate_bubble_rotation)

    def _animate_avatar(self) -> None:
        mood_idle, mood_talk = self.mood_frames.get(
            self._active_mood, (self.avatar_idle_frames, self.avatar_talk_frames)
        )
        frames = mood_talk if self._typing_on else mood_idle
        idx = self._avatar_frame % len(frames)
        self.avatar_label.configure(image=frames[idx])
        self.avatar_label.grid_configure(pady=(7 if idx % 2 else 9, 8))
        self.avatar_shadow.configure(
            width=104 if (self._typing_on or idx % 2) else 96,
            fg_color="#1d4468" if self._typing_on else ("#12385f" if idx % 2 else "#0f2e4f"),
        )
        self._avatar_frame += 1
        self._avatar_after_id = self.after(120 if self._typing_on else 240, self._animate_avatar)

    def _animate_waveform(self) -> None:
        if not self.wave.winfo_exists():
            return
        self.wave.update_idletasks()
        w = max(self.wave.winfo_width(), 8)
        h = max(self.wave.winfo_height(), 8)
        self.wave.delete("all")
        mid = h / 2
        amp = 4.5 if self._typing_on else 1.8
        color = "#8ecfff" if self._typing_on else "#6aa9dc"
        points: list[float] = []
        step = 5
        for x in range(0, w + step, step):
            y = (
                mid
                + amp * math.sin((x / 16.0) + self._wave_t)
                + (amp * 0.45) * math.sin((x / 7.0) - self._wave_t * 1.4)
            )
            points.extend((x, y))
        self.wave.create_line(*points, fill=color, width=2, smooth=True)
        self.wave.create_line(0, mid, w, mid, fill="#173b5c", width=1)
        self._wave_t += 0.24 if self._typing_on else 0.12
        self._wave_after_id = self.after(45 if self._typing_on else 80, self._animate_waveform)

    def _load_avatar_images(self) -> tuple[list[ctk.CTkImage], list[ctk.CTkImage]]:
        asset = self._resolve_avatar_asset()
        if not asset.exists():
            asset.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (512, 512), (12, 28, 46, 255)).save(asset)
        base = self._portrait_crop(Image.open(asset).convert("RGBA"))
        base = self._white_hair_grade(base)
        pack = self._load_model_pack()
        idle_pack = pack.get("idle", [])
        talk_pack = pack.get("talk", [])
        idle_ops = [
            (
                float(item.get("rotate", 0.0)),
                float(item.get("saturation", 1.0)),
                float(item.get("brightness", 1.0)),
            )
            for item in idle_pack
        ] or [(-2, 1.0, 1.02), (0, 1.0, 1.0), (2, 1.03, 1.0), (0, 1.02, 0.99)]
        talk_ops = [
            (
                float(item.get("rotate", 0.0)),
                float(item.get("saturation", 1.0)),
                float(item.get("brightness", 1.0)),
            )
            for item in talk_pack
        ] or [(-4, 1.05, 1.03), (0, 1.08, 1.06), (4, 1.05, 1.03), (0, 1.1, 1.07)]
        idle_frames = [
            ctk.CTkImage(
                light_image=self._compose_avatar_frame(base, rot, sat, bri),
                dark_image=self._compose_avatar_frame(base, rot, sat, bri),
                size=(self.avatar_idle_size, self.avatar_idle_size),
            )
            for rot, sat, bri in idle_ops
        ]
        talk_frames = [
            ctk.CTkImage(
                light_image=self._compose_avatar_frame(base, rot, sat, bri),
                dark_image=self._compose_avatar_frame(base, rot, sat, bri),
                size=(self.avatar_talk_size, self.avatar_talk_size),
            )
            for rot, sat, bri in talk_ops
        ]
        return idle_frames, talk_frames

    def _load_mood_frames(self) -> dict[str, tuple[list[ctk.CTkImage], list[ctk.CTkImage]]]:
        mapping = {
            "neutral": "alice_white.png",
            "explain": "alice2.png",
            "guide": "alice3.png",
            "success": "alice4.png",
            "alert": "alice5.png",
            "analysis": "alice6.png",
        }
        idle_ops = [(-2, 1.0, 1.02), (0, 1.0, 1.0), (2, 1.03, 1.0), (0, 1.02, 0.99)]
        talk_ops = [(-4, 1.05, 1.03), (0, 1.08, 1.06), (4, 1.05, 1.03), (0, 1.1, 1.07)]
        out: dict[str, tuple[list[ctk.CTkImage], list[ctk.CTkImage]]] = {}
        for mood, fname in mapping.items():
            path = ASSISTANT_ASSETS_DIR / fname
            if not path.exists():
                out[mood] = (self.avatar_idle_frames, self.avatar_talk_frames)
                continue
            base = self._portrait_crop(Image.open(path).convert("RGBA"))
            base = self._white_hair_grade(base)
            idle = [
                ctk.CTkImage(
                    light_image=self._compose_avatar_frame(base, rot, sat, bri),
                    dark_image=self._compose_avatar_frame(base, rot, sat, bri),
                    size=(self.avatar_idle_size, self.avatar_idle_size),
                )
                for rot, sat, bri in idle_ops
            ]
            talk = [
                ctk.CTkImage(
                    light_image=self._compose_avatar_frame(base, rot, sat, bri),
                    dark_image=self._compose_avatar_frame(base, rot, sat, bri),
                    size=(self.avatar_talk_size, self.avatar_talk_size),
                )
                for rot, sat, bri in talk_ops
            ]
            out[mood] = (idle, talk)
        return out

    @staticmethod
    def _load_model_pack() -> dict:
        pack_path = ASSISTANT_ASSETS_DIR / "model_pack.json"
        if not pack_path.exists():
            return {}
        try:
            return json.loads(pack_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _resolve_avatar_asset() -> Path:
        candidates = [
            ASSISTANT_ASSETS_DIR / "alice_white.png",
            ASSISTANT_ASSETS_DIR / "alice_avatar.png",
            ASSISTANT_ASSETS_DIR / "airi_avatar.png",
            DATA_DIR / "assistant_assets" / "alice_white.png",
            DATA_DIR / "assistant_assets" / "alice_avatar.png",
            DATA_DIR / "assistant_assets" / "airi_avatar.png",
        ]
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    def _append_hint(self, text: str) -> None:
        self.bubble.configure(text=self._trim(text, 120))

    @staticmethod
    def _trim(text: str, n: int) -> str:
        return text if len(text) <= n else text[: n - 1].rstrip() + "..."

    def _pulse_bubble(self) -> None:
        self.bubble.configure(fg_color="#214c76")
        self.after(120, lambda: self.bubble.configure(fg_color="#133f69"))
        self.after(250, lambda: self.bubble.configure(fg_color="#0a2b4c"))

    @staticmethod
    def _portrait_crop(image: Image.Image) -> Image.Image:
        # Trim dark border bars before final crop.
        gray = image.convert("L")
        mask = gray.point(lambda p: 255 if p > 18 else 0)
        bbox = mask.getbbox()
        if bbox:
            image = image.crop(bbox)
        target_ratio = 3 / 4
        src_ratio = image.width / max(image.height, 1)
        if src_ratio > target_ratio:
            new_w = int(image.height * target_ratio)
            left = (image.width - new_w) // 2
            crop = image.crop((left, 0, left + new_w, image.height))
        else:
            new_h = int(image.width / target_ratio)
            top = max(0, (image.height - new_h) // 2)
            crop = image.crop((0, top, image.width, top + new_h))
        crop = crop.resize((512, 682), Image.Resampling.LANCZOS)
        mask = Image.new("L", crop.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, crop.width - 1, crop.height - 1), radius=26, fill=255)
        out = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        out.paste(crop, (0, 0), mask)
        ring = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        ring_draw = ImageDraw.Draw(ring)
        ring_draw.rounded_rectangle(
            (2, 2, crop.width - 3, crop.height - 3),
            radius=24,
            outline=(108, 188, 255, 150),
            width=3,
        )
        ring = ring.filter(ImageFilter.GaussianBlur(0.7))
        out.alpha_composite(ring)
        return out

    @staticmethod
    def _compose_avatar_frame(
        base: Image.Image, rotate_deg: float, saturation: float, brightness: float
    ) -> Image.Image:
        img = base.rotate(rotate_deg, resample=Image.Resampling.BICUBIC, expand=False)
        img = ImageEnhance.Color(img).enhance(saturation)
        img = ImageEnhance.Brightness(img).enhance(brightness)
        overlay = Image.new("RGBA", img.size, (56, 114, 173, 22))
        img.alpha_composite(overlay)
        return img

    @staticmethod
    def _white_hair_grade(base: Image.Image) -> Image.Image:
        # Cold, bright grade to push avatar closer to "white-haired" visual style.
        gray = ImageEnhance.Color(base).enhance(0.58)
        bright = ImageEnhance.Brightness(gray).enhance(1.16)
        contrast = ImageEnhance.Contrast(bright).enhance(1.06)
        tint = Image.new("RGBA", contrast.size, (196, 226, 255, 36))
        out = contrast.copy()
        out.alpha_composite(tint)
        return out

    def _animate_size(self, target_w: int, target_h: int) -> None:
        current_w = int(float(self.cget("width")))
        current_h = int(float(self.cget("height")))
        steps = 5
        for i in range(1, steps + 1):
            w = int(current_w + (target_w - current_w) * i / steps)
            h = int(current_h + (target_h - current_h) * i / steps)
            self.after(i * 18, lambda ww=w, hh=h: self.configure(width=ww, height=hh))
