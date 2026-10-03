from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from AOA.core.machine_catalog import (
    MachineCapability,
    MachineCatalog,
    MachineSpec,
    ReliabilitySpec,
)
from AOA.core.scheduling import build_machine_profiles

QUEUE_MACHINE_SCHEMA_VERSION = 1


def queue_machine_config_path(queue_path: str | Path) -> Path:
    path = Path(queue_path).resolve()
    return path.with_suffix(path.suffix + ".machines.json")


def default_queue_machines(machine_count: int) -> tuple[MachineSpec, ...]:
    profiles = build_machine_profiles(machine_count)
    return tuple(
        MachineSpec(
            machine_id=f"QUEUE:M{profile.machine_id}",
            name=f"Auto Queue — maszyna {profile.machine_id}",
            station_id="QUEUE",
            speed_factor=profile.speed_factor,
            waste_factor=profile.waste_factor,
            energy_kwh_per_hour=profile.energy_kwh_per_hour,
            capability=MachineCapability(materials=profile.supported_materials),
            reliability=ReliabilitySpec(
                mtbf_h=80.0,
                mttr_h=2.0,
                post_changeover_failure_probability=0.03,
                post_changeover_risk_window_h=2.0,
                post_changeover_downtime_h=1.0,
            ),
        ).normalized(index)
        for index, profile in enumerate(profiles, 1)
    )


def load_queue_machines(
    queue_path: str | Path,
    machine_count: int,
) -> tuple[MachineSpec, ...]:
    target = queue_machine_config_path(queue_path)
    if not target.is_file():
        return default_queue_machines(machine_count)
    payload: Any = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Plik profili maszyn Auto Queue musi zawierac obiekt JSON.")
    version = int(payload.get("schema_version", 0))
    if version != QUEUE_MACHINE_SCHEMA_VERSION:
        raise ValueError(f"Nieobslugiwana wersja profili maszyn Auto Queue: {version}.")
    loaded = list(MachineCatalog.from_list(payload.get("machines")).machines)
    defaults = default_queue_machines(machine_count)
    if len(loaded) < machine_count:
        used = {machine.machine_id for machine in loaded}
        for machine in defaults:
            if len(loaded) >= machine_count:
                break
            if machine.machine_id not in used:
                loaded.append(machine)
                used.add(machine.machine_id)
    return tuple(loaded[:machine_count])


def save_queue_machines(
    queue_path: str | Path,
    machines: tuple[MachineSpec, ...] | list[MachineSpec],
) -> Path:
    catalog = MachineCatalog(tuple(machines)).normalized({"QUEUE"})
    if not 1 <= len(catalog.machines) <= 8:
        raise ValueError("Auto Queue wymaga od 1 do 8 profili maszyn.")
    target = queue_machine_config_path(queue_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": QUEUE_MACHINE_SCHEMA_VERSION,
        "machines": catalog.to_list(),
    }
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
    return target
