from matplotlib.figure import Figure

from AOA.core.learning_content import build_learning_figure, get_guide_steps, get_theory_modules


def test_guide_steps_are_interactive_and_ordered():
    steps = get_guide_steps()

    assert len(steps) >= 6
    assert steps[0].title.startswith("1.")
    assert all(step.clicks for step in steps)
    assert all(step.explanation for step in steps)


def test_theory_modules_have_formulas_and_figures():
    modules = get_theory_modules()

    assert len(modules) >= 8
    assert all(module.formula for module in modules)

    for module in modules:
        fig = build_learning_figure(module.key)
        assert isinstance(fig, Figure)
        assert fig.axes
