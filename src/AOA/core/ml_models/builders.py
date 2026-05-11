from __future__ import annotations

from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor


def build_regressor(model_name: str):
    if model_name == "Quality":
        return RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1)
    if model_name == "Quality_ET":
        return ExtraTreesRegressor(n_estimators=160, random_state=42, n_jobs=-1)
    if model_name == "Quality_GB":
        return GradientBoostingRegressor(n_estimators=120, learning_rate=0.06, random_state=42)
    if model_name == "Quality_HGB":
        return HistGradientBoostingRegressor(max_iter=120, learning_rate=0.06, random_state=42)
    if model_name == "Delay":
        return GradientBoostingRegressor(n_estimators=120, learning_rate=0.06, random_state=42)
    if model_name == "Delay_RF":
        return RandomForestRegressor(n_estimators=140, random_state=43, n_jobs=-1)
    if model_name == "Delay_ET":
        return ExtraTreesRegressor(n_estimators=160, random_state=43, n_jobs=-1)
    if model_name == "Delay_HGB":
        return HistGradientBoostingRegressor(max_iter=120, learning_rate=0.06, random_state=43)
    if model_name == "Quality_RIDGE":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    if model_name == "Quality_KNN":
        return make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=7))
    if model_name == "Quality_SVR":
        return make_pipeline(StandardScaler(), SVR(C=10.0, epsilon=0.1))
    if model_name == "Quality_TREE":
        return DecisionTreeRegressor(max_depth=12, random_state=42)
    raise ValueError(f"Nieznany model regresyjny ML: {model_name}")


def build_classifier(model_name: str):
    if model_name == "Schedule":
        return RandomForestClassifier(n_estimators=140, random_state=42, n_jobs=-1)
    if model_name == "Schedule_ET":
        return ExtraTreesClassifier(n_estimators=160, random_state=42, n_jobs=-1)
    if model_name == "Schedule_GB":
        return GradientBoostingClassifier(n_estimators=100, learning_rate=0.06, random_state=42)
    if model_name == "Schedule_LOG":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=600, random_state=42))
    raise ValueError(f"Nieznany model klasyfikacyjny ML: {model_name}")
