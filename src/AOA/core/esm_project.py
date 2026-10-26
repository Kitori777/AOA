from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, replace
from functools import cache
from math import isfinite
from pathlib import Path
from time import perf_counter

import pandas as pd

from AOA.core.engineering_methods import (
    evaluate_robust_flowshop,
    sequence_component_ready_flowshop,
    sequence_eco_flowshop,
)
from AOA.core.esm_costs import objective_value, validate_objective
from AOA.core.flowshop import (
    FLOW_METHODS,
    FlowShopJob,
    FlowShopResult,
    evaluate_flowshop,
    flowshop_key,
    flowshop_order,
    solve_flowshop,
    validate_flowshop,
)
from AOA.core.optimization.models import Job

COST_COLUMNS = ("koszt_opoznienia_na_min", "dopuszczalne_opoznienie_min")


def esm_csv_has_costs(content: bytes) -> bool:
    header = next(csv.reader(io.StringIO(content.decode("utf-8-sig"))), [])
    return any(column in header for column in COST_COLUMNS)


ESM_METHODS: tuple[str, ...] = (
    "MT",
    "MO",
    "MZO",
    "MOPT",
    "ECO_WASTE",
    "COMPONENT_READY_EDD",
    "ROBUST_MC",
)
ESM_COLUMNS: tuple[str, ...] = ("zlecenie", "czas_obrobki_min", "termin_min")
ESM_OPTIONAL_COLUMNS: tuple[str, ...] = (
    "material",
    "ksztalt",
    "odpad_kg",
    "czas_przezbrojenia_min",
    "odpad_przezbrojenia_kg",
    "dozwolone_maszyny",
    "components_ready_min",
    "stock_status",
)
ESM_MAX_JOBS = 10
ESM_MAX_MACHINES = 8
ESM_DEFAULT_SCENARIO = "esm_jobs.csv"
ESM_COMPARISON_METHODS = ("MT", "MO", "MZO", "MOPT")
ESM_TIME_MODES = {
    "total": "Laczny czas podzielony na maszyny",
    "per_machine": "Pelny czas na kazdej maszynie",
    "file": "Oryginalne czasy etapow z pliku",
}

ESM_SCENARIO_LABELS: dict[str, str] = {
    "esm_jobs.csv": "START: esm_jobs.csv - jeden czas zlecenia",
    **{
        f"esm_paper_0{i}.csv": f"MPER 2017 | przykład {i} | 2 maszyny | minimum STO {sto} min"
        for i, sto in enumerate((9, 6, 1, 0), 1)
    },
    **{
        f"ART3_Przyklad_{problem}_W{variant}_koszt_{minimum}{'_zamiast_330' if (problem, variant) == (2, 2) else ''}.csv": (
            "ART3 | 300 zamiast 330 | przykład 2, W2 | tabela 4 | 1 maszyna"
            if (problem, variant) == (2, 2)
            else f"ART3 | przykład {problem}, W{variant} | 1 maszyna | minimum {minimum} j.p."
        )
        for problem, variant, minimum in (
            (1, 1, 80),
            (1, 2, 60),
            (1, 3, 50),
            (1, 4, 30),
            (1, 5, 110),
            (2, 1, 160),
            (2, 2, 300),
        )
    },
    **{
        f"DYLEWSKI_Przyklad_{problem}_W{variant}_koszt_{minimum}.csv": f"DYLEWSKI | przykład {problem}, W{variant} | 2 maszyny | minimum {minimum} j.p."
        for problem, minima in ((1, (9, 9, 16)), (2, (11, 16)), (3, (154, 183, 219, 248)))
        for variant, minimum in enumerate(minima, 1)
    },
}


@dataclass(frozen=True)
class EsmTreeNode:
    node_id: str
    parent_id: str
    edge_label: str
    label: str
    details: str
    depth: int
    chosen: bool
    leaf: bool = False
    status: str = "odrzucony"
    score: float = 0.0


@dataclass(frozen=True)
class EsmScenario:
    label: str
    path: Path
    job_count: int
    machine_count: int = 1


