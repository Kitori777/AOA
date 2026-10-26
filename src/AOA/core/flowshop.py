"""Permutation flow shop with intermediate waiting, in minutes.

The two-machine timing reproduces MPER 2017-0026, tables 1-8. The forward
branch-and-bound below generalizes the objective to 1-8 stages; it is not a
claim that the paper's two-machine backward bound works unchanged for m stages.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from math import isfinite
from time import perf_counter

from AOA.core.esm_costs import cost_parameters, job_penalty, objective_value, validate_objective
from AOA.core.optimization.models import Job

FLOW_METHODS = ("MT", "MO", "MZO", "MOPT", "ECO_WASTE", "COMPONENT_READY_EDD", "ROBUST_MC")


@dataclass(frozen=True)
class FlowShopJob(Job):
    """A job with an explicit processing time on every visited machine."""

    machine_setup_times: tuple[float, ...] = ()
    tardiness_cost_per_min: float = 1.0
    allowed_tardiness_min: float = 0.0


@dataclass
class FlowShopResult:
    evaluation: dict
    source_jobs: tuple[Job, ...] = ()
    trace: dict[tuple[int, ...], dict] = field(default_factory=dict)
    visited: int = 0
    pruned: int = 0
    improvements: int = 0
    elapsed_s: float = 0.0
    confirmed: bool = False
    stop_reason: str = ""
    lower_bound: float = 0.0


def validate_flowshop(jobs: Sequence[Job], n_machines: int) -> None:
    if isinstance(n_machines, bool) or not isinstance(n_machines, int) or not 1 <= n_machines <= 8:
        raise ValueError("Przeplyw obsluguje od 1 do 8 maszyn.")
    if not 1 <= len(jobs) <= 10:
        raise ValueError("Przeplyw wymaga od 1 do 10 zlecen.")
    if len({job.job_id for job in jobs}) != len(jobs) or any(
        not job.job_id.strip() for job in jobs
    ):
        raise ValueError("Identyfikatory zlecen musza byc niepuste i unikalne.")
    for job in jobs:
        job_penalty(job)
        if len(job.machine_times) < n_machines:
            raise ValueError(
                f"{job.job_id}: CSV zawiera czasy dla {len(job.machine_times)} maszyn, "
                f"wybrano {n_machines}. Wczytaj przyklad z odpowiednia liczba etapow."
            )
        if (
            not isfinite(job.deadline)
            or job.deadline <= 0
            or any(not isfinite(t) or t <= 0 for t in job.machine_times)
        ):
            raise ValueError(f"{job.job_id}: czasy i termin musza byc dodatnie i skonczone.")
        values = (
            job.components_ready_h,
            job.setup_time,
            job.waste_kg,
            job.changeover_waste_kg,
            job.material_wait_h,
        )
        setups = getattr(job, "machine_setup_times", ())
        if any(not isfinite(v) or v < 0 for v in (*values, *setups)):
            raise ValueError(
                f"{job.job_id}: gotowosc, przezbrojenia i odpad musza byc skonczone i nieujemne."
            )
        if setups and len(setups) != len(job.machine_times):
            raise ValueError(f"{job.job_id}: podaj czas przezbrojenia dla kazdego etapu.")
        if (
            job.eligible_machines
            or job.missing_components
            or job.stock_status not in {"READY", "WAITING_COMPONENTS", "UNSCHEDULABLE"}
        ):
            raise ValueError(
                f"{job.job_id}: przeplyw wymaga stalej trasy M1...Mm i statusu "
                "READY, WAITING_COMPONENTS albo UNSCHEDULABLE."
            )


def changeover_factor(previous: Job | None, job: Job) -> float:
    """One line-wide transition; stage setup times use the same factor."""
    if previous is None:
        return 0.0
    material = previous.material != job.material
    shape = previous.shape != job.shape
    return 1.2 if material and shape else 1.0 if material else 0.45 if shape else 0.0


def advance_flowshop(
    available: tuple[float, ...],
    job: Job,
    previous: Job | None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Engineering Job times, including legacy *_h release fields, are minutes.

    Setups are non-anticipatory: both upstream completion and machine
    availability precede preparation. Components gate entry to M1.
    """
    stages = len(available)
    factor = changeover_factor(previous, job)
    base_setups = getattr(job, "machine_setup_times", ()) or (job.setup_time,) * stages
    setups = tuple(factor * t for t in base_setups[:stages])
    ends = []
    upstream = job.components_ready_h
    for stage in range(stages):
        upstream = max(available[stage], upstream) + setups[stage] + job.machine_times[stage]
        ends.append(upstream)
    return tuple(ends), setups


