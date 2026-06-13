from __future__ import annotations

from pathlib import Path

import pytest

from AOA.core import file_manager_service as fm


def test_file_manager_lists_previews_and_deletes_safe_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fm, "MANAGED_ROOTS", {"data": tmp_path})
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    files = fm.list_managed_files()

    assert len(files) == 1
    assert files[0].path == csv_path
    assert "sample.csv" in files[0].label
    assert "Podglad tabeli" in fm.preview_managed_file(csv_path)

    deleted = fm.delete_managed_file(csv_path)

    assert deleted == csv_path.resolve()
    assert not csv_path.exists()


def test_file_manager_rejects_paths_outside_managed_roots(tmp_path, monkeypatch) -> None:
    managed = tmp_path / "managed"
    outside = tmp_path / "outside.csv"
    managed.mkdir()
    outside.write_text("a\n1\n", encoding="utf-8")
    monkeypatch.setattr(fm, "MANAGED_ROOTS", {"data": managed})

    with pytest.raises(ValueError):
        fm.preview_managed_file(Path(outside))
