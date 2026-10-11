from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path


def _prepare_source_path() -> None:
    source_root = str(Path(__file__).resolve().parent / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)


def _project_python(*, windowed: bool) -> Path | None:
    scripts = Path(__file__).resolve().parent / ".venv" / "Scripts"
    candidate = scripts / ("pythonw.exe" if windowed else "python.exe")
    return candidate if candidate.is_file() else None


def _relaunch_with_project_python(argv: Sequence[str]) -> bool:
    """Detach a double-click launch into the repository's own environment."""

    if os.name != "nt" or os.getenv("AOA_LAUNCHER_REEXEC") == "1":
        return False
    smoke_test = "--smoke-test" in argv
    candidate = _project_python(windowed=not smoke_test)
    if candidate is None or Path(sys.executable).resolve().parent == candidate.resolve().parent:
        return False
    environment = os.environ.copy()
    environment["AOA_LAUNCHER_REEXEC"] = "1"
    command = [str(candidate), str(Path(__file__).resolve()), *argv]
    if smoke_test:
        completed = subprocess.run(command, cwd=Path(__file__).resolve().parent, env=environment)
        if completed.returncode:
            raise RuntimeError(f"Test uruchomienia zakonczyl sie kodem {completed.returncode}.")
    else:
        subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parent,
            env=environment,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    return True


def _show_startup_error(exc: Exception) -> None:
    message = "AOA nie moze sie uruchomic.\n\n" + str(exc)
    try:
        from tkinter import messagebox

        messagebox.showerror("AOA - blad uruchomienia", message)
    except Exception:
        print(message, file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Run AOA directly from the repository without requiring a desktop build."""

    arguments = list(argv or ())
    try:
        if _relaunch_with_project_python(arguments):
            return 0
        _prepare_source_path()
        application = import_module("AOA.app")
        return int(application.main(arguments))
    except Exception as exc:
        _show_startup_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
