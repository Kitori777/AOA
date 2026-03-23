import pandas as pd


def prepare_gantt_chart_data(df: pd.DataFrame):
    required_cols = {"ksztalt", "czas_produkcji_h"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Gantt wymaga kolumn 'ksztalt' i 'czas_produkcji_h'")

    df_g = df[["ksztalt", "czas_produkcji_h"]].dropna().copy()
    if df_g.empty:
        raise ValueError("Brak danych do wykresu Gantta")

    starts = df_g["czas_produkcji_h"].cumsum() - df_g["czas_produkcji_h"]

    return {
        "labels": df_g["ksztalt"],
        "durations": df_g["czas_produkcji_h"],
        "starts": starts,
        "x_label": "Czas [h]",
    }