def flowshop_key(result: dict) -> tuple:
    return (
        result["unscheduled_count"],
        round(objective_value(result), 9),
        round(result["sto"] if result.get("objective") == "waste" else result["total_waste_kg"], 9),
        round(result["completion_total"], 9),
    )


def _add_waste(total: float, job: Job, previous: Job | None) -> float:
    value = total + job.waste_kg + changeover_factor(previous, job) * job.changeover_waste_kg
    if not isfinite(value):
        raise ValueError("Suma odpadu przekracza zakres obliczeń. Zmniejsz wartości odpadu.")
    return value


def _advance(available: tuple[float, ...], times: tuple[float, ...]) -> tuple[float, ...]:
    ends = []
    previous = 0.0
    for ready, duration in zip(available, times, strict=True):
        previous = max(ready, previous) + duration
        ends.append(previous)
    return tuple(ends)


def evaluate_flowshop(sequence: Sequence[Job], *, n_machines: int, objective: str = "sto") -> dict:
    validate_flowshop(sequence, n_machines)
    validate_objective(objective)
    available = (0.0,) * n_machines
    steps = []
    sto = 0.0
    total_cost = 0.0
    waste = 0.0
    previous = None
    blocked = []
    scheduled_order = []
    for job in sequence:
        penalty = job_penalty(job)
        if job.stock_status == "UNSCHEDULABLE":
            blocked.append(job.job_id)
            steps.append(
                {
                    "job_id": job.job_id,
                    "machine_id": 0,
                    "scheduled": False,
                    "unscheduled_reason": "Brak kompletu komponentow.",
                    "tardiness_positive": 0.0,
                    "tardiness_cost_per_min": penalty.rate_per_min,
                    "allowed_tardiness_min": penalty.grace_min,
                }
            )
            continue
        ends, setups = advance_flowshop(available, job, previous)
        changeover_waste = changeover_factor(previous, job) * job.changeover_waste_kg
        waste = _add_waste(waste, job, previous)
        tardiness = max(0.0, ends[-1] - job.deadline)
        sto += tardiness
        charge = penalty.charge(ends[-1], job.deadline)
        total_cost += charge
        if not isfinite(total_cost):
            raise ValueError("Suma kosztów przekracza zakres obliczeń.")
        for machine, duration in enumerate(job.machine_times[:n_machines]):
            steps.append(
                {
                    "job_id": job.job_id,
                    "machine_id": machine + 1,
                    "processing_time": duration,
                    "start_time": ends[machine] - duration,
                    "completion_time": ends[machine],
                    "deadline": job.deadline,
                    "tardiness_positive": tardiness if machine == n_machines - 1 else 0.0,
                    "tardiness_cost_per_min": penalty.rate_per_min,
                    "allowed_tardiness_min": penalty.grace_min,
                    "chargeable_tardiness_min": max(0.0, tardiness - penalty.grace_min)
                    if machine == n_machines - 1
                    else 0.0,
                    "tardiness_cost": charge if machine == n_machines - 1 else 0.0,
                    "setup_time": setups[machine],
                    "setup_start": ends[machine] - duration - setups[machine],
                    "components_ready_min": job.components_ready_h,
                    "waste_kg": job.waste_kg + changeover_waste
                    if machine == n_machines - 1
                    else 0.0,
                    "scheduled": True,
                    "final_operation": machine == n_machines - 1,
                }
            )
        available = ends
        previous = job
        scheduled_order.append(job.job_id)
    return {
        "order": [job.job_id for job in sequence],
        "steps": steps,
        "sto": sto,
        "objective": objective,
        "total_tardiness_cost": total_cost,
        "cost_parameters": cost_parameters(sequence),
        "completion_total": available[-1],
        "machine_count": n_machines,
        "unscheduled_count": len(blocked),
        "blocked_jobs": blocked,
        "scheduled_order": scheduled_order,
        "total_waste_kg": waste,
        "model": "flowshop",
    }


