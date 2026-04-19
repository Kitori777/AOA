from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from AOA.utils.logging_utils import ensure_logging_configured, get_logger

AVAILABLE_ML_MODELS = {"Quality", "Delay", "Schedule"}
AVAILABLE_STO_MODELS = {"MT", "MO", "MZO", "GENETIC"}
AVAILABLE_BACKENDS = {"classic", "tabpfn"}
DEFAULT_SHAPES = ["kwadrat", "trojkat", "trapez"]
DEFAULT_MATERIALS = ["bawelna", "mikrofibra", "poliester", "wiskoza"]

logger = get_logger(__name__)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse_csv_list(value: str | None) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def validate_models(selected: Iterable[str], allowed: set[str], label: str) -> list[str]:
    selected = list(selected)
    invalid = [item for item in selected if item not in allowed]
    if invalid:
        raise ValueError(
            f"Nieprawidłowe {label}: {', '.join(invalid)}. "
            f"Dozwolone: {', '.join(sorted(allowed))}"
        )
    return selected


def print_messages(messages: list[str] | None):
    ensure_logging_configured()
    if not messages:
        return
    for msg in messages:
        logger.info(msg)


def print_key_value(title: str, value):
    ensure_logging_configured()
    logger.info("%s: %s", title, value)


def hr(title: str):
    ensure_logging_configured()
    logger.info("")
    logger.info("===== %s =====", title)


def progress_callback(model_name: str, percent: float, detail: str = ""):
    ensure_logging_configured()
    suffix = f" | {detail}" if detail else ""
    logger.info("[POSTĘP] %s: %.1f%%%s", model_name, percent, suffix)


def resolve_existing_file(path_str: str, label: str) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono {label}: {path}")
    return path


def resolve_optional_path(path_str: str | None) -> Path | None:
    if not path_str:
        return None
    return Path(path_str)
