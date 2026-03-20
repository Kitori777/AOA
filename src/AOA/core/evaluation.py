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
    df = df.copy()

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].mean())
        else:
            df[col] = df[col].ffill().fillna("Unknown")

    return df


def transform_numeric_columns(df: pd.DataFrame, transformation: str) -> pd.DataFrame:
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
            df[col] = (
                (df[col] - df[col].min()) /
                (df[col].max() - df[col].min() + 1e-6)
            )

    return df


def calculate_regression_metrics(df: pd.DataFrame, target: str) -> dict:
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
    df = df.copy()

    metrics_row = {col: "" for col in df.columns}
    metrics_row.update(metrics)

    df = pd.concat([df, pd.DataFrame([metrics_row])], ignore_index=True)
    return df.fillna("")
