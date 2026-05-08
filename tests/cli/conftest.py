from __future__ import annotations

import pytest

from AOA.utils.logging_utils import configure_logging


@pytest.fixture(autouse=True)
def configure_cli_logging() -> None:
    configure_logging()
