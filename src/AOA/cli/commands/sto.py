from __future__ import annotations

import argparse

from AOA.core.services import analyze_sto_models, solve_sto_with_saved_model, train_sto_models_flow

from ..helpers import (
    AVAILABLE_STO_MODELS,
    hr,
    logger,
    parse_csv_list,
    print_key_value,
    print_messages,
    resolve_existing_file,
    validate_models,
)


def command_sto_run(args: argparse.Namespace) -> int:
    methods = validate_models(parse_csv_list(args.methods), AVAILABLE_STO_MODELS, "metody STO")
    result = analyze_sto_models(
        job_ids_text=args.jobs,
        processing_text=args.times,
        deadlines_text=args.deadlines,
        selected_methods=methods,
        n_machines=getattr(args, "machines", 1),
    )
    print_messages(result.get("messages"))
    hr("RAPORT STO")
    logger.info("%s", result["report"])
    if result.get("saved_paths"):
        hr("ZAPISANE PLIKI")
        for item in result["saved_paths"]:
            logger.info("%s: %s | STO=%.3f", item["method"], item["path"], item["sto"])
    if result.get("best_path"):
        logger.info("")
        logger.info("BEST: %s", result["best_path"])
    if result.get("visual_path"):
        logger.info("VISUAL_STO: %s", result["visual_path"])
    return 0


def command_sto_train(args: argparse.Namespace) -> int:
    methods = validate_models(parse_csv_list(args.methods), AVAILABLE_STO_MODELS, "metody STO")
    machine_count = getattr(args, "machines", 1)
    result = (
        train_sto_models_flow(methods)
        if machine_count == 1
        else train_sto_models_flow(methods, n_machines=machine_count)
    )
    hr("ZAPIS STO")
    print_messages(result.get("messages"))
    print_key_value("MODEL_STO", result["model_path"])
    return 0


def command_sto_solve(args: argparse.Namespace) -> int:
    model_path = resolve_existing_file(args.model, "pliku modelu STO")
    data_path = resolve_existing_file(args.data, "pliku danych STO")
    bom_raw = getattr(args, "bom", None)
    inventory_raw = getattr(args, "inventory", None)
    if bom_raw or inventory_raw:
        bom_path = resolve_existing_file(bom_raw, "pliku BOM") if bom_raw else None
        inventory_path = (
            resolve_existing_file(inventory_raw, "pliku magazynu") if inventory_raw else None
        )
        result = solve_sto_with_saved_model(
            model_path=str(model_path),
            data_path=str(data_path),
            bom_path=str(bom_path) if bom_path else None,
            inventory_path=str(inventory_path) if inventory_path else None,
        )
    else:
        result = solve_sto_with_saved_model(model_path=str(model_path), data_path=str(data_path))
    print_messages(result.get("messages"))
    hr("RAPORT STO")
    logger.info("%s", result["report"])
    if result.get("saved_paths"):
        hr("ZAPISANE PLIKI")
        for item in result["saved_paths"]:
            logger.info("%s: %s | STO=%.3f", item["method"], item["path"], item["sto"])
    if result.get("best_path"):
        logger.info("")
        logger.info("BEST: %s", result["best_path"])
    if result.get("visual_path"):
        logger.info("VISUAL_STO: %s", result["visual_path"])
    return 0
