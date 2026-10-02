import pandas as pd

from AOA.core.scheduling import (
    extract_schedule_features,
    generate_schedule_label,
    optimize_schedule,
    simulate_schedule,
)


def _df():
    return pd.DataFrame(
        {
            "czas_produkcji_h": [5.0, 1.0, 2.0],
            "termin_h": [100.0, 2.0, 4.0],
            "cena": [10.0, 20.0, 30.0],
        }
    )


def test_optimize_schedule_returns_best_strategy_with_required_columns():
    result = optimize_schedule(_df())

    assert {"t_start", "t_end", "lateness_h", "strategy", "total_time", "total_lateness"}.issubset(
        result.columns
    )
    assert result["strategy"].iloc[0] in {"EDF", "SPT", "LPT", "Slack"}


def test_simulate_schedule_preserves_input_order_and_adds_time_columns():
    df = _df()
    result = simulate_schedule(df)

    pd.testing.assert_series_equal(
        result["czas_produkcji_h"], df["czas_produkcji_h"], check_names=False
    )
    assert result["t_start"].tolist() == [0.0, 5.0, 6.0]
    assert result["t_end"].tolist() == [5.0, 6.0, 8.0]
    assert result["lateness_h"].tolist() == [0.0, 4.0, 4.0]


def test_simulate_schedule_waits_for_components_and_keeps_shortage_visible():
    df = _df()
    df["components_ready_h"] = [7.0, 0.0, float("nan")]
    df["stock_status"] = ["WAITING_COMPONENTS", "READY", "UNSCHEDULABLE"]

    result = simulate_schedule(df, n_machines=1)

    assert result.loc[0, "t_start"] == 7.0
    assert result.loc[0, "material_wait_h_actual"] == 7.0
    assert result.loc[2, "scheduled"] == False  # noqa: E712
    assert result.loc[2, "machine_id"] == 0


def test_two_machine_schedule_keeps_ids_and_excludes_unavailable_machine():
    df = _df()
    df["dozwolone_maszyny"] = ["1|2", "1|2", "1|2"]

    baseline = simulate_schedule(df, n_machines=2)
    all_working = simulate_schedule(df, n_machines=2, unavailable_machines=())
    outage = simulate_schedule(df, n_machines=2, unavailable_machines=(2,))

    pd.testing.assert_frame_equal(baseline, all_working)
    assert set(outage.loc[outage["scheduled"], "machine_id"]) == {1}
    assert outage["scheduled"].all()


def test_schedule_reports_jobs_when_every_allowed_machine_is_unavailable():
    df = _df().iloc[:1].copy()
    df["dozwolone_maszyny"] = ["2"]

    result = simulate_schedule(df, n_machines=2, unavailable_machines=(2,))

    assert result.loc[0, "scheduled"] == False  # noqa: E712
    assert result.loc[0, "machine_id"] == 0
    assert "niedostepne" in result.loc[0, "unscheduled_reason"]


def test_extract_schedule_features_returns_expected_keys():
    features = extract_schedule_features(_df())

    assert set(features) == {
        "n_jobs",
        "mean_time",
        "std_time",
        "max_time",
        "mean_deadline",
        "load_ratio",
    }
    assert features["n_jobs"] == 3


def test_generate_schedule_label_returns_known_strategy_name():
    label = generate_schedule_label(_df())

    assert label in {"EDF", "SPT", "LPT", "Slack"}
