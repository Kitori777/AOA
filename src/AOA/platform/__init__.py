"""Platform-specific bootstrap helpers for desktop distributions."""

from .bootstrap import bootstrap_user_data
from .paths import AppPaths, resolve_app_paths

__all__ = ["AppPaths", "bootstrap_user_data", "resolve_app_paths"]
