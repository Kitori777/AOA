from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

READY = "READY"
WAITING_COMPONENTS = "WAITING_COMPONENTS"
UNSCHEDULABLE = "UNSCHEDULABLE"


@dataclass(frozen=True)
class ComponentRequirement:
    product_id: str
    component_sku: str
    quantity_per_unit: float


@dataclass
class InventoryLot:
    lot_id: str
    component_sku: str
    quantity: float
    available_at_h: float
    source: str = "stock"


def _required_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label}: brak kolumn: {', '.join(missing)}")


def _validated_bom(frame: pd.DataFrame) -> list[ComponentRequirement]:
    _required_columns(
        frame,
        {"produkt_id", "component_sku", "quantity_per_unit"},
        "BOM",
    )
    requirements: list[ComponentRequirement] = []
    for row in frame.itertuples(index=False):
        product_id = str(row.produkt_id).strip()
        component_sku = str(row.component_sku).strip()
        quantity = float(row.quantity_per_unit)
        if not product_id or not component_sku or quantity <= 0:
            raise ValueError("BOM zawiera pusty identyfikator lub niedodatnia ilosc.")
        requirements.append(ComponentRequirement(product_id, component_sku, quantity))
    return requirements


def _validated_inventory(frame: pd.DataFrame) -> list[InventoryLot]:
    _required_columns(
        frame,
        {"component_sku", "quantity", "available_at_h"},
        "Magazyn",
    )
    lots: list[InventoryLot] = []
    for index, row in enumerate(frame.itertuples(index=False), start=1):
        component_sku = str(row.component_sku).strip()
        quantity = float(row.quantity)
        available_at_h = float(row.available_at_h)
        if not component_sku or quantity < 0 or available_at_h < 0:
            raise ValueError("Magazyn zawiera pusty SKU albo ujemna ilosc/czas dostawy.")
        lots.append(
            InventoryLot(
                lot_id=str(getattr(row, "lot_id", f"LOT-{index:05d}")),
                component_sku=component_sku,
                quantity=quantity,
                available_at_h=available_at_h,
                source=str(getattr(row, "source", "stock")),
            )
        )
    return lots


def annotate_component_readiness(
    orders: pd.DataFrame,
    bom: pd.DataFrame | None,
    inventory: pd.DataFrame | None,
    *,
    product_col: str = "produkt_id",
    quantity_col: str = "ilosc_szt",
) -> pd.DataFrame:
    """Reserve component lots in order sequence and calculate material release times.

    Lots are consumed FIFO by availability time. A future delivery may be reserved,
    so an order receives the hour at which its last required component is available.
    """

    if orders is None or orders.empty:
        raise ValueError("Brak zamowien do analizy komponentow.")
    out = orders.copy().reset_index(drop=True)
    if bom is None or inventory is None:
        return _add_legacy_ready_defaults(out)
    if bom.empty:
        return _add_legacy_ready_defaults(out)
    if product_col not in out.columns or quantity_col not in out.columns:
        return _add_legacy_ready_defaults(out)

    requirements_by_product: dict[str, list[ComponentRequirement]] = defaultdict(list)
    for requirement in _validated_bom(bom):
        requirements_by_product[requirement.product_id].append(requirement)

    lots_by_sku: dict[str, list[InventoryLot]] = defaultdict(list)
    for lot in _validated_inventory(inventory):
        lots_by_sku[lot.component_sku].append(lot)
    for lots in lots_by_sku.values():
        lots.sort(key=lambda lot: (lot.available_at_h, lot.lot_id))

    ready_values: list[float] = []
    wait_values: list[float] = []
    missing_values: list[str] = []
    status_values: list[str] = []
    reservation_values: list[str] = []

    for _, row in out.iterrows():
        product_id = str(row[product_col]).strip()
        order_quantity = float(row[quantity_col])
        if order_quantity <= 0:
            raise ValueError("Ilosc zamowienia musi byc dodatnia.")
        requirements = requirements_by_product.get(product_id, [])
        if not requirements:
            ready_values.append(0.0)
            wait_values.append(0.0)
            missing_values.append("")
            status_values.append(READY)
            reservation_values.append("[]")
            continue

        needs: dict[str, float] = defaultdict(float)
        for requirement in requirements:
            needs[requirement.component_sku] += requirement.quantity_per_unit * order_quantity

        missing: list[str] = []
        planned: dict[str, list[tuple[InventoryLot, float]]] = {}
        ready_at = 0.0
        for sku, required_quantity in sorted(needs.items()):
            remaining = required_quantity
            allocations: list[tuple[InventoryLot, float]] = []
            for lot in lots_by_sku.get(sku, []):
                if lot.quantity <= 1e-9:
                    continue
                used = min(lot.quantity, remaining)
                allocations.append((lot, used))
                remaining -= used
                ready_at = max(ready_at, lot.available_at_h)
                if remaining <= 1e-9:
                    break
            if remaining > 1e-9:
                missing.append(f"{sku}:{remaining:.4f}")
            planned[sku] = allocations

        if missing:
            ready_values.append(float("nan"))
            wait_values.append(float("nan"))
            missing_values.append("|".join(missing))
            status_values.append(UNSCHEDULABLE)
            reservation_values.append("[]")
            continue

        reservations: list[dict[str, object]] = []
        for sku in sorted(planned):
            for lot, used in planned[sku]:
                lot.quantity -= used
                reservations.append(
                    {
                        "sku": sku,
                        "lot_id": lot.lot_id,
                        "quantity": round(used, 4),
                        "available_at_h": round(lot.available_at_h, 3),
                    }
                )
        ready_values.append(round(ready_at, 3))
        wait_values.append(round(max(0.0, ready_at), 3))
        missing_values.append("")
        status_values.append(READY if ready_at <= 0 else WAITING_COMPONENTS)
        reservation_values.append(json.dumps(reservations, ensure_ascii=False, separators=(",", ":")))

    out["components_ready_h"] = ready_values
    out["material_wait_h"] = wait_values
    out["missing_components"] = missing_values
    out["stock_status"] = status_values
    out["stock_reservation"] = reservation_values
    return out


def _add_legacy_ready_defaults(frame: pd.DataFrame) -> pd.DataFrame:
    frame["components_ready_h"] = 0.0
    frame["material_wait_h"] = 0.0
    frame["missing_components"] = ""
    frame["stock_status"] = READY
    frame["stock_reservation"] = "[]"
    return frame
