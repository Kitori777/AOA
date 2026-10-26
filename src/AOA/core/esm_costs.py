"""Engineering objectives and delay penalties; time inputs are always minutes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, replace
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from AOA.core.optimization.models import Job

OBJECTIVES = {
    "sto": "Suma opóźnień [min]",
    "cost": "Koszt opóźnień [j.p.]",
    "waste": "Minimalizacja odpadu [kg]",
}


def validate_objective(objective: str) -> None:
    if objective not in OBJECTIVES:
        raise ValueError("Nieznane kryterium: wybierz sto, cost albo waste.")


@dataclass(frozen=True)
class DelayPenalty:
    rate_per_min: float = 1.0
    grace_min: float = 0.0

    def __post_init__(self) -> None:
        if any(
            isinstance(v, bool) or not isfinite(v) or v < 0
            for v in (self.rate_per_min, self.grace_min)
        ):
            raise ValueError("Stawka i dopuszczalne opóźnienie muszą być skończone i nieujemne.")

    def charge(self, completion_min: float, deadline_min: float) -> float:
        value = self.rate_per_min * max(0.0, completion_min - deadline_min - self.grace_min)
        if not isfinite(value):
            raise ValueError("Koszt przekracza zakres obliczeń. Zmniejsz stawki lub czasy.")
        return value


def job_penalty(job: Job) -> DelayPenalty:
    return DelayPenalty(
        getattr(job, "tardiness_cost_per_min", 1.0), getattr(job, "allowed_tardiness_min", 0.0)
    )


def cost_parameters(jobs: Sequence[Job]) -> dict[str, dict[str, float]]:
    return {
        job.job_id: {
            "rate_per_min": job_penalty(job).rate_per_min,
            "grace_min": job_penalty(job).grace_min,
        }
        for job in jobs
    }


def objective_value(result: dict) -> float:
    objective = result.get("objective", "sto")
    if objective == "waste":
        return result["total_waste_kg"]
    return result["total_tardiness_cost"] if objective == "cost" else result["sto"]


def with_job_penalties(jobs: Sequence[Job], parameters: Mapping[str, DelayPenalty]) -> list[Job]:
    from AOA.core.flowshop import FlowShopJob
    from AOA.core.optimization.models import Job

    if set(parameters) != {j.job_id for j in jobs}:
        raise ValueError("Parametry kosztów muszą odpowiadać wszystkim wczytanym zleceniom.")
    updated: list[Job] = []
    for job in jobs:
        base = (
            job
            if isinstance(job, FlowShopJob)
            else FlowShopJob(**{f.name: getattr(job, f.name) for f in fields(Job)})
        )
        penalty = parameters[job.job_id]
        updated.append(
            replace(
                base,
                tardiness_cost_per_min=penalty.rate_per_min,
                allowed_tardiness_min=penalty.grace_min,
            )
        )
    return updated
