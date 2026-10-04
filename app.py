from __future__ import annotations

import sys
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path


def _prepare_source_path() -> None:
    source_root = str(Path(__file__).resolve().parent / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)


def main(argv: Sequence[str] | None = None) -> int:
    """Run AOA directly from the repository without requiring a desktop build."""

    _prepare_source_path()
    application = import_module("AOA.app")
    return int(application.main(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
