from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RouteOperation:
    operation_id: str
    station_id: str
    allowed_machine_ids: tuple[str, ...] = ()

    def normalized(self) -> RouteOperation:
        operation_id = self.operation_id.strip() or self.station_id.strip()
        station_id = self.station_id.strip()
        if not station_id:
            raise ValueError("Operacja trasy musi wskazywac stanowisko.")
        machine_ids = tuple(dict.fromkeys(item.strip() for item in self.allowed_machine_ids if item.strip()))
        return RouteOperation(operation_id, station_id, machine_ids)

    def to_dict(self) -> dict[str, Any]:
        value = self.normalized()
        return {
            "operation_id": value.operation_id,
            "station_id": value.station_id,
            "allowed_machine_ids": list(value.allowed_machine_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RouteOperation:
        return cls(
            operation_id=str(payload.get("operation_id") or ""),
            station_id=str(payload.get("station_id") or ""),
            allowed_machine_ids=tuple(str(item) for item in payload.get("allowed_machine_ids", [])),
        ).normalized()


@dataclass(frozen=True)
class ProductRoute:
    product_id: str
    name: str
    operations: tuple[RouteOperation, ...]

    def normalized(self) -> ProductRoute:
        product_id = self.product_id.strip()
        if not product_id:
            raise ValueError("Trasa produktu musi miec identyfikator produktu.")
        operations = tuple(operation.normalized() for operation in self.operations)
        if not operations:
            raise ValueError(f"Produkt {product_id} musi miec przynajmniej jedna operacje.")
        station_ids = [operation.station_id for operation in operations]
        if len(station_ids) != len(set(station_ids)):
            raise ValueError(f"Trasa produktu {product_id} powtarza stanowisko.")
        return ProductRoute(product_id, self.name.strip() or product_id, operations)

    def to_dict(self) -> dict[str, Any]:
        value = self.normalized()
        return {
            "product_id": value.product_id,
            "name": value.name,
            "operations": [operation.to_dict() for operation in value.operations],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProductRoute:
        return cls(
            product_id=str(payload.get("product_id") or ""),
            name=str(payload.get("name") or ""),
            operations=tuple(
                RouteOperation.from_dict(item) for item in payload.get("operations", [])
            ),
        ).normalized()


@dataclass(frozen=True)
class ProductRoutingCatalog:
    routes: tuple[ProductRoute, ...] = ()

    def normalized(
        self,
        *,
        station_order: tuple[str, ...] = (),
        machine_ids: set[str] | None = None,
    ) -> ProductRoutingCatalog:
        routes = tuple(route.normalized() for route in self.routes)
        product_ids = [route.product_id for route in routes]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Identyfikatory produktow w trasach musza byc unikalne.")
        station_positions = {station_id: index for index, station_id in enumerate(station_order)}
        for route in routes:
            unknown_stations = [
                operation.station_id
                for operation in route.operations
                if station_order and operation.station_id not in station_positions
            ]
            if unknown_stations:
                raise ValueError(
                    f"Trasa produktu {route.product_id} wskazuje nieistniejace stanowiska: "
                    + ", ".join(unknown_stations)
                )
            positions = [station_positions[item.station_id] for item in route.operations]
            if station_order and positions != sorted(positions):
                raise ValueError(
                    f"Trasa produktu {route.product_id} nie zachowuje kolejnosci linii."
                )
            if machine_ids is not None:
                unknown_machines = sorted(
                    {
                        machine_id
                        for operation in route.operations
                        for machine_id in operation.allowed_machine_ids
                        if machine_id not in machine_ids
                    }
                )
                if unknown_machines:
                    raise ValueError(
                        f"Trasa produktu {route.product_id} wskazuje nieistniejace maszyny: "
                        + ", ".join(unknown_machines)
                    )
        return ProductRoutingCatalog(routes)

    def for_product(self, product_id: str) -> ProductRoute | None:
        return next((route for route in self.routes if route.product_id == product_id), None)

    def to_list(self) -> list[dict[str, Any]]:
        return [route.to_dict() for route in self.routes]

    @classmethod
    def from_list(cls, payload: Any) -> ProductRoutingCatalog:
        if payload is None:
            return cls()
        if not isinstance(payload, list):
            raise ValueError("Trasy produktow musza byc lista obiektow.")
        return cls(tuple(ProductRoute.from_dict(item) for item in payload))


def product_id_from_row(row: Any) -> str:
    for column in ("product_id", "produkt", "product", "typ_produktu"):
        value = row.get(column) if hasattr(row, "get") else None
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""
