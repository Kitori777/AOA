from __future__ import annotations

import argparse

from AOA.core.services import solve_models_flow

from ..helpers import hr, print_key_value, print_messages, resolve_existing_file


def command_solve(args: argparse.Namespace) -> int:
    model_path = resolve_existing_file(args.model, "pliku modelu")
    data_path = resolve_existing_file(args.data, "pliku danych")
    hr("ROZWIĄZYWANIE ML")
    print_key_value("MODEL", model_path)
    print_key_value("DATA", data_path)
    result = solve_models_flow(model_path=str(model_path), data_path=str(data_path))
    print_messages(result.get("messages"))
    print_key_value("WYNIK", result["result_path"])
    return 0
