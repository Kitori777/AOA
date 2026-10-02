from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from AOA.core.constants import KSZTALT_DIMENSIONS
from AOA.core.scheduling import build_machine_profiles, simulate_schedule

MATERIAL_GRAMMAGE_G_M2 = {
    "bawelna": 185.0,
    "mikrofibra": 145.0,
    "poliester": 165.0,
    "wiskoza": 175.0,
}


def _shape_area_cm2(shape: str, x: float, y: float) -> float:
    if shape == "trojkat":
        return 0.5 * x * y
    if shape == "trapez":
        return 0.5 * (x + y) * y
    return x * y


def generate_production_data(
    n=5000,
    n_machines=1,
    test_size=0.2,
    seed=42,
    ksztalty=None,
    materialy=None,
    price_range=(50, 500),
    waste_range=(0.0, 0.3),
    production_time_range=(1.0, 48.0),
    deadline_buffer_range=(1.0, 72.0),
):
    """Generate realistic, backward-compatible production records.

    Price and deadline use the original random stream and formulas. New fields
    describe material demand, changeovers, energy and machine compatibility.
    Timing and waste come from the shared parallel-machine simulator.
    """
    if n_machines <= 0 or n_machines > 8:
        raise ValueError("n_machines musi miec wartosc od 1 do 8")
    if n <= 0:
        raise ValueError("n musi byc dodatnie")

    available_ksztalty = list(KSZTALT_DIMENSIONS.keys())
    available_materialy = list(MATERIAL_GRAMMAGE_G_M2)
    ksztalty = ksztalty or available_ksztalty
    materialy = materialy or available_materialy
    if not ksztaty_or_materialy_valid(ksztalty, available_ksztalty, "ksztalty"):
        raise ValueError("Nieprawidłowe wartości w liście ksztalty")
    if not ksztaty_or_materialy_valid(materialy, available_materialy, "materialy"):
        raise ValueError("Nieprawidłowe wartości w liście materialy")

    # Preserve the legacy stream through price/deadline for compatibility.
    core_rng = np.random.RandomState(seed)
    ksztalt_col = core_rng.choice(ksztalty, n)
    material_col = core_rng.choice(materialy, n)
    czas_produkcji_h = core_rng.uniform(
        float(production_time_range[0]), float(production_time_range[1]), int(n)
    )
    deadline_buffer_h = core_rng.uniform(
        float(deadline_buffer_range[0]), float(deadline_buffer_range[1]), int(n)
    )
    termin_h = czas_produkcji_h + deadline_buffer_h
    cena = core_rng.uniform(float(price_range[0]), float(price_range[1]), int(n))
    legacy_waste = core_rng.uniform(float(waste_range[0]), float(waste_range[1]), int(n))

    rng = np.random.default_rng(seed + 1009)
    quantity = rng.integers(20, 501, n)
    x = np.array([KSZTALT_DIMENSIONS[k]["x"] for k in ksztalt_col]) * rng.normal(1.0, 0.035, n)
    y = np.array([KSZTALT_DIMENSIONS[k]["y"] for k in ksztalt_col]) * rng.normal(1.0, 0.035, n)
    z = np.array([KSZTALT_DIMENSIONS[k]["z"] for k in ksztalt_col]) * rng.normal(1.0, 0.025, n)
    area_cm2 = np.array(
        [
            _shape_area_cm2(shape, x_i, y_i)
            for shape, x_i, y_i in zip(ksztalt_col, x, y, strict=True)
        ]
    )
    net_material_m2 = area_cm2 * quantity / 10_000.0
    cutting_loss = np.clip(0.035 + 0.42 * legacy_waste + rng.normal(0.0, 0.012, n), 0.025, 0.19)
    material_use_m2 = net_material_m2 / (1.0 - cutting_loss)
    grammage = np.array([MATERIAL_GRAMMAGE_G_M2[m] for m in material_col])
    material_input_kg = material_use_m2 * grammage / 1000.0
    base_waste_kg = material_input_kg * cutting_loss
    setup_h = rng.uniform(0.15, 1.3, n)
    changeover_waste_kg = np.maximum(0.02, material_input_kg * rng.uniform(0.002, 0.012, n))
    profiles = build_machine_profiles(n_machines)
    eligible = [
        "|".join(str(p.machine_id) for p in profiles if material in p.supported_materials)
        for material in material_col
    ]

    df = pd.DataFrame(
        {
            "zlecenie_id": [f"ZL-{seed:04d}-{index + 1:05d}" for index in range(n)],
            "produkt_id": [
                f"PROD-{str(material).upper()}-{str(shape).upper()}"
                for material, shape in zip(material_col, ksztalt_col, strict=True)
            ],
            "cena": cena,
            "odpad": cutting_loss,
            "termin_h": np.round(termin_h, 3),
            "czas_produkcji_h": np.round(czas_produkcji_h, 3),
            "ksztalt": ksztalt_col,
            "material": material_col,
            "x": np.round(x, 3),
            "y": np.round(y, 3),
            "z": np.round(z, 3),
            "ilosc_szt": quantity,
            "szerokosc_materialu_cm": rng.choice([140, 150, 160, 180], n),
            "pole_elementu_cm2": np.round(area_cm2, 3),
            "zuzycie_materialu_m2": np.round(material_use_m2, 4),
            "masa_materialu_kg": np.round(material_input_kg, 4),
            "odpad_kg": np.round(base_waste_kg, 4),
            "odpad_przezbrojenia_kg": np.round(changeover_waste_kg, 4),
            "czas_przezbrojenia_h": np.round(setup_h, 3),
            "energia_kwh": np.round(czas_produkcji_h * rng.uniform(3.5, 5.0, n), 3),
            "defect_rate": np.round(
                np.clip(0.006 + cutting_loss * 0.11 + rng.normal(0, 0.003, n), 0.002, 0.055), 4
            ),
            "priorytet": rng.choice([1, 2, 3, 4, 5], n, p=[0.08, 0.16, 0.40, 0.25, 0.11]),
            "dozwolone_maszyny": eligible,
        }
    )
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    scheduled = simulate_schedule(df, n_machines=n_machines)
    scheduled["lateness_h_sim"] = scheduled["lateness_h"].round(3)
    scheduled["t_start"] = scheduled["t_start"].round(3)
    scheduled["t_end"] = scheduled["t_end"].round(3)
    scheduled["odpad_kg"] = scheduled["waste_kg_actual"].round(4)
    scheduled["predkosc_maszyny"] = scheduled["machine_speed_factor"]
    scheduled["wspolczynnik_odpadu_maszyny"] = scheduled["machine_waste_factor"]
    scheduled["quality_score"] = (
        (1.0 - scheduled["defect_rate"] - scheduled["odpad"].clip(0, 0.35) * 0.25)
        .clip(0, 1)
        .round(4)
    )

    train_df, test_df = train_test_split(scheduled, test_size=test_size, random_state=seed)
    return scheduled, train_df, test_df


