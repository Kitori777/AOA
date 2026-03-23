import pandas as pd


def prepare_line_chart_data(df: pd.DataFrame, x_col: str, y_col: str, window: int = 5):
    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError("Wybrane kolumny nie istnieją w danych")

    df_line = (
        df[[x_col, y_col]]
        .dropna()
        .sort_values(by=x_col)
        .reset_index(drop=True)
    )

    if df_line.empty:
        raise ValueError("Brak danych do wykresu liniowego")

    x = df_line[x_col]
    y = df_line[y_col]
    y_smooth = y.rolling(window=window, center=True).mean()

    return {
        "x": x,
        "y": y,
        "y_smooth": y_smooth,
        "x_label": x_col,
        "y_label": y_col,
        "title": "Wykres liniowy – wygładzony",
    }
