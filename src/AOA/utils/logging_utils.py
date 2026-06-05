from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

from AOA.config import BASE_DIR

DEFAULT_LOG_FORMAT: Final[str] = "%(message)s"
VERBOSE_LOG_FORMAT: Final[str] = "%(levelname)s | %(name)s | %(message)s"
APP_LOGGER_NAME: Final[str] = "AOA"
FILE_LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
_MANAGED_ATTR: Final[str] = "_aoa_managed"
_FILE_MAX_BYTES: Final[int] = 1_000_000
_FILE_BACKUP_COUNT: Final[int] = 5

_IS_CONFIGURED = False


class StdoutConsoleHandler(logging.Handler):
    """Simple handler writing formatted logs to the current stdout stream."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            sys.stdout.write(f"{message}\n")
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


def resolve_log_level(*, verbose: bool = False, quiet: bool = False) -> int:
    if quiet:
        return logging.WARNING
    if verbose:
        return logging.DEBUG
    return logging.INFO


def configure_logging(*, verbose: bool = False, quiet: bool = False) -> int:
    """Configure application logging for CLI and GUI entry points."""
    global _IS_CONFIGURED

    level = resolve_log_level(verbose=verbose, quiet=quiet)
    log_format = VERBOSE_LOG_FORMAT if verbose else DEFAULT_LOG_FORMAT

    app_logger = logging.getLogger(APP_LOGGER_NAME)
    for existing in list(app_logger.handlers):
        if getattr(existing, _MANAGED_ATTR, False):
            app_logger.removeHandler(existing)
            existing.close()

    handler = StdoutConsoleHandler()
    handler.setFormatter(logging.Formatter(log_format))
    handler.setLevel(level)
    setattr(handler, _MANAGED_ATTR, True)
    app_logger.addHandler(handler)

    log_file = _resolve_log_file()
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_FILE_MAX_BYTES,
            backupCount=_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT))
        file_handler.setLevel(level)
        setattr(file_handler, _MANAGED_ATTR, True)
        app_logger.addHandler(file_handler)

    app_logger.setLevel(level)
    app_logger.propagate = False

    _IS_CONFIGURED = True
    return level


def ensure_logging_configured() -> None:
    if not _IS_CONFIGURED:
        configure_logging()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _resolve_log_file() -> Path | None:
    disabled = os.getenv("AOA_DISABLE_FILE_LOG", "").strip().lower()
    if disabled in {"1", "true", "yes"}:
        return None
    configured = os.getenv("AOA_LOG_FILE", "").strip()
    if configured:
        return Path(configured)
    return BASE_DIR / "logs" / "aoa.log"
