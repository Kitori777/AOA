from __future__ import annotations

import pandas as pd

from AOA.core.optimization.models import Job
from AOA.core.optimization.objectives import OPTIMIZATION_OBJECTIVES, result_key
from AOA.core.scheduling import simulate_schedule


def evaluate_sequence(
    sequence: list[Job], n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> dict:
    if objective not in OPTIMIZATION_OBJECTIVES:
        raise ValueError(f"Nieznany cel optymalizacji: {objective}")
    if not sequence:
        return {
            "order": [], "steps": [], "sto": 0.0, "completion_total": 0.0,
            "makespan_h": 0.0, "total_waste_kg": 0.0, "total_energy_kwh": 0.0,
            "max_positive_delay": 0.0, "machine_count": n_machines,
            "unavailable_machines": tuple(sorted(set(unavailable_machines))),
            "unscheduled_count": 0, "objective": objective,
        }
    frame = pd.DataFrame(
        {
            "sto_job_id": [job.job_id for job in sequence],
            "czas_produkcji_h": [job.processing_time for job in sequence],
            "termin_h": [job.deadline for job in sequence],
            "material": [job.material for job in sequence],
            "ksztalt": [job.shape for job in sequence],
            "odpad_kg": [job.waste_kg for job in sequence],
            "czas_przezbrojenia_h": [job.setup_time for job in sequence],
            "odpad_przezbrojenia_kg": [job.changeover_waste_kg for job in sequence],
            "energia_kwh": [job.energy_kwh for job in sequence],
            "dozwolone_maszyny": [
                "|".join(map(str, job.eligible_machines)) if job.eligible_machines else None
                for job in sequence
            ],
            "components_ready_h": [job.components_ready_h for job in sequence],
            "material_wait_h": [job.material_wait_h for job in sequence],
            "missing_components": [job.missing_components for job in sequence],
            "stock_status": [job.stock_status for job in sequence],
            "stock_reservation": [job.stock_reservation for job in sequence],
        }
    )
    dispatch_objective = {"waste_then_deadline": "waste", "makespan_then_deadline": "makespan"}.get(
        objective, "deadline_then_waste"
    )
    scheduled = simulate_schedule(
        frame,
        n_machines=n_machines,
        objective=dispatch_objective,
        unavailable_machines=unavailable_machines,
    )
    sto = 0.0
    steps: list[dict] = []
    for index, row in scheduled.iterrows():
        if not bool(row.get("scheduled", True)):
            steps.append(
                {
                    "lp": index + 1, "job_id": str(row["sto_job_id"]),
                    "processing_time": round(float(row["czas_produkcji_h"]), 3),
                    "deadline": round(float(row["termin_h"]), 3), "machine_id": 0,
                    "setup_time": 0.0, "start_time": float("nan"),
                    "completion_time": float("nan"), "lateness": 0.0,
                    "tardiness_positive": 0.0, "waste_kg": 0.0, "energy_kwh": 0.0,
                    "components_ready_h": float("nan"), "material_wait_h": float("nan"),
                    "missing_components": str(row.get("missing_components", "")),
                    "stock_status": str(row.get("stock_status", "UNSCHEDULABLE")),
                    "stock_reservation": str(row.get("stock_reservation", "[]")),
                    "unscheduled_reason": str(
                        row.get("unscheduled_reason", "Brak kompletu komponentow.")
                    ),
                    "scheduled": False, "sto_running": round(sto, 3),
                }
            )
            continue
        lateness = float(row["t_end"] - row["termin_h"])
        tardiness_positive = max(0.0, lateness)
        sto += tardiness_positive
        steps.append(
            {
                "lp": index + 1, "job_id": str(row["sto_job_id"]),
                "processing_time": round(float(row["czas_produkcji_h"]), 3),
                "deadline": round(float(row["termin_h"]), 3),
                "machine_id": int(row["machine_id"]),
                "setup_time": round(float(row["setup_h_actual"]), 3),
                "start_time": round(float(row["t_start"]), 3),
                "completion_time": round(float(row["t_end"]), 3),
                "lateness": round(lateness, 3),
                "tardiness_positive": round(tardiness_positive, 3),
                "waste_kg": round(float(row["waste_kg_actual"]), 4),
                "energy_kwh": round(float(row["energy_kwh_actual"]), 3),
                "components_ready_h": round(float(row.get("components_ready_h", 0.0)), 3),
                "material_wait_h": round(float(row.get("material_wait_h_actual", 0.0)), 3),
                "missing_components": str(row.get("missing_components", "")),
                "stock_status": str(row.get("stock_status", "READY")),
                "stock_reservation": str(row.get("stock_reservation", "[]")),
                "unscheduled_reason": "",
                "scheduled": True, "sto_running": round(sto, 3),
            }
        )
    makespan = float(scheduled["makespan_h"].iloc[0])
    return {
        "order": [job.job_id for job in sequence], "steps": steps, "sto": round(sto, 3),
        "completion_total": round(makespan, 3), "makespan_h": round(makespan, 3),
        "total_waste_kg": round(float(scheduled["total_waste_kg"].iloc[0]), 4),
        "total_energy_kwh": round(float(scheduled["total_energy_kwh"].iloc[0]), 3),
        "machine_count": n_machines,
        "unavailable_machines": tuple(sorted(set(unavailable_machines))),
        "unscheduled_count": sum(not step["scheduled"] for step in steps),
        "max_positive_delay": round(max((step["tardiness_positive"] for step in steps), default=0.0), 3),
        "objective": objective,
    }


def evaluation_key(
    sequence: list[Job], n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> tuple:
    result = evaluate_sequence(
        sequence,
        n_machines=n_machines,
        objective=objective,
        unavailable_machines=unavailable_machines,
    )
    return result_key(result, sequence, objective)
