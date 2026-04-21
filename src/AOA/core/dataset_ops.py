import pandas as pd


def split_train_test(df: pd.DataFrame, train_ratio: float = 0.8):
    """Split a DataFrame into train and test subsets preserving row order.

    Args:
        df: Input DataFrame with rows to split.
        train_ratio: Fraction of rows assigned to the training subset.

    Returns:
        Tuple of `(df_train, df_test)`.

    Raises:
        ValueError: If the input DataFrame is empty, the ratio is invalid, or
            the resulting split would create an empty subset.
    """
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
