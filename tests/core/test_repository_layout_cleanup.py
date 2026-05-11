from __future__ import annotations

from pathlib import Path


def test_legacy_cli_module_was_removed_after_package_split():
    assert not Path("src/AOA/cli.py").exists()


def test_sample_data_directory_is_the_only_tracked_data_source():
    sample_dir = Path("data/sample")
    assert (sample_dir / "production.csv").exists()
    assert (sample_dir / "train.csv").exists()
    assert (sample_dir / "test.csv").exists()
    assert not list(Path("data").glob("dane_*.csv"))
    assert not list(Path("data").glob("train_*.csv"))
    assert not list(Path("data").glob("test_*.csv"))


def test_gitignore_keeps_sample_data_but_ignores_generated_data():
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "/data/*" in text
    assert "!/data/sample/" in text
    assert "!/data/sample/*.csv" in text
