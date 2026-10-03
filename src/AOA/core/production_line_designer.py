from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from AOA.core.machine_catalog import MachineCatalog, MachineSpec, build_default_machines
from AOA.core.product_routing import ProductRoute, ProductRoutingCatalog, RouteOperation
from AOA.core.production_line import ProductionLineSpec, StationSpec, validate_production_line

PROJECT_SCHEMA_VERSION = 3
DEFAULT_NODE_WIDTH = 210
DEFAULT_NODE_HEIGHT = 112


@dataclass(frozen=True)
class StationLayout:
    station_id: str
    x: int
    y: int
    width: int = DEFAULT_NODE_WIDTH
    height: int = DEFAULT_NODE_HEIGHT

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StationLayout:
        return cls(
            station_id=str(payload.get("station_id") or ""),
            x=max(0, int(payload.get("x", 80))),
            y=max(0, int(payload.get("y", 120))),
            width=max(140, int(payload.get("width", DEFAULT_NODE_WIDTH))),
            height=max(88, int(payload.get("height", DEFAULT_NODE_HEIGHT))),
        )


@dataclass(frozen=True)
class LineConnection:
    source: str
    target: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LineConnection:
        return cls(str(payload.get("source") or ""), str(payload.get("target") or ""))


def default_production_line_stations() -> list[StationSpec]:
    """Return a fresh, editable starter line for the desktop designer."""
    return [
        StationSpec(
            "S1",
            "Przygotowanie",
            1,
            "czas_produkcji_h * 0.25",
            "cena * 0.01",
            "odpad * 0.05",
            "quality * 0.995",
        ),
        StationSpec(
            "S2",
            "Produkcja",
            2,
            "czas_produkcji_h",
            "cena * 0.04",
            "odpad * 0.1",
            "quality * 0.98",
        ),
        StationSpec(
            "S3",
            "Kontrola i pakowanie",
            1,
            "max(0.5, prev_duration * 0.15)",
            "2",
            "0",
            "quality * 0.995",
        ),
    ]


