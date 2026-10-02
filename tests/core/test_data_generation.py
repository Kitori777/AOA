from AOA.core.data_generation import generate_production_data


def test_generate_production_data_returns_dataframes():
    df, train_df, test_df = generate_production_data(n=100, n_machines=2)

    assert len(df) == 100
    assert not train_df.empty
    assert not test_df.empty
    assert "cena" in df.columns
    assert "lateness_h_sim" in df.columns


def test_generation_uses_requested_parallel_machine_counts_and_realistic_columns():
    required = {
        "zlecenie_id",
        "ilosc_szt",
        "zuzycie_materialu_m2",
        "odpad_kg",
        "czas_przezbrojenia_h",
        "energia_kwh",
        "defect_rate",
        "priorytet",
        "dozwolone_maszyny",
        "predkosc_maszyny",
        "wspolczynnik_odpadu_maszyny",
    }
    for machine_count in (1, 3, 4):
        df, _, _ = generate_production_data(n=120, n_machines=machine_count, seed=17)
        assert required.issubset(df.columns)
        assert df["machine_id"].nunique() == machine_count
        assert df["machine_id"].between(1, machine_count).all()
        assert (df["odpad_kg"] >= 0).all()
