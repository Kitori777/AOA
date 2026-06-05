from __future__ import annotations

import logging

from AOA.utils import logging_utils


def test_configure_logging_adds_managed_handlers(tmp_path, monkeypatch):
    log_file = tmp_path / "aoa.log"
    monkeypatch.setenv("AOA_LOG_FILE", str(log_file))
    monkeypatch.delenv("AOA_DISABLE_FILE_LOG", raising=False)

    level = logging_utils.configure_logging(verbose=False, quiet=False)
    assert level == logging.INFO

    logger = logging.getLogger(logging_utils.APP_LOGGER_NAME)
    assert logger.handlers
    logger.info("test")
    assert log_file.exists()


def test_configure_logging_can_disable_file_log(monkeypatch):
    monkeypatch.setenv("AOA_DISABLE_FILE_LOG", "1")
    monkeypatch.delenv("AOA_LOG_FILE", raising=False)
    logging_utils.configure_logging(verbose=False, quiet=False)
    logger = logging.getLogger(logging_utils.APP_LOGGER_NAME)
    file_handlers = [h for h in logger.handlers if h.__class__.__name__ == "RotatingFileHandler"]
    assert not file_handlers
