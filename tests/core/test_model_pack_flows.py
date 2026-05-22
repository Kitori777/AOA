import pandas as pd
import pytest

from AOA.core import services
from AOA.core.data_generation import generate_production_data
from AOA.core.ml_models import ML_MODEL_SPECS
from AOA.core.models import load_model_pack, save_model_pack, train_selected_models
from AOA.core.services import training as training_services


class PickleableDummyModel:
    def __init__(self, name):
        self.name = name


@pytest.fixture
def training_df():
    return pd.DataFrame(
        {
            "cena": [100, 120, 130, 150],
            "odpad": [0.1, 0.2, 0.15, 0.05],
            "termin_h": [10, 12, 14, 16],
            "czas_produkcji_h": [3, 5, 4, 6],
            "x": [10, 12, 8, 15],
            "y": [5, 6, 4, 7],
            "z": [1, 1, 1, 1],
            "ksztalt": ["kwadrat", "trapez", "trojkat", "kwadrat"],
            "material": ["bawelna", "wiskoza", "mikrofibra", "poliester"],
        }
    )


def test_save_and_load_model_pack_roundtrip_preserves_structure(tmp_path):
    pack = {
        "quality": PickleableDummyModel("quality"),
        "delay": PickleableDummyModel("delay"),
        "schedule": None,
        "scaler": {"type": "mock-scaler"},
        "selected_models": ["Quality", "Delay"],
        "backend": "classic",
    }

    path = tmp_path / "model_pack.pkl"
    save_model_pack(pack, path)
    loaded = load_model_pack(path)

    assert path.exists()
    assert set(loaded.keys()) == {
        "quality",
        "delay",
        "schedule",
        "scaler",
        "selected_models",
        "backend",
    }
    assert loaded["quality"].name == "quality"
    assert loaded["delay"].name == "delay"
    assert loaded["schedule"] is None
    assert loaded["scaler"] == {"type": "mock-scaler"}
    assert loaded["selected_models"] == ["Quality", "Delay"]
    assert loaded["backend"] == "classic"


def test_train_models_flow_saves_pack_with_generated_filename(
    tmp_path,
    monkeypatch,
    training_df,
):
    expected_path = tmp_path / "trained_pack.pkl"
    fake_pack = {
        "quality": PickleableDummyModel("quality"),
        "delay": None,
        "schedule": None,
        "scaler": {"type": "mock-scaler"},
        "selected_models": ["Quality"],
        "backend": "tabpfn",
    }

    monkeypatch.setattr(
        training_services,
        "build_model_filename",
        lambda *_args, **_kwargs: expected_path,
    )
    monkeypatch.setattr(training_services, "train_selected_models", lambda **_kwargs: fake_pack)

    result = services.train_models_flow(
        training_df,
        selected_models=["Quality"],
        metadata={"n": 4, "n_machines": 1},
        backend="tabpfn",
    )

    assert result["model_path"] == expected_path
    assert expected_path.exists()

    loaded = load_model_pack(expected_path)
    assert loaded["quality"].name == "quality"
    assert loaded["selected_models"] == ["Quality"]
    assert loaded["backend"] == "tabpfn"
    assert any("Trening zakończony" in message for message in result["messages"])
    assert any("backend: TabPFN" in message for message in result["messages"])


@pytest.mark.parametrize(
    ("df_train", "selected_models", "message"),
    [
        (None, ["Quality"], "Brak danych treningowych"),
        (pd.DataFrame(), ["Quality"], "Brak danych treningowych"),
        (pd.DataFrame({"a": [1]}), [], "Nie wybrano żadnego modelu do trenowania"),
    ],
)
def test_train_models_flow_validates_inputs(df_train, selected_models, message):
    with pytest.raises(ValueError, match=message):
        services.train_models_flow(df_train, selected_models=selected_models)


def test_train_models_flow_reuses_training_data_from_previous_model_pack(
    tmp_path,
    monkeypatch,
    training_df,
):
    first_df = training_df.iloc[:2].copy()
    second_df = training_df.iloc[2:].copy()
    previous_path = tmp_path / "previous.pkl"
    target_path = tmp_path / "trained_pack.pkl"
    captured = {}

    save_model_pack(
        {
            "pack_kind": "ml",
            "backend": "classic",
            "selected_models": ["Quality"],
            "training_data": first_df,
        },
        previous_path,
    )

    monkeypatch.setattr(training_services, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(
        training_services,
        "build_model_filename",
        lambda *_args, **_kwargs: target_path,
    )

    def fake_train_selected_models(**kwargs):
        captured["df_train"] = kwargs["df_train"]
        return {
            "quality": PickleableDummyModel("quality"),
            "delay": None,
            "schedule": None,
            "scaler": None,
            "selected_models": ["Quality"],
            "backend": "classic",
        }

    monkeypatch.setattr(training_services, "train_selected_models", fake_train_selected_models)
    monkeypatch.setattr(
        training_services, "calculate_model_training_metrics", lambda *args, **kwargs: {}
    )

    result = services.train_models_flow(second_df, selected_models=["Quality"], backend="classic")

    assert len(captured["df_train"]) == len(training_df)
    assert result["model_pack"]["training_memory"]["history_rows"] == len(first_df)
    assert result["model_pack"]["training_memory"]["current_rows"] == len(second_df)
    assert result["model_pack"]["training_memory"]["total_rows"] == len(training_df)
    assert result["model_pack"]["training_memory"]["sources"] == ["previous.pkl"]
    assert target_path.exists()


@pytest.mark.parametrize("spec", ML_MODEL_SPECS, ids=lambda spec: spec.name)
def test_every_ml_model_can_be_saved_loaded_and_used_in_solve(spec, tmp_path, monkeypatch):
    _, train_df, test_df = generate_production_data(n=48, seed=321)
    data_path = tmp_path / f"test_{spec.name}.csv"
    model_path = tmp_path / f"model_{spec.name}.pkl"
    result_path = tmp_path / f"result_{spec.name}.csv"
    test_df.to_csv(data_path, index=False)

    monkeypatch.setattr(
        training_services,
        "build_result_filename",
        lambda model_name, source_name, suffix=".csv": result_path,
    )

    pack = train_selected_models(train_df, [spec.name], backend="classic")
    pack["pack_kind"] = "ml"
    save_model_pack(pack, model_path)

    loaded = load_model_pack(model_path)
    assert spec.name in loaded["ml_models"]

    result = services.solve_models_flow(model_path, data_path)

    assert result_path.exists()
    assert not result["df"].empty