def flowshop_order(jobs: Sequence[Job], method: str, n_machines: int) -> list[Job]:
    if method == "MT":
        return sorted(jobs, key=lambda j: (j.deadline, sum(j.machine_times[:n_machines]), j.job_id))
    if method in {"MO", "MZO"}:
        sign = 1 if method == "MO" else -1
        return sorted(
            jobs, key=lambda j: (sign * sum(j.machine_times[:n_machines]), j.deadline, j.job_id)
        )
    raise ValueError(f"Nieznana regula przeplywu: {method}")


def solve_flowshop(
    jobs: Sequence[Job],
    *,
    n_machines: int,
    time_limit_s: float = 10.0,
    max_states: int = 100_000,
    objective: str = "sto",
) -> FlowShopResult:
    """Minimize the selected objective, retaining a bounded real search trace.

    Independent-job completion bounds ignore contention among remaining jobs.
    Ranked bounds use the r shortest processing times on each stage plus the
    smallest downstream tail. Matching these optimistic completions to sorted
    deadlines is a lower bound on total tardiness. Componentwise dominance is
    safe for a common remaining set since the timing recurrence is monotone.
    Equal states are explored only once; the solver does not enumerate all ties.
    """
    validate_flowshop(jobs, n_machines)
    validate_objective(objective)
    if not isfinite(time_limit_s) or time_limit_s < 0 or max_states < 0:
        raise ValueError("Limity obliczen musza byc nieujemne i skonczone.")
    started = perf_counter()
    times = [j.machine_times[:n_machines] for j in jobs]
    index_by_id = {j.job_id: i for i, j in enumerate(jobs)}
    penalties = [job_penalty(j) for j in jobs]

    def charge(i: int, completion: float) -> float:
        return (
            penalties[i].charge(completion, jobs[i].deadline)
            if objective == "cost"
            else max(0.0, completion - jobs[i].deadline)
        )

    def sequence_sto(order: tuple[int, ...]) -> float:
        ends = (0.0,) * n_machines
        total = 0.0
        previous = None
        for i in order:
            ends, _ = advance_flowshop(ends, jobs[i], previous)
            total += max(0.0, ends[-1] - jobs[i].deadline)
            previous = jobs[i]
        return total

    def search_key(score: float, waste: float, finish: float) -> tuple[float, float, float]:
        primary, secondary = (waste, score) if objective == "waste" else (score, waste)
        return round(primary, 9), round(secondary, 9), round(finish, 9)

    def sequence_key(order: tuple[int, ...]) -> tuple[float, float, float, tuple[str, ...]]:
        available = (0.0,) * n_machines
        score = 0.0
        waste = 0.0
        previous = None
        for i in order:
            available, _setups = advance_flowshop(available, jobs[i], previous)
            score += charge(i, available[-1])
            waste = _add_waste(waste, jobs[i], previous)
            previous = jobs[i]
        return (
            *search_key(score, waste, available[-1]),
            tuple(jobs[i].job_id for i in order),
        )

    admitted = [j for j in jobs if j.stock_status != "UNSCHEDULABLE"]
    blocked_jobs = [j for j in jobs if j.stock_status == "UNSCHEDULABLE"]
    seeds = [
        tuple(index_by_id[j.job_id] for j in flowshop_order(admitted, method, n_machines))
        for method in ("MT", "MO", "MZO")
    ]
    best_order = min(seeds, key=sequence_key)
    best_key = sequence_key(best_order)
    initial_sto = sequence_sto(best_order)
    initial_objective = best_key[0]
    # Insertion descent is deterministic and supplies a useful incumbent even
    # when a user intentionally sets a zero search budget.
    improving = True
    while improving:
        improving = False
        for i in range(len(admitted)):
            for position in range(len(admitted)):
                remaining = best_order[:i] + best_order[i + 1 :]
                candidate = remaining[:position] + (best_order[i],) + remaining[position:]
                key = sequence_key(candidate)
                if key < best_key:
                    best_order, best_key, improving = candidate, key, True

    result = FlowShopResult(evaluation={}, source_jobs=tuple(jobs))
    seed_sto = sequence_sto(best_order)
    seed_objective = best_key[0]
    best_from_search = False
    frontier: dict[tuple[int, int], list[tuple[tuple[float, ...], float, float]]] = {}
    full_mask = sum(1 << index_by_id[j.job_id] for j in admitted)
    stateful_setups = any(
        bool(j.setup_time)
        or any(getattr(j, "machine_setup_times", ()))
        or bool(j.changeover_waste_kg)
        for j in admitted
    )

    def bounds(mask: int, available: tuple[float, ...], score: float) -> tuple[float, float]:
        remaining = [i for i in range(len(jobs)) if mask & (1 << i)]
        if not remaining:
            return score, available[-1]
        independent = sum(charge(i, _advance(available, times[i])[-1]) for i in remaining)
        ranked = [0.0] * len(remaining)
        finish_bound = available[-1]
        for stage in range(n_machines):
            tail = min(sum(times[i][stage + 1 :]) for i in remaining)
            cumulative = available[stage]
            for rank, duration in enumerate(sorted(times[i][stage] for i in remaining)):
                cumulative += duration
                ranked[rank] = max(ranked[rank], cumulative + tail)
            finish_bound = max(finish_bound, cumulative + tail)
        sorted_due = sorted(
            jobs[i].deadline + (penalties[i].grace_min if objective == "cost" else 0.0)
            for i in remaining
        )
        ranked_score = sum(max(0.0, end - due) for end, due in zip(ranked, sorted_due, strict=True))
        if objective == "cost":
            # A common minimum rate is safe even when the job/rank pairing is
            # unknown. Sorting heterogeneous rates with due dates is not safe.
            ranked_score *= min(penalties[i].rate_per_min for i in remaining)
        return score + max(independent, ranked_score), finish_bound

    def search_bounds(
        mask: int, available: tuple[float, ...], score: float, waste: float
    ) -> tuple[float, float, float]:
        lower_score, lower_finish = bounds(mask, available, score)
        # Every remaining admitted job contributes its base waste. Future
        # transitions are nonnegative, so ignoring them is an optimistic bound.
        lower_waste = waste + sum(j.waste_kg for i, j in enumerate(jobs) if mask & (1 << i))
        if not isfinite(lower_waste):
            raise ValueError("Suma odpadu przekracza zakres obliczeń.")
        return search_key(lower_score, lower_waste, lower_finish)

    root_bound = search_bounds(full_mask, (0.0,) * n_machines, 0.0, 0.0)
    result.lower_bound = root_bound[0]

    def record(
        path: tuple[int, ...],
        available: tuple[float, ...],
        score: float,
        waste: float,
        lower: tuple[float, float, float],
        status: str,
    ) -> None:
        if len(result.trace) < 2500 or path in result.trace:
            result.trace[path] = {
                "available": available,
                "sto": sequence_sto(path) if objective == "cost" else score,
                "objective_value": waste if objective == "waste" else score,
                "bound": lower[0],
                "status": status,
            }

    def visit(
        path: tuple[int, ...], mask: int, available: tuple[float, ...], score: float, waste: float
    ) -> None:
        nonlocal best_order, best_key, best_from_search
        if result.stop_reason:
            return
        if result.visited >= max_states or perf_counter() - started >= time_limit_s:
            result.stop_reason = "limit stanow" if result.visited >= max_states else "limit czasu"
            return
        result.visited += 1
        lower = search_bounds(mask, available, score, waste)
        record(path, available, score, waste, lower, "visited")
        if lower > best_key[:3]:
            result.pruned += 1
            record(path, available, score, waste, lower, "pruned")
            return
        if mask == 0:
            key = (
                *search_key(score, waste, available[-1]),
                tuple(jobs[i].job_id for i in path),
            )
            if key < best_key:
                best_order, best_key = path, key
                best_from_search = True
                result.improvements += 1
                record(path, available, score, waste, lower, "improved")
            return
        state_key = (mask, path[-1] if path and stateful_setups else -1)
        states = frontier.setdefault(state_key, [])
        if any(
            cost <= score
            and saved_waste <= waste
            and all(a <= b for a, b in zip(ends, available, strict=True))
            for ends, cost, saved_waste in states
        ):
            result.pruned += 1
            record(path, available, score, waste, lower, "dominated")
            return
        states[:] = [
            (ends, cost, saved_waste)
            for ends, cost, saved_waste in states
            if not (
                score <= cost
                and waste <= saved_waste
                and all(a <= b for a, b in zip(available, ends, strict=True))
            )
        ]
        states.append((available, score, waste))
        candidates = []
        for i in range(len(jobs)):
            if mask & (1 << i):
                previous = jobs[path[-1]] if path else None
                ends, _setups = advance_flowshop(available, jobs[i], previous)
                new_waste = _add_waste(waste, jobs[i], previous)
                new_score = score + charge(i, ends[-1])
                new_mask = mask ^ (1 << i)
                candidates.append(
                    (
                        search_bounds(new_mask, ends, new_score, new_waste),
                        jobs[i].deadline,
                        jobs[i].job_id,
                        i,
                        ends,
                        new_score,
                        new_mask,
                        new_waste,
                    )
                )
        for _lower, _due, _id, i, ends, new_score, new_mask, new_waste in sorted(candidates):
            visit((*path, i), new_mask, ends, new_score, new_waste)
            if result.stop_reason:
                break

    visit((), full_mask, (0.0,) * n_machines, 0.0, 0.0)
    result.confirmed = not result.stop_reason
    # Preserve the incumbent's complete path even when trace storage is full.
    # A seeded path may not have been visited: label it explicitly as incumbent.
    ends = (0.0,) * n_machines
    score = 0.0
    waste = 0.0
    mask = full_mask
    for depth in range(len(best_order) + 1):
        path = best_order[:depth]
        original = result.trace.get(path)
        result.trace[path] = {
            "available": ends,
            "sto": sequence_sto(path) if objective == "cost" else score,
            "objective_value": waste if objective == "waste" else score,
            "bound": search_bounds(mask, ends, score, waste)[0],
            "status": "best",
            "origin": "search" if original or best_from_search else "incumbent",
        }
        if depth < len(best_order):
            i = best_order[depth]
            previous = jobs[best_order[depth - 1]] if depth else None
            ends, _setups = advance_flowshop(ends, jobs[i], previous)
            score += charge(i, ends[-1])
            waste = _add_waste(waste, jobs[i], previous)
            mask ^= 1 << i
    result.evaluation = evaluate_flowshop(
        [jobs[i] for i in best_order] + blocked_jobs, n_machines=n_machines, objective=objective
    )
    result.elapsed_s = perf_counter() - started
    if result.confirmed:
        result.lower_bound = objective_value(result.evaluation)
    result.evaluation.update(
        {
            "optimality_status": "OPTIMAL_CONFIRMED" if result.confirmed else "BEST_KNOWN",
            "search_status": "optimum potwierdzone"
            if result.confirmed
            else "optimum niepotwierdzone",
            "search_stop_reason": result.stop_reason,
            "search_states": result.visited,
            "search_pruned": result.pruned,
            "search_improvements": result.improvements,
            "elapsed_s": result.elapsed_s,
            "lower_bound": result.lower_bound,
            "initial_sto": initial_sto,
            "seed_sto": seed_sto,
            "initial_objective": initial_objective,
            "seed_objective": seed_objective,
        }
    )
    if blocked_jobs:
        result.evaluation["optimality_status"] = "PARTIAL_PLAN"
        result.evaluation["search_status"] = (
            "optimum dopuszczonych zlecen; plan niepelny"
            if result.confirmed
            else "plan niepelny; optimum niepotwierdzone"
        )
    return result
