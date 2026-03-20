import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from AOA.core.constants import KSZTALT_DIMENSIONS


def generate_production_data(n=5000, n_machines=1, test_size=0.2, seed=42):
    np.random.seed(seed)

    ksztalty = list(KSZTALT_DIMENSIONS.keys())
    materialy = ["bawelna", "mikrofibra", "poliester", "wiskoza"]

    ksztalt_col = np.random.choice(ksztalty, n)
    material_col = np.random.choice(materialy, n)

    x_col = [KSZTALT_DIMENSIONS[k]["x"] for k in ksztalt_col]
    y_col = [KSZTALT_DIMENSIONS[k]["y"] for k in ksztalt_col]
    z_col = [KSZTALT_DIMENSIONS[k]["z"] for k in ksztalt_col]

    termin_dni = np.random.randint(1, 30, n)
    czas_produkcji_h = np.random.uniform(1, 48, n)

    df = pd.DataFrame({
        "cena": np.random.uniform(50, 500, n),
        "odpad": np.random.uniform(0, 0.3, n),
        "termin_dni": termin_dni,
        "czas_produkcji_h": czas_produkcji_h,
        "ksztalt": ksztalt_col,
        "material": material_col,
        "x": x_col,
        "y": y_col,
        "z": z_col,
    })

    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    machines = [0.0] * n_machines
    lateness_h = []

    for _, row in df.iterrows():
        next_machine_idx = int(np.argmin(machines))
        start = machines[next_machine_idx]
        end = start + row["czas_produkcji_h"]
        machines[next_machine_idx] = end

        deadline = row["termin_dni"] * 24
        late = max(0, end - deadline)
        lateness_h.append(late)

    df["lateness_h_sim"] = np.round(lateness_h, 3)
    df["lateness_d_sim"] = np.round(df["lateness_h_sim"] / 24, 3)

    train_df, test_df = train_test_split(df, test_size=test_size, random_state=seed)
    return df, train_df, test_df
