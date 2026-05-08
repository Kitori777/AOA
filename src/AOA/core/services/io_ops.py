from __future__ import annotations

from datetime import datetime

from AOA.config import DATA_DIR
from AOA.core.data_generation import generate_production_data
from AOA.core.data_io import load_csv, save_csv
from AOA.core.dataset_ops import split_train_test

from .common import parse_generation_config


def generate_and_store_datasets_from_config(raw_config: dict):
    parsed = parse_generation_config(raw_config)
    return generate_and_store_datasets(
        n=parsed["n"],
        n_machines=parsed["n_machines"],
        test_size=parsed["test_size"],
        seed=parsed["seed"],
        ksztalty=parsed["selected_ksztalty"],
        materialy=parsed["selected_materialy"],
        production_time_range=(parsed["prod_min"], parsed["prod_max"]),
        deadline_buffer_range=(parsed["deadline_min"], parsed["deadline_max"]),
    )


def generate_and_store_datasets(
    n=5000,
    n_machines=1,
    test_size=0.2,
    seed=42,
    ksztalty=None,
    materialy=None,
    production_time_range=(1, 48),
    deadline_buffer_range=(1, 72),
):
    full_df, train_df, test_df = generate_production_data(
        n=n,
        n_machines=n_machines,
        test_size=test_size,
        seed=seed,
        ksztalty=ksztalty,
        materialy=materialy,
        production_time_range=production_time_range,
        deadline_buffer_range=deadline_buffer_range,
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_path = DATA_DIR / f"dane_{stamp}.csv"
    train_path = DATA_DIR / f"train_{stamp}.csv"
    test_path = DATA_DIR / f"test_{stamp}.csv"

    save_csv(full_df, full_path)
    save_csv(train_df, train_path)
    save_csv(test_df, test_path)

    return {
        "full_df": full_df,
        "train_df": train_df,
        "test_df": test_df,
        "full_path": full_path,
        "train_path": train_path,
        "test_path": test_path,
        "messages": [
            f"✔ Wygenerowano pełny zbiór: {full_path}",
            f"✔ Wygenerowano train: {train_path}",
            f"✔ Wygenerowano test: {test_path}",
        ],
    }


def load_and_prepare_visual_file(path, train_ratio=0.8):
    df = load_csv(path)
    columns = list(df.columns)

    if not columns:
        raise ValueError("Plik CSV nie zawiera kolumn")

    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    defaults = numeric_columns if len(numeric_columns) >= 2 else columns
    x_default = defaults[0]
    y_default = defaults[1] if len(defaults) > 1 else defaults[0]
    z_default = defaults[2] if len(defaults) > 2 else y_default

    return {
        "df": df,
        "columns": columns,
        "numeric_columns": numeric_columns,
        "x_default": x_default,
        "y_default": y_default,
        "z_default": z_default,
    }


def load_training_data(path, train_ratio=0.8):
    df_full = load_csv(path)
    df_train, df_test = split_train_test(df_full, train_ratio=train_ratio)

    return {
        "full_df": df_full,
        "train_df": df_train,
        "test_df": df_test,
        "messages": [
            f"✔ Wczytano dane: {path}",
            f"Train: {len(df_train)} rekordów",
            f"Test: {len(df_test)} rekordów",
        ],
    }
