from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from AOA.core.production_line_designer import ProductionLineDraft, StationLayout


class ProductionLineCanvas(ctk.CTkFrame):
    """Interactive canvas for a serial production-line graph."""

    def __init__(
        self,
        parent,
        draft: ProductionLineDraft,
        *,
        on_select: Callable[[str | None], None] | None = None,
        on_change: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        super().__init__(parent, fg_color="#0b1220", corner_radius=14)
        self.draft = draft
        self.on_select = on_select
        self.on_change = on_change
        self.on_error = on_error
        self.zoom = 1.0
        self.connection_source_id: str | None = None
        self._drag_station_id: str | None = None
        self._drag_offset = (0.0, 0.0)
        self._pan_origin = (0, 0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            bg="#0b1220",
            highlightthickness=0,
            cursor="arrow",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.x_scroll = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)
        self.x_scroll.grid(row=1, column=0, sticky="ew")
        self.y_scroll = ctk.CTkScrollbar(self, command=self.canvas.yview)
        self.y_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=self.x_scroll.set, yscrollcommand=self.y_scroll.set)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<ButtonPress-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.context_menu = tk.Menu(self, tearoff=False)
        self.context_menu.add_command(
            label="Połącz od tego stanowiska", command=self.begin_connection
        )
        self.context_menu.add_command(label="Usuń połączenia", command=self.disconnect_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Usuń stanowisko", command=self.delete_selected)
        self.redraw()

    def set_draft(self, draft: ProductionLineDraft) -> None:
        self.draft = draft
        self.connection_source_id = None
        self._drag_station_id = None
        self.redraw()

    def begin_connection(self) -> bool:
        station = self.draft.selected_station
        if station is None:
            self._emit_error("Najpierw zaznacz stanowisko początkowe.")
            return False
        self.connection_source_id = station.station_id
        self.canvas.configure(cursor="crosshair")
        self.redraw()
        return True

    def cancel_connection(self) -> None:
        self.connection_source_id = None
        self.canvas.configure(cursor="arrow")
        self.redraw()

    def disconnect_selected(self) -> None:
        station = self.draft.selected_station
        if station is None:
            return
        self.draft.disconnect_station(station.station_id)
        self.cancel_connection()
        self._emit_change()

    def delete_selected(self) -> None:
        if self.draft.delete_selected() is None:
            return
        self.connection_source_id = None
        if self.on_select:
            self.on_select(None)
        self._emit_change()

    def auto_layout(self) -> None:
        self.draft.auto_layout()
        self._emit_change()

    def zoom_in(self) -> None:
        self._set_zoom(self.zoom + 0.1)

    def zoom_out(self) -> None:
        self._set_zoom(self.zoom - 0.1)

    def reset_zoom(self) -> None:
        self._set_zoom(1.0)

    def redraw(self) -> None:
        self.canvas.delete("all")
        max_x = max(
            (layout.x + layout.width for layout in self.draft.layouts.values()),
            default=1000,
        )
        max_y = max(
            (layout.y + layout.height for layout in self.draft.layouts.values()),
            default=620,
        )
        world_width = max(1100, max_x + 220)
        world_height = max(650, max_y + 180)
        self.canvas.configure(
            scrollregion=(0, 0, world_width * self.zoom, world_height * self.zoom)
        )
        self._draw_grid(world_width, world_height)
        station_map = {station.station_id: station for station in self.draft.stations}
        for edge in self.draft.connections:
            source = self.draft.layouts.get(edge.source)
            target = self.draft.layouts.get(edge.target)
            if source and target:
                self._draw_connection(source, target)
        valid_graph, _message = self.draft.graph_status()
        connected_ids = {
            station_id
            for edge in self.draft.connections
            for station_id in (edge.source, edge.target)
        }
        order_map: dict[str, int] = {}
        if valid_graph:
            order_map = {
                station_id: index
                for index, station_id in enumerate(self.draft.ordered_station_ids(), 1)
            }
        for station_id, station in station_map.items():
            layout = self.draft.layouts[station_id]
            isolated = len(station_map) > 1 and station_id not in connected_ids
            self._draw_station(
                layout,
                station.name,
                station.resources,
                station.duration_formula,
                order_map.get(station_id),
                graph_valid=valid_graph,
                isolated=isolated,
            )

    def _on_press(self, event: Any) -> None:
        x, y = self._world_coordinates(event)
        station_id = self._station_at(x, y)
        if station_id is None:
            self.draft.selected_index = None
            self._drag_station_id = None
            if self.on_select:
                self.on_select(None)
            self.redraw()
            return
        self.draft.select_by_id(station_id)
        if self.connection_source_id and station_id != self.connection_source_id:
            try:
                self.draft.connect(self.connection_source_id, station_id)
            except ValueError as exc:
                self._emit_error(str(exc))
            finally:
                self.connection_source_id = None
                self.canvas.configure(cursor="arrow")
            if self.on_select:
                self.on_select(station_id)
            self._emit_change()
            return
        layout = self.draft.layouts[station_id]
        if self._near_output_handle(layout, x, y):
            self.connection_source_id = station_id
            self.canvas.configure(cursor="crosshair")
            self.redraw()
            return
        self._drag_station_id = station_id
        self._drag_offset = (x - layout.x, y - layout.y)
        if self.on_select:
            self.on_select(station_id)
        self.redraw()

    def _on_drag(self, event: Any) -> None:
        if not self._drag_station_id:
            return
        x, y = self._world_coordinates(event)
        offset_x, offset_y = self._drag_offset
        self.draft.move_station(
            self._drag_station_id,
            self._snap(x - offset_x),
            self._snap(y - offset_y),
        )
        self.redraw()

    def _on_release(self, _event: Any) -> None:
        if self._drag_station_id:
            self._emit_change()
        self._drag_station_id = None

    def _on_right_click(self, event: Any) -> None:
        x, y = self._world_coordinates(event)
        station_id = self._station_at(x, y)
        if station_id is None:
            return
        self.draft.select_by_id(station_id)
        if self.on_select:
            self.on_select(station_id)
        self.redraw()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_pan_start(self, event: Any) -> None:
        self._pan_origin = (event.x, event.y)
        self.canvas.scan_mark(event.x, event.y)

    def _on_pan(self, event: Any) -> None:
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_mousewheel(self, event: Any) -> None:
        if event.state & 0x0004:
            self._set_zoom(self.zoom + (0.1 if event.delta > 0 else -0.1))
            return
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _set_zoom(self, value: float) -> None:
        self.zoom = min(1.6, max(0.6, round(value, 2)))
        self.redraw()

    def _draw_grid(self, width: int, height: int) -> None:
        step = int(40 * self.zoom)
        for x in range(0, int(width * self.zoom), max(step, 20)):
            self.canvas.create_line(x, 0, x, height * self.zoom, fill="#172033")
        for y in range(0, int(height * self.zoom), max(step, 20)):
            self.canvas.create_line(0, y, width * self.zoom, y, fill="#172033")

    def _draw_connection(self, source: StationLayout, target: StationLayout) -> None:
        x1 = (source.x + source.width) * self.zoom
        y1 = (source.y + source.height / 2) * self.zoom
        x2 = target.x * self.zoom
        y2 = (target.y + target.height / 2) * self.zoom
        middle = (x1 + x2) / 2
        points = (x1, y1, middle, y1, middle, y2, x2, y2)
        self.canvas.create_line(
            list(points),
            fill="#60a5fa",
            width=max(2, int(3 * self.zoom)),
            arrow="last",
            joinstyle="round",
        )

    def _draw_station(
        self,
        layout: StationLayout,
        name: str,
        resources: int,
        duration_formula: str,
        order: int | None,
        *,
        graph_valid: bool,
        isolated: bool,
    ) -> None:
        x = layout.x * self.zoom
        y = layout.y * self.zoom
        width = layout.width * self.zoom
        height = layout.height * self.zoom
        selected = self.draft.selected_station is not None and (
            self.draft.selected_station.station_id == layout.station_id
        )
        outline = "#2563eb" if selected else "#22c55e" if graph_valid else "#f59e0b"
        if isolated:
            outline = "#ef4444"
        if self.connection_source_id == layout.station_id:
            outline = "#a855f7"
        line_width = 4 if selected or self.connection_source_id == layout.station_id else 2
        self.canvas.create_rectangle(
            x + 6,
            y + 8,
            x + width + 6,
            y + height + 8,
            fill="#020617",
            outline="",
        )
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill="#173553",
            outline=outline,
            width=line_width,
        )
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + 26 * self.zoom,
            fill="#1e3a5f",
            outline=outline,
            width=1,
        )
        title = f"{order}. {name}" if order is not None else name
        self.canvas.create_text(
            x + 12 * self.zoom,
            y + 13 * self.zoom,
            text=title,
            anchor="w",
            fill="#f8fafc",
            width=max(80, width - 24 * self.zoom),
            font=("Segoe UI", max(8, int(10 * self.zoom)), "bold"),
        )
        formula = duration_formula if len(duration_formula) <= 30 else f"{duration_formula[:27]}..."
        details = f"{resources} maszyn\nczas = {formula}"
        self.canvas.create_text(
            x + 14 * self.zoom,
            y + 48 * self.zoom,
            text=details,
            anchor="nw",
            fill="#bfdbfe",
            width=max(80, width - 28 * self.zoom),
            font=("Segoe UI", max(8, int(9 * self.zoom))),
        )
        self.canvas.create_text(
            x + 10 * self.zoom,
            y + height - 10 * self.zoom,
            text=layout.station_id,
            anchor="sw",
            fill="#93c5fd",
            font=("Consolas", max(7, int(8 * self.zoom))),
        )
        handle_radius = max(5, 7 * self.zoom)
        for handle_x in (x, x + width):
            self.canvas.create_oval(
                handle_x - handle_radius,
                y + height / 2 - handle_radius,
                handle_x + handle_radius,
                y + height / 2 + handle_radius,
                fill="#e2e8f0",
                outline=outline,
                width=2,
            )

    def _station_at(self, x: float, y: float) -> str | None:
        for station in reversed(self.draft.stations):
            layout = self.draft.layouts[station.station_id]
            if (
                layout.x <= x <= layout.x + layout.width
                and layout.y <= y <= layout.y + layout.height
            ):
                return station.station_id
        return None

    @staticmethod
    def _near_output_handle(layout: StationLayout, x: float, y: float) -> bool:
        return (
            abs(x - (layout.x + layout.width)) <= 14
            and abs(y - (layout.y + layout.height / 2)) <= 18
        )

    def _world_coordinates(self, event: Any) -> tuple[float, float]:
        return (
            self.canvas.canvasx(event.x) / self.zoom,
            self.canvas.canvasy(event.y) / self.zoom,
        )

    @staticmethod
    def _snap(value: float) -> int:
        return max(10, int(round(value / 20) * 20))

    def _emit_change(self) -> None:
        self.redraw()
        if self.on_change:
            self.on_change()

    def _emit_error(self, message: str) -> None:
        if self.on_error:
            self.on_error(message)
