"""Public CLI facade.

Command implementations live in ``AOA.cli.commands`` and the console entry
point lives in ``AOA.cli.main``. This module keeps the historical ``AOA.cli``
import path as a thin import-only facade.
"""

from .commands import (
    command_generate,
    command_preview,
    command_solve,
    command_status,
    command_sto_run,
    command_sto_solve,
    command_sto_train,
    command_summary,
    command_train,
    command_workflow,
)
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
from .interactive import (
    ask,
    command_interactive,
    interactive_generate,
    interactive_solve,
    interactive_status,
    interactive_sto_run,
    interactive_summary,
    interactive_train,
    interactive_workflow,
)
from .main import main
from .parser import build_examples_text, build_parser

__all__ = [
    "AVAILABLE_ML_MODELS",
    "AVAILABLE_STO_MODELS",
    "DEFAULT_MATERIALS",
    "DEFAULT_SHAPES",
    "ask",
    "build_examples_text",
    "build_parser",
    "command_generate",
    "command_interactive",
    "command_preview",
    "command_solve",
    "command_status",
    "command_sto_run",
    "command_sto_solve",
    "command_sto_train",
    "command_summary",
    "command_train",
    "command_workflow",
    "eprint",
    "hr",
    "interactive_generate",
    "interactive_solve",
    "interactive_status",
    "interactive_sto_run",
    "interactive_summary",
    "interactive_train",
    "interactive_workflow",
    "logger",
    "main",
    "parse_csv_list",
    "print_key_value",
    "print_messages",
    "progress_callback",
    "resolve_existing_file",
    "validate_models",
]
