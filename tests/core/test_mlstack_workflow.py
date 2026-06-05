from __future__ import annotations

import pandas as pd

from AOA.core.mlstack.evaluation import run_benchmark
from AOA.core.mlstack.models import ModelRegistry
from AOA.core.mlstack.pipelines import WorkflowPipeline


def _df() -> pd.DataFrame:
    return pd.read_csv("data/sample/sample_table.csv")


def test_model_registry_create_and_fit_predict() -> None:
    df = _df()
    registry = ModelRegistry()
    model = registry.create("Quality")

    from AOA.core.features import prepare_features

    X, y_quality, _y_delay, _ = prepare_features(df)
    model.fit(X, y_quality)
    n = min(5, len(X))
    pred = model.predict(X[:n])
    assert len(pred) == n


def test_workflow_pipeline_end_to_end() -> None:
    df = _df()
    pipe = WorkflowPipeline(test_size=0.2, random_state=42)
    result = pipe.run(df, ["Quality", "Delay", "Schedule"])
    assert result.train_rows > 0
    assert isinstance(result.metric_lines, list)
    assert result.model_pack.get("backend") == "classic"


def test_benchmark_returns_rows() -> None:
    df = _df()
    rows = run_benchmark(df, ["Quality"], folds=3)
    assert len(rows) == 1
    assert rows[0].folds >= 2
