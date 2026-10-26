"""Fixed transcriptions of the two supplied cost papers; existing ESM data is untouched."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "esm" / "article" / "costs"

SINGLE_P1 = [(10, 150), (20, 30), (100, 110), (50, 60)]
SINGLE_P2 = [(20, 30), (40, 60), (30, 70), (50, 80), (60, 120)]
DOUBLE_P1 = [(5, 4, 10), (6, 3, 14), (7, 2, 11)]
DOUBLE_P2 = [(5, 6, 15), (7, 3, 11), (4, 8, 13)]
DOUBLE_P3 = [
    (12, 1, 55),
    (44, 5, 95),
    (33, 3, 145),
    (45, 6, 101),
    (50, 7, 125),
    (80, 4, 300),
    (55, 8, 220),
    (10, 2, 115),
]


def cases() -> list[dict]:
    result = []
    groups = [
        (
            "single",
            1,
            SINGLE_P1,
            [
                (0, [1] * 4, 80),
                (10, [1] * 4, 60),
                (20, [1] * 4, 50),
                (30, [1] * 4, 30),
                (10, [1, 1, 10, 1], 110),
            ],
        ),
        ("single", 2, SINGLE_P2, [(0, [1] * 5, 160), (0, [1, 1, 2, 2, 4], 300)]),
        ("double", 1, DOUBLE_P1, [(0, [1] * 3, 9), (0, [1, 2, 1], 9), (0, [1, 2, 2], 16)]),
        ("double", 2, DOUBLE_P2, [(0, [1] * 3, 11), (0, [2, 1, 2], 16)]),
        (
            "double",
            3,
            DOUBLE_P3,
            [
                (0, [1] * 8, 154),
                (0, [1, 1, 2, 1, 2, 1, 1, 1], 183),
                (0, [1, 1, 1, 1, 1, 5, 5, 1], 219),
                (0, [1, 1, 2, 1, 2, 5, 3, 1], 248),
            ],
        ),
    ]
    for kind, problem, data, variants in groups:
        for variant, (grace, rates, expected) in enumerate(variants, 1):
            discrepancy = kind == "single" and problem == 2 and variant == 2
            article = "ART3" if kind == "single" else "DYLEWSKI"
            group = f"{article}_1_maszyna" if kind == "single" else f"{article}_2_maszyny"
            suffix = "_zamiast_330" if discrepancy else ""
            result.append(
                {
                    "file": f"{group}/Przyklad_{problem}/{article}_Przyklad_{problem}_W{variant}_koszt_{expected}{suffix}.csv",
                    "machines": 1 if kind == "single" else 2,
                    "source": "Art3 -v12pp.docx" if kind == "single" else "Art-Dylewski_J_D.docx",
                    "input_table": 2 * problem - 1,
                    "result_table": 2 * problem,
                    "problem": problem,
                    "variant": variant,
                    "data": data,
                    "rates": rates,
                    "grace": grace,
                    "expected_minimum_cost": expected,
                    "paper_minimum_cost": 330 if discrepancy else expected,
                    "discrepancy": "Pełny przegląd daje 300 dla Z1,Z3,Z5,Z4,Z2; artykuł podaje 330 dla Z1,Z3,Z5,Z2,Z4."
                    if discrepancy
                    else "",
                }
            )
    return result


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in cases():
        machines = case["machines"]
        columns = [
            "zlecenie",
            *(["czas_obrobki_min"] if machines == 1 else ["czas_m1_min", "czas_m2_min"]),
            "termin_min",
            "dopuszczalne_opoznienie_min",
            "koszt_opoznienia_na_min",
        ]
        destination = OUTPUT / case["file"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            for i, (data, rate) in enumerate(zip(case["data"], case["rates"], strict=True), 1):
                writer.writerow([f"Z{i}", *data, case["grace"], rate])
        manifest.append(
            {key: value for key, value in case.items() if key not in {"data", "rates", "grace"}}
        )
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Zapisano {len(manifest)} nowych wariantów w {OUTPUT}")


if __name__ == "__main__":
    main()
