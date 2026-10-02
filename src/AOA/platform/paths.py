from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Read-only application resources and writable per-user directories."""

    resource_root: Path
    user_root: Path
    config_root: Path
    data_dir: Path
    models_dir: Path
    docs_dir: Path
    logs_dir: Path
    cache_dir: Path
    assets_dir: Path
    seed_data_dir: Path
    seed_docs_dir: Path
    frozen: bool


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _source_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resource_root(frozen: bool) -> Path:
    if frozen:
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            return Path(bundle_dir).resolve()
        return Path(sys.executable).resolve().parent
    return _source_root()


def _windows_local_app_data() -> Path:
    configured = os.getenv("LOCALAPPDATA", "").strip()
    if configured:
        return Path(configured)
    return Path.home() / "AppData" / "Local"


def _windows_roaming_app_data() -> Path:
    configured = os.getenv("APPDATA", "").strip()
    if configured:
        return Path(configured)
    return Path.home() / "AppData" / "Roaming"


def resolve_app_paths(*, frozen: bool | None = None) -> AppPaths:
    """Resolve paths without creating files.

    Source checkouts keep their historical portable layout unless an explicit
    ``AOA_USER_DATA_DIR`` is provided. A packaged application always uses the
    Windows user profile so upgrades never overwrite user-generated content.
    """

    is_frozen = _is_frozen() if frozen is None else frozen
    resource_root = _resource_root(is_frozen)

    configured_user_root = os.getenv("AOA_USER_DATA_DIR", "").strip()
    if configured_user_root:
        user_root = Path(configured_user_root).expanduser().resolve()
    elif is_frozen:
        user_root = (_windows_local_app_data() / "AOA").resolve()
    else:
        user_root = resource_root

    configured_config_root = os.getenv("AOA_CONFIG_DIR", "").strip()
    if configured_config_root:
        config_root = Path(configured_config_root).expanduser().resolve()
    elif is_frozen:
        config_root = (_windows_roaming_app_data() / "AOA").resolve()
    else:
        config_root = user_root / ".aoa"

    assets_dir = (
        resource_root / "AOA" / "assets" if is_frozen else resource_root / "src" / "AOA" / "assets"
    )

    return AppPaths(
        resource_root=resource_root,
        user_root=user_root,
        config_root=config_root,
        data_dir=user_root / "data",
        models_dir=user_root / "models",
        docs_dir=user_root / "docs",
        logs_dir=user_root / "logs",
        cache_dir=user_root / "cache",
        assets_dir=assets_dir,
        seed_data_dir=resource_root / "data" / "sample",
        seed_docs_dir=resource_root / "docs",
        frozen=is_frozen,
    )