def load_esm_jobs(path: str | Path) -> list[Job]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku ESM: {source}")
    try:
        frame = pd.read_csv(source, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Nie mozna odczytac pliku ESM: {exc}") from exc
    return dataframe_to_esm_jobs(frame)


def list_esm_scenarios(directory: str | Path) -> list[EsmScenario]:
    root = Path(directory)
    if not root.is_dir():
        return []
    scenarios: list[EsmScenario] = []
    for path in sorted(root.rglob("*.csv")):
        try:
            jobs = load_esm_jobs(path)
            job_count = len(jobs)
        except (OSError, ValueError):
            continue
        scenarios.append(
            EsmScenario(
                label=ESM_SCENARIO_LABELS.get(
                    path.name,
                    ("KOSZTY: " if path.parent.name == "costs" else "")
                    + f"{path.stem} ({job_count} zlecen)",
                ),
                path=path,
                job_count=job_count,
                machine_count=len(jobs[0].machine_times) or 1,
            )
        )
    return sorted(
        scenarios,
        key=lambda item: (
            item.path.name != ESM_DEFAULT_SCENARIO,
            item.path.name != "ART3_Przyklad_2_W2_koszt_300_zamiast_330.csv",
            not item.label.startswith("ART3 |"),
            item.job_count,
            item.label,
        ),
    )


def dataframe_to_esm_jobs(frame: pd.DataFrame) -> list[Job]:
    if frame is None or frame.empty:
        raise ValueError("Plik ESM nie zawiera zlecen.")
    stage_columns = [
        f"czas_m{i}_min"
        for i in range(1, ESM_MAX_MACHINES + 1)
        if f"czas_m{i}_min" in frame.columns
    ]
    all_stage_columns = [str(c) for c in frame.columns if str(c).startswith("czas_m")]
    if all_stage_columns and stage_columns != [
        f"czas_m{i}_min" for i in range(1, len(all_stage_columns) + 1)
    ]:
        raise ValueError(
            "Kolumny przeplywu musza stanowic ciag czas_m1_min ... czas_m8_min bez luk."
        )
    required = ("zlecenie", "termin_min") if stage_columns else ESM_COLUMNS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Brak wymaganych kolumn ESM: " + ", ".join(missing))
    if len(frame) > ESM_MAX_JOBS:
        raise ValueError(f"Tryb pracy inzynierskiej obsluguje maksymalnie {ESM_MAX_JOBS} zlecen.")
    setup_columns = [
        str(c) for c in frame.columns if re.fullmatch(r"czas_przezbrojenia_m\d+_min", str(c))
    ]
    allowed_setups = {f"czas_przezbrojenia_m{i}_min" for i in range(1, len(stage_columns) + 1)}
    if set(setup_columns) - allowed_setups:
        raise ValueError(
            "Przezbrojenia etapow wymagaja odpowiadajacych im czasow operacji M1...Mm."
        )

    jobs: list[Job] = []
    seen: set[str] = set()
    for index, row in frame.reset_index(drop=True).iterrows():
        row_number = index + 2
        job_id = str(row["zlecenie"]).strip()
        if not job_id:
            raise ValueError(f"Wiersz {row_number}: brak identyfikatora zlecenia.")
        if job_id in seen:
            raise ValueError(f"Wiersz {row_number}: powtorzone zlecenie {job_id}.")
        seen.add(job_id)
        machine_times = tuple(_positive_number(row[c], row_number, c) for c in stage_columns)
        processing_time = (
            sum(machine_times)
            if machine_times
            else _positive_number(row["czas_obrobki_min"], row_number, "czas_obrobki_min")
        )
        deadline = _positive_number(row["termin_min"], row_number, "termin_min")
        has_costs = any(
            column in frame.columns
            for column in ("koszt_opoznienia_na_min", "dopuszczalne_opoznienie_min")
        )
        job_type = FlowShopJob if machine_times or has_costs else Job
        jobs.append(
            job_type(
                job_id=job_id,
                processing_time=processing_time,
                deadline=deadline,
                material=str(row.get("material", "")).strip(),
                shape=str(row.get("ksztalt", "")).strip(),
                waste_kg=_optional_nonnegative_number(row, "odpad_kg", row_number),
                setup_time=_optional_nonnegative_number(row, "czas_przezbrojenia_min", row_number),
                changeover_waste_kg=_optional_nonnegative_number(
                    row, "odpad_przezbrojenia_kg", row_number
                ),
                eligible_machines=_eligible_machines(row, row_number),
                components_ready_h=_optional_nonnegative_number(
                    row, "components_ready_min", row_number
                ),
                material_wait_h=_optional_nonnegative_number(
                    row, "components_ready_min", row_number
                ),
                stock_status=str(row.get("stock_status", "READY")).strip().upper() or "READY",
                machine_times=machine_times,
            )
        )
        if has_costs:
            assert isinstance(jobs[-1], FlowShopJob)
            jobs[-1] = replace(
                jobs[-1],
                tardiness_cost_per_min=_optional_nonnegative_number(
                    row, "koszt_opoznienia_na_min", row_number, default=1.0
                ),
                allowed_tardiness_min=_optional_nonnegative_number(
                    row, "dopuszczalne_opoznienie_min", row_number
                ),
            )
        if machine_times and setup_columns:
            flow_job = jobs[-1]
            assert isinstance(flow_job, FlowShopJob)
            jobs[-1] = replace(
                flow_job,
                machine_setup_times=tuple(
                    _optional_nonnegative_number(row, f"czas_przezbrojenia_m{i}_min", row_number)
                    for i in range(1, len(stage_columns) + 1)
                ),
            )
    if stage_columns:
        validate_flowshop(jobs, len(stage_columns))
    return jobs


def evaluate_esm_methods(
    jobs: list[Job],
    selected_methods: list[str],
    *,
    n_machines: int = 1,
    time_limit_s: float = 10.0,
    max_states: int = 100_000,
    time_mode: str | None = None,
    objective: str = "sto",
) -> list[dict]:
    if not jobs:
        raise ValueError("Brak zlecen do obliczen.")
    unknown = [method for method in selected_methods if method not in ESM_METHODS]
    if unknown:
        raise ValueError("Tryb pracy inzynierskiej nie udostepnia metod: " + ", ".join(unknown))
    if not 1 <= n_machines <= ESM_MAX_MACHINES:
        raise ValueError(f"Tryb pracy inzynierskiej obsluguje od 1 do {ESM_MAX_MACHINES} maszyn.")
    prepared = prepare_esm_flow_jobs(jobs, n_machines=n_machines, time_mode=time_mode)
    results = evaluate_flowshop_methods(
        prepared,
        selected_methods,
        n_machines=n_machines,
        time_limit_s=time_limit_s,
        max_states=max_states,
        objective=objective,
    )
    effective = esm_time_mode(jobs, n_machines, time_mode)
    for result in results:
        result["time_mode"] = effective
        if "flowshop_solution" in result:
            result["flowshop_solution"].evaluation["time_mode"] = effective
    return results


def esm_time_mode(jobs: list[Job], n_machines: int, time_mode: str | None = None) -> str:
    """Keep explicit operation data when possible; scalar data always uses flow."""
    if time_mode is not None:
        if time_mode not in ESM_TIME_MODES:
            raise ValueError("Nieznany sposob interpretacji czasu ESM.")
        return time_mode
    return "file" if jobs and all(len(j.machine_times) >= n_machines for j in jobs) else "total"


def prepare_esm_flow_jobs(
    jobs: list[Job], *, n_machines: int, time_mode: str | None = None
) -> list[Job]:
    """Build immutable runtime operations; never write or modify the source CSV.

    total: processing_time is line-wide work, distributed evenly over m stages.
    per_machine: processing_time is repeated at every stage (a separate model).
    file: preserve supplied stage times, including their per-stage setups.
    Scalar setup is line-wide in total mode and per-stage in per_machine mode.
    Explicit setup vectors are summed before redistribution, like processing.
    """
    if isinstance(n_machines, bool) or not isinstance(n_machines, int) or not 1 <= n_machines <= 8:
        raise ValueError("Przeplyw obsluguje od 1 do 8 maszyn.")
    if not jobs:
        raise ValueError("Brak zlecen do obliczen.")
    mode = esm_time_mode(jobs, n_machines, time_mode)
    prepared = []
    for job in jobs:
        if mode == "file":
            if len(job.machine_times) < n_machines:
                raise ValueError("Brak czasow etapow: wybierz podzial lacznego czasu w programie.")
            updated = replace(
                job,
                machine_times=job.machine_times[:n_machines],
                processing_time=sum(job.machine_times[:n_machines]),
            )
            if isinstance(updated, FlowShopJob):
                updated = replace(
                    updated, machine_setup_times=updated.machine_setup_times[:n_machines]
                )
            prepared.append(updated)
        else:
            duration = job.processing_time / n_machines if mode == "total" else job.processing_time
            setup_vector = getattr(job, "machine_setup_times", ())
            setup = sum(setup_vector) if setup_vector else job.setup_time
            setup = setup / n_machines if mode == "total" else setup
            updated = replace(
                job,
                machine_times=(duration,) * n_machines,
                processing_time=duration * n_machines,
                setup_time=setup,
            )
            if isinstance(updated, FlowShopJob):
                updated = replace(updated, machine_setup_times=())
            prepared.append(updated)
    validate_flowshop(prepared, n_machines)
    return prepared


def evaluate_flowshop_methods(
    jobs: list[Job],
    selected_methods: list[str],
    *,
    n_machines: int,
    time_limit_s: float = 10.0,
    max_states: int = 100_000,
    objective: str = "sto",
) -> list[dict]:
    validate_flowshop(jobs, n_machines)
    validate_objective(objective)
    if not selected_methods:
        raise ValueError("Wybierz przynajmniej jedna metode.")
    if unsupported := [m for m in selected_methods if m not in FLOW_METHODS]:
        raise ValueError("Nieznane metody przeplywu: " + ", ".join(unsupported))
    results = []
    solved = None
    for method in dict.fromkeys(selected_methods):
        started = perf_counter()
        if method == "MOPT":
            solved = solve_flowshop(
                jobs,
                n_machines=n_machines,
                time_limit_s=time_limit_s,
                max_states=max_states,
                objective=objective,
            )
            evaluation = dict(solved.evaluation)
            evaluation["flowshop_solution"] = solved
        elif method == "ROBUST_MC":
            evaluation = evaluate_robust_flowshop(jobs, n_machines=n_machines, objective=objective)
        else:
            if method == "ECO_WASTE":
                order = sequence_eco_flowshop(jobs, n_machines=n_machines, objective=objective)
            elif method == "COMPONENT_READY_EDD":
                order = sequence_component_ready_flowshop(
                    jobs, n_machines=n_machines, objective=objective
                )
            else:
                order = flowshop_order(jobs, method, n_machines)
            evaluation = evaluate_flowshop(order, n_machines=n_machines, objective=objective)
        results.append({**evaluation, "method": method, "elapsed_s": perf_counter() - started})
    results.sort(key=lambda r: (*flowshop_key(r), r["method"]))
    reference = solved.evaluation if solved else results[0]
    for result in results:
        equal = flowshop_key(result) == flowshop_key(reference)
        result["optimality_status"] = (
            "OPTIMAL_CONFIRMED"
            if solved and solved.confirmed and equal
            else "GAP_TO_OPTIMUM"
            if solved and solved.confirmed
            else "BEST_KNOWN"
            if equal
            else "CANDIDATE"
        )
        if result["unscheduled_count"]:
            result["optimality_status"] = "PARTIAL_PLAN"
        elif result["method"] == "ROBUST_MC":
            result["optimality_status"] = "RISK_ASSESSED"
        result["sto_gap_min"] = max(0.0, result["sto"] - reference["sto"])
        result["cost_gap"] = max(
            0.0, result["total_tardiness_cost"] - reference["total_tardiness_cost"]
        )
        result["waste_gap_kg"] = max(0.0, result["total_waste_kg"] - reference["total_waste_kg"])
    return results


def esm_method_warnings(jobs: list[Job], selected_methods: list[str]) -> list[str]:
    if any(job.machine_times for job in jobs):
        warnings = [
            "Przeplyw: MO/MZO szereguja wedlug sumy czasow na wybranych maszynach. "
            "Opoznienie jest liczone po ostatniej operacji. Gotowosc komponentow i dodatkowe "
            "przezbrojenia obowiazuja wszystkie porownywane metody."
        ]
        if "ECO_WASTE" in selected_methods and not any(
            j.material or j.shape or j.changeover_waste_kg for j in jobs
        ):
            warnings.append(
                "ECO Waste: brak materialow lub zmian ksztaltu; odpad nie zalezy od kolejnosci."
            )
        if "COMPONENT_READY_EDD" in selected_methods and not any(
            j.components_ready_h or j.stock_status != "READY" for j in jobs
        ):
            warnings.append("Component Ready + EDD: wszystkie komponenty gotowe od 0 min.")
        if "ROBUST_MC" in selected_methods:
            warnings.append(
                "Robust Monte Carlo: wybor 1000 symulacji (42), weryfikacja 1000 (43); "
                "syntetyczne profile MTBF=80 h, "
                "MTTR=2 h. Czasy sa przeliczane min -> h -> min. Ranking pokazuje wyniki nominalne."
            )
        return warnings
    warnings = []
    if "ECO_WASTE" in selected_methods and not any(
        job.material
        or job.shape
        or job.waste_kg > 0
        or job.setup_time > 0
        or job.changeover_waste_kg > 0
        for job in jobs
    ):
        warnings.append(
            "ECO Waste: brak danych materialowych i przezbrojen; metoda uzywa wartosci neutralnych."
        )
    if "COMPONENT_READY_EDD" in selected_methods and not any(
        job.components_ready_h > 0 or job.stock_status != "READY" for job in jobs
    ):
        warnings.append(
            "Component Ready + EDD: brak czasow gotowosci; wszystkie zlecenia sa gotowe od 0 min."
        )
    if "ROBUST_MC" in selected_methods:
        warnings.append(
            "Robust Monte Carlo: symulacja korzysta z syntetycznych profili niezawodnosci maszyn "
            "(MTBF=80 h, MTTR=2 h), z poprawna konwersja minut."
        )
    return warnings


def build_esm_gantt_rows(result: dict) -> list[dict[str, float | str]]:
    return [
        {
            "job_id": str(step["job_id"]),
            "machine": f"M{int(step.get('machine_id', 1))}",
            "start": float(step["start_time"]),
            "end": float(step["completion_time"]),
            "duration": float(step["processing_time"]),
            "deadline": float(step["deadline"]),
            "allowed_tardiness_min": float(step.get("allowed_tardiness_min", 0.0)),
            "tardiness_cost": float(step.get("tardiness_cost", 0.0)),
            "tardiness": float(step["tardiness_positive"]),
            "setup": float(step.get("setup_time", 0.0)),
            "final_operation": bool(step.get("final_operation", True)),
        }
        for step in result.get("steps", [])
        if step.get("scheduled", True)
    ]


def build_mopt_solution_tree(
    jobs: list[Job],
    *,
    max_nodes: int = 80,
    n_machines: int = 1,
    solution: FlowShopResult | None = None,
    objective: str | None = None,
) -> list[EsmTreeNode]:
    """Build an exact, educational backward-branching MOpt solution tree.

    A branch fixes the selected job at the end of the still-unscheduled block.
    Therefore the green root-to-leaf decisions are the reverse of the final
    production order.  Besides the optimum, one deterministic runner-up path
    is expanded so the diagram can explain both a checked and a pruned route.
    """

    criterion = objective or (solution.evaluation.get("objective", "sto") if solution else "sto")
    validate_objective(criterion)
    if solution is not None and tuple(jobs) != solution.source_jobs:
        jobs = prepare_esm_flow_jobs(
            jobs, n_machines=n_machines, time_mode=solution.evaluation.get("time_mode")
        )
    elif (n_machines > 1 or criterion != "sto") and not any(job.machine_times for job in jobs):
        jobs = prepare_esm_flow_jobs(jobs, n_machines=n_machines)
    if any(job.machine_times for job in jobs):
        solved = solution or solve_flowshop(jobs, n_machines=n_machines, objective=criterion)
        if (
            solved.evaluation["machine_count"] != n_machines
            or solved.source_jobs != tuple(jobs)
            or solved.evaluation.get("objective", "sto") != criterion
        ):
            raise ValueError("Drzewo i wynik musza dotyczyc tych samych danych i liczby maszyn.")
        return _flowshop_tree(jobs, solved, max_nodes=max_nodes)
    if not jobs:
        raise ValueError("Brak zlecen do drzewa MOpt.")
    if len(jobs) > ESM_MAX_JOBS:
        raise ValueError(f"Drzewo MOpt obsluguje maksymalnie {ESM_MAX_JOBS} zlecen.")
    if max_nodes < len(jobs) + 1:
        raise ValueError("Limit wezlow drzewa musi pomiescic korzen i pierwszy poziom.")

    count = len(jobs)
    full_mask = (1 << count) - 1
    remaining_processing: dict[int, float] = {0: 0.0}

    def remaining_sum(mask: int) -> float:
        if mask not in remaining_processing:
            remaining_processing[mask] = sum(
                job.processing_time for index, job in enumerate(jobs) if mask & (1 << index)
            )
        return remaining_processing[mask]

    choices: dict[int, int] = {}

    @cache
    def optimum(mask: int) -> float:
        if mask == 0:
            return 0.0
        completion = remaining_sum(mask)
        candidates: list[tuple[float, str, int]] = []
        for index, job in enumerate(jobs):
            bit = 1 << index
            if not mask & bit:
                continue
            immediate = max(0.0, completion - job.deadline)
            candidates.append((immediate + optimum(mask ^ bit), job.job_id, index))
        score, _job_id, selected_index = min(candidates)
        choices[mask] = selected_index
        return score

    optimum_score = optimum(full_mask)
    total_processing = remaining_sum(full_mask)

    def penalties(mask: int, completion: float) -> str:
        values = [
            f"{job.job_id}={max(0.0, completion - job.deadline):g}"
            for index, job in enumerate(jobs)
            if mask & (1 << index)
        ]
        return "p: " + ", ".join(values) if values else "p: -"

    nodes = [
        EsmTreeNode(
            node_id="B1",
            parent_id="",
            edge_label="",
            label="B1 | Start",
            details=(
                f"S0={total_processing:g} | Kop=0\n"
                f"{penalties(full_mask, total_processing)}\n"
                f"optimum STO={optimum_score:g}"
            ),
            depth=0,
            chosen=True,
            status="best",
            score=0.0,
        )
    ]
    next_id = 2
    truncated = False

    def candidate_rows(mask: int, kop: float) -> list[tuple[int, float, float, int]]:
        completion = remaining_sum(mask)
        rows: list[tuple[int, float, float, int]] = []
        for index, job in enumerate(jobs):
            bit = 1 << index
            if not mask & bit:
                continue
            immediate = max(0.0, completion - job.deadline)
            next_mask = mask ^ bit
            exact_total = kop + immediate + optimum(next_mask)
            rows.append((index, immediate, exact_total, next_mask))
        return rows

    def create_level(
        parent_id: str,
        mask: int,
        kop: float,
        depth: int,
        path_backward: tuple[str, ...],
        statuses: dict[int, str],
    ) -> dict[int, tuple[str, int, float, tuple[str, ...]]]:
        nonlocal next_id, truncated
        created: dict[int, tuple[str, int, float, tuple[str, ...]]] = {}
        completion = remaining_sum(mask)
        for index, immediate, exact_total, next_mask in candidate_rows(mask, kop):
            if len(nodes) >= max_nodes:
                truncated = True
                break
            job = jobs[index]
            status = statuses.get(index, "odrzucony")
            next_kop = kop + immediate
            next_completion = remaining_sum(next_mask)
            next_path = path_backward + (job.job_id,)
            sequence = tuple(reversed(next_path))
            detail_lines = [
                f"S'={completion:g}-{job.processing_time:g}={next_completion:g} | "
                f"Kop={kop:g}+{immediate:g}={next_kop:g}",
                penalties(next_mask, next_completion),
                f"najlepsze mozliwe STO={exact_total:g}",
            ]
            if next_mask == 0:
                detail_lines[-1] = f"kolejnosc: {' -> '.join(sequence)} | STO={next_kop:g}"
            node_id = f"B{next_id}"
            next_id += 1
            nodes.append(
                EsmTreeNode(
                    node_id=node_id,
                    parent_id=parent_id,
                    edge_label=job.job_id,
                    label=f"{node_id} | {job.job_id}",
                    details="\n".join(detail_lines),
                    depth=depth,
                    chosen=status == "best",
                    leaf=next_mask == 0 or status == "odrzucony",
                    status=status,
                    score=next_kop,
                )
            )
            created[index] = (node_id, next_mask, next_kop, next_path)
        return created

    root_candidates = candidate_rows(full_mask, 0.0)
    best_index = choices[full_mask]
    ranked_root = sorted(root_candidates, key=lambda item: (item[2], jobs[item[0]].job_id))
    runner_index = next((item[0] for item in ranked_root if item[0] != best_index), None)
    root_statuses = {best_index: "best"}
    if runner_index is not None:
        root_statuses[runner_index] = "pokonany"
    root_children = create_level("B1", full_mask, 0.0, 1, (), root_statuses)

    def expand_path(
        state: tuple[str, int, float, tuple[str, ...]] | None,
        status: str,
        depth: int,
    ) -> None:
        while state is not None:
            parent_id, mask, kop, path_backward = state
            if mask == 0:
                return
            selected_index = choices[mask]
            created = create_level(
                parent_id,
                mask,
                kop,
                depth,
                path_backward,
                {selected_index: status},
            )
            state = created.get(selected_index)
            depth += 1

    # Reserve the node budget for the complete optimum path before expanding
    # the explanatory runner-up path.
    expand_path(root_children.get(best_index), "best", 2)
    if runner_index is not None:
        expand_path(root_children.get(runner_index), "pokonany", 2)

    if truncated:
        nodes[0] = replace(
            nodes[0],
            details=nodes[0].details + f"\nWidok ograniczony do {max_nodes} wezlow.",
        )
    return nodes


def _flowshop_tree(jobs: list[Job], solved: FlowShopResult, *, max_nodes: int) -> list[EsmTreeNode]:
    metric = {"sto": "STO [min]", "cost": "Koszt [j.p.]", "waste": "Odpad [kg]"}[
        solved.evaluation.get("objective", "sto")
    ]
    scheduled_count = len(solved.evaluation["scheduled_order"])
    if max_nodes < scheduled_count + 1:
        raise ValueError("Limit wezlow musi pomiescic pelna najlepsza sciezke.")
    trace = solved.trace
    selected = {path for path, state in trace.items() if state["status"] == "best"}
    # Select real alternative branches with their ancestors. Sampling is only
    # presentation; no omitted branch is reclassified as mathematically pruned.
    priorities = {"improved": 0, "visited": 1, "pruned": 2, "dominated": 3}

    def include(path: tuple[int, ...]) -> None:
        ancestors = {path[:d] for d in range(len(path) + 1)}
        if len(selected | ancestors) <= max_nodes and ancestors <= trace.keys():
            selected.update(ancestors)

    # Reserve actual cutoffs before a long yellow branch fills the display.
    for status in ("improved", "pruned", "dominated", "visited"):
        group = [p for p in trace if trace[p]["status"] == status and p not in selected]
        group.sort(
            key=lambda p: (sum(p[:d] not in selected for d in range(len(p) + 1)), -len(p), p)
        )
        for path in group[:2]:
            include(path)
    candidates = sorted(trace, key=lambda p: (priorities.get(trace[p]["status"], 4), -len(p), p))
    for path in candidates:
        include(path)
    ordered = sorted(selected)
    ids = {path: f"B{i + 1}" for i, path in enumerate(ordered)}
    nodes = []
    for path in ordered:
        state = trace[path]
        chosen = state["status"] == "best"
        status = (
            "best"
            if chosen
            else "odrzucony"
            if state["status"] in {"pruned", "dominated"}
            else "pokonany"
        )
        availability = ", ".join(f"M{i + 1}={t:g}" for i, t in enumerate(state["available"]))
        if not path:
            details = (
                f"{solved.evaluation['machine_count']} maszyn | {solved.evaluation['search_status']}\n"
                f"{metric}={objective_value(solved.evaluation):g}; LB={solved.lower_bound:g}\n"
                f"STO={solved.evaluation['sto']:g} min\n"
                f"Stany={solved.visited}; odciete={solved.pruned}\n"
                f"Widok {len(ordered)} wezlow; zapis sladu {len(trace)}"
            )
        else:
            reason = {
                "pruned": "odciecie: dolna granica",
                "dominated": "odciecie: dominacja",
                "visited": "sprawdzono",
                "improved": "poprawiono wynik",
                "best": "najlepsza sciezka",
            }[state["status"]]
            if state.get("origin") == "incumbent":
                reason += " (rozwiazanie poczatkowe)"
            details = f"{metric} prefiksu={state.get('objective_value', state['sto']):g}; LB={state['bound']:g}\n{availability}\n{reason}"
            if len(path) == scheduled_count:
                details += "\nkolejnosc: " + " -> ".join(jobs[i].job_id for i in path)
        nodes.append(
            EsmTreeNode(
                node_id=ids[path],
                parent_id=ids[path[:-1]] if path else "",
                edge_label=jobs[path[-1]].job_id if path else "",
                label=f"{ids[path]} | {jobs[path[-1]].job_id}" if path else "B1 | Przeplyw MOpt",
                details=details,
                depth=len(path),
                chosen=chosen,
                leaf=len(path) == scheduled_count or status == "odrzucony",
                status=status,
                score=state.get("objective_value", state["sto"]),
            )
        )
    return nodes


def _positive_number(value: object, row_number: int, column: str) -> float:
    try:
        number = float(str(value).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"Wiersz {row_number}: {column} nie jest liczba.") from None
    if not isfinite(number) or number <= 0:
        raise ValueError(f"Wiersz {row_number}: {column} musi byc dodatnie.")
    return number


def _optional_nonnegative_number(
    row: pd.Series, column: str, row_number: int, *, default: float = 0.0
) -> float:
    value = row.get(column, "")
    if column in COST_COLUMNS and pd.isna(value):
        raise ValueError(f"Wiersz {row_number}: {column} musi być skończone i nieujemne.")
    if pd.isna(value) or not str(value).strip():
        return default
    try:
        number = float(str(value).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"Wiersz {row_number}: {column} nie jest liczba.") from None
    if not isfinite(number) or number < 0:
        raise ValueError(f"Wiersz {row_number}: {column} nie moze byc ujemne.")
    return number


def _eligible_machines(row: pd.Series, row_number: int) -> tuple[int, ...]:
    value = row.get("dozwolone_maszyny", "")
    if pd.isna(value) or not str(value).strip():
        return ()
    parts = str(value).replace(",", "|").split("|")
    machines: list[int] = []
    for part in parts:
        try:
            machine = int(part.strip())
        except ValueError:
            raise ValueError(
                f"Wiersz {row_number}: dozwolone_maszyny musi zawierac numery 1-{ESM_MAX_MACHINES}."
            ) from None
        if not 1 <= machine <= ESM_MAX_MACHINES:
            raise ValueError(
                f"Wiersz {row_number}: numer maszyny musi byc w zakresie 1-{ESM_MAX_MACHINES}."
            )
        machines.append(machine)
    return tuple(dict.fromkeys(machines))
