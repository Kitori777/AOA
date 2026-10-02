from __future__ import annotations

from collections.abc import Sequence

from AOA.core.optimization.models import Job

OPTIMIZATION_OBJECTIVES = (
    "deadline_then_waste",
    "waste_then_deadline",
    "makespan_then_deadline",
    "balanced",
)


def balanced_score(result: dict, jobs: Sequence[Job]) -> float:
    deadline_scale = max(1.0, sum(job.deadline for job in jobs))
    waste_scale = max(1.0, sum(job.waste_kg + job.changeover_waste_kg for job in jobs))
    time_scale = max(1.0, sum(job.processing_time + job.setup_time for job in jobs))
    return (
        result["sto"] / deadline_scale
        + result["total_waste_kg"] / waste_scale
        + result["makespan_h"] / time_scale
    )


def metric_key(result: dict, jobs: Sequence[Job], objective: str) -> tuple:
    metrics: tuple[object, ...]
    if objective == "waste_then_deadline":
        metrics = (result["total_waste_kg"], result["sto"], result["makespan_h"])
    elif objective == "makespan_then_deadline":
        metrics = (result["makespan_h"], result["sto"], result["total_waste_kg"])
    elif objective == "balanced":
        metrics = (
            balanced_score(result, jobs),
            result["sto"],
            result["total_waste_kg"],
            result["makespan_h"],
        )
    else:
        metrics = (result["sto"], result["total_waste_kg"], result["makespan_h"])
    return (result["unscheduled_count"], *metrics)


def result_key(result: dict, jobs: Sequence[Job], objective: str) -> tuple:
    return (*metric_key(result, jobs, objective), tuple(result["order"]))
