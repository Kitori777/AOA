from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .paths import AppPaths

BOOTSTRAP_VERSION = 4
_DOC_SUFFIXES = {".md", ".json", ".txt"}
_DATA_SUFFIXES = {".csv", ".tsv", ".txt", ".json"}
_LEGACY_SAMPLE_HASHES: dict[str, set[str] | str] = {
    "production.csv": {
        "6b7f2b9cf6b35f79c2c232ff784816b8a765c1d37ad2633b8afc0ef3b4d7715a",
        "a2068cf018c92b449b3fe45fcb000833356cdb0b7f49d9948e6e51cfded8e335",
    },
    "train.csv": {
        "b68a3396c21aecb0b1040b1da2a2201609d6bf33ea7c13f49543752524b563b7",
        "1ac30051035144117c62cf5194e9712690fac39577bf2d3a7dc49ef0961e9b5f",
    },
    "test.csv": {
        "1a1da457a80d1655d05277aab851d63c502527ef1b6e0fffa9bd267bbc01b15a",
        "bcaf0f071ab357dfc25d55f184f61b864989fcf8ff75debfd786412e22c7ba3",
    },
    "sample_table.csv": {
        "a11ca6335c791510609b8803947cab1d280b00181254e5a06b2f0c91eece9018",
        "8e00804491aa911ee95a815fe959d75198d812b854732a3d5a3650d278626253",
    },
    "schedule.csv": {
        "4ff2eeb3f56e7e904191d9375cf24fd14a57499c42877c4c4bb3a6918d9dc826",
        "1476acfb7ac874ce47681595e4f3d5717e87fa2d1baca57a79adf782bb00fb05",
    },
}


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


def _refresh_legacy_samples(source: Path, destination: Path) -> int:
    """Upgrade untouched bundled samples while preserving every user edit."""
    refreshed = 0
    for name, legacy_hashes in _LEGACY_SAMPLE_HASHES.items():
        current = destination / name
        replacement = source / name
        if not current.is_file() or not replacement.is_file():
            continue
        known_hashes = {legacy_hashes} if isinstance(legacy_hashes, str) else legacy_hashes
        if hashlib.sha256(current.read_bytes()).hexdigest() not in known_hashes:
            continue
        temporary = current.with_name(f".{current.name}.tmp")
        shutil.copy2(replacement, temporary)
        temporary.replace(current)
        refreshed += 1
    return refreshed


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
        paths.data_dir / "sample",
        _DATA_SUFFIXES,
    )
    refreshed_samples = _refresh_legacy_samples(
        paths.seed_data_dir,
        paths.data_dir / "sample",
    )
    manifest = {
        "bootstrap_version": BOOTSTRAP_VERSION,
        "copied_docs": copied_docs,
        "copied_samples": copied_samples,
        "refreshed_samples": refreshed_samples,
    }
    _write_manifest(paths.config_root / "bootstrap.json", manifest)
    return manifest
