from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pandas as pd

from AOA.core.component_inventory import annotate_component_readiness
from AOA.core.data_generation import generate_component_data, generate_production_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = PROJECT_ROOT / "data" / "sample"


def _preserve_price_and_deadline(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    previous = None
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    try:
        content = subprocess.check_output(  # noqa: S603
            [
                "git",
                "-c",
                f"safe.directory={PROJECT_ROOT.as_posix()}",
                "show",
                f"HEAD:{relative}",
            ],
            cwd=PROJECT_ROOT,
            text=True,
        )
        previous = pd.read_csv(io.StringIO(content), dtype=str)
    except (OSError, subprocess.CalledProcessError):
        if path.is_file():
            previous = pd.read_csv(path, dtype=str)
    if previous is None:
        return frame
    if "zlecenie_id" not in frame:
        return frame
    result = frame.copy()
    if "zlecenie_id" not in previous:
        if len(previous) != len(result):
            return result
        for column in ("cena", "termin_h"):
            if column in previous:
                result[column] = previous[column].to_numpy()
        return result
    previous = previous.set_index("zlecenie_id")
    for column in ("cena", "termin_h"):
        if column not in previous:
            continue
        mapped = result["zlecenie_id"].map(previous[column])
        result[column] = mapped.where(mapped.notna(), result[column])
    return result


def _with_component_results(frame: pd.DataFrame, component_results: pd.DataFrame) -> pd.DataFrame:
    component_columns = [
        "zlecenie_id",
        "components_ready_h",
        "material_wait_h",
        "missing_components",
        "stock_status",
        "stock_reservation",
    ]
    return frame.drop(
        columns=[column for column in component_columns[1:] if column in frame],
        errors="ignore",
    ).merge(component_results[component_columns], on="zlecenie_id", how="left", validate="one_to_one")


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    production, train, test = generate_production_data(n=800, n_machines=4, seed=42)
    bom, inventory = generate_component_data(production, seed=42)

    reservation_order = production.sort_values(["termin_h", "zlecenie_id"], kind="stable")
    component_results = annotate_component_readiness(reservation_order, bom, inventory)
    production = _with_component_results(production, component_results)
    train = _with_component_results(train, component_results)
    test = _with_component_results(test, component_results)
    sample_table = production.head(12).copy()

    datasets = {
        "production.csv": production,
        "train.csv": train,
        "test.csv": test,
        "sample_table.csv": sample_table,
        "bom.csv": bom,
        "inventory.csv": inventory,
    }
    for name, frame in datasets.items():
        path = SAMPLE_DIR / name
        if name not in {"bom.csv", "inventory.csv"}:
            frame = _preserve_price_and_deadline(frame, path)
        frame.to_csv(path, index=False)
        print(f"{name}: {len(frame)} rows x {len(frame.columns)} columns")


if __name__ == "__main__":
    main()
