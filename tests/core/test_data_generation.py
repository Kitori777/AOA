from AOA.core.data_generation import generate_production_data


def test_generate_production_data_returns_dataframes():
    df, train_df, test_df = generate_production_data(n=100, n_machines=2)

    assert len(df) == 100
    assert not train_df.empty
    assert not test_df.empty
    assert "cena" in df.columns
    assert "lateness_h_sim" in df.columns
