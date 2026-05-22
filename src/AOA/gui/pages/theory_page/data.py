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
    pseudocode: tuple[str, ...]
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
    "Nowe dane",
    "Pamięć treningowa",
    "Połączenie historii",
    "Przygotowanie cech",
    "Normalizacja",
    "Trening estymatorów",
    "Ścieżka decyzji",
    "Wyniki cząstkowe",
    "Łączenie głosów",
    "Rozkład wyniku",
    "Predykcja końcowa",
    "Zapis doświadczenia",
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
        "Wczytujemy rekordy z bieżącego uruchomienia: z GUI, CSV albo generatora danych.",
        "Aplikacja szuka poprzednich zapisanych model packów z pasującymi modelami i backendem.",
        "Nowe rekordy są łączone z historią, a duplikaty usuwane, żeby model uczył się na szerszym doświadczeniu.",
        "Z surowych kolumn tworzymy cechy liczbowe: presję terminu, koszt czasu, jakość materiału i geometrię.",
        "Cechy trafiają do jednej skali, żeby model nie traktował większych jednostek jako ważniejszych.",
        f"Model {algorithm} uczy się zależności między cechami a celem: {task}.",
        "Wybrana instancja przechodzi przez reguły modelu, progi drzew albo granicę decyzyjną klasyfikatora.",
        "Każdy estymator daje wynik cząstkowy: wartość, poprawkę błędu albo głos klasy.",
        "Wyniki cząstkowe są uśredniane, sumowane albo głosowane, co stabilizuje decyzję.",
        "Aplikacja pokazuje rozkład wyniku: widać nie tylko decyzję, ale też poziom pewności.",
        "Najsilniejszy wynik staje się predykcją końcową używaną w solve i raportach.",
        "Model pack zapisuje model oraz dane treningowe, żeby następne uruchomienie mogło uczyć się dalej.",
    )


def _ml_pseudocode() -> tuple[str, ...]:
    return (
        "current = load_current_training_rows()",
        "history = scan_saved_model_packs(selected_models, backend)",
        "train_df = dedupe(history + current).tail(max_rows)",
        "X, y_quality, y_delay = prepare_features(train_df)",
        "X_scaled = scaler.fit_transform(X)",
        "model.fit(X_scaled, target)",
        "path = estimator.decision_path(sample)",
        "partial = estimator.predict(sample)",
        "prediction = aggregate(partial_results)",
        "distribution = normalize_scores(prediction)",
        "result_df[column] = prediction",
        "save_model_pack(model, training_data=train_df)",
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


def _mh_pseudocode() -> tuple[str, ...]:
    return (
        "jobs = load_jobs()",
        "features = compute_processing_deadline_ratios(jobs)",
        "ordered = sort_by_rule(features)",
        "time = 0; queue = ordered",
        "start(job) = time",
        "finish(job) = start(job) + processing_time(job)",
        "lateness(job) = max(0, finish(job) - due_date(job))",
        "sto = sum(lateness)",
        "candidate = try_local_variant(queue)",
        "scores = compare_all_methods(jobs)",
        "best = min(scores, key=sto)",
        "save_result(best.queue, best.sto)",
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
                pseudocode=_ml_pseudocode(),
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
                pseudocode=_mh_pseudocode(),
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
