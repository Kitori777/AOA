import pandas as pd


def load_csv(path):
    """Load a CSV file into a pandas DataFrame.

    Args:
        path: Path to the CSV file.

    Returns:
        Loaded pandas DataFrame.
    """
    return pd.read_csv(path)


def save_csv(df, path):
    """Save a pandas DataFrame to CSV without the index column.

    Args:
        df: DataFrame to save.
        path: Target file path.
    """
    df.to_csv(path, index=False)
