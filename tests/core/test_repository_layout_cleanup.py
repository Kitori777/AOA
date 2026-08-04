from __future__ import annotations

import subprocess
from pathlib import Path


def test_legacy_cli_module_was_removed_after_package_split():
    assert not Path("src/AOA/cli.py").exists()


def test_sample_data_directory_is_the_only_tracked_data_source():
    sample_dir = Path("data/sample")
    assert (sample_dir / "production.csv").exists()
    assert (sample_dir / "train.csv").exists()
    assert (sample_dir / "test.csv").exists()
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


def test_gitignore_keeps_sample_data_but_ignores_generated_data():
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "/data/*" in text
    assert "!/data/sample/" in text
    assert "!/data/sample/*.csv" in text
