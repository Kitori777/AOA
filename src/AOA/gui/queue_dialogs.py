from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from AOA.core.queue_insights import (
    build_queue_scenario_presets,
    compare_queue_scenario,
    queue_diagnostics,
    queue_history_summary,
    verify_queue_audit,
)
from AOA.core.queue_service import load_queue_snapshot


class _TextDialog(ctk.CTkToplevel):
    def __init__(self, parent, *, title: str, geometry: str = "820x620") -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry(geometry)
        self.minsize(680, 480)
        self.configure(fg_color="#071019")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 21, "bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 8)
        )
        self.output = ctk.CTkTextbox(self, wrap="word", fg_color="#0f1d2b", font=("Consolas", 12))
        self.output.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))

    def set_text(self, value: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", value)
        self.output.configure(state="disabled")


class ScenarioLabDialog(_TextDialog):
    """Exclusive what-if selector: one scenario per comparison."""

    def __init__(
        self,
        parent,
        *,
        queue_path: str | Path,
        machine_count: int,
        unavailable_machines: tuple[int, ...] = (),
    ) -> None:
        super().__init__(parent, title="Laboratorium scenariuszy — jeden wariant na raz")
        self.queue_path = Path(queue_path)
        self.machine_count = machine_count
        self.unavailable_machines = unavailable_machines
        snapshot = load_queue_snapshot(self.queue_path)
        self.presets = build_queue_scenario_presets(
            snapshot,
            machine_count=machine_count,
            unavailable_machines=unavailable_machines,
        )
        self.by_label = {preset.label: preset for preset in self.presets}
        first_label = self.presets[0].label if self.presets else "Plan bazowy"
        self.scenario_var = ctk.StringVar(value=first_label)
        controls = ctk.CTkFrame(self, fg_color="#111827")
        controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        controls.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(controls, text="Wybierz jeden scenariusz:").grid(
            row=0, column=0, padx=12, pady=12
        )
        ctk.CTkOptionMenu(
            controls,
            variable=self.scenario_var,
            values=list(self.by_label) or [first_label],
            command=lambda _value: self.run_comparison(),
        ).grid(row=0, column=1, sticky="ew", padx=8, pady=12)
        ctk.CTkButton(controls, text="Porównaj", command=self.run_comparison, width=120).grid(
            row=0, column=2, padx=12, pady=12
        )
        self.run_comparison()

    def run_comparison(self) -> None:
        preset = self.by_label.get(self.scenario_var.get())
        if preset is None:
            self.set_text("Brak dostępnego scenariusza.")
            return
        try:
            snapshot = load_queue_snapshot(self.queue_path)
            comparison = compare_queue_scenario(
                snapshot,
                machine_count=self.machine_count,
                preset_key=preset.key,
                unavailable_machines=self.unavailable_machines,
            )
        except Exception as exc:
            self.set_text(f"Nie można policzyć scenariusza: {exc}")
            return
        lines = [preset.description, "", f"Rekomendowany wariant: {comparison.recommended_name}", ""]
        for item in comparison.scenarios:
            result = item.result
            lines.extend(
                [
                    f"{item.name}",
                    f"  Operacje: {len(result.steps)} | niewykonalne: {len(result.unscheduled)}",
                    f"  STO: {result.total_tardiness_h:.3f} h | koniec: {result.makespan_h:.3f} h",
                    f"  Odpad: {result.total_waste_kg:.3f} kg | naruszenia: {len(result.violations)}",
                    f"  Wyjaśnienie: {item.explanation.summary}",
                ]
            )
            lines.extend(f"  Wąskie gardło: {value}" for value in item.explanation.bottlenecks)
            lines.extend(f"  Zalecenie: {value}" for value in item.explanation.recommendations)
            lines.append("")
        self.set_text("\n".join(lines))


class QueueHistoryDialog(_TextDialog):
    def __init__(self, parent, *, queue_path: str | Path) -> None:
        super().__init__(parent, title="Historia planów i dziennik audytu")
        try:
            rows = queue_history_summary(queue_path, limit=30)
            audit_ok, audit_message = verify_queue_audit(queue_path)
            lines = [
                f"Integralność audytu: {'OK' if audit_ok else 'BŁĄD'} — {audit_message}",
                "",
                "Ostatnie niezmienne przebiegi:",
                *(rows or ("Brak zapisanych przebiegów.",)),
            ]
        except Exception as exc:
            lines = [f"Nie można odczytać historii: {exc}"]
        self.set_text("\n".join(lines))


class QueueDiagnosticsDialog(_TextDialog):
    def __init__(self, parent, *, queue_path: str | Path) -> None:
        super().__init__(parent, title="Diagnostyka Auto Queue", geometry="720x520")
        try:
            report = queue_diagnostics(queue_path)
            lines = [
                f"Wynik: {'OK' if report.ok else 'WYMAGA UWAGI'}",
                f"Utworzono: {report.created_at}",
                "",
            ]
            lines.extend(
                f"[{'OK' if check.ok else 'BŁĄD'}] {check.name}: {check.message}"
                for check in report.checks
            )
            lines.extend(["", "Środowisko:"])
            lines.extend(f"- {key}: {value}" for key, value in report.environment.items())
            lines.extend(["", "Raport nie zawiera treści rekordów CSV ani danych logowania."])
        except Exception as exc:
            lines = [f"Diagnostyka nie powiodła się: {exc}"]
        self.set_text("\n".join(lines))
