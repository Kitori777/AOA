from __future__ import annotations

import argparse

from AOA.core.services import generate_and_store_datasets

from ..helpers import hr, parse_csv_list, print_key_value, print_messages


def command_generate(args: argparse.Namespace) -> int:
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
