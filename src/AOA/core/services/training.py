from __future__ import annotations

from pathlib import Path

import pandas as pd

from AOA.core.data_io import load_csv, save_csv
from AOA.core.evaluation import calculate_model_training_metrics, format_training_metrics
from AOA.core.features import prepare_features
from AOA.core.ml_models import get_ml_task
from AOA.core.models import load_model_pack, save_model_pack, train_selected_models
from AOA.core.scheduling import extract_schedule_features, simulate_schedule

from .files import build_model_filename, build_result_filename, build_sto_model_filename


def train_models_flow(
    df_train,
    selected_models,
    metadata=None,
    progress_callback=None,
    backend="classic",
    df_test=None,
):
    if df_train is None or df_train.empty:
        raise ValueError("Brak danych treningowych.")
    if not selected_models:
        raise ValueError("Nie wybrano żadnego modelu do trenowania.")

    pack = train_selected_models(
        df_train=df_train,
        selected_models=selected_models,
        progress_callback=progress_callback,
        backend=backend,
    )
    pack["pack_kind"] = "ml"

    metadata = metadata or {}
    try:
        model_path = build_model_filename(selected_models, metadata, backend=backend)
    except TypeError:
        model_path = build_model_filename(selected_models, metadata)

    save_model_pack(pack, model_path)
    backend_label = "TabPFN" if backend == "tabpfn" else "Classic"

    metric_lines = format_training_metrics(
        calculate_model_training_metrics(pack, df_train, df_test=df_test)
    )
    messages = [
        f"✔ Modele zapisane do: {model_path}",
        f"✔ Trening zakończony | backend: {backend_label}",
    ]
    messages.extend(metric_lines)
    return {
        "model_pack": pack,
        "model_path": model_path,
        "messages": messages,
    }


def train_sto_models_flow(selected_methods):
    if not selected_methods:
        raise ValueError("Nie wybrano żadnego modelu STO do zapisania.")

    pack = {"pack_kind": "sto", "selected_methods": list(selected_methods)}
    model_path = build_sto_model_filename(selected_methods)
    save_model_pack(pack, model_path)
    return {
        "model_pack": pack,
        "model_path": model_path,
        "messages": [
            f"✔ Modele STO zapisane do: {model_path}",
            "✔ Zapis modelu STO zakończony",
        ],
    }


def solve_models_flow(model_path, data_path):
    if not model_path:
        raise ValueError("Nie wybrano pliku modelu.")
    if not data_path:
        raise ValueError("Nie wybrano pliku danych.")

    model_pack = load_model_pack(model_path)
    df = load_csv(data_path)
    if df.empty:
        raise ValueError("Plik danych jest pusty.")

    X, *_ = prepare_features(df)
    quality_model = model_pack.get("quality")
    delay_model = model_pack.get("delay")
    schedule_model = model_pack.get("schedule")
    scaler = model_pack.get("scaler")
    backend = model_pack.get("backend", "classic")
    X_for_pred = X

    if backend != "tabpfn" and scaler is not None:
        try:
            transformed = scaler.transform(X)
            X_for_pred = (
                pd.DataFrame(transformed, columns=X.columns, index=X.index)
                if hasattr(X, "columns")
                else transformed
            )
        except Exception:
            X_for_pred = X

    result_df = df.copy()
    variant_models = model_pack.get("ml_models") or {}
    if not variant_models:
        if quality_model is not None:
            variant_models["Quality"] = quality_model
        if delay_model is not None:
            variant_models["Delay"] = delay_model
        if schedule_model is not None:
            variant_models["Schedule"] = schedule_model

    for model_name, model in variant_models.items():
        task = get_ml_task(model_name)
        safe_name = model_name.lower()
        if task == "quality":
            predictions = model.predict(X_for_pred)
            if model_name == "Quality" or "pred_quality" not in result_df.columns:
                result_df["pred_quality"] = predictions
            result_df[f"pred_{safe_name}"] = predictions
        elif task == "delay":
            predictions = model.predict(X_for_pred)
            if model_name == "Delay" or "pred_delay" not in result_df.columns:
                result_df["pred_delay"] = predictions
            result_df[f"pred_{safe_name}"] = predictions
        elif task == "schedule":
            if model_name == "Schedule" or "recommended_machine" not in result_df.columns:
                result_df["recommended_machine"] = simulate_schedule(model, result_df)
            try:
                schedule_features = pd.DataFrame([extract_schedule_features(result_df)])
                result_df[f"recommended_{safe_name}"] = model.predict(schedule_features)[0]
            except Exception:
                result_df[f"recommended_{safe_name}"] = "n/a"

    if "pred_quality" in result_df.columns and "pred_delay" in result_df.columns:
        result_df["priority"] = (
            result_df["pred_quality"] * 0.7 + (1.0 / (1.0 + result_df["pred_delay"])) * 0.3
        )
        result_df = result_df.sort_values("priority", ascending=False).reset_index(drop=True)

    result_path = build_result_filename(Path(model_path).stem, Path(data_path).stem, suffix=".csv")
    save_csv(result_df, result_path)
    return {
        "df": result_df,
        "result_path": result_path,
        "messages": [f"✔ Rozwiązanie gotowe: {result_path}"],
    }
