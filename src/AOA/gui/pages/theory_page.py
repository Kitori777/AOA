import re
import customtkinter as ctk
from tkinter import Text, Scrollbar, BOTH

from AOA.config import THEORY_FILE


class TheoryPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        ctk.CTkLabel(
            self,
            text="Teoria projektu",
            font=("Arial", 24, "bold")
        ).pack(pady=(15, 5))

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        self.v_scroll = Scrollbar(container, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        self.box = Text(
            container,
            wrap="word",
            font=("Segoe UI", 12),
            bg="#1f1f1f",
            fg="white",
            insertbackground="white",
            relief="flat",
            padx=18,
            pady=18,
            yscrollcommand=self.v_scroll.set
        )
        self.box.pack(fill=BOTH, expand=True)

        self.v_scroll.config(command=self.box.yview)

        self._configure_tags()
        self._load_content()

    def _configure_tags(self):
        self.box.tag_configure(
            "h1",
            font=("Segoe UI", 22, "bold"),
            spacing1=10,
            spacing3=14
        )
        self.box.tag_configure(
            "h2",
            font=("Segoe UI", 18, "bold"),
            spacing1=12,
            spacing3=10
        )
        self.box.tag_configure(
            "h3",
            font=("Segoe UI", 15, "bold"),
            spacing1=10,
            spacing3=8
        )
        self.box.tag_configure(
            "h4",
            font=("Segoe UI", 13, "bold"),
            spacing1=8,
            spacing3=6
        )
        self.box.tag_configure(
            "paragraph",
            font=("Segoe UI", 12),
            spacing1=2,
            spacing3=8
        )
        self.box.tag_configure(
            "bullet",
            font=("Segoe UI", 12),
            lmargin1=25,
            lmargin2=45,
            spacing3=4
        )
        self.box.tag_configure(
            "separator",
            font=("Consolas", 11),
            foreground="#9aa0a6",
            justify="center",
            spacing1=8,
            spacing3=8
        )
        self.box.tag_configure(
            "bold",
            font=("Segoe UI", 12, "bold")
        )
        self.box.tag_configure(
            "code",
            font=("Consolas", 11),
            background="#2b2b2b",
            foreground="#7dd3fc"
        )

    def _load_content(self):
        try:
            with open(THEORY_FILE, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = (
                "# Production Optimization\n\n"
                "Nie znaleziono pliku `docs/theory.md`.\n"
                "Upewnij się, że plik istnieje."
            )

        self._render_markdown_like(content)
        self.box.configure(state="disabled")

    def _insert_inline(self, text: str, base_tag: str):
        pattern = r"(\*\*.*?\*\*|`.*?`)"
        parts = re.split(pattern, text)

        for part in parts:
            if not part:
                continue

            if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                self.box.insert("end", part[2:-2], (base_tag, "bold"))
            elif part.startswith("`") and part.endswith("`") and len(part) >= 2:
                self.box.insert("end", part[1:-1], (base_tag, "code"))
            else:
                self.box.insert("end", part, base_tag)

    def _render_markdown_like(self, content: str):
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")

        lines = content.splitlines()

        for line in lines:
            stripped = line.strip()

            if not stripped:
                self.box.insert("end", "\n")
                continue

            if stripped.startswith("════════"):
                self.box.insert("end", stripped + "\n", "separator")
            elif stripped.startswith("# "):
                self._insert_inline(stripped[2:], "h1")
                self.box.insert("end", "\n")
            elif stripped.startswith("## "):
                self._insert_inline(stripped[3:], "h2")
                self.box.insert("end", "\n")
            elif stripped.startswith("### "):
                self._insert_inline(stripped[4:], "h3")
                self.box.insert("end", "\n")
            elif stripped.startswith("#### "):
                self._insert_inline(stripped[5:], "h4")
                self.box.insert("end", "\n")
            elif stripped.startswith("- "):
                self.box.insert("end", "• ", "bullet")
                self._insert_inline(stripped[2:], "bullet")
                self.box.insert("end", "\n")
            else:
                self._insert_inline(stripped, "paragraph")
                self.box.insert("end", "\n")
