from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from AOA.config import MODELS_DIR
from AOA.core.data_io import load_csv, save_csv
from AOA.core.evaluation import calculate_model_training_metrics, format_training_metrics
from AOA.core.features import prepare_features
from AOA.core.ml_models import get_ml_task
from AOA.core.mlstack.pipelines import WorkflowPipeline
from AOA.core.models import load_model_pack, save_model_pack
from AOA.core.scheduling import extract_schedule_features, simulate_schedule

from .files import build_model_filename, build_result_filename, build_sto_model_filename

SCHEDULE_TIMING_COLUMNS = ("t_start", "t_end", "lateness_h")
TRAINING_MEMORY_MAX_ROWS = 50_000
TRAINING_MEMORY_SCAN_LIMIT = 12
SOLUTION_TREE_COLUMNS = (
    "solution_node_id",
    "solution_parent_id",
    "solution_label",
    "solution_details",
    "solution_edge_label",
    "solution_level",
    "solution_order",
    "solution_tree_json",
)


def _selected_models_overlap(left, right) -> bool:
    return bool(set(left or []) & set(right or []))


def _merge_training_history(df_train, history_frames):
    frames = [
        frame for frame in history_frames if isinstance(frame, pd.DataFrame) and not frame.empty
    ]
    if not frames:
        return df_train.copy(), 0

    history = pd.concat(frames, ignore_index=True, sort=False)
    history = history.drop_duplicates().tail(TRAINING_MEMORY_MAX_ROWS).reset_index(drop=True)
    combined = pd.concat([history, df_train], ignore_index=True, sort=False)
    combined = combined.drop_duplicates().tail(TRAINING_MEMORY_MAX_ROWS).reset_index(drop=True)
    return combined, len(history)


