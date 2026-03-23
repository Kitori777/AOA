import pandas as pd


def split_train_test(df: pd.DataFrame, train_ratio: float = 0.8):
    if df is None or df.empty:
        raise ValueError("Brak danych do podziału")

    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio musi być w przedziale (0, 1)")

    split_index = int(len(df) * train_ratio)
    df_train = df.iloc[:split_index].copy()
    df_test = df.iloc[split_index:].copy()

    if df_train.empty or df_test.empty:
        raise ValueError("Podział train/test zwrócił pusty zbiór")

    return df_train, df_test
