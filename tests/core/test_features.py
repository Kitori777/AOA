from AOA.core.data_generation import generate_production_data
from AOA.core.features import prepare_features


def test_prepare_features_returns_scaled_features_and_targets():
    df, _, _ = generate_production_data(n=50)

    X, yq, yd, scaler = prepare_features(df)

    assert not X.empty
    assert len(X) == len(df)
    assert len(yq) == len(df)
    assert len(yd) == len(df)
    assert scaler is not None
