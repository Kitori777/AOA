from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _library_candidates() -> list[Path]:
    roots = [Path(sys.base_prefix), Path(sys.prefix)]
    configured = os.environ.get("TCL_LIBRARY", "").strip()
    candidates = [Path(configured)] if configured else []
    for root in roots:
        candidates.extend((root / "tcl" / "tcl8.6", root / "lib" / "tcl8.6"))
    unique: dict[str, Path] = {}
    for candidate in candidates:
        unique.setdefault(str(candidate).casefold(), candidate)
    return list(unique.values())


def main() -> int:
    report: dict[str, object] = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "base_prefix": sys.base_prefix,
        "tcl_library_env": os.environ.get("TCL_LIBRARY", ""),
        "tk_library_env": os.environ.get("TK_LIBRARY", ""),
    }
    candidates = _library_candidates()
    candidate_report: list[dict[str, object]] = [
        {"path": str(path / "init.tcl"), "visible_to_python": (path / "init.tcl").is_file()}
        for path in candidates
    ]
    report["init_tcl_candidates"] = candidate_report
    try:
        import tkinter as tk

        report["compiled_tcl"] = tk.TclVersion
        report["compiled_tk"] = tk.TkVersion
        root = tk.Tk()
        root.withdraw()
        report["runtime_tcl"] = root.tk.eval("info patchlevel")
        report["runtime_tk"] = root.tk.eval("set tk_patchLevel")
        root.update_idletasks()
        root.destroy()
    except Exception as exc:  # Tk reports platform-specific exception types.
        report["status"] = "ERROR"
        report["error"] = f"{type(exc).__name__}: {exc}"
        visible = any(bool(item["visible_to_python"]) for item in candidate_report)
        if "init.tcl" in str(exc) and visible:
            report["diagnosis"] = (
                "Plik init.tcl istnieje i Python go widzi, ale proces Tcl nie może odczytać "
                "ścieżki. Uruchom test bez sandboxa/izolacji i sprawdź uprawnienia procesu; "
                "nie kopiuj bibliotek z innej wersji Pythona."
            )
        else:
            report["diagnosis"] = (
                "Instalacja Pythona nie udostępnia zgodnego Tcl/Tk albo wskazano błędne "
                "TCL_LIBRARY/TK_LIBRARY. Napraw tę samą dystrybucję Pythona."
            )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    report["status"] = "OK"
    report["diagnosis"] = "Python, Tcl/Tk i natywne okno działają poprawnie."
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
