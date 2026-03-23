import numpy as np
import pandas as pd


def prepare_correlation_matrix_data(df: pd.DataFrame):
    numeric_df = df.select_dtypes(include=np.number)
    if numeric_df.empty:
        raise ValueError("Brak kolumn numerycznych do macierzy korelacji")

    corr = numeric_df.corr()
    return {
        "matrix": corr,
        "title": "Macierz korelacji",
    }
