from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


def _identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip()).strip("_")
    return (cleaned or fallback)[:80]


def _machine_identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_:-]+", "_", str(value).strip()).strip("_")
    return (cleaned or fallback)[:80]


def _string_set(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        parts = value.replace(";", "|").replace(",", "|").split("|")
    else:
        parts = value
    return frozenset(str(item).strip() for item in parts if str(item).strip())


def _finite_non_negative(value: float, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} musi byc skonczona liczba nieujemna.")
    return number


@dataclass(frozen=True)
class ReliabilitySpec:
    """Failure parameters expressed in production hours.

    A zero MTBF disables spontaneous failures. Post-changeover risk is evaluated
    only when an operation contains a positive setup time.
    """

    mtbf_h: float = 0.0
    mttr_h: float = 0.0
    post_changeover_failure_probability: float = 0.0
    post_changeover_risk_window_h: float = 0.0
    post_changeover_downtime_h: float = 0.0

    def normalized(self) -> ReliabilitySpec:
        mtbf = _finite_non_negative(self.mtbf_h, "MTBF")
        mttr = _finite_non_negative(self.mttr_h, "MTTR")
        probability = float(self.post_changeover_failure_probability)
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("Prawdopodobienstwo awarii po przezbrojeniu musi byc w zakresie 0..1.")
        risk_window = _finite_non_negative(
            self.post_changeover_risk_window_h, "Okno ryzyka po przezbrojeniu"
        )
        downtime = _finite_non_negative(
            self.post_changeover_downtime_h, "Przestoj po przezbrojeniu"
        )
        if mtbf > 0 and mttr <= 0:
            raise ValueError("Dla aktywnego MTBF czas naprawy MTTR musi byc wiekszy od zera.")
        return ReliabilitySpec(mtbf, mttr, probability, risk_window, downtime)

    def to_dict(self) -> dict[str, float]:
        value = self.normalized()
        return {
            "mtbf_h": value.mtbf_h,
            "mttr_h": value.mttr_h,
            "post_changeover_failure_probability": value.post_changeover_failure_probability,
            "post_changeover_risk_window_h": value.post_changeover_risk_window_h,
            "post_changeover_downtime_h": value.post_changeover_downtime_h,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> ReliabilitySpec:
        values = payload or {}
        return cls(
            mtbf_h=float(values.get("mtbf_h", 0.0)),
            mttr_h=float(values.get("mttr_h", 0.0)),
            post_changeover_failure_probability=float(
                values.get("post_changeover_failure_probability", 0.0)
            ),
            post_changeover_risk_window_h=float(
                values.get("post_changeover_risk_window_h", 0.0)
            ),
            post_changeover_downtime_h=float(
                values.get("post_changeover_downtime_h", 0.0)
            ),
        ).normalized()


@dataclass(frozen=True)
class MachineCapability:
    products: frozenset[str] = frozenset()
    materials: frozenset[str] = frozenset()
    operations: frozenset[str] = frozenset()

    def normalized(self) -> MachineCapability:
        return MachineCapability(
            _string_set(self.products),
            _string_set(self.materials),
            _string_set(self.operations),
        )

    def accepts(self, *, product: str = "", material: str = "", operation: str = "") -> bool:
        value = self.normalized()
        return (
            (not value.products or not product or product in value.products)
            and (not value.materials or not material or material in value.materials)
            and (not value.operations or not operation or operation in value.operations)
        )

    def to_dict(self) -> dict[str, list[str]]:
        value = self.normalized()
        return {
            "products": sorted(value.products),
            "materials": sorted(value.materials),
            "operations": sorted(value.operations),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> MachineCapability:
        values = payload or {}
        return cls(
            products=_string_set(values.get("products")),
            materials=_string_set(values.get("materials")),
            operations=_string_set(values.get("operations")),
        ).normalized()


@dataclass(frozen=True)
class MachineSpec:
    machine_id: str
    name: str
    station_id: str
    speed_factor: float = 1.0
    waste_factor: float = 1.0
    energy_kwh_per_hour: float = 0.0
    cost_per_hour: float = 0.0
    setup_time_h: float = 0.0
    planned_hours_h: float = 0.0
    capability: MachineCapability = MachineCapability()
    reliability: ReliabilitySpec = ReliabilitySpec()

    def normalized(self, fallback_index: int = 1) -> MachineSpec:
        speed = float(self.speed_factor)
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("Wspolczynnik predkosci maszyny musi byc wiekszy od zera.")
        station_id = _identifier(self.station_id, "S1")
        machine_id = _machine_identifier(self.machine_id, f"{station_id}:M{fallback_index}")
        return MachineSpec(
            machine_id=machine_id,
            name=self.name.strip() or machine_id,
            station_id=station_id,
            speed_factor=speed,
            waste_factor=_finite_non_negative(self.waste_factor, "Wspolczynnik odpadu"),
            energy_kwh_per_hour=_finite_non_negative(
                self.energy_kwh_per_hour, "Zuzycie energii"
            ),
            cost_per_hour=_finite_non_negative(self.cost_per_hour, "Koszt godziny"),
            setup_time_h=_finite_non_negative(self.setup_time_h, "Czas przezbrojenia"),
            planned_hours_h=_finite_non_negative(self.planned_hours_h, "Planowany czas pracy"),
            capability=self.capability.normalized(),
            reliability=self.reliability.normalized(),
        )

    def to_dict(self) -> dict[str, Any]:
        value = self.normalized()
        return {
            "machine_id": value.machine_id,
            "name": value.name,
            "station_id": value.station_id,
            "speed_factor": value.speed_factor,
            "waste_factor": value.waste_factor,
            "energy_kwh_per_hour": value.energy_kwh_per_hour,
            "cost_per_hour": value.cost_per_hour,
            "setup_time_h": value.setup_time_h,
            "planned_hours_h": value.planned_hours_h,
            "capability": value.capability.to_dict(),
            "reliability": value.reliability.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MachineSpec:
        return cls(
            machine_id=str(payload.get("machine_id") or ""),
            name=str(payload.get("name") or ""),
            station_id=str(payload.get("station_id") or ""),
            speed_factor=float(payload.get("speed_factor", 1.0)),
            waste_factor=float(payload.get("waste_factor", 1.0)),
            energy_kwh_per_hour=float(payload.get("energy_kwh_per_hour", 0.0)),
            cost_per_hour=float(payload.get("cost_per_hour", 0.0)),
            setup_time_h=float(payload.get("setup_time_h", 0.0)),
            planned_hours_h=float(payload.get("planned_hours_h", 0.0)),
            capability=MachineCapability.from_dict(payload.get("capability")),
            reliability=ReliabilitySpec.from_dict(payload.get("reliability")),
        ).normalized()


@dataclass(frozen=True)
class MachineCatalog:
    machines: tuple[MachineSpec, ...]

    def normalized(self, station_ids: Iterable[str] | None = None) -> MachineCatalog:
        normalized = tuple(
            machine.normalized(index) for index, machine in enumerate(self.machines, 1)
        )
        identifiers = [machine.machine_id for machine in normalized]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Identyfikatory maszyn musza byc unikalne.")
        allowed_stations = set(station_ids or ())
        unknown = sorted(
            {machine.station_id for machine in normalized if allowed_stations}
            - allowed_stations
        )
        if unknown:
            raise ValueError("Maszyny wskazuja nieistniejace stanowiska: " + ", ".join(unknown))
        return MachineCatalog(normalized)

    def for_station(self, station_id: str) -> tuple[MachineSpec, ...]:
        return tuple(machine for machine in self.machines if machine.station_id == station_id)

    def to_list(self) -> list[dict[str, Any]]:
        return [machine.to_dict() for machine in self.machines]

    @classmethod
    def from_list(cls, payload: Any) -> MachineCatalog:
        if payload is None:
            return cls(())
        if not isinstance(payload, list):
            raise ValueError("Katalog maszyn musi byc lista obiektow.")
        return cls(tuple(MachineSpec.from_dict(item) for item in payload)).normalized()


def build_default_machines(
    stations: Iterable[tuple[str, str, int]],
) -> tuple[MachineSpec, ...]:
    machines: list[MachineSpec] = []
    for station_id, station_name, resources in stations:
        for index in range(1, int(resources) + 1):
            machines.append(
                MachineSpec(
                    machine_id=f"{station_id}:M{index}",
                    name=f"{station_name} — maszyna {index}",
                    station_id=station_id,
                    capability=MachineCapability(operations=frozenset({station_id})),
                ).normalized(index)
            )
    return tuple(machines)
