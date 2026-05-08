from __future__ import annotations

import argparse
from textwrap import dedent

from .helpers import AVAILABLE_BACKENDS, DEFAULT_MATERIALS, DEFAULT_SHAPES


def build_examples_text() -> str:
    return dedent(
        """

        Przykłady:

          aoa-cli generate --n 800 --machines 1 --test-size 0.2 --seed 42
          aoa-cli train --data data/train_x.csv --models Quality,Delay --backend classic
          aoa-cli train --data data/train_x.csv --models Quality --backend tabpfn
          aoa-cli solve --model models/model_x.pkl --data data/test_x.csv
          aoa-cli sto-run --jobs Z1,Z2,Z3 --times 10,20,100 --deadlines 150,30,110 --methods MT,MO,MZO
          aoa-cli sto-train --methods MT,MO,MZO,GENETIC
          aoa-cli sto-solve --model models/model_sto_x.pkl --data data/test_x.csv
          aoa-cli preview --data data/test_x.csv --rows 10
          aoa-cli summary --models Quality,Delay,MT --backend tabpfn --n 800 --machines 1
          aoa-cli status --data data/train_x.csv
          aoa-cli workflow --n 800 --models Quality,Delay --backend classic
          aoa-cli interactive
        """
    ).strip()


def build_parser() -> argparse.ArgumentParser:
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(
        prog="aoa-cli",
        description="CLI do AOA: generowanie danych, trening modeli ML/STO i rozwiązywanie bez GUI.",
        epilog=build_examples_text(),
        formatter_class=formatter,
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Włącz bardziej szczegółowe logowanie"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Ogranicz logowanie do ostrzeżeń i błędów"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser(
        "generate",
        help="Wygeneruj dane treningowe i testowe",
        description="Generuje pełny zbiór danych oraz automatycznie zapisuje full/train/test do katalogu data.",
        epilog="Przykład: aoa-cli generate --n 800 --machines 1 --test-size 0.2 --seed 42",
        formatter_class=formatter,
    )
    gen_parser.add_argument("--n", type=int, default=5000, help="Liczba rekordów do wygenerowania")
    gen_parser.add_argument("--machines", type=int, default=1, help="Liczba maszyn")
    gen_parser.add_argument(
        "--test-size", type=float, default=0.2, help="Udział zbioru testowego, np. 0.2"
    )
    gen_parser.add_argument("--seed", type=int, default=42, help="Seed generatora")
    gen_parser.add_argument(
        "--prod-min", type=float, default=1.0, help="Minimalny czas produkcji [h]"
    )
    gen_parser.add_argument(
        "--prod-max", type=float, default=48.0, help="Maksymalny czas produkcji [h]"
    )
    gen_parser.add_argument(
        "--deadline-min", type=float, default=1.0, help="Minimalny bufor terminu [h]"
    )
    gen_parser.add_argument(
        "--deadline-max", type=float, default=72.0, help="Maksymalny bufor terminu [h]"
    )
    gen_parser.add_argument(
        "--shapes", type=str, default=",".join(DEFAULT_SHAPES), help="Lista kształtów po przecinku"
    )
    gen_parser.add_argument(
        "--materials",
        type=str,
        default=",".join(DEFAULT_MATERIALS),
        help="Lista materiałów po przecinku",
    )

    train_parser = subparsers.add_parser(
        "train",
        help="Wytrenuj i zapisz modele ML lub STO",
        description="Wczytuje CSV, dzieli dane na train/test i zapisuje wytrenowane modele.",
        epilog="Przykład: aoa-cli train --data data/train_x.csv --models Quality,Delay --backend classic",
        formatter_class=formatter,
    )
    train_parser.add_argument("--data", required=True, type=str, help="Ścieżka do CSV z danymi")
    train_parser.add_argument(
        "--models",
        required=True,
        type=str,
        help="Lista modeli po przecinku, np. Quality,Delay albo MT,MO",
    )
    train_parser.add_argument(
        "--backend",
        choices=sorted(AVAILABLE_BACKENDS),
        default="classic",
        help="Backend ML: classic albo tabpfn",
    )
    train_parser.add_argument(
        "--train-ratio", type=float, default=0.8, help="Podział train/test przy wczytaniu CSV"
    )
    train_parser.add_argument(
        "--n-meta", type=int, default=None, help="Opcjonalne n do nazwy modelu"
    )
    train_parser.add_argument(
        "--machines-meta", type=int, default=None, help="Opcjonalne n_machines do nazwy modelu"
    )
    train_parser.add_argument(
        "--shapes-meta", type=str, default="", help="Opcjonalne kształty do nazwy modelu"
    )
    train_parser.add_argument(
        "--materials-meta", type=str, default="", help="Opcjonalne materiały do nazwy modelu"
    )

    solve_parser = subparsers.add_parser(
        "solve",
        help="Rozwiąż zapisanym modelem ML",
        description="Wczytuje zapisany model ML i tworzy wynikowy CSV dla wskazanych danych.",
        epilog="Przykład: aoa-cli solve --model models/model_x.pkl --data data/test_x.csv",
        formatter_class=formatter,
    )
    solve_parser.add_argument(
        "--model", required=True, type=str, help="Ścieżka do pliku modelu .pkl"
    )
    solve_parser.add_argument("--data", required=True, type=str, help="Ścieżka do pliku CSV")

    sto_run_parser = subparsers.add_parser(
        "sto-run",
        help="Uruchom ręczną analizę STO",
        description="Liczy metody STO na danych wpisanych bezpośrednio z terminala.",
        epilog="Przykład: aoa-cli sto-run --jobs Z1,Z2,Z3 --times 10,20,100 --deadlines 150,30,110 --methods MT,MO,MZO",
        formatter_class=formatter,
    )
    sto_run_parser.add_argument(
        "--jobs", required=True, type=str, help="Lista zleceń, np. Z1,Z2,Z3"
    )
    sto_run_parser.add_argument(
        "--times", required=True, type=str, help="Lista czasów, np. 10,20,100"
    )
    sto_run_parser.add_argument(
        "--deadlines", required=True, type=str, help="Lista terminów, np. 150,30,110"
    )
    sto_run_parser.add_argument(
        "--methods", required=True, type=str, help="Lista metod STO, np. MT,MO,MZO"
    )

    sto_train_parser = subparsers.add_parser(
        "sto-train",
        help="Zapisz paczkę modeli STO",
        description="Zapisuje paczkę metod STO do późniejszego użycia.",
        epilog="Przykład: aoa-cli sto-train --methods MT,MO,MZO,GENETIC",
        formatter_class=formatter,
    )
    sto_train_parser.add_argument("--methods", required=True, type=str, help="Lista metod STO")

    sto_solve_parser = subparsers.add_parser(
        "sto-solve",
        help="Rozwiąż zapisanym modelem STO",
        description="Wczytuje paczkę STO i tworzy wynikowe CSV dla wskazanych danych.",
        epilog="Przykład: aoa-cli sto-solve --model models/model_sto_x.pkl --data data/test_x.csv",
        formatter_class=formatter,
    )
    sto_solve_parser.add_argument(
        "--model", required=True, type=str, help="Ścieżka do pliku modelu STO .pkl"
    )
    sto_solve_parser.add_argument("--data", required=True, type=str, help="Ścieżka do pliku CSV")

    preview_parser = subparsers.add_parser(
        "preview",
        help="Pokaż podgląd CSV",
        description="Wyświetla podgląd danych z pliku CSV w terminalu.",
        epilog="Przykład: aoa-cli preview --data data/test_x.csv --rows 10",
        formatter_class=formatter,
    )
    preview_parser.add_argument("--data", required=True, type=str, help="Ścieżka do pliku CSV")
    preview_parser.add_argument(
        "--rows", type=int, default=15, help="Maksymalna liczba wierszy podglądu"
    )

    summary_parser = subparsers.add_parser(
        "summary",
        help="Pokaż podsumowanie konfiguracji jak w GUI",
        description="Buduje tekstowe podsumowanie podobne do panelu bocznego w GUI.",
        epilog="Przykład: aoa-cli summary --models Quality,Delay,MT --backend tabpfn --n 800 --machines 1",
        formatter_class=formatter,
    )
    summary_parser.add_argument(
        "--models", required=True, type=str, help="Lista modeli po przecinku"
    )
    summary_parser.add_argument(
        "--backend", choices=sorted(AVAILABLE_BACKENDS), default="classic", help="Backend ML"
    )
    summary_parser.add_argument("--n", type=int, default=5000, help="Liczba rekordów")
    summary_parser.add_argument("--machines", type=int, default=1, help="Liczba maszyn")
    summary_parser.add_argument(
        "--test-size", type=float, default=0.2, help="Udział zbioru testowego"
    )
    summary_parser.add_argument("--seed", type=int, default=42, help="Seed")
    summary_parser.add_argument(
        "--prod-min", type=float, default=1.0, help="Minimalny czas produkcji [h]"
    )
    summary_parser.add_argument(
        "--prod-max", type=float, default=48.0, help="Maksymalny czas produkcji [h]"
    )
    summary_parser.add_argument(
        "--deadline-min", type=float, default=1.0, help="Minimalny bufor terminu [h]"
    )
    summary_parser.add_argument(
        "--deadline-max", type=float, default=72.0, help="Maksymalny bufor terminu [h]"
    )
    summary_parser.add_argument(
        "--shapes", type=str, default=",".join(DEFAULT_SHAPES), help="Lista kształtów"
    )
    summary_parser.add_argument(
        "--materials", type=str, default=",".join(DEFAULT_MATERIALS), help="Lista materiałów"
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Pokaż status danych",
        description="Pokazuje status danych podobny do GUI. Gdy podasz CSV, liczy train/test z podziałem.",
        epilog="Przykład: aoa-cli status --data data/train_x.csv",
        formatter_class=formatter,
    )
    status_parser.add_argument(
        "--data", type=str, default="", help="Opcjonalna ścieżka do pliku CSV"
    )
    status_parser.add_argument("--train-ratio", type=float, default=0.8, help="Podział train/test")

    workflow_parser = subparsers.add_parser(
        "workflow",
        help="Wykonaj cały przepływ: generate -> train -> solve",
        description="Komenda zbiorcza dla pracy bez GUI: generuje dane, trenuje modele i rozwiązuje test.",
        epilog="Przykład: aoa-cli workflow --n 800 --models Quality,Delay --backend classic",
        formatter_class=formatter,
    )
    workflow_parser.add_argument("--n", type=int, default=800, help="Liczba rekordów")
    workflow_parser.add_argument("--machines", type=int, default=1, help="Liczba maszyn")
    workflow_parser.add_argument(
        "--test-size", type=float, default=0.2, help="Udział zbioru testowego"
    )
    workflow_parser.add_argument("--seed", type=int, default=42, help="Seed")
    workflow_parser.add_argument(
        "--prod-min", type=float, default=1.0, help="Minimalny czas produkcji [h]"
    )
    workflow_parser.add_argument(
        "--prod-max", type=float, default=48.0, help="Maksymalny czas produkcji [h]"
    )
    workflow_parser.add_argument(
        "--deadline-min", type=float, default=1.0, help="Minimalny bufor terminu [h]"
    )
    workflow_parser.add_argument(
        "--deadline-max", type=float, default=72.0, help="Maksymalny bufor terminu [h]"
    )
    workflow_parser.add_argument(
        "--shapes", type=str, default=",".join(DEFAULT_SHAPES), help="Lista kształtów"
    )
    workflow_parser.add_argument(
        "--materials", type=str, default=",".join(DEFAULT_MATERIALS), help="Lista materiałów"
    )
    workflow_parser.add_argument(
        "--models", required=True, type=str, help="Lista modeli, np. Quality,Delay"
    )
    workflow_parser.add_argument(
        "--backend", choices=sorted(AVAILABLE_BACKENDS), default="classic", help="Backend ML"
    )
    workflow_parser.add_argument(
        "--skip-solve",
        action="store_true",
        help="Tylko wygeneruj i wytrenuj, bez rozwiązywania testu",
    )

    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Uruchom prosty tryb interaktywny",
        description="Proste menu tekstowe do pracy z terminala bez wpisywania pełnych komend.",
        formatter_class=formatter,
    )
    interactive_parser.add_argument(
        "--quick",
        action="store_true",
        help="Tryb skrócony z domyślnymi wartościami tam, gdzie to możliwe",
    )

    return parser
