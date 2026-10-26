from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_legacy_cli_module_was_removed_after_package_split():
    assert not Path("src/AOA/cli.py").exists()


def test_esm_data_is_the_only_tracked_data_source():
    esm_path = Path("data/esm/esm_jobs.csv")
    assert esm_path.exists()
    existing = sorted(path.as_posix() for path in Path("data").rglob("*") if path.is_file())
    expected = [
        "data/esm/esm_jobs.csv",
        "data/esm/README.md",
        "data/esm/article/README.md",
        "data/esm/article/mper-2017-0026.pdf",
    ]
    expected += [f"data/esm/article/esm_paper_0{i}.csv" for i in range(1, 5)]
    expected += ["data/esm/article/costs/README.md", "data/esm/article/costs/manifest.json"]
    costs = Path("data/esm/article/costs")
    cases = json.loads((costs / "manifest.json").read_text(encoding="utf-8"))
    assert len(cases) == 16
    assert not list(costs.glob("*.csv"))
    assert {p.name for p in costs.iterdir() if p.is_dir()} == {
        "ART3_1_maszyna",
        "DYLEWSKI_2_maszyny",
    }
    expected += [(costs / case["file"]).as_posix() for case in cases]
    assert existing == sorted(expected)


def test_synthetic_regression_data_is_outside_the_selectable_data_directory():
    assert not Path("data/esm/examples").exists()
    assert len(list(Path("tests/fixtures/esm").glob("*.csv"))) == 17


def test_esm_sample_matches_the_four_job_pdf_example() -> None:
    project_root = Path(__file__).resolve().parents[2]
    esm = pd.read_csv(project_root / "data" / "esm" / "esm_jobs.csv")

    assert list(esm.columns) == ["zlecenie", "czas_obrobki_min", "termin_min"]
    assert esm.to_dict("records") == [
        {"zlecenie": "Z1", "czas_obrobki_min": 10, "termin_min": 150},
        {"zlecenie": "Z2", "czas_obrobki_min": 20, "termin_min": 30},
        {"zlecenie": "Z3", "czas_obrobki_min": 100, "termin_min": 110},
        {"zlecenie": "Z4", "czas_obrobki_min": 50, "termin_min": 60},
    ]


def test_gitignore_keeps_only_esm_data_and_local_backups():
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "/data/*" in text
    assert "!/data/esm/" in text
    assert "!/data/esm/esm_jobs.csv" in text
    assert "!/data/esm/examples/" not in text
    assert "!/data/esm/article/" in text
    assert ".aoa-backups/" in text
    assert ".pytest-run/" in text
    assert ".uv-cache-codex/" in text
