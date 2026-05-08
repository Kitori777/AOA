from __future__ import annotations

import logging
import sys
from typing import Final

DEFAULT_LOG_FORMAT: Final[str] = "%(message)s"
VERBOSE_LOG_FORMAT: Final[str] = "%(levelname)s | %(name)s | %(message)s"
APP_LOGGER_NAME: Final[str] = "AOA"

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

    handler = StdoutConsoleHandler()
    handler.setFormatter(logging.Formatter(log_format))
    handler.setLevel(level)

    app_logger = logging.getLogger(APP_LOGGER_NAME)
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.setLevel(level)
    app_logger.propagate = False

    _IS_CONFIGURED = True
    return level


def ensure_logging_configured() -> None:
    if not _IS_CONFIGURED:
        configure_logging()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
