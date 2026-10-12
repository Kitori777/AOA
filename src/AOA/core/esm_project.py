from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

import pandas as pd

from AOA.core.optimization.models import Job
from AOA.core.optimization.runner import run_selected_sto_models

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
ESM_MAX_MACHINES = 3

ESM_SCENARIO_LABELS: dict[str, str] = {
    "esm_jobs.csv": "ESM Z1-Z4 (dane z PDF)",
    "esm_jobs_05_tight_deadlines.csv": "Z1-Z5 - ciasne terminy",
    "esm_jobs_06_component_wait.csv": "Z1-Z6 - oczekiwanie na komponenty",
    "esm_jobs_07_parallel_balance.csv": "Z1-Z7 - balans maszyn",
    "esm_jobs_08_changeovers.csv": "Z1-Z8 - materialy i przezbrojenia",
    "esm_jobs_09_urgent_mix.csv": "Z1-Z9 - pilne i dlugie zlecenia",
    "esm_jobs_10_mixed_constraints.csv": "Z1-Z10 - mieszane ograniczenia",
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
            job_count = len(load_esm_jobs(path))
        except (OSError, ValueError):
            continue
        scenarios.append(
            EsmScenario(
                label=ESM_SCENARIO_LABELS.get(path.name, f"{path.stem} ({job_count} zlecen)"),
                path=path,
                job_count=job_count,
            )
        )
    return sorted(scenarios, key=lambda item: (item.job_count, item.label))


def dataframe_to_esm_jobs(frame: pd.DataFrame) -> list[Job]:
    if frame is None or frame.empty:
        raise ValueError("Plik ESM nie zawiera zlecen.")
    missing = [column for column in ESM_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError("Brak wymaganych kolumn ESM: " + ", ".join(missing))
    if len(frame) > ESM_MAX_JOBS:
        raise ValueError(f"Tryb pracy inzynierskiej obsluguje maksymalnie {ESM_MAX_JOBS} zlecen.")

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
        processing_time = _positive_number(row["czas_obrobki_min"], row_number, "czas_obrobki_min")
        deadline = _positive_number(row["termin_min"], row_number, "termin_min")
        jobs.append(
            Job(
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
            )
        )
    return jobs


def evaluate_esm_methods(
    jobs: list[Job], selected_methods: list[str], *, n_machines: int = 1
) -> list[dict]:
    if not jobs:
        raise ValueError("Brak zlecen do obliczen.")
    unknown = [method for method in selected_methods if method not in ESM_METHODS]
    if unknown:
        raise ValueError("Tryb pracy inzynierskiej nie udostepnia metod: " + ", ".join(unknown))
    if not 1 <= n_machines <= ESM_MAX_MACHINES:
        raise ValueError(f"Tryb pracy inzynierskiej obsluguje od 1 do {ESM_MAX_MACHINES} maszyn.")
    return run_selected_sto_models(
        jobs,
        selected_methods,
        n_machines=n_machines,
        objective="deadline_then_waste",
    )


def esm_method_warnings(jobs: list[Job], selected_methods: list[str]) -> list[str]:
    warnings: list[str] = []
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
            "Robust Monte Carlo: symulacja korzysta z konserwatywnych profili niezawodnosci maszyn."
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
            "tardiness": float(step["tardiness_positive"]),
            "setup": float(step.get("setup_time", 0.0)),
        }
        for step in result.get("steps", [])
        if step.get("scheduled", True)
    ]


def build_mopt_solution_tree(jobs: list[Job], *, max_nodes: int = 80) -> list[EsmTreeNode]:
    """Build an exact, educational backward-branching MOpt solution tree.

    A branch fixes the selected job at the end of the still-unscheduled block.
    Therefore the green root-to-leaf decisions are the reverse of the final
    production order.  Besides the optimum, one deterministic runner-up path
    is expanded so the diagram can explain both a checked and a pruned route.
    """

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


def _positive_number(value: object, row_number: int, column: str) -> float:
    try:
        number = float(str(value).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"Wiersz {row_number}: {column} nie jest liczba.") from None
    if number <= 0:
        raise ValueError(f"Wiersz {row_number}: {column} musi byc dodatnie.")
    return number


def _optional_nonnegative_number(row: pd.Series, column: str, row_number: int) -> float:
    value = row.get(column, "")
    if pd.isna(value) or not str(value).strip():
        return 0.0
    try:
        number = float(str(value).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"Wiersz {row_number}: {column} nie jest liczba.") from None
    if number < 0:
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
