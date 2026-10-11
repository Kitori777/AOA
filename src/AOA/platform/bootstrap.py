from __future__ import annotations

import json
import shutil
from pathlib import Path

from .paths import AppPaths

BOOTSTRAP_VERSION = 6
_DOC_SUFFIXES = {".md", ".json", ".txt"}
_DATA_SUFFIXES = {".csv", ".tsv", ".txt", ".json"}


def _copy_if_missing(source: Path, destination: Path) -> bool:
    if destination.exists() or not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)
    return True


def _copy_seed_tree(source: Path, destination: Path, suffixes: set[str]) -> int:
    if not source.exists():
        return 0
    copied = 0
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        target = destination / path.relative_to(source)
        copied += int(_copy_if_missing(path, target))
    return copied


def _write_manifest(path: Path, payload: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def bootstrap_user_data(paths: AppPaths) -> dict[str, int]:
    """Create writable directories and seed only files that do not exist.

    Existing user files are never overwritten, making repeated launches and
    upgrades idempotent.
    """

    for directory in (
        paths.user_root,
        paths.config_root,
        paths.data_dir,
        paths.models_dir,
        paths.docs_dir,
        paths.logs_dir,
        paths.cache_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    copied_docs = _copy_seed_tree(paths.seed_docs_dir, paths.docs_dir, _DOC_SUFFIXES)
    copied_samples = _copy_seed_tree(
        paths.seed_data_dir,
        paths.data_dir / "esm",
        _DATA_SUFFIXES,
    )
    manifest = {
        "bootstrap_version": BOOTSTRAP_VERSION,
        "copied_docs": copied_docs,
        "copied_samples": copied_samples,
        "refreshed_samples": 0,
    }
    _write_manifest(paths.config_root / "bootstrap.json", manifest)
    return manifest
