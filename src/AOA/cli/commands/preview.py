from __future__ import annotations

import argparse

from AOA.core.data_io import load_csv
from AOA.core.services import (
    build_dataframe_preview_text,
    build_main_page_status,
    build_main_page_summary,
    load_training_data,
    split_selected_models,
)

from ..helpers import (
    AVAILABLE_ML_MODELS,
    AVAILABLE_STO_MODELS,
    logger,
    parse_csv_list,
    print_key_value,
    resolve_existing_file,
)


def command_preview(args: argparse.Namespace) -> int:
    data_path = resolve_existing_file(args.data, "pliku danych")
    df = load_csv(data_path)
    logger.info(
        "%s",
        build_dataframe_preview_text(df, title=f"Podgląd: {data_path.name}", max_rows=args.rows),
    )
    return 0


def command_summary(args: argparse.Namespace) -> int:
    selected_models = parse_csv_list(args.models)
    ml_models, sto_models = split_selected_models(selected_models)
    invalid = [m for m in selected_models if m not in AVAILABLE_ML_MODELS | AVAILABLE_STO_MODELS]
    if invalid:
        raise ValueError(f"Nieprawidłowe modele: {', '.join(invalid)}")
    config = {
        "selected_models": ml_models + sto_models,
        "selected_ksztalty": parse_csv_list(args.shapes),
        "selected_materialy": parse_csv_list(args.materials),
        "n": args.n,
        "n_machines": args.machines,
        "test_size": args.test_size,
        "seed": args.seed,
        "prod_min": args.prod_min,
        "prod_max": args.prod_max,
        "deadline_min": args.deadline_min,
        "deadline_max": args.deadline_max,
        "backend": args.backend,
    }
    from ..helpers import hr

    hr("PODSUMOWANIE KONFIGURACJI")
    logger.info("%s", build_main_page_summary(config))
    return 0


def command_status(args: argparse.Namespace) -> int:
    from ..helpers import hr

    if not args.data:
        hr("STATUS")
        logger.info("%s", build_main_page_status(None, None))
        return 0
    data_path = resolve_existing_file(args.data, "pliku danych")
    loaded = load_training_data(path=str(data_path), train_ratio=args.train_ratio)
    hr("STATUS")
    logger.info("%s", build_main_page_status(loaded["train_df"], loaded["test_df"]))
    print_key_value("ŹRÓDŁO", data_path)
    return 0
