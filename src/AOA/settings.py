from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from AOA.config import CONFIG_DIR

SETTINGS_VERSION = 5


@dataclass(frozen=True)
class AppSettings:
    version: int = SETTINGS_VERSION
    theme: str = "dark"
    storage_provider: str = "local"
    online_services_enabled: bool = False
    queue_csv_path: str = ""
    queue_poll_seconds: float = 2.0
    queue_objective: str = "deadline_then_waste"
    queue_unavailable_machines: str = ""
    queue_planning_mode: str = "continuous"
    queue_week_start_hour: int = 6
    queue_workdays: int = 5
    queue_workday_hours: float = 8.0
    queue_timezone: str = "Europe/Warsaw"
    sync_enabled: bool = False
    sharepoint_site_url: str = ""
    sharepoint_library: str = ""
    sync_prefix: str = "queues"
    history_retention: int = 50
    backup_retention: int = 10


def load_settings(path: Path | None = None) -> AppSettings:
    settings_path = path or CONFIG_DIR / "settings.json"
    if not settings_path.exists():
        return AppSettings()
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return AppSettings()
    if not isinstance(payload, dict):
        return AppSettings()
    allowed = {field.name for field in fields(AppSettings)}
    values = {key: value for key, value in payload.items() if key in allowed}
    try:
        return AppSettings(**values)
    except TypeError:
        return AppSettings()


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    settings_path = path or CONFIG_DIR / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = settings_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    temporary.replace(settings_path)
    return settings_path
