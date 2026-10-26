"""Regenerate synthetic test fixtures and the four faithful MPER table transcriptions."""

from __future__ import annotations

import csv
import random
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "esm"
ARTICLE = Path(__file__).resolve().parents[1] / "data" / "esm" / "article"

# These are deliberately selected teaching cases, not a frequency estimate.
THESIS_CASES = [
    (
        "esm_flow_10_urgent",
        "MOpt przerwany limitem",
        "seed=19; limit 100 stanow kontra pelne wyszukiwanie",
    ),
    (
        "esm_flow_10_eco_trap",
        "Pulapka przezbrojen",
        "seed=1; ten sam STO, ale dalsza redukcja odpadu",
    ),
    (
        "esm_flow_10_component_wait",
        "Dalsza poprawa Component Ready",
        "seed=2; opoznione komponenty i wiecej niz dwa przebiegi",
    ),
    (
        "esm_flow_10_intentional_idle",
        "Oplacalny przestoj",
        "konstrukcja: Z2 dostepne od 5 min i wymagane do 8 min",
    ),
    (
        "esm_jobs_10_mixed_constraints",
        "Konflikt STO i odpadu",
        "seed=8; mniejszy odpad moze wymagac wiekszego STO",
    ),
    (
        "esm_flow_10_eco_components",
        "Nominalne optimum a ryzyko",
        "dotychczasowy seed=13, trzy materialy i dostawy",
    ),
    (
        "esm_flow_10_multiple_optima",
        "Wiele rownorzednych optimow",
        "konstrukcja: dwie rodziny, luźne terminy, symetria wewnatrz rodzin",
    ),
    (
        "esm_flow_10_blocked_components",
        "Pozornie lepszy plan niepelny",
        "seed=0; Z4 trwale zablokowane; wariant kontrolny: wszystkie READY/WAITING",
    ),
]


def write_example(
    name: str, rows: Sequence[tuple[tuple[int, ...], int]], *, directory: Path = ROOT
) -> None:
    stages = len(rows[0][0])
    with (directory / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["zlecenie", *[f"czas_m{i}_min" for i in range(1, stages + 1)], "termin_min"]
        )
        writer.writerows([f"Z{i}", *times, deadline] for i, (times, deadline) in enumerate(rows, 1))