@dataclass
class ProductionLineDraft:
    """Editable graph state shared by the GUI, persistence layer and tests."""

    line_id: str = "moja_linia"
    name: str = "Moja linia produkcyjna"
    stations: list[StationSpec] = field(default_factory=default_production_line_stations)
    selected_index: int | None = None
    layouts: dict[str, StationLayout] = field(default_factory=dict)
    connections: list[LineConnection] = field(default_factory=list)
    machines: list[MachineSpec] = field(default_factory=list)
    product_routes: list[ProductRoute] = field(default_factory=list)
    initialize_serial: bool = field(default=True, repr=False)

    def __post_init__(self) -> None:
        self.stations = [
            station.normalized(index) for index, station in enumerate(self.stations, 1)
        ]
        if not self.machines:
            self.machines = list(
                build_default_machines(
                    (station.station_id, station.name, station.resources)
                    for station in self.stations
                )
            )
        else:
            self.machines = list(
                MachineCatalog(tuple(self.machines))
                .normalized(station.station_id for station in self.stations)
                .machines
            )
        self.product_routes = list(ProductRoutingCatalog(tuple(self.product_routes)).routes)
        if not self.layouts:
            self.layouts = self._automatic_layouts(self.stations)
        else:
            self.layouts = dict(self.layouts)
            self._ensure_all_layouts()
        if self.initialize_serial and not self.connections:
            self.connections = self._serial_connections(self.stations)
        else:
            self.connections = list(dict.fromkeys(self.connections))

    @classmethod
    def from_spec(cls, spec: ProductionLineSpec) -> ProductionLineDraft:
        normalized = spec.normalized()
        return cls(
            normalized.line_id,
            normalized.name,
            list(normalized.stations),
            machines=list(normalized.machines),
            product_routes=list(normalized.product_routes),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProductionLineDraft:
        if not isinstance(payload, dict):
            raise ValueError("Projekt linii produkcyjnej musi zawierac obiekt JSON.")
        raw_schema_version = payload.get("schema_version")
        if raw_schema_version is not None:
            if isinstance(raw_schema_version, bool):
                raise ValueError("Wersja formatu projektu linii musi byc liczba calkowita.")
            try:
                schema_version = int(raw_schema_version)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Wersja formatu projektu linii musi byc liczba calkowita."
                ) from exc
            if schema_version < 1:
                raise ValueError("Wersja formatu projektu linii musi byc dodatnia.")
            if schema_version > PROJECT_SCHEMA_VERSION:
                raise ValueError(
                    f"Projekt uzywa nowszego formatu {schema_version}; "
                    f"ta wersja AOA obsluguje maksymalnie {PROJECT_SCHEMA_VERSION}."
                )
        spec = ProductionLineSpec.from_dict(payload)
        raw_layouts = payload.get("layout")
        raw_connections = payload.get("connections")
        if raw_layouts is None and raw_connections is None:
            return cls.from_spec(spec)
        if not isinstance(raw_layouts, list) or not isinstance(raw_connections, list):
            raise ValueError("Graficzny projekt linii ma nieprawidlowy uklad lub polaczenia.")
        layouts = {}
        for item in raw_layouts:
            if not isinstance(item, dict):
                raise ValueError("Uklad stanowisk musi byc lista obiektow.")
            layout = StationLayout.from_dict(item)
            if layout.station_id:
                layouts[layout.station_id] = layout
        connections = []
        for item in raw_connections:
            if not isinstance(item, dict):
                raise ValueError("Polaczenia stanowisk musza byc lista obiektow.")
            connection = LineConnection.from_dict(item)
            if connection.source and connection.target:
                connections.append(connection)
        return cls(
            spec.line_id,
            spec.name,
            list(spec.stations),
            layouts=layouts,
            connections=connections,
            machines=list(spec.machines),
            product_routes=list(spec.product_routes),
            initialize_serial=False,
        )

    def to_dict(self) -> dict[str, Any]:
        self._ensure_all_layouts()
        return {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "line_id": self.line_id,
            "name": self.name,
            "stations": [asdict(station) for station in self.stations],
            "machines": [machine.to_dict() for machine in self.machines],
            "product_routes": [route.to_dict() for route in self.product_routes],
            "layout": [asdict(self.layouts[station.station_id]) for station in self.stations],
            "connections": [asdict(connection) for connection in self.connections],
        }

    @property
    def selected_station(self) -> StationSpec | None:
        if self.selected_index is None or self.selected_index >= len(self.stations):
            return None
        return self.stations[self.selected_index]

    def select(self, index: int) -> StationSpec:
        if index < 0 or index >= len(self.stations):
            raise IndexError("Nieprawidlowy numer stanowiska.")
        self.selected_index = index
        return self.stations[index]

    def select_by_id(self, station_id: str) -> StationSpec:
        index = self._station_index(station_id)
        return self.select(index)

    def new_station_template(self) -> StationSpec:
        self.selected_index = None
        next_index = len(self.stations) + 1
        return StationSpec(self._unique_station_id(f"S{next_index}"), f"Stanowisko {next_index}")

    def add_station(
        self,
        station: StationSpec,
        *,
        x: int | None = None,
        y: int | None = None,
        auto_connect: bool = False,
    ) -> int:
        normalized = station.normalized(len(self.stations) + 1)
        if normalized.station_id in self.station_ids:
            raise ValueError("Identyfikatory stanowisk musza byc unikalne.")
        previous = self.stations[-1].station_id if self.stations else None
        self.stations.append(normalized)
        self.machines.extend(
            build_default_machines(
                [(normalized.station_id, normalized.name, normalized.resources)]
            )
        )
        default_x = 80 + (len(self.stations) - 1) * 260
        self.layouts[normalized.station_id] = StationLayout(
            normalized.station_id,
            default_x if x is None else max(0, int(x)),
            140 if y is None else max(0, int(y)),
        )
        if auto_connect and previous:
            self.connections.append(LineConnection(previous, normalized.station_id))
        self.selected_index = len(self.stations) - 1
        return self.selected_index

    def save_station(
        self,
        station: StationSpec,
        *,
        columns: list[str] | None = None,
        line_id: str | None = None,
        name: str | None = None,
    ) -> int:
        candidate_line_id = line_id or self.line_id
        candidate_name = name or self.name
        if self.selected_index is None:
            normalized = station.normalized(len(self.stations) + 1)
            if normalized.station_id in self.station_ids:
                raise ValueError("Identyfikatory stanowisk musza byc unikalne.")
            candidate_machines = [
                *self.machines,
                *build_default_machines(
                    [(normalized.station_id, normalized.name, normalized.resources)]
                ),
            ]
            validate_production_line(
                ProductionLineSpec(
                    candidate_line_id,
                    candidate_name,
                    tuple([*self.stations, normalized]),
                    tuple(candidate_machines),
                    tuple(self.product_routes),
                ),
                columns,
            )
            selected_index = self.add_station(normalized, auto_connect=True)
        else:
            selected_index = self.update_selected_station(station, columns=columns)
        self.line_id = candidate_line_id
        self.name = candidate_name
        return selected_index

    def update_selected_station(
        self,
        station: StationSpec,
        *,
        columns: list[str] | None = None,
    ) -> int:
        if self.selected_index is None:
            raise ValueError("Najpierw zaznacz stanowisko na diagramie.")
        old_station = self.stations[self.selected_index]
        normalized = station.normalized(self.selected_index + 1)
        duplicate_ids = self.station_ids - {old_station.station_id}
        if normalized.station_id in duplicate_ids:
            raise ValueError("Identyfikatory stanowisk musza byc unikalne.")
        candidate = list(self.stations)
        candidate[self.selected_index] = normalized
        validate_production_line(
            ProductionLineSpec(
                self.line_id,
                self.name,
                tuple(candidate),
                tuple(self._reconciled_machines(old_station, normalized)),
                tuple(self.product_routes),
            ),
            columns,
        )
        self.stations = candidate
        self.machines = self._reconciled_machines(old_station, normalized)
        if normalized.station_id != old_station.station_id:
            layout = self.layouts.pop(old_station.station_id)
            self.layouts[normalized.station_id] = StationLayout(
                normalized.station_id,
                layout.x,
                layout.y,
                layout.width,
                layout.height,
            )
            self.connections = [
                LineConnection(
                    normalized.station_id if edge.source == old_station.station_id else edge.source,
                    normalized.station_id if edge.target == old_station.station_id else edge.target,
                )
                for edge in self.connections
            ]
            self.product_routes = [
                ProductRoute(
                    route.product_id,
                    route.name,
                    tuple(
                        RouteOperation(
                            operation.operation_id,
                            normalized.station_id
                            if operation.station_id == old_station.station_id
                            else operation.station_id,
                            operation.allowed_machine_ids,
                        )
                        for operation in route.operations
                    ),
                )
                for route in self.product_routes
            ]
        return self.selected_index

    def move_selected(self, direction: int) -> bool:
        if self.selected_index is None:
            return False
        target = self.selected_index + direction
        if target < 0 or target >= len(self.stations):
            return False
        self.stations[self.selected_index], self.stations[target] = (
            self.stations[target],
            self.stations[self.selected_index],
        )
        self.selected_index = target
        self.connections = self._serial_connections(self.stations)
        return True

    def move_station(self, station_id: str, x: int, y: int) -> None:
        self._station_index(station_id)
        layout = self.layouts[station_id]
        self.layouts[station_id] = StationLayout(
            station_id,
            max(0, int(x)),
            max(0, int(y)),
            layout.width,
            layout.height,
        )

    def delete_selected(self) -> StationSpec | None:
        station = self.selected_station
        selected_index = self.selected_index
        if station is None or selected_index is None:
            return None
        removed = self.stations.pop(selected_index)
        removed_machine_ids = {
            machine.machine_id for machine in self.machines if machine.station_id == removed.station_id
        }
        self.machines = [
            machine for machine in self.machines if machine.station_id != removed.station_id
        ]
        self.product_routes = [
            ProductRoute(
                route.product_id,
                route.name,
                tuple(
                    RouteOperation(
                        operation.operation_id,
                        operation.station_id,
                        tuple(
                            machine_id
                            for machine_id in operation.allowed_machine_ids
                            if machine_id not in removed_machine_ids
                        ),
                    )
                    for operation in route.operations
                    if operation.station_id != removed.station_id
                ),
            )
            for route in self.product_routes
            if any(operation.station_id != removed.station_id for operation in route.operations)
        ]
        self.layouts.pop(removed.station_id, None)
        self.connections = [
            edge
            for edge in self.connections
            if edge.source != removed.station_id and edge.target != removed.station_id
        ]
        self.selected_index = None
        return removed

    def connect(self, source: str, target: str) -> None:
        self._station_index(source)
        self._station_index(target)
        if source == target:
            raise ValueError("Stanowisko nie moze byc polaczone samo ze soba.")
        edge = LineConnection(source, target)
        if edge in self.connections:
            return
        if any(item.source == source for item in self.connections):
            raise ValueError(f"Stanowisko {source} ma juz polaczenie wyjsciowe.")
        if any(item.target == target for item in self.connections):
            raise ValueError(f"Stanowisko {target} ma juz polaczenie wejsciowe.")
        candidate = [*self.connections, edge]
        if self._contains_cycle(candidate):
            raise ValueError("Polaczenie utworzyloby cykl w linii produkcyjnej.")
        self.connections = candidate

    def disconnect(self, source: str, target: str) -> bool:
        edge = LineConnection(source, target)
        if edge not in self.connections:
            return False
        self.connections.remove(edge)
        return True

    def disconnect_station(self, station_id: str) -> int:
        before = len(self.connections)
        self.connections = [
            edge
            for edge in self.connections
            if edge.source != station_id and edge.target != station_id
        ]
        return before - len(self.connections)

    def load_spec(self, spec: ProductionLineSpec) -> None:
        replacement = ProductionLineDraft.from_spec(spec)
        self._replace_with(replacement)

    def load_project(self, project: ProductionLineDraft) -> None:
        self._replace_with(project)

    def auto_layout(self) -> None:
        try:
            order = self.ordered_station_ids()
        except ValueError:
            order = [station.station_id for station in self.stations]
        for index, station_id in enumerate(order):
            layout = self.layouts[station_id]
            self.layouts[station_id] = StationLayout(
                station_id,
                80 + index * 260,
                140,
                layout.width,
                layout.height,
            )

    def ordered_station_ids(self) -> list[str]:
        if not self.stations:
            raise ValueError("Linia produkcyjna musi zawierac przynajmniej jedno stanowisko.")
        if len(self.stations) == 1:
            if self.connections:
                raise ValueError("Pojedyncze stanowisko nie moze miec polaczen.")
            return [self.stations[0].station_id]
        if len(self.connections) != len(self.stations) - 1:
            raise ValueError("Polacz wszystkie stanowiska w jedna sciezke produkcyjna.")
        incoming = {station.station_id: 0 for station in self.stations}
        outgoing: dict[str, list[str]] = {station.station_id: [] for station in self.stations}
        for edge in self.connections:
            if edge.source not in outgoing or edge.target not in incoming:
                raise ValueError("Polaczenie wskazuje nieistniejace stanowisko.")
            incoming[edge.target] += 1
            outgoing[edge.source].append(edge.target)
        if any(value > 1 for value in incoming.values()) or any(
            len(value) > 1 for value in outgoing.values()
        ):
            raise ValueError("Linia szeregowa nie moze zawierac rozgalezien.")
        starts = [station_id for station_id, count in incoming.items() if count == 0]
        ends = [station_id for station_id, targets in outgoing.items() if not targets]
        if len(starts) != 1 or len(ends) != 1:
            raise ValueError("Linia musi miec jedno wejscie i jedno wyjscie.")
        order: list[str] = []
        current = starts[0]
        while current not in order:
            order.append(current)
            targets = outgoing[current]
            if not targets:
                break
            current = targets[0]
        if len(order) != len(self.stations):
            raise ValueError("Linia zawiera cykl albo odlaczone stanowisko.")
        return order

    def graph_status(self) -> tuple[bool, str]:
        try:
            order = self.ordered_station_ids()
        except ValueError as exc:
            return False, str(exc)
        return True, f"Linia gotowa: {' -> '.join(order)}"

    def to_spec(
        self,
        *,
        columns: list[str] | None = None,
        line_id: str | None = None,
        name: str | None = None,
    ) -> ProductionLineSpec:
        self.line_id = line_id or self.line_id
        self.name = name or self.name
        station_by_id = {station.station_id: station for station in self.stations}
        ordered_stations = tuple(
            station_by_id[station_id] for station_id in self.ordered_station_ids()
        )
        return validate_production_line(
            ProductionLineSpec(
                self.line_id,
                self.name,
                ordered_stations,
                tuple(self.machines),
                tuple(self.product_routes),
            ),
            columns,
        )

    def set_machines(self, machines: list[MachineSpec]) -> None:
        self.set_configuration(machines, self.product_routes)

    def set_configuration(
        self,
        machines: list[MachineSpec],
        routes: list[ProductRoute],
    ) -> None:
        catalog = MachineCatalog(tuple(machines)).normalized(self.station_ids)
        counts = {
            station.station_id: len(catalog.for_station(station.station_id))
            for station in self.stations
        }
        missing = [station.name for station in self.stations if counts[station.station_id] == 0]
        if missing:
            raise ValueError("Kazde stanowisko musi miec maszyne: " + ", ".join(missing))
        updated_stations = [
            StationSpec(
                station.station_id,
                station.name,
                counts[station.station_id],
                station.duration_formula,
                station.cost_formula,
                station.waste_formula,
                station.quality_formula,
            )
            for station in self.stations
        ]
        route_catalog = ProductRoutingCatalog(tuple(routes)).normalized(
            station_order=tuple(self.ordered_station_ids()),
            machine_ids={machine.machine_id for machine in catalog.machines},
        )
        self.machines = list(catalog.machines)
        self.stations = updated_stations
        self.product_routes = list(route_catalog.routes)

    def set_product_routes(self, routes: list[ProductRoute]) -> None:
        self.set_configuration(self.machines, routes)

    @property
    def station_ids(self) -> set[str]:
        return {station.station_id for station in self.stations}

    def _replace_with(self, replacement: ProductionLineDraft) -> None:
        self.line_id = replacement.line_id
        self.name = replacement.name
        self.stations = list(replacement.stations)
        self.layouts = dict(replacement.layouts)
        self.connections = list(replacement.connections)
        self.machines = list(replacement.machines)
        self.product_routes = list(replacement.product_routes)
        self.selected_index = None

    def _reconciled_machines(
        self,
        previous: StationSpec,
        replacement: StationSpec,
    ) -> list[MachineSpec]:
        station_machines = [
            machine for machine in self.machines if machine.station_id == previous.station_id
        ]
        others = [machine for machine in self.machines if machine.station_id != previous.station_id]
        kept = [
            MachineSpec(
                machine.machine_id,
                machine.name,
                replacement.station_id,
                machine.speed_factor,
                machine.waste_factor,
                machine.energy_kwh_per_hour,
                machine.cost_per_hour,
                machine.setup_time_h,
                machine.planned_hours_h,
                machine.capability,
                machine.reliability,
            ).normalized(index)
            for index, machine in enumerate(station_machines[: replacement.resources], 1)
        ]
        used_ids = {machine.machine_id for machine in [*others, *kept]}
        next_index = 1
        while len(kept) < replacement.resources:
            candidate = f"{replacement.station_id}:M{next_index}"
            next_index += 1
            if candidate in used_ids:
                continue
            generated = build_default_machines(
                [(replacement.station_id, replacement.name, 1)]
            )[0]
            kept.append(
                MachineSpec(
                    candidate,
                    f"{replacement.name} — maszyna {len(kept) + 1}",
                    replacement.station_id,
                    capability=generated.capability,
                ).normalized(len(kept) + 1)
            )
            used_ids.add(candidate)
        return [*others, *kept]

    def _station_index(self, station_id: str) -> int:
        for index, station in enumerate(self.stations):
            if station.station_id == station_id:
                return index
        raise ValueError(f"Nie istnieje stanowisko: {station_id}.")

    def _unique_station_id(self, candidate: str) -> str:
        if candidate not in self.station_ids:
            return candidate
        index = len(self.stations) + 1
        while f"S{index}" in self.station_ids:
            index += 1
        return f"S{index}"

    def _ensure_all_layouts(self) -> None:
        valid_ids = self.station_ids
        self.layouts = {
            station_id: layout
            for station_id, layout in self.layouts.items()
            if station_id in valid_ids
        }
        for index, station in enumerate(self.stations):
            if station.station_id not in self.layouts:
                self.layouts[station.station_id] = StationLayout(
                    station.station_id,
                    80 + index * 260,
                    140,
                )

    @staticmethod
    def _automatic_layouts(stations: list[StationSpec]) -> dict[str, StationLayout]:
        return {
            station.station_id: StationLayout(station.station_id, 80 + index * 260, 140)
            for index, station in enumerate(stations)
        }

    @staticmethod
    def _serial_connections(stations: list[StationSpec]) -> list[LineConnection]:
        return [
            LineConnection(stations[index].station_id, stations[index + 1].station_id)
            for index in range(len(stations) - 1)
        ]

    @staticmethod
    def _contains_cycle(connections: list[LineConnection]) -> bool:
        outgoing = {edge.source: edge.target for edge in connections}
        for start in outgoing:
            visited: set[str] = set()
            current = start
            while current in outgoing:
                if current in visited:
                    return True
                visited.add(current)
                current = outgoing[current]
        return False
