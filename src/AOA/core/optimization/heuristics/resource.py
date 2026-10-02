from __future__ import annotations

from AOA.core.optimization.evaluation import evaluation_key
from AOA.core.optimization.heuristics.classic import sequence_mo, sequence_mt
from AOA.core.optimization.heuristics.search import sequence_local_search
from AOA.core.optimization.models import Job


def _best_refined_sequence(
    jobs: list[Job], seeds: list[list[Job]], n_machines: int, objective: str,
    unavailable_machines: tuple[int, ...],
) -> list[Job]:
    unique_seeds: dict[tuple[str, ...], list[Job]] = {
        tuple(job.job_id for job in seed): seed for seed in seeds
    }
    ordered_seeds = sorted(
        unique_seeds.values(),
        key=lambda seed: evaluation_key(
            seed, n_machines, objective, unavailable_machines
        ),
    )
    if len(jobs) > 40:
        ordered_seeds = ordered_seeds[:2]
    refined = [
        sequence_local_search(
            jobs,
            n_machines=n_machines,
            initial=seed,
            max_passes=1 if len(jobs) > 40 else None,
            objective=objective,
            unavailable_machines=unavailable_machines,
        )
        for seed in ordered_seeds
    ]
    return min(
        refined,
        key=lambda candidate: evaluation_key(
            candidate, n_machines, objective, unavailable_machines
        ),
    )


def sequence_eco_waste(
    jobs: list[Job], n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    """Reduce material/shape changeovers while respecting deadline pressure."""
    seeds = [
        sorted(jobs, key=lambda job: (job.material, job.shape, job.deadline, job.processing_time, job.job_id)),
        sequence_mt(jobs), sequence_mo(jobs),
        sorted(jobs, key=lambda job: (job.components_ready_h, job.material, job.shape, job.deadline, job.job_id)),
    ]
    return _best_refined_sequence(
        jobs, seeds, n_machines, objective, unavailable_machines
    )


def sequence_component_ready_edd(
    jobs: list[Job], n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    """Prioritize feasible component release, then deadline, delay, waste and finish time."""
    feasible = [job for job in jobs if job.stock_status.upper() != "UNSCHEDULABLE"]
    impossible = [job for job in jobs if job.stock_status.upper() == "UNSCHEDULABLE"]
    seeds = [
        sorted(feasible, key=lambda job: (job.components_ready_h, job.deadline, job.processing_time, job.waste_kg, job.job_id)),
        sorted(feasible, key=lambda job: (job.deadline, job.components_ready_h, job.job_id)),
        sorted(feasible, key=lambda job: (job.material, job.shape, job.components_ready_h, job.deadline, job.job_id)),
        sequence_mo(feasible),
    ]
    improved = _best_refined_sequence(
        feasible, seeds, n_machines, objective, unavailable_machines
    )
    return improved + sorted(impossible, key=lambda job: (job.deadline, job.job_id))
