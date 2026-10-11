from __future__ import annotations

from dataclasses import dataclass
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


def build_mopt_solution_tree(jobs: list[Job]) -> list[EsmTreeNode]:
    """Return a compact, exact dynamic-programming solution tree for MOpt.

    The calculation considers every remaining first choice through memoized
    subproblems.  The visual trace keeps the optimal branch and up to two best
    alternatives at each level, so the diagram remains readable for 10 jobs.
    """

    if not jobs:
        raise ValueError("Brak zlecen do drzewa MOpt.")
    if len(jobs) > ESM_MAX_JOBS:
        raise ValueError(f"Drzewo MOpt obsluguje maksymalnie {ESM_MAX_JOBS} zlecen.")

    count = len(jobs)
    full_mask = (1 << count) - 1
    total_processing = sum(job.processing_time for job in jobs)
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
        elapsed = total_processing - remaining_sum(mask)
        candidates: list[tuple[float, str, int]] = []
        for index, job in enumerate(jobs):
            bit = 1 << index
            if not mask & bit:
                continue
            completion = elapsed + job.processing_time
            immediate = max(0.0, completion - job.deadline)
            candidates.append((immediate + optimum(mask ^ bit), job.job_id, index))
        score, _job_id, selected_index = min(candidates)
        choices[mask] = selected_index
        return score

    optimum(full_mask)
    nodes = [
        EsmTreeNode(
            node_id="B1",
            parent_id="",
            edge_label="",
            label="Start",
            details=f"{count} zlecen | optimum STO={optimum(full_mask):g}",
            depth=0,
            chosen=True,
        )
    ]
    next_id = 2
    parent_id = "B1"
    mask = full_mask
    running_sto = 0.0
    depth = 1
    while mask:
        elapsed = total_processing - remaining_sum(mask)
        selected_index = choices[mask]
        candidates: list[tuple[float, str, int, float, float]] = []
        for index, job in enumerate(jobs):
            bit = 1 << index
            if not mask & bit:
                continue
            completion = elapsed + job.processing_time
            immediate = max(0.0, completion - job.deadline)
            total = running_sto + immediate + optimum(mask ^ bit)
            candidates.append((total, job.job_id, index, completion, immediate))
        candidates.sort(key=lambda item: (item[0], item[1]))
        visible = [candidate for candidate in candidates if candidate[2] == selected_index]
        visible.extend(candidate for candidate in candidates if candidate[2] != selected_index)
        visible = visible[:3]

        selected_node_id = ""
        for total, job_id, index, completion, immediate in visible:
            chosen = index == selected_index
            node_id = f"B{next_id}"
            next_id += 1
            if chosen:
                selected_node_id = node_id
            nodes.append(
                EsmTreeNode(
                    node_id=node_id,
                    parent_id=parent_id,
                    edge_label=job_id,
                    label=job_id if chosen else f"{job_id} (odrzucono)",
                    details=(
                        f"koniec={completion:g} | T+={immediate:g} | "
                        f"najlepsze mozliwe STO={total:g}"
                    ),
                    depth=depth,
                    chosen=chosen,
                    leaf=(mask ^ (1 << index)) == 0,
                )
            )
        selected_job = jobs[selected_index]
        selected_completion = elapsed + selected_job.processing_time
        running_sto += max(0.0, selected_completion - selected_job.deadline)
        mask ^= 1 << selected_index
        parent_id = selected_node_id
        depth += 1
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
