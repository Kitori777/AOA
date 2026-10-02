from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class DiagnosticReport:
    created_at: str
    checks: tuple[DiagnosticCheck, ...]
    environment: dict[str, str]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "created_at": self.created_at,
            "ok": self.ok,
            "checks": [asdict(check) for check in self.checks],
            "environment": self.environment,
        }
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(target)
        return target


def run_diagnostics(
    *,
    data_dir: str | Path,
    config_dir: str | Path,
    queue_path: str | Path | None = None,
) -> DiagnosticReport:
    checks: list[DiagnosticCheck] = []
    for name, raw_path in (("data", data_dir), ("config", config_dir)):
        path = Path(raw_path).resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".aoa-write-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            checks.append(DiagnosticCheck(f"writable_{name}", True, str(path)))
        except OSError as exc:
            checks.append(DiagnosticCheck(f"writable_{name}", False, str(exc)))
    if queue_path:
        queue = Path(queue_path).resolve()
        if queue.is_file():
            digest = hashlib.sha256(queue.read_bytes()).hexdigest()
            checks.append(DiagnosticCheck("queue", True, f"sha256={digest[:16]}"))
        else:
            checks.append(DiagnosticCheck("queue", False, "Nie znaleziono pliku kolejki."))
    return DiagnosticReport(
        datetime.now(UTC).isoformat(),
        tuple(checks),
        {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "mode": "frozen" if getattr(sys, "frozen", False) else "source",
        },
    )
