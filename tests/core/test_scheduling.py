from AOA.core.data_generation import generate_production_data
from AOA.core.scheduling import optimize_schedule, simulate_schedule


def test_optimize_schedule_adds_strategy_and_lateness():
    df, _, _ = generate_production_data(n=30)
    result = optimize_schedule(df)

    assert "strategy" in result.columns
    assert "lateness_h" in result.columns
    assert result["strategy"].iloc[0] in {"EDF", "SPT", "LPT", "Slack"}


def test_simulate_schedule_adds_time_columns():
    df, _, _ = generate_production_data(n=20)
    result = simulate_schedule(df)

    assert "t_start" in result.columns
    assert "t_end" in result.columns
    assert "lateness_h" in result.columns