def generate_component_data(
    orders: pd.DataFrame, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a realistic BOM and dated inventory lots for generated orders."""
    required = {
        "produkt_id",
        "material",
        "ksztalt",
        "ilosc_szt",
        "zuzycie_materialu_m2",
        "x",
        "y",
    }
    missing = sorted(required - set(orders.columns))
    if missing:
        raise ValueError(f"Nie mozna zbudowac BOM; brak kolumn: {', '.join(missing)}")

    bom_rows: list[dict[str, object]] = []
    for product_id, group in orders.groupby("produkt_id", sort=True):
        material = str(group["material"].iloc[0])
        shape = str(group["ksztalt"].iloc[0])
        material_per_unit = float(
            (group["zuzycie_materialu_m2"] / group["ilosc_szt"]).median()
        )
        thread_per_unit = float(((2.0 * (group["x"] + group["y"])) / 100.0).median() * 1.08)
        bom_rows.extend(
            [
                {
                    "produkt_id": product_id,
                    "component_sku": f"MAT-{material.upper()}",
                    "component_name": f"Material {material}",
                    "quantity_per_unit": round(material_per_unit, 6),
                    "unit": "m2",
                },
                {
                    "produkt_id": product_id,
                    "component_sku": "NIC-UNIWERSALNA",
                    "component_name": "Nic przemyslowa",
                    "quantity_per_unit": round(thread_per_unit, 4),
                    "unit": "m",
                },
                {
                    "produkt_id": product_id,
                    "component_sku": "ETYKIETA-STANDARD",
                    "component_name": "Etykieta wyrobu",
                    "quantity_per_unit": 1.0,
                    "unit": "szt",
                },
                {
                    "produkt_id": product_id,
                    "component_sku": f"OPAK-{shape.upper()}",
                    "component_name": f"Opakowanie {shape}",
                    "quantity_per_unit": 0.04,
                    "unit": "szt",
                },
            ]
        )
    bom = pd.DataFrame(bom_rows)

    quantities_by_product = orders.groupby("produkt_id")["ilosc_szt"].sum().to_dict()
    demand_by_sku: dict[str, float] = {}
    for row in bom.itertuples(index=False):
        demand_by_sku[row.component_sku] = demand_by_sku.get(row.component_sku, 0.0) + (
            float(row.quantity_per_unit) * float(quantities_by_product[row.produkt_id])
        )

    rng = np.random.default_rng(seed + 4099)
    inventory_rows: list[dict[str, object]] = []
    shortage_sku = sorted(sku for sku in demand_by_sku if sku.startswith("OPAK-"))[-1]
    suppliers = ("Textil Polska", "Komponent SA", "LogiPack", "Nord Supply")
    lot_number = 1
    for sku, demand in sorted(demand_by_sku.items()):
        coverage = 0.86 if sku == shortage_sku else float(rng.uniform(1.03, 1.12))
        available_total = demand * coverage
        shares = (0.58, 0.24, 0.18)
        for lot_index, (share, available_at_h, source) in enumerate(
            zip(shares, (0.0, 24.0, 72.0), ("stock", "delivery", "delivery"), strict=True)
        ):
            inventory_rows.append(
                {
                    "lot_id": f"LOT-{lot_number:05d}",
                    "component_sku": sku,
                    "quantity": round(available_total * share, 4),
                    "available_at_h": available_at_h,
                    "source": source,
                    "supplier": suppliers[(lot_number + lot_index) % len(suppliers)],
                    "unit_cost_pln": round(float(rng.uniform(0.08, 24.0)), 2),
                    "quality_status": "released",
                }
            )
            lot_number += 1
    inventory = pd.DataFrame(inventory_rows)
    return bom, inventory


def ksztaty_or_materialy_valid(values, allowed, field_name):
    """Check whether every provided value belongs to the allowed set."""
    del field_name
    if not values:
        return False
    return all(value in allowed for value in values)
