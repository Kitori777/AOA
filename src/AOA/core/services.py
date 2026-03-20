from AOA.core.data_generation import generate_production_data
from AOA.core.data_io import load_csv, save_csv
from AOA.core.features import prepare_features
from AOA.core.models import load_model_pack, save_model_pack, train_selected_models
from AOA.core.scheduling import simulate_schedule


def generate_and_split_data(n=5000, n_machines=1, test_size=0.2, seed=42):
    return generate_production_data(n=n, n_machines=n_machines, test_size=test_size, seed=seed)


def train_models_service(df_train, choice, model_path, progress_callback=None):
    pack = train_selected_models(df_train, choice=choice, progress_callback=progress_callback)
    save_model_pack(pack, model_path)
    return pack


def solve_existing_models_service(model_path, data_path, output_path):
    pack = load_model_pack(model_path)
    df_sol = load_csv(data_path)

    X, _, _, _ = prepare_features(df_sol, pack.get("scaler"))

    if pack.get("quality") is not None:
        df_sol["pred_quality"] = pack["quality"].predict(X)

    if pack.get("delay") is not None:
        df_sol["pred_delay"] = pack["delay"].predict(X)

    if "pred_quality" in df_sol.columns and "pred_delay" in df_sol.columns:
        df_sol["priority"] = df_sol["pred_quality"] / (df_sol["pred_delay"] + 1e-6)
        df_sol = df_sol.sort_values("priority", ascending=False)

    df_sol = simulate_schedule(df_sol)
    save_csv(df_sol, output_path)
    return df_sol
