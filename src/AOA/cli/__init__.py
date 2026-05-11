# ruff: noqa: F401, I001
"""Public CLI facade.

The command implementations live in ``AOA.cli.commands``. This module keeps the
historical ``AOA.cli`` import path and the console entry point while avoiding a
second copy of the command logic.
"""

from typing import Any, cast

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

from .commands import generate as _generate
from .commands import preview as _preview
from .commands import solve as _solve
from .commands import sto as _sto
from .commands import train as _train
from .commands import workflow as _workflow
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
from . import interactive as _interactive
from .parser import build_examples_text, build_parser


def _sync_command_modules() -> None:
    for module in (_generate, _preview, _solve, _sto, _train, _workflow, _interactive):
        module_any = cast(Any, module)
        if hasattr(module, "parse_csv_list"):
            module_any.parse_csv_list = parse_csv_list
        if hasattr(module, "resolve_existing_file"):
            module_any.resolve_existing_file = resolve_existing_file
        if hasattr(module, "print_messages"):
            module_any.print_messages = print_messages
        if hasattr(module, "print_key_value"):
            module_any.print_key_value = print_key_value
        if hasattr(module, "hr"):
            module_any.hr = hr
        if hasattr(module, "progress_callback"):
            module_any.progress_callback = progress_callback
    _generate.generate_and_store_datasets = generate_and_store_datasets
    _train.load_training_data = load_training_data
    _train.train_models_flow = train_models_flow
    _train.train_sto_models_flow = train_sto_models_flow
    _solve.solve_models_flow = solve_models_flow
    _preview.load_csv = load_csv
    _preview.load_training_data = load_training_data
    _preview.build_dataframe_preview_text = build_dataframe_preview_text
    _preview.build_main_page_status = build_main_page_status
    _sto.analyze_sto_models = analyze_sto_models
    _sto.train_sto_models_flow = train_sto_models_flow
    _sto.solve_sto_with_saved_model = solve_sto_with_saved_model
    _workflow.generate_and_store_datasets = generate_and_store_datasets
    _workflow.train_models_flow = train_models_flow
    _workflow.train_sto_models_flow = train_sto_models_flow
    _workflow.solve_models_flow = solve_models_flow
    _interactive.command_generate = command_generate
    _interactive.command_train = command_train
    _interactive.command_solve = command_solve
    _interactive.command_sto_run = command_sto_run
    _interactive.command_summary = command_summary
    _interactive.command_status = command_status
    _interactive.command_workflow = command_workflow


def command_generate(args):
    _sync_command_modules()
    return _generate.command_generate(args)


def command_train(args):
    _sync_command_modules()
    return _train.command_train(args)


def command_solve(args):
    _sync_command_modules()
    return _solve.command_solve(args)


def command_sto_run(args):
    _sync_command_modules()
    return _sto.command_sto_run(args)


def command_sto_train(args):
    _sync_command_modules()
    return _sto.command_sto_train(args)


def command_sto_solve(args):
    _sync_command_modules()
    return _sto.command_sto_solve(args)


def command_preview(args):
    _sync_command_modules()
    return _preview.command_preview(args)


def command_summary(args):
    return _preview.command_summary(args)


def command_status(args):
    _sync_command_modules()
    return _preview.command_status(args)


def command_workflow(args):
    _sync_command_modules()
    return _workflow.command_workflow(args)


ask = _interactive.ask


def interactive_generate():
    _sync_command_modules()
    return _interactive.interactive_generate()


def interactive_train():
    _sync_command_modules()
    return _interactive.interactive_train()


def interactive_solve():
    _sync_command_modules()
    return _interactive.interactive_solve()


def interactive_sto_run():
    _sync_command_modules()
    return _interactive.interactive_sto_run()


def interactive_summary():
    _sync_command_modules()
    return _interactive.interactive_summary()


def interactive_status():
    _sync_command_modules()
    return _interactive.interactive_status()


def interactive_workflow():
    _sync_command_modules()
    return _interactive.interactive_workflow()


def command_interactive(args):
    _sync_command_modules()
    return _interactive.command_interactive(args)


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


__all__ = [name for name in globals() if not name.startswith("_")]