def _load_training_history(selected_models, backend):
    history_frames: list[pd.DataFrame] = []
    used_sources: list[str] = []
    if not MODELS_DIR.exists():
        return history_frames, used_sources

    model_paths = sorted(
        MODELS_DIR.glob("*.pkl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in model_paths:
        if len(history_frames) >= TRAINING_MEMORY_SCAN_LIMIT:
            break
        try:
            pack = load_model_pack(path)
        except Exception:
            continue
        if pack.get("pack_kind") != "ml" or pack.get("backend", "classic") != backend:
            continue
        if not _selected_models_overlap(selected_models, pack.get("selected_models")):
            continue
        training_data = pack.get("training_data")
        if isinstance(training_data, pd.DataFrame) and not training_data.empty:
            history_frames.append(training_data)
            used_sources.append(path.name)
    return history_frames, used_sources


def _predict_schedule_strategy(model, result_df):
    try:
        schedule_features = pd.DataFrame([extract_schedule_features(result_df)])
        return model.predict(schedule_features)[0]
    except Exception:
        return "n/a"


def _append_schedule_simulation(result_df):
    if all(column in result_df.columns for column in SCHEDULE_TIMING_COLUMNS):
        return result_df

    scheduled_df = simulate_schedule(result_df)
    for column in SCHEDULE_TIMING_COLUMNS:
        result_df[column] = scheduled_df[column].values
    return result_df


def _append_solution_tree_columns(result_df):
    out = result_df.copy().reset_index(drop=True)
    if out.empty:
        return out

    for column in SOLUTION_TREE_COLUMNS:
        if column in out.columns:
            out = out.drop(columns=[column])

    node_ids = [f"B{i + 1}" for i in range(len(out))]
    out["solution_node_id"] = node_ids
    out["solution_parent_id"] = [""] + node_ids[:-1]
    out["solution_label"] = node_ids

    detail_columns = [
        column
        for column in (
            "pred_quality",
            "pred_delay",
            "priority",
            "recommended_machine",
            "t_start",
            "t_end",
            "lateness_h",
        )
        if column in out.columns
    ]
    fallback_columns = [
        column
        for column in ("czas_produkcji_h", "termin_h", "odpad", "cena")
        if column in out.columns and column not in detail_columns
    ]
    shown_columns = (detail_columns or fallback_columns)[:4]

    def format_value(value):
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.4g}"
        return str(value)

    out["solution_details"] = [
        "; ".join(f"{column}={format_value(row[column])}" for column in shown_columns)
        for _, row in out.iterrows()
    ]
    out["solution_edge_label"] = [
        "" if index == 0 else f"rank {index + 1}" for index in range(len(out))
    ]
    out["solution_level"] = list(range(len(out)))
    out["solution_order"] = list(range(1, len(out) + 1))
    tree_records = [
        {
            "id": "B1",
            "parent": "",
            "label": "B1",
            "details": f"records={len(out)}; view=ranking wynikow",
            "edge_label": "",
        }
    ]
    for index, (_, row) in enumerate(out.head(8).iterrows(), start=2):
        detail = "; ".join(f"{column}={format_value(row[column])}" for column in shown_columns)
        tree_records.append(
            {
                "id": f"B{index}",
                "parent": "B1",
                "label": f"B{index}",
                "details": detail,
                "edge_label": f"rank {index - 1}",
            }
        )
    out["solution_tree_json"] = ""
    out.loc[out.index[0], "solution_tree_json"] = json.dumps(tree_records, ensure_ascii=False)
    return out


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

    history_frames, history_sources = _load_training_history(selected_models, backend)
    training_df, history_rows = _merge_training_history(df_train, history_frames)

    test_size = 0.0
    if df_test is not None and isinstance(df_test, pd.DataFrame) and not df_test.empty:
        total = len(training_df) + len(df_test)
        if total > 0:
            test_size = len(df_test) / total
    pack = train_selected_models(
        df_train=training_df,
        selected_models=selected_models,
        backend=backend,
        test_size=test_size,
    )
    pack["pack_kind"] = "ml"
    pack["training_data"] = training_df.copy()
    pack["training_memory"] = {
        "current_rows": len(df_train),
        "history_rows": history_rows,
        "total_rows": len(training_df),
        "sources": history_sources,
        "max_rows": TRAINING_MEMORY_MAX_ROWS,
    }

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
    if history_rows:
        messages.append(
            f"✔ Uczenie z historią: {len(df_train)} nowych + {history_rows} z poprzednich zapisów = {len(training_df)} rekordów"
        )
    else:
        messages.append(
            f"✔ Pamięć treningowa gotowa: zapisano {len(training_df)} rekordów do kolejnych uruchomień"
        )
    messages.extend(metric_lines)
    return {
        "model_pack": pack,
        "model_path": model_path,
        "messages": messages,
    }


def train_selected_models(
    *,
    df_train: pd.DataFrame,
    selected_models: list[str],
    backend: str = "classic",
    test_size: float = 0.0,
):
    """Compatibility wrapper used by tests and external callers."""
    pipeline = WorkflowPipeline(
        test_size=test_size,
        random_state=42,
        backend=backend,
    )
    result = pipeline.run(df_train, selected_models)
    return result.model_pack


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

    quality_model = model_pack.get("quality")
    delay_model = model_pack.get("delay")
    schedule_model = model_pack.get("schedule")
    scaler = model_pack.get("scaler")
    backend = model_pack.get("backend", "classic")
    if backend != "tabpfn" and scaler is not None:
        X_for_pred, *_ = prepare_features(df, scaler_obj=scaler)
    else:
        X_for_pred, *_ = prepare_features(df)

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
            result_df = _append_schedule_simulation(result_df)
            strategy = _predict_schedule_strategy(model, result_df)
            result_df[f"recommended_{safe_name}"] = strategy
            if model_name == "Schedule" or "recommended_machine" not in result_df.columns:
                result_df["recommended_machine"] = strategy

    if "pred_quality" in result_df.columns and "pred_delay" in result_df.columns:
        result_df["priority"] = (
            result_df["pred_quality"] * 0.7 + (1.0 / (1.0 + result_df["pred_delay"])) * 0.3
        )
        result_df = result_df.sort_values("priority", ascending=False).reset_index(drop=True)

    result_df = _append_solution_tree_columns(result_df)

    result_path = build_result_filename(Path(model_path).stem, Path(data_path).stem, suffix=".csv")
    save_csv(result_df, result_path)
    return {
        "df": result_df,
        "result_path": result_path,
        "messages": [f"✔ Rozwiązanie gotowe: {result_path}"],
    }
