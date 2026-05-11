from __future__ import annotations

import argparse

from AOA.core.services import (
    generate_and_store_datasets,
    solve_models_flow,
    train_models_flow,
    train_sto_models_flow,
)

from ..helpers import (
    AVAILABLE_ML_MODELS,
    AVAILABLE_STO_MODELS,
    hr,
    parse_csv_list,
    print_key_value,
    print_messages,
    progress_callback,
)


def command_workflow(args: argparse.Namespace) -> int:
    selected_models = parse_csv_list(args.models)
    if not selected_models:
        raise ValueError("Nie podano modeli do workflow.")
    ml_models = [m for m in selected_models if m in AVAILABLE_ML_MODELS]
    sto_models = [m for m in selected_models if m in AVAILABLE_STO_MODELS]
    invalid_models = [
        m for m in selected_models if m not in AVAILABLE_ML_MODELS | AVAILABLE_STO_MODELS
    ]
    if invalid_models:
        raise ValueError(f"Nieprawidłowe modele: {', '.join(invalid_models)}")

    hr("WORKFLOW | GENEROWANIE")
    gen_result = generate_and_store_datasets(
        n=args.n,
        n_machines=args.machines,
        test_size=args.test_size,
        seed=args.seed,
        ksztalty=parse_csv_list(args.shapes),
        materialy=parse_csv_list(args.materials),
        production_time_range=(args.prod_min, args.prod_max),
        deadline_buffer_range=(args.deadline_min, args.deadline_max),
    )
    print_messages(gen_result.get("messages"))
    ml_model_path = None

    if ml_models:
        hr("WORKFLOW | TRENING ML")
        train_result = train_models_flow(
            df_train=gen_result["train_df"],
            selected_models=ml_models,
            metadata={
                "n": args.n,
                "n_machines": args.machines,
                "ksztalty": parse_csv_list(args.shapes),
                "materialy": parse_csv_list(args.materials),
            },
            progress_callback=progress_callback,
            backend=args.backend,
            df_test=gen_result.get("test_df"),
        )
        print_messages(train_result.get("messages"))
        ml_model_path = train_result["model_path"]

    if sto_models:
        hr("WORKFLOW | ZAPIS STO")
        sto_result = train_sto_models_flow(sto_models)
        print_messages(sto_result.get("messages"))

    if ml_models and not args.skip_solve and ml_model_path is not None:
        hr("WORKFLOW | ROZWIĄZYWANIE TESTU")
        solve_result = solve_models_flow(
            model_path=str(ml_model_path), data_path=str(gen_result["test_path"])
        )
        print_messages(solve_result.get("messages"))
        print_key_value("WYNIK_TEST", solve_result["result_path"])

    hr("WORKFLOW | KONIEC")
    print_key_value("FULL", gen_result["full_path"])
    print_key_value("TRAIN", gen_result["train_path"])
    print_key_value("TEST", gen_result["test_path"])
    if ml_model_path is not None:
        print_key_value("MODEL_ML", ml_model_path)
    return 0
