from __future__ import annotations

from AOA.gui.pages.theory_page.animation import ModelAnimationCard
from AOA.gui.pages.theory_page.data import find_theory_model, get_theory_models


def test_theory_modern_models_include_required_segments() -> None:
    models = get_theory_models("tabpfn")
    by_key = {model.key: model for model in models}

    assert {
        "tabpfn_quality",
        "tabpfn_delay",
        "tabpfn_schedule",
        "modern_xgboost_quality",
        "modern_mlp_delay",
        "modern_stacking_schedule",
    } <= set(by_key)
    assert by_key["modern_xgboost_quality"].algorithm == "xgboost.XGBRegressor"
    assert by_key["modern_mlp_delay"].algorithm == "sklearn.neural_network.MLPRegressor"
    assert by_key["modern_stacking_schedule"].algorithm == "sklearn.ensemble.StackingClassifier"


def test_theory_modern_models_have_complete_learning_content() -> None:
    for model in get_theory_models("tabpfn"):
        assert model.steps, model.key
        assert model.step_details, model.key
        assert model.pseudocode, model.key
        assert model.next_steps, model.key
        assert model.tip, model.key


def test_modern_xgboost_theory_mentions_validation_and_baselines() -> None:
    model = find_theory_model("modern_xgboost_quality")
    content = " ".join((*model.step_details, *model.pseudocode, *model.next_steps, model.tip)).lower()

    assert "walidac" in content
    assert "train/test" in content
    assert "tabpfn" in content
    assert "compare_with_baseline_and_tabpfn" in content


def test_modern_theory_models_use_distinct_animation_kinds() -> None:
    assert ModelAnimationCard._modern_visual_kind(find_theory_model("tabpfn_quality")) == "tabpfn"
    assert ModelAnimationCard._modern_visual_kind(find_theory_model("modern_xgboost_quality")) == "xgboost"
    assert ModelAnimationCard._modern_visual_kind(find_theory_model("modern_mlp_delay")) == "mlp"
    assert ModelAnimationCard._modern_visual_kind(find_theory_model("modern_stacking_schedule")) == "stacking"


def test_modern_theory_footer_formulas_are_model_specific() -> None:
    assert "tree_m" in ModelAnimationCard._formula_label("xgboost", "jakosc")
    assert "sigma" in ModelAnimationCard._formula_label("mlp", "opoznienie")
    assert "meta" in ModelAnimationCard._formula_label("stacking", "schedule")
