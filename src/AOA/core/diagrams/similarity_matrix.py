import numpy as np
import pandas as pd
from sklearn.metrics import jaccard_score
from sklearn.preprocessing import LabelEncoder


def prepare_similarity_matrix_data(df: pd.DataFrame):
    if df.empty:
        raise ValueError("Brak danych do macierzy podobieństwa")

    bin_df = pd.DataFrame()

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            bin_df[col] = (df[col] >= df[col].median()).astype(int)
        else:
            bin_df[col] = LabelEncoder().fit_transform(df[col].astype(str))

    n = len(bin_df.columns)
    sim = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            sim[i, j] = jaccard_score(
                bin_df.iloc[:, i],
                bin_df.iloc[:, j],
                average="macro"
            )

    return {
        "matrix": sim,
        "labels": list(bin_df.columns),
        "title": "Macierz podobieństw (Jaccard)",
    }
