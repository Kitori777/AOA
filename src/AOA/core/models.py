import inspect
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)

from AOA.core.features import prepare_features
from AOA.core.ml_models import (
    ML_MODEL_NAMES,
    build_classifier,
    build_regressor,
    get_ml_task,
)
from AOA.core.scheduling import extract_schedule_features, generate_schedule_label
from AOA.core.tabpfn_models import train_tabpfn_classifier, train_tabpfn_regressor
from AOA.messages import (
    NO_MODELS_SELECTED,
    PROGRESS_DONE,
    PROGRESS_ESTIMATOR,
    PROGRESS_PREPARING_DATA,
    PROGRESS_SAMPLE,
    PROGRESS_START,
    PROGRESS_TABPFN_DONE,
    PROGRESS_TABPFN_INIT,
    PROGRESS_TREE,
    UNKNOWN_MODEL_BACKEND,
)


def _emit_progress(progress_callback, model_name: str, percent: float, detail: str = ""):
    """Call a progress callback with a supported argument shape.

    Supported callback forms are:
    - `(model_name, percent, detail)`
    - `(model_name, percent)`
    - `(percent)`

    Internal exceptions raised by the callback are propagated unchanged.
    """
    if progress_callback is None:
        return

    callback_args_candidates = [
        (model_name, percent, detail),
        (model_name, percent),
        (percent,),
    ]

    try:
        signature = inspect.signature(progress_callback)
    except (TypeError, ValueError):
        progress_callback(model_name, percent, detail)
        return

    for args in callback_args_candidates:
        try:
            signature.bind(*args)
        except TypeError:
            continue

        progress_callback(*args)
        return

    raise TypeError(
        "Progress callback must accept one of the supported signatures: "
        "(model_name, percent, detail), (model_name, percent) or (percent)."
    )


def _train_quality_with_progress(X_train, yq, progress_callback=None):
    total_estimators = 200
    model = RandomForestRegressor(
        n_estimators=1,
        warm_start=True,
        random_state=42,
    )

    _emit_progress(progress_callback, "Quality", 0.0, PROGRESS_START)
    _emit_progress(progress_callback, "Quality", 0.5, PROGRESS_PREPARING_DATA)

    for i in range(1, total_estimators + 1):
        model.n_estimators = i
        model.fit(X_train, yq)
        percent = min(100.0, 0.5 + (i / total_estimators) * 99.0)
        _emit_progress(
            progress_callback,
            "Quality",
            round(percent, 1),
            PROGRESS_TREE.format(index=i, total=total_estimators),
        )

    _emit_progress(progress_callback, "Quality", 100.0, PROGRESS_DONE)
    return model


def _train_delay_with_progress(X_train, yd, progress_callback=None):
    total_estimators = 200
    model = GradientBoostingRegressor(
        n_estimators=1,
        warm_start=True,
        random_state=42,
    )

    _emit_progress(progress_callback, "Delay", 0.0, PROGRESS_START)
    _emit_progress(progress_callback, "Delay", 0.5, PROGRESS_PREPARING_DATA)

    for i in range(1, total_estimators + 1):
        model.n_estimators = i
        model.fit(X_train, yd)
        percent = min(100.0, 0.5 + (i / total_estimators) * 99.0)
        _emit_progress(
            progress_callback,
            "Delay",
            round(percent, 1),
            PROGRESS_ESTIMATOR.format(index=i, total=total_estimators),
        )

    _emit_progress(progress_callback, "Delay", 100.0, PROGRESS_DONE)
    return model


def _train_tabpfn_quality_with_progress(X_train, yq, progress_callback=None):
    _emit_progress(progress_callback, "Quality", 0.0, PROGRESS_START)
    _emit_progress(progress_callback, "Quality", 5.0, PROGRESS_TABPFN_INIT)
    model = train_tabpfn_regressor(X_train, yq)
    _emit_progress(progress_callback, "Quality", 100.0, PROGRESS_TABPFN_DONE)
    return model


