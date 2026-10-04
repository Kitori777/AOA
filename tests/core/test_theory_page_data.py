from __future__ import annotations

import pytest

from AOA.core.mh_models.specs import MH_MODEL_SPECS
from AOA.core.optimization.models import Job
from AOA.core.optimization.runner import run_selected_sto_models
from AOA.gui.pages.theory_page.animation import ModelAnimationCard
from AOA.gui.pages.theory_page.data import find_theory_model, get_theory_models
from AOA.gui.pages.theory_page.heuristics import HEURISTIC_THEORY


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
    content = " ".join(
        (*model.step_details, *model.pseudocode, *model.next_steps, model.tip)
    ).lower()

    assert "walidac" in content
    assert "train/test" in content
    assert "tabpfn" in content
    assert "compare_with_baseline_and_tabpfn" in content


def test_modern_theory_models_use_distinct_animation_kinds() -> None:
    assert ModelAnimationCard._modern_visual_kind(find_theory_model("tabpfn_quality")) == "tabpfn"
    assert (
        ModelAnimationCard._modern_visual_kind(find_theory_model("modern_xgboost_quality"))
        == "xgboost"
    )
    assert ModelAnimationCard._modern_visual_kind(find_theory_model("modern_mlp_delay")) == "mlp"
    assert (
        ModelAnimationCard._modern_visual_kind(find_theory_model("modern_stacking_schedule"))
        == "stacking"
    )


def test_modern_theory_footer_formulas_are_model_specific() -> None:
    assert "tree_m" in ModelAnimationCard._formula_label("xgboost", "jakosc")
    assert "sigma" in ModelAnimationCard._formula_label("mlp", "opoznienie")
    assert "meta" in ModelAnimationCard._formula_label("stacking", "schedule")


def test_theory_exposes_three_user_sections_and_line_formulas() -> None:
    assert get_theory_models("ml")
    assert get_theory_models("mh")
    line_models = get_theory_models("line")
    assert {"line_flow", "line_time_formula", "line_kpi_formula"} == {
        model.key for model in line_models
    }
    assert all(model.family == "line" for model in line_models)
    assert all(len(model.steps) == 12 for model in line_models)


def test_every_builtin_heuristic_has_dedicated_learning_content() -> None:
    builtin_names = {spec.name for spec in MH_MODEL_SPECS}
    models = {model.key: model for model in get_theory_models("mh")}

    assert set(HEURISTIC_THEORY) == builtin_names
    assert builtin_names <= set(models)
    assert len({models[name].pseudocode for name in builtin_names}) == len(builtin_names)
    for name in builtin_names:
        model = models[name]
        assert len(model.step_details) == 12
        assert model.formula
        assert model.symbols
        assert model.worked_example
        assert model.complexity
        assert model.limitation
        assert len(model.example_order) == 4
        assert model.short_title == name


def test_heuristic_examples_match_the_real_scheduler() -> None:
    jobs = [
        Job("J1", 6, 10),
        Job("J2", 4, 11),
        Job("J3", 2, 8),
        Job("J4", 7, 18),
    ]
    method_names = [spec.name for spec in MH_MODEL_SPECS]

    results = {
        result["method"]: result
        for result in run_selected_sto_models(jobs, method_names, n_machines=1)
    }

    for name, theory in HEURISTIC_THEORY.items():
        assert tuple(results[name]["order"]) == theory.example_order
        assert results[name]["sto"] == pytest.approx(theory.example_sto)
