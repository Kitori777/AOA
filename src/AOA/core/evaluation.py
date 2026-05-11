import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing numeric values with the mean and text values forward."""
    df = df.copy()

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].mean())
        else:
            df[col] = df[col].ffill().fillna("Unknown")

    return df


def transform_numeric_columns(df: pd.DataFrame, transformation: str) -> pd.DataFrame:
    """Apply a named numeric transformation to all numeric columns."""
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not numeric_cols:
        return df

    if transformation == "MinMax Normalizacja":
        df[numeric_cols] = MinMaxScaler().fit_transform(df[numeric_cols])

    elif transformation == "Standaryzacja":
        df[numeric_cols] = StandardScaler().fit_transform(df[numeric_cols])

    elif transformation == "Logarytm":
        for col in numeric_cols:
            df[col] = np.log1p(df[col])

    elif transformation == "Skalowanie 0-1":
        for col in numeric_cols:
            df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min() + 1e-6)

    return df


def _regression_metric_dict(y_true, y_pred) -> dict[str, float]:
    return {
        "R2": round(float(r2_score(y_true, y_pred)), 4),
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "MSE": round(float(mean_squared_error(y_true, y_pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "MAPE_%": round(float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-6))) * 100), 2),
    }


def calculate_regression_metrics(df: pd.DataFrame, target: str) -> dict:
    """Train a simple regression baseline and return in-sample metrics.

    This function is used only by the exploratory Results/analysis view. The
    production training flow uses ``calculate_model_training_metrics`` below,
    which reports train and test metrics separately.
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if target not in numeric_cols:
        raise ValueError("Target musi być kolumną liczbową do regresji")

    feature_cols = [col for col in numeric_cols if col != target]
    if not feature_cols:
        raise ValueError("Brak cech liczbowych do regresji")

    X = df[feature_cols]
    y = df[target]

    model = DecisionTreeRegressor(max_depth=3, random_state=42)
    model.fit(X, y)
    y_pred = model.predict(X)

    return _regression_metric_dict(y, y_pred)


