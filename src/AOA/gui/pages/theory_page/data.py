from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from AOA.core.mh_models import get_mh_model_specs
from AOA.core.ml_models import get_ml_model_specs

ModelFamily = Literal["ml", "mh"]


@dataclass(frozen=True)
class ExampleRow:
    row_id: int
    klass: str
    mt: float
    mo: float
    mzo: float
    gen: float


@dataclass(frozen=True)
class JobRow:
    job_id: str
    klass: str
    processing_time: float
    due_date: int
    ratio: float
    gen: float


@dataclass(frozen=True)
class TheoryModel:
    key: str
    family: ModelFamily
    title: str
    short_title: str
    subtitle: str
    model_type: str
    algorithm: str
    goal: str
    metric: str
    focus: str
    steps: tuple[str, ...]
    step_details: tuple[str, ...]
    next_steps: tuple[str, ...]
    tip: str
    probabilities: tuple[tuple[str, float], ...]
    result: str


EXAMPLE_ROWS: tuple[ExampleRow, ...] = (
    ExampleRow(1, "A", 0.60, 0.30, 0.10, 0.20),
    ExampleRow(2, "B", 0.40, 0.50, 0.10, 0.30),
    ExampleRow(3, "C", 0.20, 0.20, 0.30, 0.40),
    ExampleRow(4, "A", 0.70, 0.20, 0.10, 0.40),
    ExampleRow(5, "B", 0.30, 0.60, 0.20, 0.20),
)

JOB_ROWS: tuple[JobRow, ...] = (
    JobRow("J1", "A", 6.0, 30, 0.20, 0.20),
    JobRow("J2", "B", 4.0, 20, 0.20, 0.30),
    JobRow("J3", "C", 2.0, 12, 0.17, 0.40),
    JobRow("J4", "A", 7.0, 25, 0.28, 0.40),
)

ML_STEPS: tuple[str, ...] = (
    "Dane wejściowe",
    "Wybór instancji",
    "Normalizacja cech",
    "Skanowanie cech",
    "Pierwszy podział",
    "Przejście po gałęzi",
    "Wynik drzewa",
    "Kolejne estymatory",
    "Łączenie głosów",
    "Rozkład wyniku",
    "Predykcja końcowa",
    "Zapis do raportu",
)

MH_STEPS: tuple[str, ...] = (
    "Dane zleceń",
    "Obliczenie wskaźników",
    "Reguła sortowania",
    "Kolejność startowa",
    "Start J1/J4",
    "Czas zakończenia",
    "Opóźnienie Tj",
    "Suma T+",
    "Korekta wariantu",
    "Porównanie metod",
    "Ranking STO",
    "Wybór kolejki",
)


def _task_label(name: str) -> str:
    if name.startswith("Quality"):
        return "jakość"
    if name.startswith("Delay"):
        return "opóźnienie"
    return "strategia"


def _ml_algorithm(name: str) -> str:
    if name.endswith("_ET"):
        return "Extra Trees"
    if name.endswith("_GB") or name == "Delay":
        return "Gradient Boosting"
    if name.endswith("_HGB"):
        return "HistGradient Boosting"
    if name.endswith("_LOG"):
        return "Regresja logistyczna"
    return "Random Forest"


def _ml_probabilities(name: str) -> tuple[tuple[str, float], ...]:
    if name.startswith("Quality"):
        return (("wysoka jakość", 0.72), ("średnia", 0.20), ("ryzyko", 0.08))
    if name.startswith("Delay"):
        return (("niski delay", 0.61), ("średni", 0.26), ("wysoki", 0.13))
    return (("A", 0.58), ("B", 0.27), ("C", 0.15))


def _ml_result(name: str) -> str:
    if name.startswith("Quality"):
        return "pred_quality: 0.82"
    if name.startswith("Delay"):
        return "pred_delay: 3.4 h"
    return "Predykcja: A"


def _ml_details(algorithm: str, task: str) -> tuple[str, ...]:
    return (
        "Wczytujemy przykładowe rekordy i pokazujemy cechy, z których model może korzystać.",
        "Wybieramy jeden przypadek, żeby śledzić jego drogę przez model od początku do końca.",
        "Cechy MT, MO, MZO i GEN są ustawiane w jednej skali, aby żadna kolumna nie dominowała tylko przez jednostkę.",
        f"Model {algorithm} sprawdza, które cechy najsilniej pomagają przewidzieć {task}.",
        "Drzewo lub estymator wybiera pierwszy podział, który najmocniej zmniejsza błąd na danych treningowych.",
        "Instancja przechodzi do lewej albo prawej gałęzi, zależnie od wartości cechy i progu.",
        "Pojedyncze drzewo daje wynik cząstkowy: głos klasy, wartość jakości albo poprawkę opóźnienia.",
        "Kolejne drzewa/estymatory analizują ten sam przypadek z innych losowań lub poprawiają wcześniejszy błąd.",
        "Wyniki cząstkowe są uśredniane albo sumowane, dzięki czemu decyzja jest stabilniejsza niż jedno drzewo.",
        "Aplikacja zamienia wyniki na czytelny rozkład: widać, która klasa lub wariant ma największą pewność.",
        "Najwyższy wynik staje się predykcją końcową widoczną dla użytkownika.",
        "Predykcja może trafić do tabeli wyników, priorytetu zlecenia, raportu lub dalszej symulacji.",
    )


