import numpy as np
from sklearn.metrics import r2_score

from AOA.core.data_generation import generate_production_data
from AOA.core.features import prepare_features
from AOA.core.models import train_selected_models


def test_train_selected_models_returns_model_pack():
    _, train_df, _ = generate_production_data(n=100)
    pack = train_selected_models(
        train_df,
        selected_models=["Quality", "Delay"],
    )

    assert isinstance(pack, dict)
    assert "quality" in pack
    assert "delay" in pack
    assert "schedule" in pack
    assert "scaler" in pack
    assert "selected_models" in pack
    assert "backend" in pack
    assert pack["quality"] is not None
    assert pack["delay"] is not None
    assert pack["schedule"] is None
    assert pack["scaler"] is not None
    assert pack["selected_models"] == ["Quality", "Delay"]
    assert pack["backend"] == "classic"


def test_train_selected_models_produces_stable_predictions_in_expected_ranges():
    _, train_df, _ = generate_production_data(n=200, seed=42)
    pack = train_selected_models(train_df, selected_models=["Quality", "Delay"])

    X_train, y_quality, y_delay, _ = prepare_features(train_df, scaler_obj=pack["scaler"])
    quality_pred = pack["quality"].predict(X_train)
    delay_pred = pack["delay"].predict(X_train)

    assert np.all((quality_pred >= 0.0) & (quality_pred <= 1.0))
    assert np.all(delay_pred >= 0.0)
    assert r2_score(y_quality, quality_pred) > 0.95
    assert r2_score(y_delay, delay_pred) > 0.95


def test_train_selected_models_is_deterministic_for_same_input_data():
    _, train_df, _ = generate_production_data(n=160, seed=123)

    first_pack = train_selected_models(train_df, selected_models=["Quality", "Delay"])
    second_pack = train_selected_models(train_df, selected_models=["Quality", "Delay"])

    X_train_first, _, _, _ = prepare_features(train_df, scaler_obj=first_pack["scaler"])
    X_train_second, _, _, _ = prepare_features(train_df, scaler_obj=second_pack["scaler"])

    first_quality_pred = first_pack["quality"].predict(X_train_first)
    second_quality_pred = second_pack["quality"].predict(X_train_second)
    first_delay_pred = first_pack["delay"].predict(X_train_first)
    second_delay_pred = second_pack["delay"].predict(X_train_second)

    assert np.allclose(first_quality_pred, second_quality_pred)
    assert np.allclose(first_delay_pred, second_delay_pred)
