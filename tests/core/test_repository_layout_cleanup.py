from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_legacy_cli_module_was_removed_after_package_split():
    assert not Path("src/AOA/cli.py").exists()


def test_esm_data_is_the_only_tracked_data_source():
    esm_path = Path("data/esm/esm_jobs.csv")
    assert esm_path.exists()
    existing = sorted(path.as_posix() for path in Path("data").rglob("*") if path.is_file())
    assert existing == sorted([
        "data/esm/esm_jobs.csv",
        "data/esm/examples/esm_jobs_05_tight_deadlines.csv",
        "data/esm/examples/esm_jobs_06_component_wait.csv",
        "data/esm/examples/esm_jobs_07_parallel_balance.csv",
        "data/esm/examples/esm_jobs_08_changeovers.csv",
        "data/esm/examples/esm_jobs_09_urgent_mix.csv",
        "data/esm/examples/esm_jobs_10_mixed_constraints.csv",
    ])


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
    assert "!/data/esm/examples/" in text
    assert "!/data/esm/examples/*.csv" in text
    assert ".aoa-backups/" in text
    assert ".pytest-run/" in text
    assert ".uv-cache-codex/" in text
