from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from AOA import __version__
from AOA.config import APP_PATHS
from AOA.utils.logging_utils import configure_logging


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test", action="store_true")
    options, _unknown = parser.parse_known_args(argv)
    return options


def _write_smoke_marker() -> None:
    marker_value = os.getenv("AOA_SMOKE_MARKER", "").strip()
    if not marker_value:
        return
    marker = Path(marker_value)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "version": __version__,
                "frozen": APP_PATHS.frozen,
                "resource_root": str(APP_PATHS.resource_root),
                "user_root": str(APP_PATHS.user_root),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    options = _parse_args(argv)
    configure_logging()
    from AOA.gui.main_window import App

    application = App()
    if options.smoke_test:
        application.withdraw()
        application.after(750, application.destroy)
        _write_smoke_marker()
    application.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
