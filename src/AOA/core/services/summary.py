from __future__ import annotations

from .common import split_selected_models


def build_main_page_summary(config: dict) -> str:
    selected_models = config.get("selected_models", [])
    ml_models, sto_models = split_selected_models(selected_models)

    selected_ksztalty = config.get("selected_ksztalty", [])
    selected_materialy = config.get("selected_materialy", [])
    backend = config.get("backend", "classic")
    backend_label = "TabPFN (eksperymentalny)" if backend == "tabpfn" else "Klasyczny"

    return (
        "AKTUALNA KONFIGURACJA\n"
        "======================\n\n"
        f"Backend ML: {backend_label}\n\n"
        f"Modele ML:\n - {', '.join(ml_models) if ml_models else 'brak'}\n\n"
        f"Modele STO:\n - {', '.join(sto_models) if sto_models else 'brak'}\n\n"
        f"Liczba rekordów: {config.get('n', '')}\n"
        f"Liczba maszyn: {config.get('n_machines', '')}\n"
        f"Test size: {config.get('test_size', '')}\n"
        f"Seed: {config.get('seed', '')}\n\n"
        f"Czas produkcji [h]: {config.get('prod_min', '')} -> {config.get('prod_max', '')}\n"
        f"Bufor terminu [h]: {config.get('deadline_min', '')} -> {config.get('deadline_max', '')}\n\n"
        f"Kształty:\n - {', '.join(selected_ksztalty) if selected_ksztalty else 'brak'}\n\n"
        f"Materiały:\n - {', '.join(selected_materialy) if selected_materialy else 'brak'}\n"
    )


def build_main_page_status(df_train=None, df_test=None) -> str:
    if df_train is None and df_test is None:
        return "Brak danych treningowych"

    train_count = len(df_train) if df_train is not None else 0
    test_count = len(df_test) if df_test is not None else 0
    total_count = train_count + test_count

    return (
        "Aktualnie załadowane dane\n"
        f"Łącznie: {total_count} rekordów\n"
        f"Train: {train_count} rekordów\n"
        f"Test: {test_count} rekordów"
    )


def build_dataframe_preview_text(df, title="Podgląd danych", max_rows=15):
    if df is None:
        return f"{title}\n\nBrak danych."
    if df.empty:
        return f"{title}\n\nDataFrame jest pusty."

    preview = df.head(max_rows).to_string(index=True)
    return (
        f"{title}\n"
        f"{'=' * len(title)}\n\n"
        f"Liczba rekordów: {len(df)}\n"
        f"Liczba kolumn: {len(df.columns)}\n\n"
        f"{preview}"
    )