def calculate_classification_metrics(df: pd.DataFrame, target: str) -> dict:
    """Train a simple classification baseline and return in-sample metrics."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if target not in categorical_cols:
        raise ValueError("Target musi być kolumną kategorialną do klasyfikacji")

    if not numeric_cols:
        raise ValueError("Brak cech liczbowych do klasyfikacji")

    X = df[numeric_cols]
    y = df[target].astype(str)

    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    model = DecisionTreeClassifier(max_depth=3, random_state=42)
    model.fit(X, y_encoded)
    y_pred = model.predict(X)

    return {
        "Accuracy": round(accuracy_score(y_encoded, y_pred), 4),
        "F1_score": round(f1_score(y_encoded, y_pred, average="macro"), 4),
        "Precision": round(precision_score(y_encoded, y_pred, average="macro", zero_division=0), 4),
        "Recall": round(recall_score(y_encoded, y_pred, average="macro", zero_division=0), 4),
    }


def append_metrics_row(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    """Append a metrics summary row to the provided DataFrame."""
    df = df.copy()

    metrics_row = {col: "" for col in df.columns}
    metrics_row.update(metrics)

    df = pd.concat([df, pd.DataFrame([metrics_row])], ignore_index=True)
    return df.fillna("")


def _safe_prepare_features(df: pd.DataFrame | None, scaler_obj=None):
    from AOA.core.features import prepare_features

    if df is None or df.empty:
        return None
    try:
        return prepare_features(df, scaler_obj=scaler_obj)
    except (KeyError, TypeError, ValueError):
        return None


def _metrics_for_split(model, X, y) -> dict[str, float] | None:
    if model is None or not hasattr(model, "predict"):
        return None
    try:
        pred = model.predict(X)
    except (AttributeError, TypeError, ValueError):
        return None
    return {
        "R2": round(float(r2_score(y, pred)), 4),
        "MAE": round(float(mean_absolute_error(y, pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y, pred))), 4),
    }


def _combine_train_test_metrics(
    train_metrics: dict[str, float] | None,
    test_metrics: dict[str, float] | None,
) -> dict[str, float]:
    if not train_metrics:
        return {}
    combined: dict[str, float] = {}
    for name, value in train_metrics.items():
        combined[f"train_{name}"] = value
    if test_metrics:
        for name, value in test_metrics.items():
            combined[f"test_{name}"] = value
        if "R2" in train_metrics and "R2" in test_metrics:
            combined["gap_R2"] = round(float(train_metrics["R2"] - test_metrics["R2"]), 4)
    else:
        combined["test_available"] = 0.0
    return combined


def calculate_model_training_metrics(
    model_pack: dict,
    df_train: pd.DataFrame,
    df_test: pd.DataFrame | None = None,
) -> dict[str, dict[str, float]]:
    """Calculate train/test metrics for fitted production ML models.

    ``df_train`` is still used to show learning fit, but whenever ``df_test`` is
    available the function also reports holdout metrics. This prevents the GUI
    and CLI from presenting in-sample R² as if it were real generalization
    quality.
    """
    prepared_train = _safe_prepare_features(df_train)
    if prepared_train is None:
        return {}

    X_train, y_quality_train, y_delay_train, fitted_scaler = prepared_train
    scaler = model_pack.get("scaler") or fitted_scaler
    prepared_test = (
        _safe_prepare_features(df_test, scaler_obj=scaler) if df_test is not None else None
    )

    if prepared_test is None:
        X_test = y_quality_test = y_delay_test = None
    else:
        X_test, y_quality_test, y_delay_test, _ = prepared_test

    results: dict[str, dict[str, float]] = {}

    quality_model = model_pack.get("quality")
    quality_train = _metrics_for_split(quality_model, X_train, y_quality_train)
    quality_test = (
        _metrics_for_split(quality_model, X_test, y_quality_test)
        if X_test is not None and y_quality_test is not None
        else None
    )
    combined = _combine_train_test_metrics(quality_train, quality_test)
    if combined:
        results["Quality"] = combined

    delay_model = model_pack.get("delay")
    delay_train = _metrics_for_split(delay_model, X_train, y_delay_train)
    delay_test = (
        _metrics_for_split(delay_model, X_test, y_delay_test)
        if X_test is not None and y_delay_test is not None
        else None
    )
    combined = _combine_train_test_metrics(delay_train, delay_test)
    if combined:
        results["Delay"] = combined

    if model_pack.get("schedule") is not None:
        results["Schedule"] = {"trained": 1.0}
    return results


def _format_metric_value(value: float) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def format_training_metrics(metrics: dict[str, dict[str, float]]) -> list[str]:
    """Format train/test model metrics as log lines for the GUI and CLI."""
    if not metrics:
        return []
    lines = ["📊 Ocena modelu na train/test:"]
    for model_name, values in metrics.items():
        if model_name == "Schedule" and "trained" in values:
            lines.append(
                "   Schedule: model klasyfikacyjny nauczony; oceniaj go później przez Accuracy/F1 na danych testowych."
            )
            continue
        train_text = (
            f"train R²={_format_metric_value(values['train_R2'])} | "
            f"MAE={_format_metric_value(values['train_MAE'])} | "
            f"RMSE={_format_metric_value(values['train_RMSE'])}"
        )
        if values.get("test_available") == 0.0:
            lines.append(f"   {model_name}: {train_text} | test: brak zbioru testowego")
            continue
        test_text = (
            f"test R²={_format_metric_value(values['test_R2'])} | "
            f"MAE={_format_metric_value(values['test_MAE'])} | "
            f"RMSE={_format_metric_value(values['test_RMSE'])} | "
            f"gap R²={_format_metric_value(values['gap_R2'])}"
        )
        lines.append(f"   {model_name}: {train_text} || {test_text}")
    lines.append(
        "   Jak czytać: test pokazuje jakość na danych niewidzianych; duży gap R² sygnalizuje możliwy overfitting."
    )
    return lines
