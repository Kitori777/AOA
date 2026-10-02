from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd


def test_legacy_cli_module_was_removed_after_package_split():
    assert not Path("src/AOA/cli.py").exists()


def test_sample_data_directory_is_the_only_tracked_data_source():
    sample_dir = Path("data/sample")
    assert (sample_dir / "production.csv").exists()
    assert (sample_dir / "train.csv").exists()
    assert (sample_dir / "test.csv").exists()
    assert (sample_dir / "bom.csv").exists()
    assert (sample_dir / "inventory.csv").exists()
    assert (sample_dir / "logistics.csv").exists()
    assert (sample_dir / "warehouse.csv").exists()
    assert (sample_dir / "quality.csv").exists()
    assert (sample_dir / "schedule.csv").exists()
    assert (sample_dir / "service.csv").exists()
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={Path.cwd().as_posix()}",
            "ls-files",
            "data",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_top_level = [
        Path(line.strip())
        for line in result.stdout.splitlines()
        if line.strip() and Path(line.strip()).parent == Path("data")
    ]
    generated = [
        path
        for path in tracked_top_level
        if path.name.startswith(("dane_", "train_", "test_")) and path.suffix == ".csv"
    ]
    assert not generated


def test_schedule_sample_contains_four_orders_and_real_operation_dependencies() -> None:
    project_root = Path(__file__).resolve().parents[2]
    schedule = pd.read_csv(project_root / "data" / "sample" / "schedule.csv")

    assert schedule["zlecenie_id"].nunique() == 4
    assert len(schedule) == 12
    assert schedule["operation_id"].is_unique
    assert {"predecessors", "frozen", "started", "station_type", "cena"}.issubset(
        schedule.columns
    )
    assert schedule.groupby("zlecenie_id")["cena"].nunique().eq(1).all()
    assert schedule.groupby("zlecenie_id")["termin_h"].nunique().eq(1).all()
    assert schedule["predecessors"].notna().sum() == 8


def test_gitignore_keeps_sample_data_but_ignores_generated_data():
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "/data/*" in text
    assert "!/data/sample/" in text
    assert "!/data/sample/*.csv" in text
    assert "/data/sample/*_latest.csv" in text
    assert ".pytest-run/" in text
    assert ".uv-cache-codex/" in text
