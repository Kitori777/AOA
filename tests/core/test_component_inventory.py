import json

import pandas as pd
import pytest

from AOA.core.component_inventory import (
    READY,
    UNSCHEDULABLE,
    WAITING_COMPONENTS,
    annotate_component_readiness,
)
from AOA.core.data_generation import generate_component_data, generate_production_data
from AOA.core.models import save_model_pack
from AOA.core.services import sto as sto_services
from AOA.core.sto_models import dataframe_to_jobs, run_selected_sto_models


def _orders():
    return pd.DataFrame(
        {
            "zlecenie_id": ["Z1", "Z2", "Z3"],
            "produkt_id": ["P1", "P1", "P2"],
            "ilosc_szt": [4, 3, 2],
            "czas_produkcji_h": [2.0, 2.0, 1.0],
            "termin_h": [20.0, 12.0, 8.0],
        }
    )


def _bom():
    return pd.DataFrame(
        {
            "produkt_id": ["P1", "P1", "P2"],
            "component_sku": ["A", "B", "A"],
            "quantity_per_unit": [2.0, 1.0, 1.0],
        }
    )


def test_reservation_uses_stock_then_future_delivery_and_preserves_shared_stock():
    inventory = pd.DataFrame(
        {
            "lot_id": ["A0", "A8", "B0", "B5"],
            "component_sku": ["A", "A", "B", "B"],
            "quantity": [8.0, 8.0, 4.0, 3.0],
            "available_at_h": [0.0, 8.0, 0.0, 5.0],
        }
    )

    result = annotate_component_readiness(_orders(), _bom(), inventory)

    assert result["stock_status"].tolist() == [READY, WAITING_COMPONENTS, WAITING_COMPONENTS]
    assert result["components_ready_h"].tolist() == [0.0, 8.0, 8.0]
    first_reservation = json.loads(result.loc[0, "stock_reservation"])
    assert {item["lot_id"] for item in first_reservation} == {"A0", "B0"}


def test_permanent_shortage_is_visible_and_not_partially_reserved():
    inventory = pd.DataFrame(
        {
            "lot_id": ["A0", "B0"],
            "component_sku": ["A", "B"],
            "quantity": [100.0, 3.0],
            "available_at_h": [0.0, 0.0],
        }
    )

    result = annotate_component_readiness(_orders(), _bom(), inventory)

    assert result.loc[0, "stock_status"] == UNSCHEDULABLE
    assert result.loc[0, "missing_components"] == "B:1.0000"
    assert result.loc[1, "stock_status"] == READY


@pytest.mark.parametrize("machine_count", [1, 2, 3, 4])
def test_component_ready_heuristic_runs_on_parallel_machines(machine_count):
    orders = pd.DataFrame(
        {
            "zlecenie_id": ["Z1", "Z2", "Z3"],
            "produkt_id": ["P1", "P1", "P2"],
            "ilosc_szt": [4, 3, 2],
            "czas_produkcji_h": [2.0, 2.0, 1.0],
            "termin_h": [20.0, 12.0, 8.0],
        }
    )
    inventory = pd.DataFrame(
        {
            "lot_id": ["A0", "A8", "B0", "B5"],
            "component_sku": ["A", "A", "B", "B"],
            "quantity": [8.0, 20.0, 4.0, 20.0],
            "available_at_h": [0.0, 8.0, 0.0, 5.0],
        }
    )
    annotated = annotate_component_readiness(orders, _bom(), inventory)
    jobs = dataframe_to_jobs(annotated, job_id_col="zlecenie_id")

    result = run_selected_sto_models(
        jobs, ["COMPONENT_READY_EDD"], n_machines=machine_count
    )[0]

    assert result["machine_count"] == machine_count
    assert result["unscheduled_count"] == 0
    assert all(step["start_time"] >= step["components_ready_h"] for step in result["steps"])


def test_generated_component_files_are_realistic_and_include_future_deliveries():
    orders, _, _ = generate_production_data(n=60, n_machines=4, seed=42)
    bom, inventory = generate_component_data(orders, seed=42)

    assert len(bom) >= orders["produkt_id"].nunique() * 4
    assert {"component_name", "unit"}.issubset(bom.columns)
    assert {"supplier", "unit_cost_pln", "quality_status"}.issubset(inventory.columns)
    assert (inventory["available_at_h"] > 0).any()
    assert inventory["component_sku"].nunique() >= 8


def test_legacy_orders_without_component_files_are_ready_at_zero():
    result = annotate_component_readiness(_orders(), None, None)

    assert (result["components_ready_h"] == 0).all()
    assert (result["stock_status"] == READY).all()


def test_saved_sto_solver_auto_discovers_bom_and_inventory(tmp_path, monkeypatch):
    orders = _orders().iloc[:2].copy()
    inventory = pd.DataFrame(
        {
            "lot_id": ["A0", "A8", "B0", "B5"],
            "component_sku": ["A", "A", "B", "B"],
            "quantity": [8.0, 8.0, 4.0, 3.0],
            "available_at_h": [0.0, 8.0, 0.0, 5.0],
        }
    )
    data_path = tmp_path / "orders.csv"
    model_path = tmp_path / "sto.pkl"
    orders.to_csv(data_path, index=False)
    _bom().to_csv(tmp_path / "bom.csv", index=False)
    inventory.to_csv(tmp_path / "inventory.csv", index=False)
    save_model_pack(
        {"pack_kind": "sto", "selected_methods": ["COMPONENT_READY_EDD"], "n_machines": 3},
        model_path,
    )
    monkeypatch.setattr(
        sto_services,
        "build_result_filename",
        lambda model_name, source_name, suffix=".csv": tmp_path / f"{model_name}{suffix}",
    )

    result = sto_services.solve_sto_with_saved_model(model_path, data_path)

    assert result["best_result"]["method"] == "COMPONENT_READY_EDD"
    assert result["best_result"]["machine_count"] == 3
    assert result["bom_path"] == tmp_path / "bom.csv"
    assert any("Komponenty" in message for message in result["messages"])
