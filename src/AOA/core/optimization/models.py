from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Job:
    job_id: str
    processing_time: float
    deadline: float
    material: str = ""
    shape: str = ""
    waste_kg: float = 0.0
    setup_time: float = 0.0
    changeover_waste_kg: float = 0.0
    energy_kwh: float = 0.0
    eligible_machines: tuple[int, ...] = ()
    components_ready_h: float = 0.0
    material_wait_h: float = 0.0
    missing_components: str = ""
    stock_status: str = "READY"
    stock_reservation: str = "[]"


def parse_jobs(job_ids_text: str, processing_text: str, deadlines_text: str) -> list[Job]:
    if not job_ids_text.strip() or not processing_text.strip() or not deadlines_text.strip():
        raise ValueError("Wprowadź komplet danych.")
    job_ids = [item.strip() for item in job_ids_text.split(",") if item.strip()]
    processing_values = [item.strip() for item in processing_text.split(",") if item.strip()]
    deadline_values = [item.strip() for item in deadlines_text.split(",") if item.strip()]
    if not (len(job_ids) == len(processing_values) == len(deadline_values)):
        raise ValueError("Liczba zleceń, czasów i terminów musi być taka sama.")
    jobs: list[Job] = []
    for job_id, p_raw, d_raw in zip(job_ids, processing_values, deadline_values, strict=False):
        try:
            processing_time = float(p_raw)
            deadline = float(d_raw)
        except ValueError:
            raise ValueError("Czasy i terminy muszą być liczbami.") from None
        if processing_time <= 0 or deadline <= 0:
            raise ValueError("Czasy i terminy muszą być dodatnie.")
        jobs.append(Job(job_id=job_id, processing_time=processing_time, deadline=deadline))
    return jobs


def dataframe_to_jobs(
    df: pd.DataFrame,
    job_id_col: str | None = None,
    processing_col: str = "czas_produkcji_h",
    deadline_col: str = "termin_h",
    round_to_int: bool = False,
) -> list[Job]:
    if df is None or df.empty:
        raise ValueError("Brak danych do analizy STO.")
    if processing_col not in df.columns:
        raise ValueError(f"Brak kolumny czasu produkcji: {processing_col}")
    if deadline_col not in df.columns:
        raise ValueError(f"Brak kolumny terminu: {deadline_col}")
    jobs: list[Job] = []
    for idx, row in df.reset_index(drop=True).iterrows():
        job_id = str(row[job_id_col]) if job_id_col and job_id_col in df.columns else f"JOB_{idx + 1}"
        processing_time = float(row[processing_col])
        deadline = float(row[deadline_col])
        if round_to_int:
            processing_time = float(int(round(processing_time)))
            deadline = float(int(round(deadline)))
        if processing_time <= 0 or deadline <= 0:
            raise ValueError("Czasy i terminy w danych STO muszą być dodatnie.")
        raw_eligible = str(row.get("dozwolone_maszyny", "")).replace(",", "|")
        eligible = tuple(int(item) for item in raw_eligible.split("|") if item.strip().isdigit())
        jobs.append(
            Job(
                job_id=job_id,
                processing_time=processing_time,
                deadline=deadline,
                material=str(row.get("material", "")),
                shape=str(row.get("ksztalt", "")),
                waste_kg=float(row.get("odpad_kg", row.get("odpad", 0.0))),
                setup_time=float(row.get("czas_przezbrojenia_h", 0.0)),
                changeover_waste_kg=float(row.get("odpad_przezbrojenia_kg", 0.0)),
                energy_kwh=float(row.get("energia_kwh", 0.0)),
                eligible_machines=eligible,
                components_ready_h=float(row.get("components_ready_h", 0.0))
                if not pd.isna(row.get("components_ready_h", 0.0))
                else float("nan"),
                material_wait_h=float(row.get("material_wait_h", 0.0))
                if not pd.isna(row.get("material_wait_h", 0.0))
                else float("nan"),
                missing_components=str(row.get("missing_components", "")),
                stock_status=str(row.get("stock_status", "READY")),
                stock_reservation=str(row.get("stock_reservation", "[]")),
            )
        )
    return jobs
