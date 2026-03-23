from AOA.config import (
    DEFAULT_RESULT_FILE,
    FULL_DATA_FILE,
    MODEL_FILE,
    TEST_DATA_FILE,
    TRAIN_DATA_FILE,
)
from AOA.core.data_generation import generate_production_data
from AOA.core.data_io import load_csv, save_csv
from AOA.core.dataset_ops import split_train_test
from AOA.core.evaluation import (
    append_metrics_row,
    calculate_classification_metrics,
    calculate_regression_metrics,
    fill_missing_values,
    transform_numeric_columns,
)
from AOA.core.features import prepare_features
from AOA.core.models import load_model_pack, save_model_pack, train_selected_models
from AOA.core.scheduling import simulate_schedule


def generate_and_store_datasets(n=5000, n_machines=1, test_size=0.2, seed=42):
    df_full, df_train, df_test = generate_production_data(
        n=n,
        n_machines=n_machines,
        test_size=test_size,
        seed=seed
    )

    save_csv(df_full, FULL_DATA_FILE)
    save_csv(df_train, TRAIN_DATA_FILE)
    save_csv(df_test, TEST_DATA_FILE)

    return {
        "full_df": df_full,
        "train_df": df_train,
        "test_df": df_test,
        "messages": [
            "✔ Dane wygenerowane i podzielone na train/test",
            f"Train: {len(df_train)} rekordów",
            f"Test: {len(df_test)} rekordów",
            f"📄 Zapisano pełny zbiór: {FULL_DATA_FILE}",
            f"📄 Zapisano train: {TRAIN_DATA_FILE}",
            f"📄 Zapisano test: {TEST_DATA_FILE}",
        ],
    }


def load_and_prepare_visual_file(path, train_ratio=0.8):
    df = load_csv(path)
    columns = list(df.columns)

    if not columns:
        raise ValueError("Plik CSV nie zawiera kolumn")

    x_default = columns[0]
    y_default = columns[1] if len(columns) > 1 else columns[0]

    return {
        "df": df,
        "columns": columns,
        "x_default": x_default,
        "y_default": y_default,
    }


def prepare_results_analysis(df, selected_cols, transformation, target, mode):
    if df is None or df.empty:
        raise ValueError("Brak danych do analizy")

    if not selected_cols:
        raise ValueError("Nie wybrano kolumn do analizy")

    df_to_show = df[selected_cols].copy()
    df_to_show = fill_missing_values(df_to_show)
    df_to_show = transform_numeric_columns(df_to_show, transformation)

    if target not in df_to_show.columns:
        raise ValueError("Nieprawidłowy target")

    if mode == "regresja":
        metrics = calculate_regression_metrics(df_to_show, target)
    elif mode == "klasyfikacja":
        metrics = calculate_classification_metrics(df_to_show, target)
    else:
        raise ValueError("Nieznany tryb analizy")

    df_to_show = append_metrics_row(df_to_show, metrics)

    return {
        "df": df_to_show,
        "text": df_to_show.to_string(index=True),
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


def train_models_flow(df_train, choice, progress_callback=None):
    pack = train_selected_models(
        df_train,
        choice=choice,
        progress_callback=progress_callback
    )

    save_model_pack(pack, MODEL_FILE)

    return {
        "model_pack": pack,
        "messages": [
            f"💾 Modele zapisane do: {MODEL_FILE}",
            "✔ Trening zakończony",
        ],
    }


def solve_models_flow(model_path, data_path):
    pack = load_model_pack(model_path)
    df_sol = load_csv(data_path)

    X, _, _, _ = prepare_features(df_sol, pack.get("scaler"))

    if pack.get("quality") is not None:
        df_sol["pred_quality"] = pack["quality"].predict(X)

    if pack.get("delay") is not None:
        df_sol["pred_delay"] = pack["delay"].predict(X)

    if "pred_quality" in df_sol.columns and "pred_delay" in df_sol.columns:
        df_sol["priority"] = df_sol["pred_quality"] / (df_sol["pred_delay"] + 1e-6)
        df_sol = df_sol.sort_values("priority", ascending=False)

    df_sol = simulate_schedule(df_sol)
    save_csv(df_sol, DEFAULT_RESULT_FILE)

    return {
        "df": df_sol,
        "messages": [
            "🏁 Rozwiązanie gotowe",
            "TOP 10 produktów:",
            df_sol.head(10).to_string(),
            f"📄 Zapisano: {DEFAULT_RESULT_FILE}",
        ],
    }
