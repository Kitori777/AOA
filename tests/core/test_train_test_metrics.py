from __future__ import annotations

import numpy as np
import pandas as pd

from AOA.core.evaluation import calculate_model_training_metrics, format_training_metrics
from AOA.core.models import train_selected_models
from AOA.core.services import train_models_flow
from AOA.core.services import training as training_services


def _production_df(n: int = 40) -> pd.DataFrame:
    shapes = ["kwadrat", "trojkat", "trapez", "kwadrat"] * ((n // 4) + 1)
    materials = ["bawelna", "mikrofibra", "poliester", "wiskoza"] * ((n // 4) + 1)
    idx = np.arange(1, n + 1, dtype=float)
    return pd.DataFrame(
        {
            "cena": 90.0 + idx * 1.7,
            "odpad": (idx % 7) / 20.0 + 0.02,
            "termin_h": 12.0 + (idx % 9) * 2.0,
            "czas_produkcji_h": 2.0 + (idx % 6) * 0.7,
            "x": 20.0 + (idx % 5),
            "y": 10.0 + (idx % 4),
            "z": 0.3 + (idx % 3) * 0.1,
            "ksztalt": shapes[:n],
            "material": materials[:n],
        }
    )


def test_model_training_metrics_report_train_and_test_splits():
    df_train = _production_df(36)
    df_test = _production_df(12)
    pack = train_selected_models(df_train, ["Quality"], backend="classic")

    metrics = calculate_model_training_metrics(pack, df_train, df_test=df_test)

    assert "Quality" in metrics
    assert "train_R2" in metrics["Quality"]
    assert "test_R2" in metrics["Quality"]
    assert "gap_R2" in metrics["Quality"]
    assert "test_available" not in metrics["Quality"]


def test_format_training_metrics_makes_holdout_scope_explicit():
    lines = format_training_metrics(
        {
            "Quality": {
                "train_R2": 0.99,
                "train_MAE": 0.01,
                "train_RMSE": 0.02,
                "test_R2": 0.75,
                "test_MAE": 0.08,
                "test_RMSE": 0.12,
                "gap_R2": 0.24,
            }
        }
    )

    joined = "\n".join(lines)
    assert "train/test" in joined
    assert "test R²" in joined
    assert "gap R²" in joined
    assert "overfitting" in joined


def test_train_models_flow_passes_test_split_into_metric_calculation(monkeypatch, tmp_path):
    df_train = _production_df(16)
    df_test = _production_df(8)
    fake_pack = {
        "quality": object(),
        "delay": None,
        "schedule": None,
        "scaler": None,
        "selected_models": ["Quality"],
        "backend": "classic",
    }
    seen = {}

    monkeypatch.setattr(training_services, "train_selected_models", lambda **kwargs: fake_pack)
    monkeypatch.setattr(
        training_services, "build_model_filename", lambda *args, **kwargs: tmp_path / "m.pkl"
    )
    monkeypatch.setattr(training_services, "save_model_pack", lambda *args, **kwargs: None)

    def fake_metrics(pack, train_arg, df_test=None):
        seen["train"] = train_arg
        seen["test"] = df_test
        return {}

    monkeypatch.setattr(training_services, "calculate_model_training_metrics", fake_metrics)

    result = train_models_flow(df_train, ["Quality"], df_test=df_test)

    assert result["model_path"] == tmp_path / "m.pkl"
    assert seen["train"] is df_train
    assert seen["test"] is df_test
