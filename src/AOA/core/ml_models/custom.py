from __future__ import annotations

import importlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler

from AOA.config import MODELS_DIR

from .specs import MLModelSpec, ModelTask

CUSTOM_MODEL_CONFIG = MODELS_DIR / "custom_ml_models.json"


@dataclass(frozen=True)
class CustomMLModelConfig:
    name: str
    task: ModelTask
    label: str
    estimator: str
    params: dict[str, Any]
    scaler: str = "auto"


def _ensure_config_parent() -> None:
    CUSTOM_MODEL_CONFIG.parent.mkdir(parents=True, exist_ok=True)


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_")
    if not cleaned:
        cleaned = "model"
    if not cleaned.startswith("Custom_"):
        cleaned = f"Custom_{cleaned}"
    return cleaned[:80]


def load_custom_model_configs(path: Path | None = None) -> tuple[CustomMLModelConfig, ...]:
    path = path or CUSTOM_MODEL_CONFIG
    if not path.exists():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    configs: list[CustomMLModelConfig] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            configs.append(
                CustomMLModelConfig(
                    name=_safe_name(str(item["name"])),
                    task=item["task"],
                    label=str(item.get("label") or item["name"]),
                    estimator=str(item["estimator"]),
                    params=dict(item.get("params") or {}),
                    scaler=str(item.get("scaler") or "auto"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(configs)


def save_custom_model_config(
    *,
    name: str,
    task: ModelTask,
    label: str,
    estimator: str,
    params: dict[str, Any] | None = None,
    scaler: str = "auto",
    path: Path | None = None,
) -> CustomMLModelConfig:
    path = path or CUSTOM_MODEL_CONFIG
    config = CustomMLModelConfig(
        name=_safe_name(name),
        task=task,
        label=label.strip() or _safe_name(name),
        estimator=estimator,
        params=params or {},
        scaler=scaler,
    )
    configs = [item for item in load_custom_model_configs(path) if item.name != config.name]
    configs.append(config)
    _ensure_config_parent()
    payload = [asdict(item) for item in sorted(configs, key=lambda item: item.name)]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return config


def get_custom_model_specs() -> tuple[MLModelSpec, ...]:
    return tuple(
        MLModelSpec(
            config.name,
            config.task,
            config.label,
            f"Własny model sklearn: {config.estimator}.",
            "konfiguracja użytkownika zapisana w JSON",
        )
        for config in load_custom_model_configs()
    )


def get_custom_model_config(model_name: str) -> CustomMLModelConfig | None:
    return next(
        (config for config in load_custom_model_configs() if config.name == model_name),
        None,
    )


def available_sklearn_estimators(task: ModelTask) -> tuple[str, ...]:
    try:
        from sklearn.utils.discovery import all_estimators
    except ImportError:
        from sklearn.utils import all_estimators

    estimator_type = "classifier" if task == "schedule" else "regressor"
    estimators = all_estimators(type_filter=estimator_type)
    names = []
    for _name, cls in estimators:
        module = getattr(cls, "__module__", "")
        if module.startswith("sklearn.") and not module.startswith("sklearn.tests"):
            names.append(f"{module}.{cls.__name__}")
    names.append("xgboost.XGBClassifier" if task == "schedule" else "xgboost.XGBRegressor")
    return tuple(sorted(set(names)))


def parse_params_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Parametry muszą być obiektem JSON, np. {\"n_estimators\": 300}.")
    return parsed


def build_custom_model(model_name: str) -> Pipeline:
    config = get_custom_model_config(model_name)
    if config is None:
        raise ValueError(f"Nieznany własny model ML: {model_name}")
    estimator_cls = _load_sklearn_estimator(config.estimator)
    estimator = estimator_cls(**config.params)
    scaler = _select_scaler(config)
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if scaler is not None:
        steps.append(("scaler", scaler))
    steps.append(("model", estimator))
    return Pipeline(steps=steps)


def _load_sklearn_estimator(path: str):
    if not (path.startswith("sklearn.") or path.startswith("xgboost.")):
        raise ValueError("Dozwolone są estymatory z pakietu sklearn oraz xgboost.")
    module_name, _, class_name = path.rpartition(".")
    if not module_name or not class_name:
        raise ValueError(f"Nieprawidłowa ścieżka estymatora: {path}")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if path.startswith("xgboost."):
            raise ValueError(
                "XGBoost jest dopuszczony jako opcja eksperymentalna, ale pakiet nie jest "
                "zainstalowany w tym środowisku. Zainstaluj go przez: pip install aoa[experimental] "
                "albo pip install xgboost."
            ) from exc
        raise
    return getattr(module, class_name)


def _select_scaler(config: CustomMLModelConfig):
    scaler = config.scaler.lower()
    if scaler == "none":
        return None
    if scaler == "standard":
        return StandardScaler()
    if scaler == "robust":
        return RobustScaler()
    name = config.estimator.lower()
    needs_scale = ("linear_model" in name or "svm" in name or "neighbors" in name or "neural_network" in name)
    return RobustScaler() if needs_scale else None