def generated(seed: int, count: int = 10, stages: int = 3, *, bottleneck: bool = False):
    rng = random.Random(seed)
    rows = []
    for _ in range(count):
        times = tuple(rng.randint(2, 24) for _ in range(stages))
        deadline = rng.randint(35, 180) if stages == 3 else rng.randint(90, 230)
        if bottleneck:
            times = (max(2, times[0] // 2), times[1] + 12, max(2, times[2] // 2))
        rows.append((times, deadline))
    return rows


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    ARTICLE.mkdir(parents=True, exist_ok=True)
    write_example("esm_flow_10_three_machines.csv", generated(13))
    write_example("esm_flow_10_bottleneck.csv", generated(27, bottleneck=True))
    write_example("esm_flow_10_urgent.csv", generated(71))
    write_example("esm_flow_10_eight_machines.csv", generated(29, stages=8))
    write_example("esm_flow_06_ties.csv", [((4, 7, 3), 120)] * 6)
    write_extended_example()
    for count, name, seed in [
        (5, "tight_deadlines", 13),
        (6, "component_wait", 27),
        (7, "parallel_balance", 41),
        (8, "changeovers", 71),
        (9, "urgent_mix", 83),
        (10, "mixed_constraints", 41),
    ]:
        # Keep fixture filenames stable for regression tests and reports.
        write_example(f"esm_jobs_{count:02}_{name}.csv", generated(seed, count))
    paper = [
        [((5, 4), 10), ((6, 3), 14), ((7, 2), 11)],
        [((5, 4), 10), ((6, 3), 14), ((7, 1), 13)],
        [((1, 5), 18), ((4, 3), 8), ((2, 6), 12)],
        [((10, 2), 70), ((5, 11), 20), ((20, 1), 60), ((15, 6), 50)],
    ]
    for i, rows in enumerate(paper, 1):
        write_example(f"esm_paper_{i:02}.csv", rows, directory=ARTICLE)
    write_thesis_cases()


def selected_rows(seed: int) -> list[list]:
    """Frozen draw order reproduces the exploratory counterexamples."""
    rng = random.Random(seed)
    rows = []
    for i in range(10):
        deadline = rng.randint(45, 200)
        times = tuple(rng.randint(2, 24) for _ in range(3))
        material = rng.choice(["A", "B", "C"])
        ready = rng.choice([0, 0, 0, 20, 40, 60])
        rows.append(
            [
                f"Z{i + 1}",
                *times,
                deadline,
                material,
                "X",
                1,
                4,
                5,
                8,
                3,
                ready,
                "WAITING_COMPONENTS" if ready else "READY",
            ]
        )
    return rows


def write_thesis_cases() -> None:
    columns = [
        "zlecenie",
        "czas_m1_min",
        "czas_m2_min",
        "czas_m3_min",
        "termin_min",
        "material",
        "ksztalt",
        "odpad_kg",
        "odpad_przezbrojenia_kg",
        "czas_przezbrojenia_m1_min",
        "czas_przezbrojenia_m2_min",
        "czas_przezbrojenia_m3_min",
        "components_ready_min",
        "stock_status",
    ]
    cases = {
        "esm_flow_10_urgent": selected_rows(19),
        "esm_flow_10_eco_trap": selected_rows(1),
        "esm_flow_10_component_wait": selected_rows(2),
        "esm_jobs_10_mixed_constraints": selected_rows(8),
        "esm_flow_10_blocked_components": selected_rows(0),
    }
    cases["esm_flow_10_blocked_components"][3][-1] = "UNSCHEDULABLE"
    idle = [
        ["Z1", 40, 1, 1, 500, "A", "X", 1, 0, 0, 0, 0, 0, "READY"],
        ["Z2", 1, 1, 1, 8, "A", "X", 1, 0, 0, 0, 0, 5, "WAITING_COMPONENTS"],
    ]
    idle += [
        [f"Z{i}", 2, 2, 2, 500, "A", "X", 1, 0, 0, 0, 0, 50, "WAITING_COMPONENTS"]
        for i in range(3, 11)
    ]
    cases["esm_flow_10_intentional_idle"] = idle
    cases["esm_flow_10_multiple_optima"] = [
        [f"Z{i + 1}", 2, 3, 2, 500, "A" if i % 2 else "B", "X", 1, 4, 0, 0, 0, 0, "READY"]
        for i in range(10)
    ]
    for name, rows in cases.items():
        with (ROOT / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(columns)
            writer.writerows(rows)


def write_extended_example() -> None:
    """Synthetic 3x10 sample for ECO, readiness and stochastic execution."""
    materials = [
        "bawelna",
        "poliester",
        "bawelna",
        "wiskoza",
        "poliester",
        "bawelna",
        "wiskoza",
        "poliester",
        "bawelna",
        "wiskoza",
    ]
    shapes = {"bawelna": "PLYTA", "poliester": "WALEK", "wiskoza": "DETAL"}
    ready = [0, 35, 0, 60, 0, 10, 40, 0, 80, 0]
    with (ROOT / "esm_flow_10_eco_components.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "zlecenie",
                "czas_m1_min",
                "czas_m2_min",
                "czas_m3_min",
                "termin_min",
                "material",
                "ksztalt",
                "odpad_kg",
                "odpad_przezbrojenia_kg",
                "czas_przezbrojenia_m1_min",
                "czas_przezbrojenia_m2_min",
                "czas_przezbrojenia_m3_min",
                "components_ready_min",
                "stock_status",
            ]
        )
        for i, (times, deadline) in enumerate(generated(13)):
            material = materials[i]
            writer.writerow(
                [
                    f"Z{i + 1}",
                    *times,
                    deadline + 25,
                    material,
                    shapes[material],
                    round(0.3 + (i % 4) * 0.2, 1),
                    1.5 + (i % 3) * 0.5,
                    3,
                    5,
                    2,
                    ready[i],
                    "WAITING_COMPONENTS" if ready[i] else "READY",
                ]
            )


if __name__ == "__main__":
    main()