def _mh_details(label: str, description: str) -> tuple[str, ...]:
    return (
        "Wczytujemy listę zleceń: każde ma czas przetwarzania p, termin d i dodatkowe cechy pomocnicze.",
        "Dla każdego zlecenia liczymy wskaźniki, np. p/d, zapas czasu albo ranking według danej reguły.",
        f"Stosujemy heurystykę {label}: {description}",
        "Po sortowaniu powstaje pierwsza kolejka — to kandydat do realizacji na stanowisku.",
        "Pierwsze zlecenie zaczyna się od czasu 0, a kolejne czekają na zakończenie poprzedniego.",
        "Po każdym zleceniu liczymy czas zakończenia Cj, czyli narastający czas pracy kolejki.",
        "Opóźnienie Tj liczymy tylko wtedy, gdy Cj przekracza termin d. Wynik ujemny traktujemy jako 0.",
        "Sumujemy dodatnie opóźnienia T+. To jest główny wynik STO — im niżej, tym lepiej.",
        "Jeżeli metoda dopuszcza poprawki, aplikacja sprawdza zamiany lub warianty kolejności.",
        "Ten sam zestaw zleceń jest liczony innymi heurystykami, żeby mieć punkt odniesienia.",
        "Wyniki trafiają do rankingu STO. Najniższa suma opóźnień wygrywa.",
        "Wybrana kolejka może zostać zapisana jako rekomendacja, CSV albo raport dla użytkownika.",
    )


def _build_ml_models() -> list[TheoryModel]:
    models: list[TheoryModel] = []
    for spec in get_ml_model_specs():
        task = _task_label(spec.name)
        algorithm = _ml_algorithm(spec.name)
        title = f"{spec.label} — {task}"
        if spec.name == "Schedule":
            title = "Schedule — strategia"
        elif spec.name == "Delay":
            title = "Delay — opóźnienie"
        elif spec.name == "Quality":
            title = "Quality — jakość"
        models.append(
            TheoryModel(
                key=spec.name,
                family="ml",
                title=title,
                short_title=spec.label.replace("Quality ", "Q ").replace("Schedule ", "S "),
                subtitle=spec.description,
                model_type="Model ML" if task != "strategia" else "Klasyfikator ML",
                algorithm=algorithm,
                goal=f"Przewidzieć {task} na podstawie cech zlecenia.",
                metric="RMSE / MAE / R²"
                if task != "strategia"
                else "Accuracy / F1 / prawdopodobieństwo klasy",
                focus=spec.focus,
                steps=ML_STEPS,
                step_details=_ml_details(algorithm, task),
                next_steps=(
                    "Następny krok pokaże przepływ danych przez kolejną część modelu.",
                    "Po przejściu wszystkich kroków zobaczysz wynik i rozkład pewności.",
                    "Możesz porównać model z innymi algorytmami z tej samej grupy.",
                ),
                tip="Użyj ▶ albo suwaka, aby zobaczyć pełny proces uczenia i decyzji krok po kroku.",
                probabilities=_ml_probabilities(spec.name),
                result=_ml_result(spec.name),
            )
        )
    return models


def _build_mh_models() -> list[TheoryModel]:
    models: list[TheoryModel] = []
    for spec in get_mh_model_specs():
        models.append(
            TheoryModel(
                key=spec.name,
                family="mh",
                title=f"{spec.label} — heurystyka STO",
                short_title=spec.name,
                subtitle=spec.description,
                model_type="Model heurystyczny",
                algorithm=spec.label,
                goal="Ułożyć kolejność zleceń tak, aby zmniejszyć sumę opóźnień STO.",
                metric="STO = suma dodatnich opóźnień; niżej znaczy lepiej",
                focus=spec.focus,
                steps=MH_STEPS,
                step_details=_mh_details(spec.label, spec.description),
                next_steps=(
                    "Następny krok przelicza kolejkę i pokazuje, skąd bierze się STO.",
                    "Na końcu porównamy wynik z innymi heurystykami.",
                    "Najlepszy wariant można przenieść do raportu lub dalszej analizy.",
                ),
                tip="Heurystyka jest szybka i czytelna: zamiast trenowania ma jasną regułę sortowania.",
                probabilities=(("STO", 0.23), ("czas", 0.42), ("bufor", 0.35)),
                result="Najniższe STO",
            )
        )
    return models


THEORY_MODELS: tuple[TheoryModel, ...] = tuple(_build_ml_models() + _build_mh_models())


def get_theory_models(family: ModelFamily | None = None) -> tuple[TheoryModel, ...]:
    if family is None:
        return THEORY_MODELS
    return tuple(model for model in THEORY_MODELS if model.family == family)


def find_theory_model(key: str) -> TheoryModel:
    for model in THEORY_MODELS:
        if model.key == key:
            return model
    return THEORY_MODELS[0]
