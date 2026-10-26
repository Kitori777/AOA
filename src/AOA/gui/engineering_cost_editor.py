"""In-memory penalty editor; never writes an input CSV."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import customtkinter as ctk

from AOA.core.esm_costs import DelayPenalty, job_penalty
from AOA.core.optimization.models import Job


class EngineeringCostEditor(ctk.CTkToplevel):
    def __init__(
        self, parent, jobs: Sequence[Job], apply: Callable[[dict[str, DelayPenalty]], None]
    ):
        super().__init__(parent)
        self.title("Koszty opóźnień — stawki i tolerancje")
        self.geometry("640x620")
        self.minsize(560, 420)
        self.apply = apply
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self,
            text="Koszt = stawka × max(0, koniec − termin − tolerancja)\n"
            "Stawka w j.p./min, tolerancja w minutach. CSV pozostaje bez zmian.",
            wraplength=580,
            justify="left",
        ).grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        body = ctk.CTkScrollableFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=12)
        body.grid_columnconfigure((0, 1, 2), weight=1)
        for column, title in enumerate(("Zlecenie", "Stawka [j.p./min]", "Tolerancja [min]")):
            ctk.CTkLabel(body, text=title, font=("Segoe UI", 13, "bold")).grid(
                row=0, column=column, padx=6, pady=6
            )
        self.entries: dict[str, tuple[ctk.StringVar, ctk.StringVar]] = {}
        for row, job in enumerate(jobs, 1):
            penalty = job_penalty(job)
            rate, grace = (
                ctk.StringVar(value=f"{penalty.rate_per_min:g}"),
                ctk.StringVar(value=f"{penalty.grace_min:g}"),
            )
            self.entries[job.job_id] = (rate, grace)
            ctk.CTkLabel(body, text=job.job_id).grid(row=row, column=0, padx=6, pady=5)
            ctk.CTkEntry(body, textvariable=rate).grid(
                row=row, column=1, padx=6, pady=5, sticky="ew"
            )
            ctk.CTkEntry(body, textvariable=grace).grid(
                row=row, column=2, padx=6, pady=5, sticky="ew"
            )
        self.status = ctk.StringVar(value="Zastosowanie parametrów unieważni poprzednie wyniki.")
        ctk.CTkLabel(self, textvariable=self.status, wraplength=580).grid(
            row=2, column=0, sticky="ew", padx=12, pady=8
        )
        self.apply_button = ctk.CTkButton(
            self, text="Zastosuj parametry", command=self.apply_values
        )
        self.apply_button.grid(row=3, column=0, sticky="ew", padx=16, pady=12)
        self.lift()

    def apply_values(self) -> None:
        try:
            parameters = {}
            for job_id, (rate, grace) in self.entries.items():
                try:
                    parameters[job_id] = DelayPenalty(
                        float(rate.get().strip().replace(",", ".")),
                        float(grace.get().strip().replace(",", ".")),
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"{job_id}: podaj nieujemną, skończoną stawkę i tolerancję."
                    ) from exc
            self.apply(parameters)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.destroy()
