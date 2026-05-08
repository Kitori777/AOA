import numpy as np
import pandas as pd
import pytest

from AOA.core import models
from AOA.core.models import _emit_progress


def _sample_training_df(n=40):
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "cena": rng.uniform(50, 200, n),
            "odpad": rng.uniform(0.01, 0.3, n),
            "termin_h": rng.uniform(10, 80, n),
            "czas_produkcji_h": rng.uniform(1, 20, n),
            "x": rng.uniform(1, 30, n),
            "y": rng.uniform(1, 30, n),
            "z": rng.uniform(0.1, 5, n),
            "ksztalt": rng.choice(["kwadrat", "trojkat", "trapez"], n),
            "material": rng.choice(
                ["bawelna", "mikrofibra", "poliester", "wiskoza"],
                n,
            ),
            "lateness_h_sim": rng.uniform(0, 15, n),
        }
    )


def test_train_selected_models_returns_only_requested_quality():
    df = _sample_training_df()
    pack = models.train_selected_models(df, ["Quality"])

    assert pack["quality"] is not None
    assert pack["delay"] is None
    assert pack["schedule"] is None
    assert pack["scaler"] is not None
    assert pack["selected_models"] == ["Quality"]
    assert pack["backend"] == "classic"


def test_train_selected_models_returns_all_requested_models():
    df = _sample_training_df()
    pack = models.train_selected_models(df, ["Quality", "Delay", "Schedule"])

    assert pack["quality"] is not None
    assert pack["delay"] is not None
    assert pack["schedule"] is not None
    assert pack["scaler"] is not None
    assert pack["selected_models"] == ["Quality", "Delay", "Schedule"]
    assert pack["backend"] == "classic"


def test_train_schedule_model_calls_progress_callback():
    df = _sample_training_df()
    progress_calls = []

    def progress_callback(*args):
        progress_calls.append(args)

    model = models.train_schedule_model(df, n_samples=20, progress_callback=progress_callback)

    assert model is not None
    assert progress_calls, "Callback postępu nie został wywołany"
    flattened = " | ".join(" ".join(map(str, call)) for call in progress_calls)
    assert "Schedule" in flattened
    assert any(
        "100" in " ".join(map(str, call)) or "Zakończono" in " ".join(map(str, call))
        for call in progress_calls
    )


def test_train_selected_models_rejects_unknown_backend():
    df = _sample_training_df()

    with pytest.raises(ValueError, match="Nieznany backend modeli"):
        models.train_selected_models(df, ["Quality"], backend="cosmos")


def test_train_selected_models_uses_tabpfn_backend_when_requested(monkeypatch):
    df = _sample_training_df()

    monkeypatch.setattr(models, "train_tabpfn_regressor", lambda X, y: {"kind": "tabpfn_reg"})
    monkeypatch.setattr(models, "train_tabpfn_classifier", lambda X, y: {"kind": "tabpfn_clf"})

    pack = models.train_selected_models(
        df,
        ["Quality", "Delay", "Schedule"],
        backend="tabpfn",
    )

    assert pack["quality"] == {"kind": "tabpfn_reg"}
    assert pack["delay"] == {"kind": "tabpfn_reg"}
    assert pack["schedule"] == {"kind": "tabpfn_clf"}
    assert pack["backend"] == "tabpfn"


def test_emit_progress_supports_three_argument_callback():
    calls = []

    def callback(model_name, percent, detail):
        calls.append((model_name, percent, detail))

    _emit_progress(callback, "Quality", 12.5, "step")

    assert calls == [("Quality", 12.5, "step")]


def test_emit_progress_supports_two_argument_callback():
    calls = []

    def callback(model_name, percent):
        calls.append((model_name, percent))

    _emit_progress(callback, "Quality", 12.5, "step")

    assert calls == [("Quality", 12.5)]


def test_emit_progress_supports_single_argument_callback():
    calls = []

    def callback(percent):
        calls.append(percent)

    _emit_progress(callback, "Quality", 12.5, "step")

    assert calls == [12.5]


def test_emit_progress_does_not_swallow_internal_type_error():
    def callback(model_name, percent, detail):
        return 1 + "x"  # type: ignore[operator]

    with pytest.raises(TypeError):
        _emit_progress(callback, "Quality", 12.5, "step")


def test_emit_progress_raises_for_unsupported_signature():
    def callback():
        return None

    with pytest.raises(TypeError, match="Progress callback must accept"):
        _emit_progress(callback, "Quality", 12.5, "step")
