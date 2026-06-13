from __future__ import annotations

import re
import tkinter as tk
from datetime import datetime
from functools import partial
from tkinter import filedialog, messagebox

import customtkinter as ctk

from AOA.config import DATA_DIR
from AOA.core.drawio_service import (
    DRAWIO_SHAPES,
    DRAWIO_TEMPLATES,
    DiagramEdge,
    DiagramNode,
    save_diagram,
    smart_diagram_from_description,
    template_nodes_edges,
)

FILL_PALETTE = [
    ("Bialy", "#ffffff"),
    ("Zielony", "#dcfce7"),
    ("Zolty", "#fef9c3"),
    ("Niebieski", "#dbeafe"),
    ("Czerwony", "#fee2e2"),
    ("Fioletowy", "#ede9fe"),
    ("Szary", "#f1f5f9"),
    ("Pomarańczowy", "#ffedd5"),
]

STROKE_PALETTE = [
    ("Ciemny", "#111827"),
    ("Niebieski", "#2563eb"),
    ("Zielony", "#16a34a"),
    ("Zolty", "#ca8a04"),
    ("Czerwony", "#dc2626"),
    ("Fioletowy", "#7c3aed"),
]

SIZE_PRESETS = [
    ("Maly", 130, 56),
    ("Standard", 180, 72),
    ("Szeroki", 240, 82),
    ("Wysoki", 180, 110),
    ("Duzy", 260, 130),
]

STYLE_PRESETS = {
    "neutral": ("#ffffff", "#111827"),
    "process": ("#dbeafe", "#2563eb"),
    "success": ("#dcfce7", "#16a34a"),
    "warning": ("#fef9c3", "#ca8a04"),
    "danger": ("#fee2e2", "#dc2626"),
    "data": ("#ede9fe", "#7c3aed"),
    "note": ("#ffedd5", "#ea580c"),
}

QUICK_BLOCKS = {
    "Maszyna": ("machine", "Maszyna\noperacja", "process", "Szeroki"),
    "Magazyn": ("warehouse", "Magazyn\nlokacja", "neutral", "Szeroki"),
    "Transport": ("truck", "Transport\ntrasa", "process", "Szeroki"),
    "Kontrola QC": ("inspection", "Kontrola\njakosci", "success", "Wysoki"),
    "Bufor WIP": ("buffer", "Bufor WIP\nkolejka", "warning", "Standard"),
    "Czujnik": ("sensor", "Czujnik\npomiar", "data", "Standard"),
    "Operator": ("operator", "Operator\nrola", "neutral", "Wysoki"),
    "Robot": ("robot", "Robot\nstanowisko", "process", "Wysoki"),
    "Ryzyko": ("risk", "Ryzyko\nblokada", "danger", "Standard"),
    "Model ML": ("model", "Model ML\npredykcja", "data", "Szeroki"),
    "KPI": ("kpi", "KPI\nmetryka", "warning", "Standard"),
    "Przeplyw danych": ("database", "Dane\nwejscie", "data", "Standard"),
    "Dostawca": ("supplier", "Dostawca\nmaterial", "neutral", "Szeroki"),
    "Klient": ("customer", "Klient\nodbiorca", "success", "Szeroki"),
    "Stacja": ("station", "Stacja\nproces", "process", "Szeroki"),
    "Kanban": ("kanban", "Kanban\nsygnal", "warning", "Standard"),
    "Paleta": ("pallet", "Paleta\npartia", "neutral", "Standard"),
    "PLC": ("plc", "PLC\nsterowanie", "data", "Standard"),
    "Andon": ("andon", "ANDON\nalarm", "danger", "Standard"),
    "Energia": ("energy", "Energia\nmedia", "warning", "Standard"),
}


class DrawIOPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.assistant_sections = {}
        self.nodes: list[DiagramNode] = []
        self.edges: list[DiagramEdge] = []
        self.selected_node_id: str | None = None
        self._drag_node_id: str | None = None
        self._drag_offset = (0, 0)
        self.template_var = ctk.StringVar(value="Flowchart")
        self.shape_var = ctk.StringVar(value="rounded")
        self.label_var = ctk.StringVar(value="New block")
        self.fill_var = ctk.StringVar(value="Bialy")
        self.stroke_var = ctk.StringVar(value="Ciemny")
        self.size_var = ctk.StringVar(value="Standard")
        self.style_var = ctk.StringVar(value="neutral")
        self.quick_block_var = ctk.StringVar(value="Maszyna")
        self.source_var = ctk.StringVar(value="")
        self.target_var = ctk.StringVar(value="")
        self.edge_label_var = ctk.StringVar(value="")
        self.status_var = ctk.StringVar(value="Wczytaj szablon albo dodaj pierwszy ksztalt.")
        self._context_node_id: str | None = None
        self._context_canvas_pos = (80, 80)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_controls()
        self._build_canvas()
        self._build_context_menu()
        self.load_template()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=18, fg_color="#0f1d2b")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Diagrams Studio - interaktywne diagramy, UML, ERD, BPMN i eksport",
            font=("Arial", 25, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text=(
                "Przesuwaj elementy myszka, dodawaj ksztalty i polaczenia, kliknij dwukrotnie "
                "element aby zmienic tekst, a prawym przyciskiem otworz menu edycji: tekst, kolor, duplikacja i usuwanie."
            ),
            text_color="#cbd5e1",
            wraplength=1180,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
        ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            fg_color="#123456",
            corner_radius=12,
            text_color="#dbeafe",
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=18, pady=16)

    def _build_controls(self) -> None:
        controls = ctk.CTkFrame(self, corner_radius=18, fg_color="#111827")
        self.assistant_sections["controls"] = controls
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        controls.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        def _group(column: int, title: str) -> ctk.CTkFrame:
            frame = ctk.CTkFrame(controls, fg_color="#0f172a", corner_radius=12)
            frame.grid(row=0, column=column, sticky="nsew", padx=8, pady=10)
            frame.grid_columnconfigure((0, 1), weight=1)
            ctk.CTkLabel(
                frame,
                text=title,
                font=("Arial", 12, "bold"),
                text_color="#bfdbfe",
            ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))
            return frame

        template_group = _group(0, "1. Szablon")
        self.template_menu = ctk.CTkOptionMenu(
            template_group, values=DRAWIO_TEMPLATES, variable=self.template_var
        )
        self.template_menu.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(template_group, text="Wczytaj", command=self.load_template).grid(
            row=2, column=0, sticky="ew", padx=10, pady=(4, 10)
        )
        ctk.CTkButton(template_group, text="Pomysly", command=self.show_diagram_guide).grid(
            row=2, column=1, sticky="ew", padx=10, pady=(4, 10)
        )
        ctk.CTkButton(template_group, text="Z opisu", command=self.show_smart_diagram_builder).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10)
        )

        element_group = _group(1, "2. Element")
        self.shape_menu = ctk.CTkOptionMenu(
            element_group, values=DRAWIO_SHAPES, variable=self.shape_var
        )
        self.shape_menu.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkEntry(
            element_group,
            textvariable=self.label_var,
            placeholder_text="Nazwa elementu",
        ).grid(row=1, column=1, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(element_group, text="Dodaj", command=self.add_shape).grid(
            row=2, column=0, sticky="ew", padx=10, pady=4
        )
        ctk.CTkButton(element_group, text="Duplikuj", command=self.duplicate_selected).grid(
            row=2, column=1, sticky="ew", padx=10, pady=4
        )
        ctk.CTkOptionMenu(
            element_group,
            values=list(QUICK_BLOCKS),
            variable=self.quick_block_var,
        ).grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(
            element_group,
            text="Wstaw gotowiec",
            command=self.add_quick_block,
        ).grid(row=3, column=1, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(element_group, text="Notatka", command=lambda: self.add_quick_shape("note")).grid(
            row=4, column=0, sticky="ew", padx=10, pady=(4, 10)
        )
        ctk.CTkButton(
            element_group,
            text="Kontener",
            command=lambda: self.add_quick_shape("container"),
        ).grid(row=4, column=1, sticky="ew", padx=10, pady=(4, 10))

        style_group = _group(2, "3. Styl")
        ctk.CTkOptionMenu(
            style_group,
            values=[label for label, _color in FILL_PALETTE],
            variable=self.fill_var,
        ).grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkOptionMenu(
            style_group,
            values=[label for label, _color in STROKE_PALETTE],
            variable=self.stroke_var,
        ).grid(row=1, column=1, sticky="ew", padx=10, pady=4)
        ctk.CTkOptionMenu(
            style_group,
            values=[label for label, _width, _height in SIZE_PRESETS],
            variable=self.size_var,
        ).grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkOptionMenu(
            style_group,
            values=list(STYLE_PRESETS),
            variable=self.style_var,
        ).grid(row=2, column=1, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(style_group, text="Zastosuj styl", command=self.apply_selected_style).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 10)
        )

        edge_group = _group(3, "4. Polaczenia")
        self.source_menu = ctk.CTkOptionMenu(edge_group, values=[""], variable=self.source_var)
        self.source_menu.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        self.target_menu = ctk.CTkOptionMenu(edge_group, values=[""], variable=self.target_var)
        self.target_menu.grid(row=1, column=1, sticky="ew", padx=10, pady=4)
        ctk.CTkEntry(
            edge_group,
            textvariable=self.edge_label_var,
            placeholder_text="Etykieta",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(edge_group, text="Dodaj polaczenie", command=self.add_edge).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 10)
        )

        file_group = _group(4, "5. Eksport i akcje")
        ctk.CTkButton(file_group, text="Auto layout", command=self.auto_layout).grid(
            row=1, column=0, sticky="ew", padx=10, pady=4
        )
        ctk.CTkButton(file_group, text="Wyczysc", command=self.clear_diagram).grid(
            row=1, column=1, sticky="ew", padx=10, pady=4
        )
        ctk.CTkButton(file_group, text="Usun zaznaczony", command=self.delete_selected).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=4
        )
        ctk.CTkButton(
            file_group, text=".drawio", command=lambda: self.export("drawio")
        ).grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(file_group, text="SVG", command=lambda: self.export("svg")).grid(
            row=3, column=1, sticky="ew", padx=10, pady=4
        )
        ctk.CTkButton(
            file_group, text="Mermaid", command=lambda: self.export("mermaid")
        ).grid(row=4, column=0, sticky="ew", padx=10, pady=(4, 10))
        ctk.CTkButton(file_group, text="HTML", command=lambda: self.export("html")).grid(
            row=4, column=1, sticky="ew", padx=10, pady=(4, 10)
        )

    def _build_canvas(self) -> None:
        body = ctk.CTkFrame(self, corner_radius=18, fg_color="#0b1220")
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, bg="#f8fafc", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.h_scroll = tk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        self.v_scroll = tk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.h_scroll.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.v_scroll.grid(row=0, column=1, sticky="ns", pady=12, padx=(0, 12))
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)

    def _build_context_menu(self) -> None:
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Edytuj tekst", command=self.edit_selected_label)
        self.context_menu.add_command(label="Duplikuj", command=self.duplicate_selected)
        self.context_menu.add_command(
            label="Dodaj polaczenie stad", command=self.start_edge_from_selected
        )
        self.context_menu.add_command(
            label="Polacz wybrane -> tutaj", command=self.connect_source_to_selected
        )
        self.context_menu.add_separator()

        shape_menu = tk.Menu(self.context_menu, tearoff=0)
        for shape in DRAWIO_SHAPES:
            shape_menu.add_command(label=shape, command=partial(self.set_selected_shape, shape))
        self.context_menu.add_cascade(label="Zmien ksztalt", menu=shape_menu)

        fill_menu = tk.Menu(self.context_menu, tearoff=0)
        for label, color in FILL_PALETTE:
            fill_menu.add_command(label=label, command=partial(self.set_selected_fill, color))
        self.context_menu.add_cascade(label="Wypelnienie", menu=fill_menu)

        stroke_menu = tk.Menu(self.context_menu, tearoff=0)
        for label, color in STROKE_PALETTE:
            stroke_menu.add_command(label=label, command=partial(self.set_selected_stroke, color))
        self.context_menu.add_cascade(label="Obramowanie", menu=stroke_menu)

        size_menu = tk.Menu(self.context_menu, tearoff=0)
        for label, width, height in SIZE_PRESETS:
            size_menu.add_command(label=label, command=partial(self.resize_selected, width, height))
        self.context_menu.add_cascade(label="Rozmiar", menu=size_menu)

        align_menu = tk.Menu(self.context_menu, tearoff=0)
        align_menu.add_command(
            label="Wyrównaj do lewej", command=lambda: self.align_selected_group("left")
        )
        align_menu.add_command(
            label="Wyrównaj do środka X", command=lambda: self.align_selected_group("center_x")
        )
        align_menu.add_command(
            label="Wyrównaj do prawej", command=lambda: self.align_selected_group("right")
        )
        align_menu.add_command(
            label="Wyrównaj do góry", command=lambda: self.align_selected_group("top")
        )
        align_menu.add_command(
            label="Wyrównaj do środka Y", command=lambda: self.align_selected_group("center_y")
        )
        align_menu.add_command(
            label="Wyrównaj do dołu", command=lambda: self.align_selected_group("bottom")
        )
        self.context_menu.add_cascade(label="Wyrównaj do zaznaczonego", menu=align_menu)

        layer_menu = tk.Menu(self.context_menu, tearoff=0)
        layer_menu.add_command(
            label="Na wierzch", command=lambda: self.move_selected_layer("front")
        )
        layer_menu.add_command(label="Na spód", command=lambda: self.move_selected_layer("back"))
        self.context_menu.add_cascade(label="Warstwa", menu=layer_menu)

        self.context_menu.add_separator()
        self.context_menu.add_command(label="Auto layout", command=self.auto_layout)
        self.context_menu.add_command(label="Dopasuj do siatki", command=self.snap_selected_to_grid)
        self.context_menu.add_command(label="Ustaw jako start", command=self.mark_selected_as_start)
        self.context_menu.add_command(label="Ustaw jako koniec", command=self.mark_selected_as_end)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Usun", command=self.delete_selected)

        self.canvas_menu = tk.Menu(self, tearoff=0)
        self.canvas_menu.add_command(label="Dodaj ksztalt tutaj", command=self.add_shape_at_context)
        self.canvas_menu.add_command(
            label="Wklej kopie tutaj", command=self.duplicate_selected_at_context
        )
        self.canvas_menu.add_separator()
        self.canvas_menu.add_command(label="Auto layout", command=self.auto_layout)
        self.canvas_menu.add_command(label="Wyczysc diagram", command=self.clear_diagram)

    def load_template(self) -> None:
        self.nodes, self.edges = template_nodes_edges(self.template_var.get())
        self.selected_node_id = self.nodes[0].id if self.nodes else None
        self.status_var.set(
            f"Szablon: {self.template_var.get()} | elementy: {len(self.nodes)} | polaczenia: {len(self.edges)}"
        )
        self._refresh_node_menus()
        self._draw_preview()

    def add_shape(self) -> None:
        next_index = len(self.nodes) + 1
        x = 80 + ((next_index - 1) % 4) * 220
        y = 80 + ((next_index - 1) // 4) * 140
        self._add_shape_at(x, y)

    def add_shape_at_context(self) -> None:
        x, y = self._context_canvas_pos
        self._add_shape_at(x, y)

    def _add_shape_at(self, x: int, y: int) -> None:
        index = len(self.nodes) + 1
        width, height = self._selected_size()
        fill, stroke = self._selected_colors()
        node = DiagramNode(
            id=f"n{index}",
            label=self.label_var.get().strip() or f"Node {index}",
            shape=self.shape_var.get(),
            x=x,
            y=y,
            width=width,
            height=height,
            fill=fill,
            stroke=stroke,
        )
        self.nodes.append(node)
        self.selected_node_id = node.id
        self.status_var.set(f"Dodano: {node.label}")
        self._refresh_node_menus()
        self._draw_preview()

    def add_quick_shape(self, shape: str) -> None:
        self.shape_var.set(shape)
        if shape == "note":
            self.style_var.set("note")
            self.label_var.set("Notatka")
        elif shape == "container":
            self.style_var.set("data")
            self.label_var.set("Sekcja / grupa")
            self.size_var.set("Duzy")
        self.apply_style_to_controls()
        self.add_shape()

    def add_quick_block(self) -> None:
        shape, label, style, size = QUICK_BLOCKS.get(
            self.quick_block_var.get(), QUICK_BLOCKS["Maszyna"]
        )
        self.shape_var.set(shape)
        self.label_var.set(label)
        self.style_var.set(style)
        self.size_var.set(size)
        self.apply_style_to_controls()
        self.add_shape()

    def apply_style_to_controls(self) -> None:
        fill, stroke = STYLE_PRESETS.get(self.style_var.get(), STYLE_PRESETS["neutral"])
        fill_label = next((label for label, color in FILL_PALETTE if color == fill), self.fill_var.get())
        stroke_label = next((label for label, color in STROKE_PALETTE if color == stroke), self.stroke_var.get())
        self.fill_var.set(fill_label)
        self.stroke_var.set(stroke_label)

    def apply_selected_style(self) -> None:
        self.apply_style_to_controls()
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            self.status_var.set("Styl ustawiony dla nowych elementow. Zaznacz element, aby go przemalowac.")
            return
        fill, stroke = self._selected_colors()
        width, height = self._selected_size()
        node.fill = fill
        node.stroke = stroke
        node.width = width
        node.height = height
        self.status_var.set(f"Zastosowano styl do: {node.label}")
        self._draw_preview()

    def _selected_colors(self) -> tuple[str, str]:
        fill = next((color for label, color in FILL_PALETTE if label == self.fill_var.get()), "#ffffff")
        stroke = next((color for label, color in STROKE_PALETTE if label == self.stroke_var.get()), "#111827")
        return fill, stroke

    def _selected_size(self) -> tuple[int, int]:
        return next(
            ((width, height) for label, width, height in SIZE_PRESETS if label == self.size_var.get()),
            (180, 72),
        )

    def show_diagram_guide(self) -> None:
        guide = ctk.CTkToplevel(self)
        guide.title("Guide: jak wymyslic i zbudowac diagram")
        guide.geometry("980x760")
        guide.minsize(820, 620)
        guide.transient(self.winfo_toplevel())
        guide.grab_set()
        guide.grid_columnconfigure(0, weight=1)
        guide.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            guide,
            text="Jak zrobic dowolny diagram",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))
        text = ctk.CTkTextbox(guide, wrap="word")
        text.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 14))
        text.insert(
            "1.0",
            (
                "1. Najpierw wybierz typ myslenia, nie ksztalt.\n"
                "   Flowchart: kroki procesu i decyzje. UML Class: klasy, pola i metody. ERD: tabele i relacje. BPMN: proces biznesowy. "
                "Network/System Architecture: komponenty systemu. Mind Map: burza pomyslow. Swimlane: odpowiedzialnosc osob lub dzialow.\n\n"
                "2. Dobierz ksztalty.\n"
                "   rounded/process = zwykly krok. diamond/decision = pytanie lub warunek. terminator = start/koniec. database/cylinder = dane. "
                "document = raport lub plik. actor = uzytkownik. container/swimlane = grupa, modul albo dzial.\n\n"
                "3. Dobierz kolory wedlug znaczenia.\n"
                "   Zielony = OK/sukces. Zolty = decyzja lub ostrzezenie. Czerwony = blad/ryzyko. Niebieski = system/proces. Fioletowy = dane/analityka. "
                "Kolory ustawiasz w pasku: wypelnienie, obramowanie, rozmiar i styl.\n\n"
                "4. Buduj diagram w trzech warstwach.\n"
                "   Najpierw dodaj glowny przeplyw od lewej do prawej albo z gory na dol. Potem dodaj decyzje i wyjatki. Na koncu dodaj notatki, kontenery i etykiety polaczen.\n\n"
                "5. Polaczenia opisuj czasownikami.\n"
                "   Dobre etykiety to: yes/no, request, validate, save, retry, error, 1:N, creates, uses. Dzieki temu diagram da sie czytac bez tlumaczenia autora.\n\n"
                "6. Uzywaj szablonow jako startu.\n"
                "   Flowchart do procesu. Data Pipeline do danych. System Architecture do aplikacji. ERD Database do baz. Swimlane do odpowiedzialnosci. "
                "Po wczytaniu szablonu mozesz wszystko przesuwac, zmieniac tekst, kolor, rozmiar i eksportowac.\n\n"
                "7. Szybka kontrola jakosci.\n"
                "   Diagram jest dobry, gdy ma tytul/logiczny start, czytelny kierunek, malo krzyzujacych sie linii, opisane decyzje i maksymalnie jeden sens na element.\n\n"
                "8. Eksport.\n"
                "   .drawio do dalszej edycji, SVG do dokumentu, Mermaid do README, HTML do interaktywnego podgladu."
            ),
        )
        text.configure(state="disabled")
        ctk.CTkButton(guide, text="Zamknij", command=guide.destroy, width=140).grid(
            row=2, column=0, sticky="e", padx=20, pady=(0, 18)
        )

    def show_smart_diagram_builder(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Madry generator diagramu z opisu")
        dialog.geometry("980x760")
        dialog.minsize(820, 620)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            dialog,
            text="Opisz proces, a aplikacja dobierze diagram",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            dialog,
            text=(
                "Mozesz pisac naturalnie albo strzalkami. Przyklady: "
                "dostawca -> magazyn -> produkcja -> QC -> wysylka; "
                "CSV -> walidacja -> model ML -> raport; klient -> API -> baza -> dashboard."
            ),
            text_color="#cbd5e1",
            wraplength=900,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))

        text = ctk.CTkTextbox(dialog, wrap="word", font=("Segoe UI", 14))
        text.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 12))
        text.insert(
            "1.0",
            "Dostawca -> magazyn -> kontrola jakosci -> produkcja -> model ML przewiduje ryzyko -> raport dla kierownika",
        )

        presets = ctk.CTkFrame(dialog, fg_color="transparent")
        presets.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))
        for col in range(4):
            presets.grid_columnconfigure(col, weight=1)
        examples = [
            ("Produkcja", "Dostawca -> magazyn -> linia produkcyjna -> QC -> pakowanie -> wysylka"),
            ("Dane/ML", "CSV -> walidacja danych -> cechy X -> model ML -> metryki -> raport"),
            ("System", "Uzytkownik -> panel GUI -> API -> baza danych -> dashboard -> alert"),
            ("Logistyka", "Zamowienie -> kompletacja -> transport -> magazyn klienta -> potwierdzenie"),
        ]

        def _set_example(value: str) -> None:
            text.delete("1.0", "end")
            text.insert("1.0", value)

        for idx, (label_text, example) in enumerate(examples):
            ctk.CTkButton(
                presets,
                text=label_text,
                command=lambda value=example: _set_example(value),
            ).grid(row=0, column=idx, sticky="ew", padx=5)

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        def _build() -> None:
            description = text.get("1.0", "end").strip()
            if not description:
                messagebox.showwarning("Diagram z opisu", "Najpierw opisz proces albo wybierz przyklad.")
                return
            self.nodes, self.edges, template, note = smart_diagram_from_description(description)
            self.template_var.set(template)
            self.selected_node_id = self.nodes[0].id if self.nodes else None
            self.status_var.set(f"Zbudowano z opisu: {template} | {note}")
            self._refresh_node_menus()
            self._draw_preview()
            dialog.destroy()

        ctk.CTkLabel(
            footer,
            text="Po wygenerowaniu nadal mozesz przesuwac elementy, zmieniac kolory, dodawac kontenery i eksportowac.",
            text_color="#bfdbfe",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ctk.CTkButton(footer, text="Zbuduj diagram", command=_build, width=170).grid(
            row=0, column=1, padx=6
        )
        ctk.CTkButton(footer, text="Zamknij", command=dialog.destroy, width=130).grid(
            row=0, column=2, padx=6
        )

    def _diagram_from_description(
        self, description: str
    ) -> tuple[list[DiagramNode], list[DiagramEdge], str, str]:
        return smart_diagram_from_description(description)

    def _unused_legacy_diagram_from_description(
        self, description: str
    ) -> tuple[list[DiagramNode], list[DiagramEdge], str, str]:
        compact = description.lower()
        if any(word in compact for word in ["api", "system", "baza", "dashboard", "serwer"]):
            template = "System Architecture"
        elif any(word in compact for word in ["csv", "dane", "model", "metryk", "raport", "walid"]):
            template = "Data Pipeline"
        elif any(word in compact for word in ["dostaw", "magazyn", "transport", "wysyl", "logist"]):
            template = "Supply Chain"
        elif any(word in compact for word in ["qc", "jakosc", "produkc", "linia", "pakow"]):
            template = "Production Line"
        else:
            template = "Flowchart"

        raw_parts = re.split(r"\s*(?:->|=>|→|,|;|\n)\s*", description)
        parts = [part.strip(" .:-") for part in raw_parts if part.strip(" .:-")]
        if len(parts) < 2:
            parts = ["Start", description.strip(), "Wynik"]
        parts = parts[:10]

        nodes: list[DiagramNode] = []
        edges: list[DiagramEdge] = []
        for idx, part in enumerate(parts):
            shape, fill, stroke = self._smart_shape_style(part, idx, len(parts))
            node = DiagramNode(
                id=f"s{idx + 1}",
                label=part[:42],
                shape=shape,
                x=80 + idx * 230,
                y=150 if idx % 2 == 0 else 270,
                width=190 if shape not in {"database", "decision"} else 170,
                height=74 if shape != "decision" else 88,
                fill=fill,
                stroke=stroke,
            )
            nodes.append(node)
            if idx > 0:
                edges.append(DiagramEdge(f"s{idx}", node.id, self._smart_edge_label(parts[idx - 1], part)))
        return nodes, edges, template, "wybrano ksztalty, kolory i polaczenia z tekstu"

    @staticmethod
    def _smart_shape_style(label_text: str, index: int, total: int) -> tuple[str, str, str]:
        text = label_text.lower()
        if index == 0 and any(word in text for word in ["start", "wejsc", "dostaw", "klient", "uzytkownik"]):
            return "terminator", "#dcfce7", "#16a34a"
        if index == total - 1 and any(word in text for word in ["wynik", "raport", "wysyl", "koniec", "dashboard"]):
            return "terminator", "#dbeafe", "#2563eb"
        if any(word in text for word in ["czy", "ok", "decyz", "warunek", "quality"]):
            return "decision", "#fef9c3", "#ca8a04"
        if any(word in text for word in ["baza", "csv", "dane", "database", "sql"]):
            return "database", "#ede9fe", "#7c3aed"
        if any(word in text for word in ["model", "ml", "tabpfn", "predyk"]):
            return "model", "#ede9fe", "#7c3aed"
        if any(word in text for word in ["qc", "jakosc", "kontrola", "test"]):
            return "inspection", "#dcfce7", "#16a34a"
        if any(word in text for word in ["ryzyk", "blad", "alert", "awaria"]):
            return "risk", "#fee2e2", "#dc2626"
        if any(word in text for word in ["magazyn", "warehouse"]):
            return "warehouse", "#f1f5f9", "#111827"
        if any(word in text for word in ["transport", "wysyl", "trasa"]):
            return "truck", "#dbeafe", "#2563eb"
        return "process", "#dbeafe", "#2563eb"

    @staticmethod
    def _smart_edge_label(previous: str, current: str) -> str:
        current_lower = current.lower()
        if any(word in current_lower for word in ["walid", "kontrola", "qc", "test"]):
            return "sprawdz"
        if any(word in current_lower for word in ["model", "predyk", "metryk"]):
            return "ucz/ocen"
        if any(word in current_lower for word in ["raport", "dashboard"]):
            return "pokaz"
        if any(word in current_lower for word in ["transport", "wysyl"]):
            return "przekaz"
        return "dalej"

    def add_edge(self) -> None:
        source = self.source_var.get()
        target = self.target_var.get()
        if not source or not target or source == target:
            messagebox.showwarning("Polaczenie", "Wybierz dwa rozne elementy.")
            return
        self.edges.append(DiagramEdge(source, target, self.edge_label_var.get().strip()))
        self.status_var.set(f"Dodano polaczenie: {source} -> {target}")
        self._draw_preview()

    def delete_last(self) -> None:
        if self.edges:
            removed = self.edges.pop()
            self.status_var.set(f"Usunieto polaczenie: {removed.source} -> {removed.target}")
        elif self.nodes:
            removed_node = self.nodes.pop()
            self.edges = [
                edge
                for edge in self.edges
                if edge.source != removed_node.id and edge.target != removed_node.id
            ]
            self.status_var.set(f"Usunieto element: {removed_node.label}")
        else:
            self.status_var.set("Diagram jest pusty.")
        self._refresh_node_menus()
        self._draw_preview()

    def delete_selected(self) -> None:
        if not self.selected_node_id:
            self.delete_last()
            return
        node = self._node_by_id(self.selected_node_id)
        if node is None:
            self.delete_last()
            return
        self.nodes = [candidate for candidate in self.nodes if candidate.id != node.id]
        self.edges = [
            edge for edge in self.edges if edge.source != node.id and edge.target != node.id
        ]
        self.selected_node_id = self.nodes[0].id if self.nodes else None
        self.status_var.set(f"Usunieto zaznaczony element: {node.label}")
        self._refresh_node_menus()
        self._draw_preview()

    def duplicate_selected(self) -> None:
        source = self._node_by_id(self.selected_node_id or "")
        if source is None:
            messagebox.showinfo("Duplikuj", "Najpierw zaznacz element diagramu.")
            return
        self._duplicate_node(source, source.x + 32, source.y + 32)

    def duplicate_selected_at_context(self) -> None:
        source = self._node_by_id(self.selected_node_id or "")
        if source is None:
            self.add_shape_at_context()
            return
        x, y = self._context_canvas_pos
        self._duplicate_node(source, x, y)

    def _duplicate_node(self, source: DiagramNode, x: int, y: int) -> None:
        index = len(self.nodes) + 1
        node = DiagramNode(
            id=f"n{index}",
            label=f"{source.label} copy",
            shape=source.shape,
            x=x,
            y=y,
            width=source.width,
            height=source.height,
            fill=source.fill,
            stroke=source.stroke,
        )
        self.nodes.append(node)
        self.selected_node_id = node.id
        self.status_var.set(f"Zduplikowano: {source.label}")
        self._refresh_node_menus()
        self._draw_preview()

    def edit_selected_label(self) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        dialog = ctk.CTkInputDialog(text="Nowy tekst elementu:", title="Edytuj diagram")
        value = dialog.get_input()
        if value is None:
            return
        value = value.strip()
        if not value:
            return
        node.label = value
        self.label_var.set(value)
        self.status_var.set(f"Zmieniono tekst: {node.id}")
        self._draw_preview()

    def set_selected_fill(self, color: str) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        node.fill = color
        fill_label = next((label for label, item_color in FILL_PALETTE if item_color == color), self.fill_var.get())
        self.fill_var.set(fill_label)
        self.status_var.set(f"Zmieniono kolor: {node.label}")
        self._draw_preview()

    def set_selected_stroke(self, color: str) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        node.stroke = color
        stroke_label = next((label for label, item_color in STROKE_PALETTE if item_color == color), self.stroke_var.get())
        self.stroke_var.set(stroke_label)
        self.status_var.set(f"Zmieniono obramowanie: {node.label}")
        self._draw_preview()

    def set_selected_shape(self, shape: str) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        node.shape = shape
        self.shape_var.set(shape)
        self.status_var.set(f"Zmieniono ksztalt: {node.label} -> {shape}")
        self._draw_preview()

    def resize_selected(self, width: int, height: int) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        node.width = width
        node.height = height
        size_label = next(
            (label for label, item_width, item_height in SIZE_PRESETS if item_width == width and item_height == height),
            self.size_var.get(),
        )
        self.size_var.set(size_label)
        self.status_var.set(f"Zmieniono rozmiar: {node.label} ({width}x{height})")
        self._draw_preview()

    def snap_selected_to_grid(self) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        node.x = round(node.x / 40) * 40
        node.y = round(node.y / 40) * 40
        self.status_var.set(f"Dopasowano do siatki: {node.label}")
        self._draw_preview()

    def mark_selected_as_start(self) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        node.shape = "terminator"
        node.label = "Start"
        node.fill = "#dcfce7"
        self.label_var.set(node.label)
        self.status_var.set("Element ustawiony jako Start.")
        self._draw_preview()

    def mark_selected_as_end(self) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        node.shape = "terminator"
        node.label = "End"
        node.fill = "#dbeafe"
        self.label_var.set(node.label)
        self.status_var.set("Element ustawiony jako End.")
        self._draw_preview()

    def start_edge_from_selected(self) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        self.source_var.set(node.id)
        self.status_var.set(
            f"Źródło polaczenia: {node.label}. Kliknij prawym na cel i wybierz polaczenie."
        )

    def connect_source_to_selected(self) -> None:
        target = self._node_by_id(self.selected_node_id or "")
        source = self.source_var.get()
        if target is None or not source or source == target.id:
            messagebox.showwarning("Polaczenie", "Wybierz poprawne zrodlo i cel.")
            return
        if any(edge.source == source and edge.target == target.id for edge in self.edges):
            self.status_var.set("Takie polaczenie juz istnieje.")
            return
        self.edges.append(DiagramEdge(source, target.id, self.edge_label_var.get().strip()))
        self.status_var.set(f"Dodano polaczenie: {source} -> {target.id}")
        self._draw_preview()

    def move_selected_layer(self, direction: str) -> None:
        node = self._node_by_id(self.selected_node_id or "")
        if node is None:
            return
        self.nodes = [candidate for candidate in self.nodes if candidate.id != node.id]
        if direction == "front":
            self.nodes.append(node)
            self.status_var.set(f"Przeniesiono na wierzch: {node.label}")
        else:
            self.nodes.insert(0, node)
            self.status_var.set(f"Przeniesiono na spod: {node.label}")
        self._draw_preview()

    def align_selected_group(self, mode: str) -> None:
        anchor = self._node_by_id(self.selected_node_id or "")
        if anchor is None:
            return
        selected_ids = {anchor.id}
        selected_ids.update(edge.target for edge in self.edges if edge.source == anchor.id)
        selected_ids.update(edge.source for edge in self.edges if edge.target == anchor.id)
        group = [node for node in self.nodes if node.id in selected_ids]
        if len(group) <= 1:
            self.status_var.set("Nie ma polaczonych elementow do wyrownania.")
            return
        for node in group:
            if node.id == anchor.id:
                continue
            if mode == "left":
                node.x = anchor.x
            elif mode == "center_x":
                node.x = int(anchor.x + anchor.width / 2 - node.width / 2)
            elif mode == "right":
                node.x = anchor.x + anchor.width - node.width
            elif mode == "top":
                node.y = anchor.y
            elif mode == "center_y":
                node.y = int(anchor.y + anchor.height / 2 - node.height / 2)
            elif mode == "bottom":
                node.y = anchor.y + anchor.height - node.height
        self.status_var.set(f"Wyrownano polaczone elementy do: {anchor.label}")
        self._draw_preview()

    def auto_layout(self) -> None:
        if not self.nodes:
            self.status_var.set("Diagram jest pusty.")
            return
        levels: dict[str, int] = {node.id: 0 for node in self.nodes}
        changed = True
        while changed:
            changed = False
            for edge in self.edges:
                next_level = levels.get(edge.source, 0) + 1
                if next_level > levels.get(edge.target, 0):
                    levels[edge.target] = min(next_level, 8)
                    changed = True
        grouped: dict[int, list[DiagramNode]] = {}
        for node in self.nodes:
            grouped.setdefault(levels.get(node.id, 0), []).append(node)
        for level, group in sorted(grouped.items()):
            for index, node in enumerate(group):
                node.x = 80 + level * 240
                node.y = 80 + index * 140
        self.status_var.set("Auto layout: ulozono elementy wedlug polaczen.")
        self._draw_preview()

    def clear_diagram(self) -> None:
        self.nodes = []
        self.edges = []
        self.status_var.set("Wyczyszczono diagram.")
        self._refresh_node_menus()
        self._draw_preview()

    def export(self, fmt: str) -> None:
        if not self.nodes:
            messagebox.showwarning("Eksport", "Najpierw dodaj element do diagramu.")
            return
        ext = "mmd" if fmt == "mermaid" else fmt
        output_dir = DATA_DIR / "diagrams"
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"diagram_{self.template_var.get().lower().replace(' ', '_')}_{stamp}.{ext}"
        filetypes = {
            "drawio": [("Draw.io", "*.drawio"), ("XML", "*.xml")],
            "svg": [("SVG", "*.svg")],
            "mermaid": [("Mermaid", "*.mmd"), ("Text", "*.txt")],
            "html": [("HTML", "*.html")],
        }[fmt]
        path = filedialog.asksaveasfilename(
            title="Zapisz diagram",
            initialdir=str(output_dir),
            initialfile=default_name,
            defaultextension=f".{ext}",
            filetypes=filetypes,
        )
        if not path:
            return
        saved = save_diagram(path, self.nodes, self.edges, fmt)
        self.status_var.set(f"Zapisano: {saved}")
        messagebox.showinfo("Gotowe", f"Zapisano diagram:\n{saved}")

    def _on_canvas_press(self, event) -> None:
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        node = self._node_at(x, y)
        if node is None:
            self.selected_node_id = None
            self._drag_node_id = None
            self._draw_preview()
            return
        self.selected_node_id = node.id
        self._drag_node_id = node.id
        self._drag_offset = (x - node.x, y - node.y)
        self.source_var.set(node.id)
        self._sync_controls_from_node(node)
        self.status_var.set(f"Zaznaczono: {node.label}. Przeciagnij, aby przesunac.")
        self._draw_preview()

    def _on_canvas_drag(self, event) -> None:
        if not self._drag_node_id:
            return
        node = self._node_by_id(self._drag_node_id)
        if node is None:
            return
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        offset_x, offset_y = self._drag_offset
        node.x = max(10, x - offset_x)
        node.y = max(10, y - offset_y)
        self.status_var.set(f"Przesuwasz: {node.label} | x={node.x}, y={node.y}")
        self._draw_preview()

    def _on_canvas_release(self, _event) -> None:
        if self._drag_node_id:
            node = self._node_by_id(self._drag_node_id)
            if node is not None:
                self.status_var.set(f"Przeniesiono: {node.label} | x={node.x}, y={node.y}")
        self._drag_node_id = None

    def _on_canvas_double_click(self, event) -> None:
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        node = self._node_at(x, y)
        if node is None:
            return
        new_label = self.label_var.get().strip()
        if not new_label:
            messagebox.showinfo("Edycja", "Wpisz nowa nazwe elementu w polu 'Nazwa elementu'.")
            return
        node.label = new_label
        self.selected_node_id = node.id
        self.status_var.set(f"Zmieniono tekst: {node.id} -> {new_label}")
        self._draw_preview()

    def _on_canvas_right_click(self, event) -> None:
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        self._context_canvas_pos = (max(10, x), max(10, y))
        node = self._node_at(x, y)
        if node is None:
            self.status_var.set("Menu diagramu: dodaj element albo uloz diagram.")
            try:
                self.canvas_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.canvas_menu.grab_release()
            return
        self.selected_node_id = node.id
        self._context_node_id = node.id
        self.source_var.set(node.id)
        self._sync_controls_from_node(node)
        self.status_var.set(f"Menu edycji: {node.label}")
        self._draw_preview()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _node_by_id(self, node_id: str) -> DiagramNode | None:
        return next((node for node in self.nodes if node.id == node_id), None)

    def _node_at(self, x: int, y: int) -> DiagramNode | None:
        for node in reversed(self.nodes):
            if node.x <= x <= node.x + node.width and node.y <= y <= node.y + node.height:
                return node
        return None

    def _refresh_node_menus(self) -> None:
        values = [node.id for node in self.nodes] or [""]
        self.source_menu.configure(values=values)
        self.target_menu.configure(values=values)
        self.source_var.set(values[0])
        self.target_var.set(values[1] if len(values) > 1 else values[0])

    def _sync_controls_from_node(self, node: DiagramNode) -> None:
        self.shape_var.set(node.shape)
        self.label_var.set(node.label.replace("\\n", " "))
        fill_label = next((label for label, color in FILL_PALETTE if color == node.fill), self.fill_var.get())
        stroke_label = next((label for label, color in STROKE_PALETTE if color == node.stroke), self.stroke_var.get())
        size_label = next(
            (
                label
                for label, width, height in SIZE_PRESETS
                if width == node.width and height == node.height
            ),
            self.size_var.get(),
        )
        self.fill_var.set(fill_label)
        self.stroke_var.set(stroke_label)
        self.size_var.set(size_label)

    def _draw_preview(self) -> None:
        self.canvas.delete("all")
        max_x = max((node.x + node.width for node in self.nodes), default=900) + 120
        max_y = max((node.y + node.height for node in self.nodes), default=620) + 120
        self.canvas.configure(scrollregion=(0, 0, max_x, max_y))
        self._draw_grid(max_x, max_y)
        node_map = {node.id: node for node in self.nodes}
        for edge in self.edges:
            source = node_map.get(edge.source)
            target = node_map.get(edge.target)
            if source is None or target is None:
                continue
            x1, y1, x2, y2, points = self._edge_points(source, target)
            self.canvas.create_line(
                *points,
                fill="#1f2a3a",
                width=2,
                arrow="last",
                smooth=False,
                joinstyle="round",
            )
            if edge.label:
                self.canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2 - 12,
                    text=edge.label,
                    fill="#0f172a",
                    font=("Segoe UI", 10, "bold"),
                )
        for node in self.nodes:
            self._draw_node(node)

    def _draw_grid(self, max_x: int, max_y: int) -> None:
        for x in range(0, max_x, 40):
            self.canvas.create_line(x, 0, x, max_y, fill="#e2e8f0")
        for y in range(0, max_y, 40):
            self.canvas.create_line(0, y, max_x, y, fill="#e2e8f0")

    def _draw_node(self, node: DiagramNode) -> None:
        x, y, w, h = node.x, node.y, node.width, node.height
        outline = "#2563eb" if node.id == self.selected_node_id else node.stroke
        width = 4 if node.id == self.selected_node_id else 2
        fill = node.fill
        if node.id == self.selected_node_id:
            self.canvas.create_rectangle(
                x - 8, y - 8, x + w + 8, y + h + 8, fill="#dbeafe", outline=""
            )
        self.canvas.create_rectangle(x + 6, y + 7, x + w + 6, y + h + 7, fill="#d6dde7", outline="")
        if node.shape in {"ellipse", "terminator", "cloud"}:
            self.canvas.create_oval(x, y, x + w, y + h, fill=fill, outline=outline, width=width)
        elif node.shape in {"diamond", "decision"}:
            self.canvas.create_polygon(
                x + w / 2,
                y,
                x + w,
                y + h / 2,
                x + w / 2,
                y + h,
                x,
                y + h / 2,
                fill=fill,
                outline=outline,
                width=width,
            )
        elif node.shape in {"hexagon"}:
            self.canvas.create_polygon(
                x + 25,
                y,
                x + w - 25,
                y,
                x + w,
                y + h / 2,
                x + w - 25,
                y + h,
                x + 25,
                y + h,
                x,
                y + h / 2,
                fill=fill,
                outline=outline,
                width=width,
            )
        elif node.shape in {"parallelogram"}:
            self.canvas.create_polygon(
                x + 26,
                y,
                x + w,
                y,
                x + w - 26,
                y + h,
                x,
                y + h,
                fill=fill,
                outline=outline,
                width=width,
            )
        elif node.shape in {"warehouse", "supplier"}:
            self.canvas.create_polygon(
                x,
                y + h * 0.35,
                x + w / 2,
                y,
                x + w,
                y + h * 0.35,
                x + w,
                y + h,
                x,
                y + h,
                fill=fill,
                outline=outline,
                width=width,
            )
            for bay in range(1, 4):
                bx = x + bay * w / 4
                self.canvas.create_line(bx, y + h * 0.42, bx, y + h - 10, fill=outline, width=1)
        elif node.shape in {"truck"}:
            self.canvas.create_rectangle(x + 6, y + h * 0.25, x + w * 0.68, y + h * 0.75, fill=fill, outline=outline, width=width)
            self.canvas.create_polygon(
                x + w * 0.68,
                y + h * 0.38,
                x + w * 0.88,
                y + h * 0.38,
                x + w - 8,
                y + h * 0.75,
                x + w * 0.68,
                y + h * 0.75,
                fill=fill,
                outline=outline,
                width=width,
            )
            for wheel_x in (x + w * 0.25, x + w * 0.78):
                self.canvas.create_oval(wheel_x - 9, y + h * 0.72, wheel_x + 9, y + h * 0.72 + 18, fill="#111827", outline="")
        elif node.shape in {"machine", "station"}:
            self.canvas.create_rectangle(x, y + 8, x + w, y + h, fill=fill, outline=outline, width=width)
            self.canvas.create_rectangle(x + 12, y, x + w - 12, y + 18, fill="#eef2ff", outline=outline, width=1)
            self.canvas.create_oval(x + w - 42, y + 28, x + w - 18, y + 52, fill="#f8fafc", outline=outline, width=2)
            self.canvas.create_line(x + 18, y + h - 18, x + w - 18, y + h - 18, fill=outline, width=2)
        elif node.shape in {"kanban", "kpi"}:
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=fill, outline=outline, width=width)
            self.canvas.create_rectangle(x, y, x + w, y + 22, fill="#e0f2fe", outline=outline, width=1)
            self.canvas.create_line(x + 16, y + 42, x + w - 16, y + 42, fill=outline, width=2)
            self.canvas.create_line(x + 16, y + 58, x + w - 34, y + 58, fill=outline, width=2)
        elif node.shape in {"andon", "risk"}:
            self.canvas.create_polygon(
                x + w / 2,
                y,
                x + w,
                y + h,
                x,
                y + h,
                fill=fill,
                outline=outline,
                width=width,
            )
            self.canvas.create_text(x + w / 2, y + h * 0.45, text="!", fill=outline, font=("Segoe UI", 18, "bold"))
        elif node.shape in {"energy"}:
            self.canvas.create_polygon(
                x + w * 0.55,
                y,
                x + w * 0.32,
                y + h * 0.46,
                x + w * 0.52,
                y + h * 0.46,
                x + w * 0.38,
                y + h,
                x + w * 0.72,
                y + h * 0.38,
                x + w * 0.52,
                y + h * 0.38,
                fill=fill,
                outline=outline,
                width=width,
            )
        elif node.shape in {"actor"}:
            cx = x + w / 2
            self.canvas.create_oval(cx - 18, y + 6, cx + 18, y + 42, outline=outline, width=2)
            self.canvas.create_line(cx, y + 42, cx, y + 82, fill=outline, width=2)
            self.canvas.create_line(cx - 34, y + 55, cx + 34, y + 55, fill=outline, width=2)
            self.canvas.create_line(cx, y + 82, cx - 30, y + h - 8, fill=outline, width=2)
            self.canvas.create_line(cx, y + 82, cx + 30, y + h - 8, fill=outline, width=2)
        else:
            self.canvas.create_rectangle(
                x, y, x + w, y + h, fill=fill, outline=outline, width=width
            )
            if node.shape in {"database", "cylinder"}:
                self.canvas.create_arc(
                    x, y - 12, x + w, y + 28, start=0, extent=180, outline=outline, width=2
                )
                self.canvas.create_arc(
                    x,
                    y + h - 28,
                    x + w,
                    y + h + 12,
                    start=180,
                    extent=180,
                    outline=outline,
                    width=2,
                )
        text = node.label.replace("\\n", "\n")
        self.canvas.create_text(
            x + w / 2,
            y + h / 2,
            text=text,
            fill="#111827",
            width=max(60, w - 16),
            justify="center",
            font=("Segoe UI", 10, "bold"),
        )
        self.canvas.create_text(
            x + 8, y + 10, text=node.id, anchor="w", fill="#64748b", font=("Segoe UI", 8)
        )
        if node.id == self.selected_node_id:
            for hx, hy in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]:
                self.canvas.create_rectangle(
                    hx - 4, hy - 4, hx + 4, hy + 4, fill="#1f8fff", outline="white"
                )

    @staticmethod
    def _edge_points(
        source: DiagramNode, target: DiagramNode
    ) -> tuple[float, float, float, float, tuple[float, ...]]:
        sx = source.x + source.width / 2
        sy = source.y + source.height / 2
        tx = target.x + target.width / 2
        ty = target.y + target.height / 2
        dx = tx - sx
        dy = ty - sy
        x1: float
        y1: float
        x2: float
        y2: float
        points: tuple[float, ...]
        if abs(dx) < 24:
            x1 = sx
            y1 = source.y + (source.height if dy >= 0 else 0)
            x2 = tx
            y2 = target.y if dy >= 0 else target.y + target.height
            points = (x1, y1, x2, y2)
        elif abs(dy) < 24:
            x1 = source.x + (source.width if dx >= 0 else 0)
            y1 = sy
            x2 = target.x if dx >= 0 else target.x + target.width
            y2 = ty
            points = (x1, y1, x2, y2)
        elif abs(dx) >= abs(dy):
            x1 = source.x + (source.width if dx >= 0 else 0)
            y1 = sy
            x2 = target.x if dx >= 0 else target.x + target.width
            y2 = ty
            mid_x = (x1 + x2) / 2
            points = (x1, y1, mid_x, y1, mid_x, y2, x2, y2)
        else:
            x1 = sx
            y1 = source.y + (source.height if dy >= 0 else 0)
            x2 = tx
            y2 = target.y if dy >= 0 else target.y + target.height
            mid_y = (y1 + y2) / 2
            points = (x1, y1, x1, mid_y, x2, mid_y, x2, y2)
        return x1, y1, x2, y2, points

    def focus_section(self, section: str) -> None:
        frame = self.assistant_sections.get(section)
        if frame is None:
            return
        try:
            frame.configure(border_width=2, border_color="#1f8fff")
            self.after(1400, lambda: frame.configure(border_width=0))
        except Exception:
            return