def _train_tabpfn_delay_with_progress(X_train, yd, progress_callback=None):
    _emit_progress(progress_callback, "Delay", 0.0, PROGRESS_START)
    _emit_progress(progress_callback, "Delay", 5.0, PROGRESS_TABPFN_INIT)
    model = train_tabpfn_regressor(X_train, yd)
    _emit_progress(progress_callback, "Delay", 100.0, PROGRESS_TABPFN_DONE)
    return model


def train_schedule_model(df, n_samples=200, progress_callback=None, backend="classic"):
    """Train a schedule classification model on sampled schedule descriptors.

    Args:
        df: Production DataFrame used to derive schedule samples.
        n_samples: Number of synthetic schedule samples used for training.
        progress_callback: Optional callback invoked as `(model, percent, detail)`.
        backend: Supported backend name: `"classic"` or `"tabpfn"`.

    Returns:
        Trained schedule classification model.
    """

    _emit_progress(progress_callback, "Schedule", 0.0, PROGRESS_START)

    X = []
    y = []

    for i in range(n_samples):
        batch_size = np.random.randint(5, len(df))
        batch = df.sample(n=batch_size, replace=False)
        X.append(extract_schedule_features(batch))
        y.append(generate_schedule_label(batch))
        percent = ((i + 1) / n_samples) * 100.0
        _emit_progress(
            progress_callback,
            "Schedule",
            round(percent, 1),
            PROGRESS_SAMPLE.format(index=i + 1, total=n_samples),
        )

    X = pd.DataFrame(X)
    y = pd.Series(y)

    if backend == "tabpfn":
        model = train_tabpfn_classifier(X, y)
    else:
        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(X, y)

    _emit_progress(progress_callback, "Schedule", 100.0, PROGRESS_DONE)
    return model


def _train_variant_regressor_with_progress(
    model_name: str,
    X_train,
    y_target,
    progress_callback=None,
):
    _emit_progress(progress_callback, model_name, 0.0, PROGRESS_START)
    _emit_progress(progress_callback, model_name, 10.0, PROGRESS_PREPARING_DATA)
    model = build_regressor(model_name)
    _emit_progress(progress_callback, model_name, 35.0, "Dopasowanie estymatora")
    model.fit(X_train, y_target)
    _emit_progress(progress_callback, model_name, 100.0, PROGRESS_DONE)
    return model


def _train_variant_classifier_with_progress(
    model_name: str,
    X_train,
    y_target,
    progress_callback=None,
):
    _emit_progress(progress_callback, model_name, 0.0, PROGRESS_START)
    _emit_progress(progress_callback, model_name, 10.0, PROGRESS_PREPARING_DATA)
    model = build_classifier(model_name)
    _emit_progress(progress_callback, model_name, 35.0, "Dopasowanie klasyfikatora")
    model.fit(X_train, y_target)
    _emit_progress(progress_callback, model_name, 100.0, PROGRESS_DONE)
    return model


def _build_schedule_training_frame(
    df, n_samples=200, progress_callback=None, model_name="Schedule"
):
    X = []
    y = []

    for i in range(n_samples):
        batch_size = np.random.randint(5, len(df))
        batch = df.sample(n=batch_size, replace=False)
        X.append(extract_schedule_features(batch))
        y.append(generate_schedule_label(batch))
        percent = ((i + 1) / n_samples) * 70.0
        _emit_progress(
            progress_callback,
            model_name,
            round(percent, 1),
            PROGRESS_SAMPLE.format(index=i + 1, total=n_samples),
        )

    return pd.DataFrame(X), pd.Series(y)


