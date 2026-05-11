from __future__ import annotations

import customtkinter as ctk

BG_CARD = "#171b1f"
BG_CARD_2 = "#1d232a"
BORDER = "#303842"
TEXT_MUTED = "#a9b4c2"
BLUE = "#1f8fff"
GREEN = "#22c55e"
YELLOW = "#fbbf24"
PURPLE = "#a855f7"


def make_card(parent, *, radius: int = 14, fg_color: str = BG_CARD, border: bool = True):
    return ctk.CTkFrame(
        parent,
        corner_radius=radius,
        fg_color=fg_color,
        border_width=1 if border else 0,
        border_color=BORDER,
    )


def label(
    parent,
    text: str,
    *,
    size: int = 13,
    weight: str | None = None,
    color: str = "#f8fafc",
    wraplength: int | None = None,
):
    font = ("Segoe UI", size, weight) if weight else ("Segoe UI", size)
    kwargs: dict[str, object] = {
        "text": text,
        "font": font,
        "text_color": color,
        "justify": "left",
    }
    if wraplength is not None:
        kwargs["wraplength"] = wraplength
    return ctk.CTkLabel(parent, **kwargs)


def small_badge(parent, text: str, *, color: str = BLUE):
    badge = ctk.CTkLabel(
        parent,
        text=text,
        fg_color=color,
        text_color="#ffffff",
        corner_radius=12,
        font=("Segoe UI", 11, "bold"),
        padx=10,
        pady=3,
    )
    return badge
