from AOA.core.data_generation import generate_production_data
from AOA.core.models import train_selected_models


def test_train_selected_models_returns_model_pack():
    df, train_df, _ = generate_production_data(n=100)

    pack = train_selected_models(train_df, choice="Oba")

    assert "quality" in pack
    assert "delay" in pack
    assert "schedule" in pack
    assert "scaler" in pack
