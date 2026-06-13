from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd

try:
    from tabpfn import TabPFNClassifier, TabPFNRegressor

    TABPFN_AVAILABLE = True
    TABPFN_IMPORT_ERROR = None
except Exception as e:
    TabPFNClassifier = None
    TabPFNRegressor = None
    TABPFN_AVAILABLE = False
    TABPFN_IMPORT_ERROR = e


class TabPFNNotAvailableError(RuntimeError):
    """Raised when TabPFN backend was requested but dependency is unavailable."""


def ensure_tabpfn_available() -> None:
    if not TABPFN_AVAILABLE:
        raise TabPFNNotAvailableError(
            f"TabPFN nie jest zainstalowany. Błąd importu: {TABPFN_IMPORT_ERROR}"
        )


def _prepare_env_for_cpu_large_dataset() -> None:
    os.environ["TABPFN_ALLOW_CPU_LARGE_DATASET"] = "1"


def _validate_tabpfn_inputs(
    X_train: pd.DataFrame | np.ndarray,
    y_train: pd.Series | np.ndarray,
    *,
    classification: bool,
) -> None:
    if X_train is None or y_train is None:
        raise ValueError("TabPFN wymaga danych X_train oraz celu y_train.")

    x_array = np.asarray(X_train)
    y_array = np.asarray(y_train)

    if x_array.ndim != 2:
        raise ValueError("TabPFN wymaga tabeli 2D: wiersze = rekordy, kolumny = cechy.")
    if y_array.ndim != 1:
        y_array = y_array.reshape(-1)
    if x_array.shape[0] == 0 or x_array.shape[1] == 0:
        raise ValueError("TabPFN nie moze trenowac na pustej tabeli albo bez cech.")
    if x_array.shape[0] != y_array.shape[0]:
        raise ValueError(
            f"TabPFN wymaga tej samej liczby rekordow w X i y: X={x_array.shape[0]}, y={y_array.shape[0]}."
        )
    if not np.isfinite(x_array.astype(float, copy=False)).all():
        raise ValueError("TabPFN dostal NaN albo inf w cechach. Najpierw uzupelnij i oczysc dane.")
    if x_array.shape[0] < 3:
        raise ValueError("TabPFN potrzebuje co najmniej 3 rekordow treningowych do sensownej walidacji.")
    if classification:
        if pd.isna(pd.Series(y_array)).any():
            raise ValueError("TabPFNClassifier dostal puste klasy w y_train.")
        if np.unique(y_array).size < 2:
            raise ValueError("TabPFNClassifier wymaga co najmniej 2 klas w y_train.")
    elif not np.isfinite(y_array.astype(float, copy=False)).all():
        raise ValueError("TabPFNRegressor dostal NaN albo inf w celu y. Najpierw oczysc kolumne celu.")


def _build_tabpfn_regressor():
    ensure_tabpfn_available()
    _prepare_env_for_cpu_large_dataset()

    errors = []

    for kwargs in (
        {"ignore_pretraining_limits": True},
        {"device": "cpu", "ignore_pretraining_limits": True},
        {},
        {"device": "cpu"},
    ):
        try:
            return TabPFNRegressor(**kwargs)
        except TypeError as e:
            errors.append(f"{kwargs} -> TypeError: {e}")
        except Exception as e:
            errors.append(f"{kwargs} -> {type(e).__name__}: {e}")

    raise RuntimeError("Nie udało się utworzyć TabPFNRegressor.\n" + "\n".join(errors))


def _build_tabpfn_classifier():
    ensure_tabpfn_available()
    _prepare_env_for_cpu_large_dataset()

    errors = []

    for kwargs in (
        {"ignore_pretraining_limits": True},
        {"device": "cpu", "ignore_pretraining_limits": True},
        {},
        {"device": "cpu"},
    ):
        try:
            return TabPFNClassifier(**kwargs)
        except TypeError as e:
            errors.append(f"{kwargs} -> TypeError: {e}")
        except Exception as e:
            errors.append(f"{kwargs} -> {type(e).__name__}: {e}")

    raise RuntimeError("Nie udało się utworzyć TabPFNClassifier.\n" + "\n".join(errors))


def train_tabpfn_regressor(
    X_train: pd.DataFrame | np.ndarray,
    y_train: pd.Series | np.ndarray,
) -> Any:
    _validate_tabpfn_inputs(X_train, y_train, classification=False)
    model = _build_tabpfn_regressor()

    try:
        model.fit(X_train, y_train)
        return model
    except Exception as e:
        raise RuntimeError(
            "TabPFNRegressor.fit() zakończył się błędem.\n"
            f"Typ błędu: {type(e).__name__}\n"
            f"Szczegóły: {e}"
        ) from e


def train_tabpfn_classifier(
    X_train: pd.DataFrame | np.ndarray,
    y_train: pd.Series | np.ndarray,
) -> Any:
    _validate_tabpfn_inputs(X_train, y_train, classification=True)
    model = _build_tabpfn_classifier()

    try:
        model.fit(X_train, y_train)
        return model
    except Exception as e:
        raise RuntimeError(
            "TabPFNClassifier.fit() zakończył się błędem.\n"
            f"Typ błędu: {type(e).__name__}\n"
            f"Szczegóły: {e}"
        ) from e
