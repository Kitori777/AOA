from __future__ import annotations

from AOA.utils.error_utils import write_exception_log
from AOA.utils.logging_utils import configure_logging

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
from .helpers import eprint
from .interactive import command_interactive
from .parser import build_parser


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
