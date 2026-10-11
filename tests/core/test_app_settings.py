from __future__ import annotations

from AOA.settings import AppSettings, load_settings, save_settings


def test_settings_round_trip_defaults_to_offline(tmp_path) -> None:
    path = tmp_path / "settings.json"
    defaults = load_settings(path)
    saved = AppSettings(
        theme="light",
        online_services_enabled=True,
        queue_csv_path="C:/factory/schedule.csv",
        queue_poll_seconds=3.0,
        queue_unavailable_machines="2|4",
    )
    save_settings(saved, path)

    assert defaults.online_services_enabled is False
    assert defaults.sync_enabled is False
    assert defaults.storage_provider == "local"
    assert defaults.app_mode == "engineering"
    assert defaults.sharepoint_site_url == ""
    assert load_settings(path) == saved
    assert load_settings(path).queue_unavailable_machines == "2|4"


def test_malformed_settings_degrade_to_safe_defaults(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")

    loaded = load_settings(path)

    assert loaded == AppSettings()
