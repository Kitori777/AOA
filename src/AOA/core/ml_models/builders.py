from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

from .custom import build_custom_model, get_custom_model_config


@dataclass(frozen=True)
class ModelFactory:
    """Small registry entry describing how a production model is built."""

    name: str
    factory: Callable[[], Pipeline]
    notes: str


def _numeric_tree_pipeline(estimator) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("model", estimator),
        ]
    )


def _scaled_pipeline(estimator, *, robust: bool = False) -> Pipeline:
    scaler = RobustScaler() if robust else StandardScaler()
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", scaler),
            ("model", estimator),
        ]
    )


REGRESSOR_FACTORIES: dict[str, ModelFactory] = {
    "Quality": ModelFactory(
        "Quality",
        lambda: _numeric_tree_pipeline(
            RandomForestRegressor(
                n_estimators=320,
                min_samples_leaf=2,
                max_features=0.85,
                bootstrap=True,
                oob_score=True,
                random_state=42,
                n_jobs=-1,
            )
        ),
        "stabilny bagging drzew z OOB jako wewnętrzną kontrolą jakości",
    ),
    "Quality_ET": ModelFactory(
        "Quality_ET",
        lambda: _numeric_tree_pipeline(
            ExtraTreesRegressor(
                n_estimators=360,
                min_samples_leaf=2,
                max_features=0.9,
                random_state=42,
                n_jobs=-1,
            )
        ),
        "szybki ensemble z mocniej losowanymi progami",
    ),
    "Quality_GB": ModelFactory(
        "Quality_GB",
        lambda: _numeric_tree_pipeline(
            GradientBoostingRegressor(
                n_estimators=220,
                learning_rate=0.045,
                max_depth=3,
                subsample=0.9,
                validation_fraction=0.12,
                n_iter_no_change=12,
                random_state=42,
            )
        ),
        "boosting z walidacją wewnętrzną i wcześniejszym zatrzymaniem",
    ),
    "Quality_HGB": ModelFactory(
        "Quality_HGB",
        lambda: _numeric_tree_pipeline(
            HistGradientBoostingRegressor(
                max_iter=260,
                learning_rate=0.045,
                l2_regularization=0.04,
                early_stopping="auto",
                random_state=42,
            )
        ),
        "histogramowy boosting dla większych zbiorów",
    ),
    "Delay": ModelFactory(
        "Delay",
        lambda: _numeric_tree_pipeline(
            GradientBoostingRegressor(
                n_estimators=260,
                learning_rate=0.04,
                max_depth=3,
                subsample=0.9,
                validation_fraction=0.12,
                n_iter_no_change=15,
                random_state=43,
            )
        ),
        "bazowy model opóźnień, ostrożny boosting z early stopping",
    ),
    "Delay_RF": ModelFactory(
        "Delay_RF",
        lambda: _numeric_tree_pipeline(
            RandomForestRegressor(
                n_estimators=340,
                min_samples_leaf=2,
                max_features=0.85,
                bootstrap=True,
                oob_score=True,
                random_state=43,
                n_jobs=-1,
            )
        ),
        "stabilna predykcja opóźnień przez uśrednianie drzew",
    ),
    "Delay_ET": ModelFactory(
        "Delay_ET",
        lambda: _numeric_tree_pipeline(
            ExtraTreesRegressor(
                n_estimators=360,
                min_samples_leaf=2,
                max_features=0.9,
                random_state=43,
                n_jobs=-1,
            )
        ),
        "szybki wariant dla szumu i podobnych zleceń",
    ),
    "Delay_HGB": ModelFactory(
        "Delay_HGB",
        lambda: _numeric_tree_pipeline(
            HistGradientBoostingRegressor(
                max_iter=280,
                learning_rate=0.04,
                l2_regularization=0.05,
                early_stopping="auto",
                random_state=43,
            )
        ),
        "wydajny boosting histogramowy dla ryzyka opóźnień",
    ),
    "Quality_RIDGE": ModelFactory(
        "Quality_RIDGE",
        lambda: _scaled_pipeline(Ridge(alpha=1.4), robust=True),
        "liniowy punkt odniesienia z odpornym skalowaniem",
    ),
    "Quality_KNN": ModelFactory(
        "Quality_KNN",
        lambda: _scaled_pipeline(
            KNeighborsRegressor(n_neighbors=9, weights="distance"), robust=True
        ),
        "lokalny model podobnych przypadków",
    ),
    "Quality_SVR": ModelFactory(
        "Quality_SVR",
        lambda: _scaled_pipeline(SVR(C=12.0, epsilon=0.08, gamma="scale"), robust=True),
        "nieliniowy model marginesowy dla jakości",
    ),
    "Quality_TREE": ModelFactory(
        "Quality_TREE",
        lambda: _numeric_tree_pipeline(
            DecisionTreeRegressor(max_depth=14, min_samples_leaf=2, random_state=42)
        ),
        "czytelne pojedyncze drzewo do demonstracji reguł",
    ),
}


CLASSIFIER_FACTORIES: dict[str, ModelFactory] = {
    "Schedule": ModelFactory(
        "Schedule",
        lambda: _numeric_tree_pipeline(
            RandomForestClassifier(
                n_estimators=320,
                min_samples_leaf=2,
                max_features="sqrt",
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=-1,
            )
        ),
        "bagging strategii harmonogramowania",
    ),
    "Schedule_ET": ModelFactory(
        "Schedule_ET",
        lambda: _numeric_tree_pipeline(
            ExtraTreesClassifier(
                n_estimators=360,
                min_samples_leaf=2,
                max_features="sqrt",
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
        ),
        "szybki klasyfikator odporny na szum",
    ),
    "Schedule_GB": ModelFactory(
        "Schedule_GB",
        lambda: _numeric_tree_pipeline(
            GradientBoostingClassifier(
                n_estimators=180,
                learning_rate=0.045,
                max_depth=3,
                subsample=0.9,
                validation_fraction=0.12,
                n_iter_no_change=12,
                random_state=42,
            )
        ),
        "boosting dla trudniejszych granic między strategiami",
    ),
    "Schedule_LOG": ModelFactory(
        "Schedule_LOG",
        lambda: _scaled_pipeline(
            LogisticRegression(
                max_iter=1200,
                C=1.2,
                class_weight="balanced",
                random_state=42,
                solver="lbfgs",
            ),
            robust=True,
        ),
        "lekki baseline liniowy z klasami ważonymi",
    ),
}


def build_regressor(model_name: str):
    try:
        return REGRESSOR_FACTORIES[model_name].factory()
    except KeyError:
        config = get_custom_model_config(model_name)
        if config is not None and config.task in {"quality", "delay"}:
            return build_custom_model(model_name)
        raise ValueError(f"Nieznany model regresyjny ML: {model_name}") from None


def build_classifier(model_name: str):
    try:
        return CLASSIFIER_FACTORIES[model_name].factory()
    except KeyError:
        config = get_custom_model_config(model_name)
        if config is not None and config.task == "schedule":
            return build_custom_model(model_name)
        raise ValueError(f"Nieznany model klasyfikacyjny ML: {model_name}") from None
