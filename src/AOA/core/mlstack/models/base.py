from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import joblib
import numpy as np


class BaseAOAModel(ABC):
    """Scikit-like unified interface used by modular AOA stack."""

    @abstractmethod
    def fit(self, X, y):
        raise NotImplementedError

    @abstractmethod
    def predict(self, X):
        raise NotImplementedError

    @abstractmethod
    def score(self, X, y) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_params(self, deep: bool = True) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def set_params(self, **params):
        raise NotImplementedError

    def export(self, path: str | Path) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, out)
        return str(out)


class SklearnModelAdapter(BaseAOAModel):
    """Wrap any sklearn-compatible estimator into AOA unified API."""

    def __init__(self, estimator, *, model_name: str):
        self.estimator = estimator
        self.model_name = model_name

    def fit(self, X, y):
        self.estimator.fit(X, y)
        return self

    def predict(self, X):
        return self.estimator.predict(X)

    def score(self, X, y) -> float:
        return float(self.estimator.score(X, y))

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        if hasattr(self.estimator, "get_params"):
            return dict(self.estimator.get_params(deep=deep))
        return {}

    def set_params(self, **params):
        if hasattr(self.estimator, "set_params"):
            self.estimator.set_params(**params)
        return self

    def feature_importance(self) -> np.ndarray | None:
        if hasattr(self.estimator, "feature_importances_"):
            return self.estimator.feature_importances_
        return None
