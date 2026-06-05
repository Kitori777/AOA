import pandas as pd


def prepare_gantt_chart_data(df: pd.DataFrame):
    duration_col = "czas_produkcji_h" if "czas_produkcji_h" in df.columns else None
    if duration_col is None:
        raise ValueError("Gantt wymaga kolumny 'czas_produkcji_h'")

    machine_col = None
    for candidate in ("machine_id", "recommended_machine", "maszyna", "machine"):
        if candidate in df.columns:
            machine_col = candidate
            break

    job_col = None
    for candidate in ("sto_job_id", "job_id", "zlecenie", "id", "ksztalt"):
        if candidate in df.columns:
            job_col = candidate
            break

    start_col = "sto_start" if "sto_start" in df.columns else None
    end_col = "sto_end" if "sto_end" in df.columns else None

    required = [duration_col]
    if machine_col:
        required.append(machine_col)
    if job_col:
        required.append(job_col)
    if start_col:
        required.append(start_col)
    if end_col:
        required.append(end_col)

    df_g = df[required].copy()
    df_g[duration_col] = pd.to_numeric(df_g[duration_col], errors="coerce")
    if start_col:
        df_g[start_col] = pd.to_numeric(df_g[start_col], errors="coerce")
    if end_col:
        df_g[end_col] = pd.to_numeric(df_g[end_col], errors="coerce")
    df_g = df_g.dropna(subset=[duration_col])
    if df_g.empty:
        raise ValueError("Brak danych do wykresu Gantta")

    if machine_col is None:
        df_g["_machine"] = "M1"
    else:
        df_g["_machine"] = df_g[machine_col].astype(str)
    if job_col is None:
        df_g["_job"] = [f"zad_{i + 1}" for i in range(len(df_g))]
    else:
        df_g["_job"] = df_g[job_col].astype(str)

    # Jeśli mamy start/end ze STO, używamy ich bezpośrednio.
    if start_col and end_col and df_g[start_col].notna().any() and df_g[end_col].notna().any():
        starts = df_g[start_col].fillna(0.0)
        durations = (df_g[end_col] - df_g[start_col]).where(
            (df_g[end_col] - df_g[start_col]) > 0, df_g[duration_col]
        )
    else:
        # W przeciwnym razie budujemy harmonogram sekwencyjnie per maszyna.
        starts = []
        durations = df_g[duration_col].fillna(0.0)
        machine_clocks: dict[str, float] = {}
        for _, row in df_g.iterrows():
            machine = row["_machine"]
            start = machine_clocks.get(machine, 0.0)
            starts.append(start)
            machine_clocks[machine] = start + float(row[duration_col])
        starts = pd.Series(starts, index=df_g.index, dtype=float)

    df_g["_start"] = starts.astype(float)
    df_g["_duration"] = durations.astype(float)
    df_g = df_g.sort_values(["_machine", "_start", "_job"], kind="stable")

    return {
        "labels": df_g["_job"],
        "machines": df_g["_machine"],
        "durations": df_g["_duration"],
        "starts": df_g["_start"],
        "x_label": "Czas [h]",
    }
