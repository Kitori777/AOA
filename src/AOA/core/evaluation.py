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


def calculate_regression_metrics(df: pd.DataFrame, target: str) -> dict:
    """Train a simple regression baseline and return standard metrics."""
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

    return {
        "R2": round(r2_score(y, y_pred), 4),
        "MAE": round(mean_absolute_error(y, y_pred), 4),
        "MSE": round(mean_squared_error(y, y_pred), 4),
        "RMSE": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
        "MAPE_%": round(np.mean(np.abs((y - y_pred) / (y + 1e-6))) * 100, 2),
    }


def calculate_classification_metrics(df: pd.DataFrame, target: str) -> dict:
    """Train a simple classification baseline and return standard metrics."""
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


def calculate_model_training_metrics(
    model_pack: dict, df_train: pd.DataFrame
) -> dict[str, dict[str, float]]:
    """Calculate compact in-sample metrics for real trained ML models.

    This helper is defensive because tests and some GUI flows may use lightweight
    placeholder objects in model packs. Metrics are displayed only when the
    object behaves like a fitted estimator and the input contains all production
    feature columns required by ``prepare_features``.
    """
    from AOA.core.features import prepare_features

    if df_train is None or df_train.empty:
        return {}

    try:
        X_train, y_quality, y_delay, _ = prepare_features(df_train)
    except (KeyError, TypeError, ValueError):
        return {}

    results: dict[str, dict[str, float]] = {}

    quality_model = model_pack.get("quality")
    if quality_model is not None and hasattr(quality_model, "predict"):
        try:
            pred = quality_model.predict(X_train)
        except (AttributeError, TypeError, ValueError):
            pred = None
        if pred is not None:
            results["Quality"] = {
                "R2": round(float(r2_score(y_quality, pred)), 4),
                "MAE": round(float(mean_absolute_error(y_quality, pred)), 4),
                "RMSE": round(float(np.sqrt(mean_squared_error(y_quality, pred))), 4),
            }

    delay_model = model_pack.get("delay")
    if delay_model is not None and hasattr(delay_model, "predict"):
        try:
            pred = delay_model.predict(X_train)
        except (AttributeError, TypeError, ValueError):
            pred = None
        if pred is not None:
            results["Delay"] = {
                "R2": round(float(r2_score(y_delay, pred)), 4),
                "MAE": round(float(mean_absolute_error(y_delay, pred)), 4),
                "RMSE": round(float(np.sqrt(mean_squared_error(y_delay, pred))), 4),
            }

    if model_pack.get("schedule") is not None:
        results["Schedule"] = {"trained": 1.0}
    return results


def format_training_metrics(metrics: dict[str, dict[str, float]]) -> list[str]:
    """Format model metrics as log lines for the GUI and CLI."""
    if not metrics:
        return []
    lines = ["📊 Ocena uczenia modelu:"]
    for model_name, values in metrics.items():
        if model_name == "Schedule" and "trained" in values:
            lines.append(
                "   Schedule: model klasyfikacyjny nauczony; oceniaj go później przez Accuracy/F1 na danych testowych."
            )
            continue
        metric_text = " | ".join(f"{name}={value}" for name, value in values.items())
        lines.append(f"   {model_name}: {metric_text}")
    lines.append("   Jak czytać: RMSE/MAE im niżej tym lepiej, R² im bliżej 1 tym lepiej.")
    return lines
