from __future__ import annotations

import random
from functools import cache
from itertools import permutations

from AOA.core.optimization.evaluation import evaluate_sequence, evaluation_key
from AOA.core.optimization.heuristics.classic import (
    sequence_mo,
    sequence_mt,
    sequence_mzo,
    sequence_slack,
)
from AOA.core.optimization.models import Job
from AOA.core.optimization.objectives import result_key


def sequence_mopt(
    jobs: list[Job], n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    if not jobs:
        return []
    if len(jobs) <= 8:
        return best_by_full_search(
            jobs,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        )
    has_component_constraints = any(
        job.components_ready_h > 0 or job.stock_status.upper() == "UNSCHEDULABLE" for job in jobs
    )
    if n_machines > 1 or has_component_constraints or objective != "deadline_then_waste" or len(jobs) > 18:
        return sequence_random_restart(
            jobs, restarts=12 if len(jobs) <= 30 else 6,
            n_machines=n_machines, objective=objective,
            unavailable_machines=unavailable_machines,
        )
    indexed_jobs = tuple(enumerate(jobs))
    processing_sum_cache: dict[int, float] = {}

    def processing_sum(mask: int) -> float:
        if mask not in processing_sum_cache:
            processing_sum_cache[mask] = sum(
                job.processing_time for index, job in indexed_jobs if mask & (1 << index)
            )
        return processing_sum_cache[mask]

    @cache
    def best_for(mask: int) -> tuple[float, tuple[int, ...]]:
        if mask == 0:
            return 0.0, ()
        current_completion = processing_sum(mask)
        best_cost = float("inf")
        best_order: tuple[int, ...] = ()
        for index, job in indexed_jobs:
            bit = 1 << index
            if not mask & bit:
                continue
            previous_cost, previous_order = best_for(mask ^ bit)
            total_cost = previous_cost + max(0.0, current_completion - job.deadline)
            candidate_order = previous_order + (index,)
            if total_cost < best_cost:
                best_cost, best_order = total_cost, candidate_order
            elif total_cost == best_cost:
                current_ids = tuple(jobs[i].job_id for i in best_order)
                candidate_ids = tuple(jobs[i].job_id for i in candidate_order)
                if candidate_ids < current_ids:
                    best_order = candidate_order
        return best_cost, best_order

    _, order = best_for((1 << len(jobs)) - 1)
    return [jobs[index] for index in order]


def sequence_neh(
    jobs: list[Job], n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    ordered = sorted(jobs, key=lambda job: (-job.processing_time, job.deadline, job.job_id))
    if len(ordered) > 60:
        return sequence_local_search(
            jobs,
            n_machines=n_machines,
            initial=ordered,
            objective=objective,
            unavailable_machines=unavailable_machines,
        )
    sequence: list[Job] = []
    for job in ordered:
        candidates = [sequence[:position] + [job] + sequence[position:] for position in range(len(sequence) + 1)]
        sequence = min(
            candidates,
            key=lambda candidate: evaluation_key(
                candidate, n_machines, objective, unavailable_machines
            ),
        )
    return sequence


def sequence_local_search(
    jobs: list[Job], n_machines: int = 1, initial: list[Job] | None = None,
    max_passes: int | None = None, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    best = list(initial) if initial is not None else sequence_mt(jobs)
    large_queue = len(best) > 40
    if max_passes is None and large_queue:
        max_passes = 2
    improved, passes = True, 0
    best_key = evaluation_key(best, n_machines, objective, unavailable_machines)
    while improved and (max_passes is None or passes < max_passes):
        improved = False
        passes += 1
        candidate_indexes = list(range(len(best) - 1))
        if large_queue and len(candidate_indexes) > 24:
            last = len(candidate_indexes) - 1
            candidate_indexes = sorted({round(step * last / 23) for step in range(24)})
        for index in candidate_indexes:
            candidate = best[:]
            candidate[index], candidate[index + 1] = candidate[index + 1], candidate[index]
            candidate_key = evaluation_key(
                candidate, n_machines, objective, unavailable_machines
            )
            if candidate_key < best_key:
                best, best_key, improved = candidate, candidate_key, True
    return best


def sequence_random_restart(
    jobs: list[Job], restarts: int = 80, seed: int = 123, n_machines: int = 1,
    objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    if restarts == 80:
        if len(jobs) > 150:
            restarts = 4
        elif len(jobs) > 60:
            restarts = 6
        elif len(jobs) > 30:
            restarts = 24
    rng = random.Random(seed)
    best = min(
        [sequence_mt(jobs), sequence_mo(jobs), sequence_mzo(jobs), sequence_slack(jobs)],
        key=lambda candidate: evaluation_key(
            candidate, n_machines, objective, unavailable_machines
        ),
    )
    best_key = evaluation_key(best, n_machines, objective, unavailable_machines)
    for _ in range(restarts):
        candidate = list(jobs)
        rng.shuffle(candidate)
        candidate = sequence_local_search(
            jobs,
            n_machines=n_machines,
            initial=candidate,
            objective=objective,
            unavailable_machines=unavailable_machines,
        )
        candidate_key = evaluation_key(
            candidate, n_machines, objective, unavailable_machines
        )
        if candidate_key < best_key:
            best, best_key = candidate, candidate_key
    return best


def best_by_full_search(
    jobs: list[Job], n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    return list(
        _best_by_full_search_cached(
            tuple(jobs), n_machines, objective, tuple(sorted(set(unavailable_machines)))
        )
    )


@cache
def _best_by_full_search_cached(
    jobs: tuple[Job, ...], n_machines: int, objective: str,
    unavailable_machines: tuple[int, ...],
) -> tuple[Job, ...]:
    best_sequence: list[Job] | None = None
    best_eval: dict | None = None
    for perm in permutations(jobs):
        sequence = list(perm)
        evaluation = evaluate_sequence(
            sequence,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        )
        if best_eval is None or result_key(evaluation, jobs, objective) < result_key(best_eval, jobs, objective):
            best_sequence, best_eval = sequence, evaluation
    return tuple(best_sequence if best_sequence is not None else jobs)


def _mutate(order: list[Job], rng: random.Random) -> list[Job]:
    if len(order) < 2:
        return order[:]
    mutated = order[:]
    i, j = rng.sample(range(len(mutated)), 2)
    mutated[i], mutated[j] = mutated[j], mutated[i]
    return mutated


def sequence_genetic(
    jobs: list[Job], population_size: int = 30, generations: int = 40, seed: int = 42,
    n_machines: int = 1, objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> list[Job]:
    if len(jobs) <= 8:
        return best_by_full_search(
            jobs,
            n_machines=n_machines,
            objective=objective,
            unavailable_machines=unavailable_machines,
        )
    if population_size == 30 and len(jobs) > 60:
        population_size = 16
    if generations == 40 and len(jobs) > 60:
        generations = 12
    rng = random.Random(seed)
    population = [sequence_mt(jobs), sequence_mo(jobs), sequence_mzo(jobs), list(jobs)]
    while len(population) < population_size:
        candidate = list(jobs)
        rng.shuffle(candidate)
        population.append(candidate)
    population = population[:population_size]
    for _ in range(generations):
        scored = sorted(
            (
                (
                    evaluation_key(
                        candidate, n_machines, objective, unavailable_machines
                    ),
                    candidate,
                )
                for candidate in population
            ),
            key=lambda item: item[0],
        )
        survivors = [candidate for _, candidate in scored[: max(4, population_size // 3)]]
        population = survivors[:]
        while len(population) < population_size:
            population.append(_mutate(rng.choice(survivors), rng))
    return min(
        population,
        key=lambda candidate: evaluation_key(
            candidate, n_machines, objective, unavailable_machines
        ),
    )
