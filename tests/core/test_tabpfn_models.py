import numpy as np
import pandas as pd
import pytest

from AOA.core import tabpfn_models


def test_ensure_tabpfn_available_raises_when_dependency_is_missing(monkeypatch):
    monkeypatch.setattr(tabpfn_models, "TABPFN_AVAILABLE", False)

    with pytest.raises(
        tabpfn_models.TabPFNNotAvailableError, match="TabPFN nie jest zainstalowany"
    ):
        tabpfn_models.ensure_tabpfn_available()


def test_train_tabpfn_regressor_uses_model_fit(monkeypatch):
    calls = {}

    class DummyRegressor:
        def fit(self, X, y):
            calls["shape"] = (len(X), len(y))
            return self

    monkeypatch.setattr(tabpfn_models, "TABPFN_AVAILABLE", True)
    monkeypatch.setattr(tabpfn_models, "TabPFNRegressor", DummyRegressor)

    X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    y = pd.Series([0.1, 0.2, 0.3])

    model = tabpfn_models.train_tabpfn_regressor(X, y)

    assert isinstance(model, DummyRegressor)
    assert calls["shape"] == (3, 3)


def test_train_tabpfn_classifier_uses_model_fit(monkeypatch):
    calls = {}

    class DummyClassifier:
        def fit(self, X, y):
            calls["shape"] = (len(X), len(y))
            return self

    monkeypatch.setattr(tabpfn_models, "TABPFN_AVAILABLE", True)
    monkeypatch.setattr(tabpfn_models, "TabPFNClassifier", DummyClassifier)

    X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    y = np.array([0, 1, 0])

    model = tabpfn_models.train_tabpfn_classifier(X, y)

    assert isinstance(model, DummyClassifier)
    assert calls["shape"] == (3, 3)


def test_tabpfn_rejects_mismatched_lengths(monkeypatch):
    monkeypatch.setattr(tabpfn_models, "TABPFN_AVAILABLE", True)

    X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    y = pd.Series([0.1, 0.2])

    with pytest.raises(ValueError, match="tej samej liczby rekordow"):
        tabpfn_models.train_tabpfn_regressor(X, y)


def test_tabpfn_classifier_requires_two_classes(monkeypatch):
    monkeypatch.setattr(tabpfn_models, "TABPFN_AVAILABLE", True)

    X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    y = np.array(["A", "A", "A"])

    with pytest.raises(ValueError, match="co najmniej 2 klas"):
        tabpfn_models.train_tabpfn_classifier(X, y)