def train_selected_models(df_train, selected_models, progress_callback=None, backend="classic"):
    """Train selected production models and return them as a model pack.

    Classic mode now supports 12 model variants:
    four quality regressors, four delay regressors and four schedule classifiers.
    Legacy names (`Quality`, `Delay`, `Schedule`) are still kept as the main
    model slots so older tests, saved flows and CLI calls remain compatible.
    """
    if not selected_models:
        raise ValueError(NO_MODELS_SELECTED)

    if backend not in {"classic", "tabpfn"}:
        raise ValueError(UNKNOWN_MODEL_BACKEND.format(backend=backend))

    unknown_models = [name for name in selected_models if name not in ML_MODEL_NAMES]
    if unknown_models:
        raise ValueError(f"Nieznane modele ML: {', '.join(unknown_models)}")

    X_train, yq, yd, scaler = prepare_features(df_train)

    quality_model = None
    delay_model = None
    schedule_model = None
    variant_models: dict[str, object] = {}

    if backend == "tabpfn":
        if "Quality" in selected_models:
            quality_model = _train_tabpfn_quality_with_progress(
                X_train,
                yq,
                progress_callback=progress_callback,
            )
            variant_models["Quality"] = quality_model
        if "Delay" in selected_models:
            delay_model = _train_tabpfn_delay_with_progress(
                X_train,
                yd,
                progress_callback=progress_callback,
            )
            variant_models["Delay"] = delay_model
        if "Schedule" in selected_models:
            schedule_model = train_schedule_model(
                df_train,
                progress_callback=progress_callback,
                backend=backend,
            )
            variant_models["Schedule"] = schedule_model
    else:
        schedule_training_cache = None
        for model_name in selected_models:
            task = get_ml_task(model_name)
            if task == "quality":
                model = _train_variant_regressor_with_progress(
                    model_name,
                    X_train,
                    yq,
                    progress_callback=progress_callback,
                )
                variant_models[model_name] = model
                if model_name == "Quality" or quality_model is None:
                    quality_model = model
            elif task == "delay":
                model = _train_variant_regressor_with_progress(
                    model_name,
                    X_train,
                    yd,
                    progress_callback=progress_callback,
                )
                variant_models[model_name] = model
                if model_name == "Delay" or delay_model is None:
                    delay_model = model
            elif task == "schedule":
                _emit_progress(progress_callback, model_name, 0.0, PROGRESS_START)
                if schedule_training_cache is None:
                    schedule_training_cache = _build_schedule_training_frame(
                        df_train,
                        progress_callback=progress_callback,
                        model_name=model_name,
                    )
                X_schedule, y_schedule = schedule_training_cache
                model = _train_variant_classifier_with_progress(
                    model_name,
                    X_schedule,
                    y_schedule,
                    progress_callback=progress_callback,
                )
                variant_models[model_name] = model
                if model_name == "Schedule" or schedule_model is None:
                    schedule_model = model

    return {
        "quality": quality_model,
        "delay": delay_model,
        "schedule": schedule_model,
        "ml_models": variant_models,
        "scaler": scaler,
        "selected_models": selected_models,
        "backend": backend,
    }


SAFE_BUILTINS = {
    "dict",
    "list",
    "tuple",
    "set",
    "frozenset",
    "str",
    "int",
    "float",
    "bool",
    "bytes",
    "bytearray",
    "complex",
    "slice",
}
SAFE_MODULE_PREFIXES = (
    "collections",
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "AOA",
)


def _is_safe_module(module: str) -> bool:
    if module.startswith("test_"):
        return True

    return any(
        module == prefix or module.startswith(prefix + ".") for prefix in SAFE_MODULE_PREFIXES
    )


class RestrictedModelUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "builtins" and name in SAFE_BUILTINS:
            return super().find_class(module, name)
        if _is_safe_module(module):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Loading model packs from module '{module}' is not allowed.")


def _validate_model_pack_path(path) -> Path:
    resolved = Path(path)
    if resolved.suffix != ".pkl":
        raise ValueError("Model pack must be loaded from a .pkl file.")
    return resolved


def save_model_pack(model_pack, path):
    """Serialize a trained model pack to disk using pickle."""
    path = _validate_model_pack_path(path)
    with open(path, "wb") as f:
        pickle.dump(model_pack, f)


def load_model_pack(path):
    """Load a pickled model pack from disk using a restricted unpickler."""
    path = _validate_model_pack_path(path)

    with open(path, "rb") as f:
        return RestrictedModelUnpickler(f).load()
