from __future__ import annotations

import pandas as pd
import pytest

from AOA.cli.helpers import AVAILABLE_ML_MODELS, AVAILABLE_STO_MODELS
from AOA.core.data_generation import generate_production_data
from AOA.core.mh_models import MH_MODEL_NAMES
from AOA.core.ml_models import ML_MODEL_NAMES, ML_MODEL_SPECS, ML_MODELS_BY_TASK, get_ml_task
from AOA.core.models import train_selected_models
from AOA.gui.pages.theory_page.animation import ModelAnimationCard
from AOA.gui.pages.theory_page.data import THEORY_MODELS


class _FastModel:
    def fit(self, X, y):
        self.n_features_in_ = getattr(X, "shape", [0, 0])[1]
        return self

    def predict(self, X):
        return [0 for _ in range(len(X))]


def _tiny_schedule_frame():
    return (
        pd.DataFrame(
            {
                "job_count": [5, 6, 7, 8, 9, 10],
                "avg_processing_time": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                "max_processing_time": [5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
                "avg_deadline": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0],
                "min_deadline": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
                "deadline_spread": [6.0, 7.0, 8.0, 9.0, 10.0, 11.0],
            }
        ),
        pd.Series(["MT", "MO", "MZO", "MT", "MO", "MZO"]),
    )


def test_ml_registry_contains_twelve_models_grouped_by_task():
    assert len(ML_MODEL_SPECS) == 12
    assert len(ML_MODELS_BY_TASK["quality"]) == 4
    assert len(ML_MODELS_BY_TASK["delay"]) == 4
    assert len(ML_MODELS_BY_TASK["schedule"]) == 4
    assert {spec.name for spec in ML_MODEL_SPECS} == set().union(*ML_MODELS_BY_TASK.values())


def test_cli_uses_ml_registry_model_names():
    assert AVAILABLE_ML_MODELS == ML_MODEL_NAMES


def test_cli_uses_sto_registry_model_names():
    assert AVAILABLE_STO_MODELS == MH_MODEL_NAMES


@pytest.mark.parametrize("spec", ML_MODEL_SPECS, ids=lambda spec: spec.name)
def test_every_ml_model_can_be_selected_and_trained(spec, monkeypatch):
    from AOA.core import models

    _, train_df, _ = generate_production_data(n=32, seed=123)
    monkeypatch.setattr(models, "build_regressor", lambda model_name: _FastModel())
    monkeypatch.setattr(models, "build_classifier", lambda model_name: _FastModel())

    if spec.task == "schedule":
        monkeypatch.setattr(
            models,
            "_build_schedule_training_frame",
            lambda *args, **kwargs: _tiny_schedule_frame(),
        )

    pack = train_selected_models(train_df, [spec.name], backend="classic")

    assert pack["selected_models"] == [spec.name]
    assert spec.name in pack["ml_models"]
    assert pack["ml_models"][spec.name] is not None
    assert get_ml_task(spec.name) == spec.task

    if spec.task == "quality":
        assert pack["quality"] is pack["ml_models"][spec.name]
    elif spec.task == "delay":
        assert pack["delay"] is pack["ml_models"][spec.name]
    else:
        assert pack["schedule"] is pack["ml_models"][spec.name]


@pytest.mark.parametrize("spec", ML_MODEL_SPECS, ids=lambda spec: spec.name)
def test_every_ml_model_has_theory_card_with_full_step_animation(spec):
    theory_by_key = {model.key: model for model in THEORY_MODELS if model.family == "ml"}

    card = theory_by_key[spec.name]

    assert card.title
    assert card.goal
    assert card.algorithm
    assert len(card.steps) == 12
    assert len(card.step_details) == 12
    assert len(card.pseudocode) == 12
    assert len(card.next_steps) >= 3


def test_theory_explains_ml_algorithms_with_correct_mechanics():
    theory_by_key = {model.key: model for model in THEORY_MODELS if model.family == "ml"}

    forest = theory_by_key["Quality"]
    extra = theory_by_key["Quality_ET"]
    boosting = theory_by_key["Delay"]
    hist = theory_by_key["Quality_HGB"]
    logistic = theory_by_key["Schedule_LOG"]

    assert "drzewa nie potrzebuja skalowania" in " ".join(forest.step_details)
    assert "Losowe progi" in extra.steps
    assert "blad" in " ".join(boosting.step_details).lower()
    assert "koszyki" in " ".join(hist.step_details).lower()
    assert "granice liniowa" in " ".join(logistic.step_details).lower()


def test_theory_keeps_sto_separate_from_ml_training():
    sto_cards = [model for model in THEORY_MODELS if model.family == "mh"]

    assert sto_cards
    joined = " ".join(sto_cards[0].step_details + (sto_cards[0].tip,))
    assert "nie trenuje modelu ML" in joined
    assert "STO to suma dodatnich opoznien" in joined


def test_theory_animation_uses_distinct_ml_visual_modes():
    theory_by_key = {model.key: model for model in THEORY_MODELS if model.family == "ml"}

    assert ModelAnimationCard._ml_visual_kind(theory_by_key["Quality"]) == "forest"
    assert ModelAnimationCard._ml_visual_kind(theory_by_key["Quality_ET"]) == "extra"
    assert ModelAnimationCard._ml_visual_kind(theory_by_key["Delay"]) == "boost"
    assert ModelAnimationCard._ml_visual_kind(theory_by_key["Quality_HGB"]) == "hist"
    assert ModelAnimationCard._ml_visual_kind(theory_by_key["Schedule_LOG"]) == "logistic"
