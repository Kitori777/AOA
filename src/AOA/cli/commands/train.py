from __future__ import annotations

import argparse

from AOA.core.services import load_training_data, train_models_flow, train_sto_models_flow

from ..helpers import (
    AVAILABLE_ML_MODELS,
    AVAILABLE_STO_MODELS,
    hr,
    logger,
    parse_csv_list,
    print_key_value,
    print_messages,
    progress_callback,
    resolve_existing_file,
)


def command_train(args: argparse.Namespace) -> int:
    data_path = resolve_existing_file(args.data, "pliku danych")
    selected_models = parse_csv_list(args.models)
    if not selected_models:
        raise ValueError("Nie podano żadnych modeli.")

    ml_models = [m for m in selected_models if m in AVAILABLE_ML_MODELS]
    sto_models = [m for m in selected_models if m in AVAILABLE_STO_MODELS]
    invalid_models = [
        m for m in selected_models if m not in AVAILABLE_ML_MODELS | AVAILABLE_STO_MODELS
    ]
    if invalid_models:
        raise ValueError(
            f"Nieprawidłowe modele: {', '.join(invalid_models)}. "
            f"ML: {', '.join(sorted(AVAILABLE_ML_MODELS))}. "
            f"STO: {', '.join(sorted(AVAILABLE_STO_MODELS))}."
        )

    loaded = load_training_data(path=str(data_path), train_ratio=args.train_ratio)
    df_train = loaded["train_df"]
    hr("WCZYTANIE DANYCH")
    print_messages(loaded.get("messages"))

    if ml_models:
        metadata = {
            "n": args.n_meta if args.n_meta is not None else len(loaded["full_df"]),
            "n_machines": args.machines_meta if args.machines_meta is not None else "x",
            "ksztalty": parse_csv_list(args.shapes_meta),
            "materialy": parse_csv_list(args.materials_meta),
        }
        hr("TRENING ML")
        logger.info("Modele ML: %s", ", ".join(ml_models))
        logger.info("Backend: %s", args.backend)
        result = train_models_flow(
            df_train=df_train,
            selected_models=ml_models,
            metadata=metadata,
            progress_callback=progress_callback,
            backend=args.backend,
        )
        print_messages(result.get("messages"))
        print_key_value("MODEL_ML", result["model_path"])

    if sto_models:
        hr("ZAPIS STO")
        logger.info("Metody STO: %s", ", ".join(sto_models))
        result = train_sto_models_flow(sto_models)
        print_messages(result.get("messages"))
        print_key_value("MODEL_STO", result["model_path"])

    return 0
