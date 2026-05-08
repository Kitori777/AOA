from __future__ import annotations

import argparse
from typing import Any

from AOA.core.data_io import load_csv
from AOA.core.services import (
    analyze_sto_models,
    build_dataframe_preview_text,
    build_main_page_status,
    build_main_page_summary,
    generate_and_store_datasets,
    load_training_data,
    solve_models_flow,
    solve_sto_with_saved_model,
    split_selected_models,
    train_models_flow,
    train_sto_models_flow,
)
from AOA.utils.error_utils import write_exception_log
from AOA.utils.logging_utils import configure_logging

from .helpers import (
    AVAILABLE_ML_MODELS,
    AVAILABLE_STO_MODELS,
    DEFAULT_MATERIALS,
    DEFAULT_SHAPES,
    eprint,
    hr,
    logger,
    parse_csv_list,
    print_key_value,
    print_messages,
    progress_callback,
    resolve_existing_file,
    validate_models,
)
from .parser import build_examples_text as build_examples_text
from .parser import build_parser


def command_generate(args: Any) -> int:
    result = generate_and_store_datasets(
        n=args.n,
        n_machines=args.machines,
        test_size=args.test_size,
        seed=args.seed,
        ksztalty=parse_csv_list(args.shapes),
        materialy=parse_csv_list(args.materials),
        production_time_range=(args.prod_min, args.prod_max),
        deadline_buffer_range=(args.deadline_min, args.deadline_max),
    )
    hr("GENEROWANIE")
    print_messages(result.get("messages"))
    print_key_value("FULL", result["full_path"])
    print_key_value("TRAIN", result["train_path"])
    print_key_value("TEST", result["test_path"])
    return 0


