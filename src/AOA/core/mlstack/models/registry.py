from __future__ import annotations

from dataclasses import dataclass

from AOA.core.ml_models import ML_MODEL_NAMES, get_ml_task
from AOA.core.ml_models.builders import build_classifier, build_regressor

from .base import SklearnModelAdapter


@dataclass(frozen=True)
class ModelSpec:
    name: str
    task: str


class ModelRegistry:
    """Central model catalog with one interface for all model families."""

    def __init__(self) -> None:
        self._specs = {
            name: ModelSpec(name=name, task=get_ml_task(name)) for name in ML_MODEL_NAMES
        }

    def list_models(self) -> list[ModelSpec]:
        return [self._specs[name] for name in sorted(self._specs)]

    def create(self, name: str) -> SklearnModelAdapter:
        if name not in self._specs:
            raise ValueError(f"Unknown model: {name}")
        task = self._specs[name].task
        estimator = build_classifier(name) if task == "schedule" else build_regressor(name)
        return SklearnModelAdapter(estimator=estimator, model_name=name)
