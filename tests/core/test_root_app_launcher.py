from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from AOA import app as application_entrypoint


def test_root_app_launcher_exposes_main_without_starting_gui() -> None:
    project_root = Path(__file__).resolve().parents[2]

    namespace = runpy.run_path(str(project_root / "app.py"), run_name="aoa_launcher_test")

    assert callable(namespace["main"])


def test_direct_source_script_does_not_shadow_stdlib_platform() -> None:
    project_root = Path(__file__).resolve().parents[2]
    source_app = project_root / "src" / "AOA" / "app.py"
    command = (
        "import runpy; "
        f"runpy.run_path({str(source_app)!r}, run_name='pycharm_direct_test'); "
        "import platform; "
        "assert callable(platform.release)"
    )

    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=source_app.parent,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_source_smoke_test_quits_before_destroying(monkeypatch) -> None:
    events: list[str] = []

    class FakeApp:
        def withdraw(self) -> None:
            events.append("withdraw")

        def after(self, delay: int, callback) -> None:
            assert delay == 750
            events.append("after")
            self.callback = callback

        def quit(self) -> None:
            events.append("quit")

        def mainloop(self) -> None:
            events.append("mainloop")
            self.callback()

        def destroy(self) -> None:
            events.append("destroy")

    fake_module = ModuleType("AOA.gui.main_window")
    fake_module.App = FakeApp  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "AOA.gui.main_window", fake_module)
    monkeypatch.delenv("AOA_SMOKE_TEST", raising=False)

    assert application_entrypoint.main(["--smoke-test"]) == 0
    assert events == ["withdraw", "after", "mainloop", "quit", "destroy"]
    assert "AOA_SMOKE_TEST" not in application_entrypoint.os.environ