def command_train(args: Any) -> int:
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
    hr("WCZYTANIE DANYCH")
    print_messages(loaded.get("messages"))

    if ml_models:
        hr("TRENING ML")
        logger.info("Modele ML: %s", ", ".join(ml_models))
        logger.info("Backend: %s", args.backend)

        result = train_models_flow(
            df_train=loaded["train_df"],
            selected_models=ml_models,
            metadata={
                "n": args.n_meta if args.n_meta is not None else len(loaded["full_df"]),
                "n_machines": args.machines_meta if args.machines_meta is not None else "x",
                "ksztalty": parse_csv_list(args.shapes_meta),
                "materialy": parse_csv_list(args.materials_meta),
            },
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


def command_solve(args: Any) -> int:
    model_path = resolve_existing_file(args.model, "pliku modelu")
    data_path = resolve_existing_file(args.data, "pliku danych")
    hr("ROZWIĄZYWANIE ML")
    print_key_value("MODEL", model_path)
    print_key_value("DATA", data_path)
    result = solve_models_flow(model_path=str(model_path), data_path=str(data_path))
    print_messages(result.get("messages"))
    print_key_value("WYNIK", result["result_path"])

    return 0


def command_sto_run(args: Any) -> int:
    methods = validate_models(parse_csv_list(args.methods), AVAILABLE_STO_MODELS, "metody STO")

    result = analyze_sto_models(
        job_ids_text=args.jobs,
        processing_text=args.times,
        deadlines_text=args.deadlines,
        selected_methods=methods,
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

    return 0


def command_sto_train(args: Any) -> int:
    methods = validate_models(parse_csv_list(args.methods), AVAILABLE_STO_MODELS, "metody STO")
    result = train_sto_models_flow(methods)
    hr("ZAPIS STO")
    print_messages(result.get("messages"))
    print_key_value("MODEL_STO", result["model_path"])
    return 0


def command_sto_solve(args: Any) -> int:
    model_path = resolve_existing_file(args.model, "pliku modelu STO")
    data_path = resolve_existing_file(args.data, "pliku danych STO")
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

    return 0


def command_preview(args: Any) -> int:
    data_path = resolve_existing_file(args.data, "pliku danych")
    df = load_csv(data_path)
    logger.info(
        "%s",
        build_dataframe_preview_text(
            df,
            title=f"Podgląd: {data_path.name}",
            max_rows=args.rows,
        ),
    )
    return 0


def command_summary(args: Any) -> int:
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

    hr("PODSUMOWANIE KONFIGURACJI")
    logger.info("%s", build_main_page_summary(config))
    return 0


def command_status(args: Any) -> int:
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


def command_workflow(args: Any) -> int:
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
            model_path=str(ml_model_path),
            data_path=str(gen_result["test_path"]),
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


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value if value else default


def interactive_generate():
    return command_generate(
        argparse.Namespace(
            n=int(ask("Liczba rekordów", "800")),
            machines=int(ask("Liczba maszyn", "1")),
            test_size=float(ask("Test size", "0.2")),
            seed=int(ask("Seed", "42")),
            prod_min=float(ask("Czas prod. min", "1")),
            prod_max=float(ask("Czas prod. max", "48")),
            deadline_min=float(ask("Bufor terminu min", "1")),
            deadline_max=float(ask("Bufor terminu max", "72")),
            shapes=ask("Kształty", ",".join(DEFAULT_SHAPES)),
            materials=ask("Materiały", ",".join(DEFAULT_MATERIALS)),
        )
    )


def interactive_train():
    return command_train(
        argparse.Namespace(
            data=ask("Ścieżka do CSV z danymi"),
            models=ask("Modele", "Quality"),
            backend=ask("Backend ML", "classic"),
            train_ratio=float(ask("Train ratio", "0.8")),
            n_meta=None,
            machines_meta=None,
            shapes_meta="",
            materials_meta="",
        )
    )


def interactive_solve():
    return command_solve(
        argparse.Namespace(
            model=ask("Ścieżka do modelu .pkl"),
            data=ask("Ścieżka do danych CSV"),
        )
    )


def interactive_sto_run():
    return command_sto_run(
        argparse.Namespace(
            jobs=ask("Zlecenia", "Z1,Z2,Z3"),
            times=ask("Czasy", "10,20,100"),
            deadlines=ask("Terminy", "150,30,110"),
            methods=ask("Metody", "MT,MO,MZO"),
        )
    )


def interactive_summary():
    return command_summary(
        argparse.Namespace(
            models=ask("Modele", "Quality,Delay"),
            backend=ask("Backend", "classic"),
            n=int(ask("Liczba rekordów", "800")),
            machines=int(ask("Liczba maszyn", "1")),
            test_size=float(ask("Test size", "0.2")),
            seed=int(ask("Seed", "42")),
            prod_min=float(ask("Czas prod. min", "1")),
            prod_max=float(ask("Czas prod. max", "48")),
            deadline_min=float(ask("Bufor terminu min", "1")),
            deadline_max=float(ask("Bufor terminu max", "72")),
            shapes=ask("Kształty", ",".join(DEFAULT_SHAPES)),
            materials=ask("Materiały", ",".join(DEFAULT_MATERIALS)),
        )
    )


def interactive_status():
    return command_status(
        argparse.Namespace(
            data=ask("Ścieżka do CSV (puste = brak danych)", ""),
            train_ratio=float(ask("Train ratio", "0.8")),
        )
    )


def interactive_workflow():
    return command_workflow(
        argparse.Namespace(
            n=int(ask("Liczba rekordów", "800")),
            machines=int(ask("Liczba maszyn", "1")),
            test_size=float(ask("Test size", "0.2")),
            seed=int(ask("Seed", "42")),
            prod_min=float(ask("Czas prod. min", "1")),
            prod_max=float(ask("Czas prod. max", "48")),
            deadline_min=float(ask("Bufor terminu min", "1")),
            deadline_max=float(ask("Bufor terminu max", "72")),
            shapes=ask("Kształty", ",".join(DEFAULT_SHAPES)),
            materials=ask("Materiały", ",".join(DEFAULT_MATERIALS)),
            models=ask("Modele", "Quality"),
            backend=ask("Backend", "classic"),
            skip_solve=ask("Pominąć solve? tak/nie", "nie").lower() in {"tak", "t", "yes", "y"},
        )
    )


def command_interactive(args: Any) -> int:
    while True:
        hr("TRYB INTERAKTYWNY")
        logger.info("1. Generate")
        logger.info("2. Train")
        logger.info("3. Solve")
        logger.info("4. STO run")
        logger.info("5. Summary")
        logger.info("6. Status")
        logger.info("7. Workflow")
        logger.info("0. Wyjście")

        choice = input("Wybierz opcję: ").strip()

        if choice == "1":
            interactive_generate()
        elif choice == "2":
            interactive_train()
        elif choice == "3":
            interactive_solve()
        elif choice == "4":
            interactive_sto_run()
        elif choice == "5":
            interactive_summary()
        elif choice == "6":
            interactive_status()
        elif choice == "7":
            interactive_workflow()
        elif choice == "0":
            logger.info("Koniec.")
            return 0
        else:
            logger.warning("Nieprawidłowy wybór.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False))

    try:
        if args.command == "generate":
            return command_generate(args)
        if args.command == "train":
            return command_train(args)
        if args.command == "solve":
            return command_solve(args)
        if args.command == "sto-run":
            return command_sto_run(args)
        if args.command == "sto-train":
            return command_sto_train(args)
        if args.command == "sto-solve":
            return command_sto_solve(args)
        if args.command == "preview":
            return command_preview(args)
        if args.command == "summary":
            return command_summary(args)
        if args.command == "status":
            return command_status(args)
        if args.command == "workflow":
            return command_workflow(args)
        if args.command == "interactive":
            return command_interactive(args)

        parser.print_help()
        return 1

    except KeyboardInterrupt:
        eprint("Przerwano przez użytkownika.")
        return 130

    except Exception as e:
        log_path = write_exception_log("cli.main", e)
        eprint(f"❌ Błąd: {type(e).__name__}: {e}")
        eprint(f"Szczegóły zapisano w: {log_path}")
        return 1
