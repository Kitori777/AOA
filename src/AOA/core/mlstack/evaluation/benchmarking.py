from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from AOA.core.features import prepare_features
from AOA.core.mlstack.models import ModelRegistry


@dataclass
class BenchmarkRow:
    model: str
    folds: int
    mean_score: float
    std_score: float
    fit_seconds: float


def run_benchmark(df: pd.DataFrame, model_names: list[str], folds: int = 5) -> list[BenchmarkRow]:
    X, y_quality, _y_delay, _ = prepare_features(df)
    X_np = X.to_numpy() if hasattr(X, "to_numpy") else X
    y_np = y_quality.to_numpy() if hasattr(y_quality, "to_numpy") else y_quality
    max_splits = max(2, len(X_np) // 2)
    n_splits = min(max(2, folds), max_splits)
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    registry = ModelRegistry()
    out: list[BenchmarkRow] = []

    for model_name in model_names:
        scores: list[float] = []
        start = perf_counter()
        try:
            for train_idx, test_idx in splitter.split(X_np):
                model = registry.create(model_name)
                model.fit(X_np[train_idx], y_np[train_idx])
                scores.append(model.score(X_np[test_idx], y_np[test_idx]))
        except Exception:
            # Skip a broken model in this benchmark run instead of failing the whole cycle.
            continue
        if not scores:
            continue
        elapsed = perf_counter() - start
        out.append(
            BenchmarkRow(
                model=model_name,
                folds=len(scores),
                mean_score=float(np.mean(scores)),
                std_score=float(np.std(scores)),
                fit_seconds=float(elapsed),
            )
        )
    return out
