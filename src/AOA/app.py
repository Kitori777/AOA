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
    previous_smoke_flag = os.environ.get("AOA_SMOKE_TEST")
    if options.smoke_test:
        # Pages inspect this flag while they are being constructed.  Setting it
        # before importing/creating the window prevents background refreshes
        # from racing with the deliberately short smoke-test lifetime.
        os.environ["AOA_SMOKE_TEST"] = "1"
    from AOA.gui.main_window import App

    application = App()
    if options.smoke_test:
        application.withdraw()
        # CTk performs Windows title-bar setup immediately before entering the
        # Tk loop.  Destroying the window from a timer can therefore tear down
        # Tcl while CTk is still finishing that setup.  Quit the loop first and
        # destroy the widget only after mainloop has returned.
        application.after(750, application.quit)
        _write_smoke_marker()
    try:
        application.mainloop()
    finally:
        if options.smoke_test:
            try:
                application.destroy()
            except Exception:
                pass
            if previous_smoke_flag is None:
                os.environ.pop("AOA_SMOKE_TEST", None)
            else:
                os.environ["AOA_SMOKE_TEST"] = previous_smoke_flag
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
