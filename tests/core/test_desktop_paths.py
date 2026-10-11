from __future__ import annotations

from pathlib import Path

from AOA.platform.bootstrap import bootstrap_user_data
from AOA.platform.paths import AppPaths, resolve_app_paths


def _paths(root: Path) -> AppPaths:
    resources = root / "resources"
    user = root / "user"
    return AppPaths(
        resource_root=resources,
        user_root=user,
        config_root=user / "config",
        data_dir=user / "data",
        models_dir=user / "models",
        docs_dir=user / "docs",
        logs_dir=user / "logs",
        cache_dir=user / "cache",
        assets_dir=resources / "AOA" / "assets",
        seed_data_dir=resources / "data" / "esm",
        seed_docs_dir=resources / "docs",
        frozen=True,
    )


def test_packaged_paths_use_windows_profile_and_bundle_resources(tmp_path, monkeypatch) -> None:
    bundle = tmp_path / "bundle"
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    monkeypatch.setattr("sys._MEIPASS", str(bundle), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.delenv("AOA_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("AOA_CONFIG_DIR", raising=False)

    paths = resolve_app_paths(frozen=True)

    assert paths.resource_root == bundle.resolve()
    assert paths.user_root == (local / "AOA").resolve()
    assert paths.config_root == (roaming / "AOA").resolve()
    assert paths.assets_dir == bundle.resolve() / "AOA" / "assets"


def test_bootstrap_copies_seeds_once_and_preserves_user_edits(tmp_path) -> None:
    paths = _paths(tmp_path)
    paths.seed_docs_dir.mkdir(parents=True)
    paths.seed_data_dir.mkdir(parents=True)
    (paths.seed_docs_dir / "guide.md").write_text("seed guide", encoding="utf-8")
    (paths.seed_data_dir / "sample.csv").write_text("a\n1\n", encoding="utf-8")

    first = bootstrap_user_data(paths)
    (paths.docs_dir / "guide.md").write_text("user guide", encoding="utf-8")
    second = bootstrap_user_data(paths)

    assert first["copied_docs"] == 1
    assert first["copied_samples"] == 1
    assert second["copied_docs"] == 0
    assert (paths.docs_dir / "guide.md").read_text(encoding="utf-8") == "user guide"
    assert (paths.data_dir / "esm" / "sample.csv").read_text(encoding="utf-8") == "a\n1\n"
    assert (paths.config_root / "bootstrap.json").exists()
