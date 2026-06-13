# ruff: noqa: F401
"""Public ML model registry and builders."""

from .builders import build_classifier, build_regressor
from .custom import available_sklearn_estimators, parse_params_json, save_custom_model_config
from .specs import (
    ML_MODEL_FOCUS,
    ML_MODEL_LABELS,
    ML_MODEL_NAMES,
    ML_MODEL_SPECS,
    ML_MODELS_BY_TASK,
    MLModelSpec,
    ModelTask,
    get_ml_model_names,
    get_ml_model_specs,
    get_ml_task,
)

__all__ = [
    "ML_MODEL_FOCUS",
    "ML_MODEL_LABELS",
    "ML_MODEL_NAMES",
    "ML_MODEL_SPECS",
    "ML_MODELS_BY_TASK",
    "MLModelSpec",
    "ModelTask",
    "available_sklearn_estimators",
    "build_classifier",
    "build_regressor",
    "get_ml_model_names",
    "get_ml_model_specs",
    "get_ml_task",
    "parse_params_json",
    "save_custom_model_config",
]
