from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import train_test_split

from AOA.core.evaluation import calculate_model_training_metrics, format_training_metrics
from AOA.core.models import train_selected_models


@dataclass
class WorkflowResult:
    model_pack: dict
    train_metrics: dict[str, dict[str, float]]
    metric_lines: list[str]
    train_rows: int
    test_rows: int


class WorkflowPipeline:
    """End-to-end pipeline: data -> train -> metrics -> report lines."""

    def __init__(self, test_size: float = 0.2, random_state: int = 42, backend: str = "classic"):
        self.test_size = float(test_size)
        self.random_state = int(random_state)
        self.backend = backend

    def run(self, df: pd.DataFrame, selected_models: list[str]) -> WorkflowResult:
        if df is None or df.empty:
            raise ValueError("Brak danych do pipeline.")
        if not selected_models:
            raise ValueError("Brak modeli do treningu.")

        if 0 < self.test_size < 1 and len(df) > 8:
            df_train, df_test = train_test_split(
                df,
                test_size=self.test_size,
                random_state=self.random_state,
                shuffle=True,
            )
        else:
            df_train, df_test = df.copy(), None

        safe_models = list(selected_models)
        if len(df_train) < 6:
            safe_models = [name for name in safe_models if name != "Schedule"]
        if not safe_models:
            raise ValueError("Za malo danych do treningu wybranego zestawu modeli.")

        pack = train_selected_models(
            df_train=df_train,
            selected_models=safe_models,
            backend=self.backend,
        )
        metrics = calculate_model_training_metrics(pack, df_train, df_test=df_test)
        lines = format_training_metrics(metrics)
        return WorkflowResult(
            model_pack=pack,
            train_metrics=metrics,
            metric_lines=lines,
            train_rows=len(df_train),
            test_rows=0 if df_test is None else len(df_test),
        )
