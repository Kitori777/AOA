from __future__ import annotations

import argparse

from .commands import (
    command_generate,
    command_solve,
    command_status,
    command_sto_run,
    command_summary,
    command_train,
    command_workflow,
)
from .helpers import DEFAULT_MATERIALS, DEFAULT_SHAPES, logger


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
    args = argparse.Namespace(
        data=ask("Ścieżka do CSV z danymi"),
        models=ask("Modele", "Quality"),
        backend=ask("Backend ML", "classic"),
        train_ratio=float(ask("Train ratio", "0.8")),
        n_meta=None,
        machines_meta=None,
        shapes_meta="",
        materials_meta="",
    )
    return command_train(args)


def interactive_solve():
    return command_solve(
        argparse.Namespace(model=ask("Ścieżka do modelu .pkl"), data=ask("Ścieżka do danych CSV"))
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


def command_interactive(args: argparse.Namespace) -> int:
    from .helpers import hr

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
