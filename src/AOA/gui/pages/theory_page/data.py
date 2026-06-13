from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from AOA.core.mh_models import get_mh_model_specs
from AOA.core.ml_models import get_ml_model_specs

ModelFamily = Literal["ml", "mh", "tabpfn"]


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


FOREST_STEPS = (
    "Dane i cel",
    "Braki danych",
    "Losowe probki",
    "Budowa wielu drzew",
    "Podzial w wezle",
    "Lisc drzewa",
    "Predykcja drzew",
    "Agregacja",
    "Kontrola OOB",
    "Walidacja testowa",
    "Predykcja koncowa",
    "Zapis model pack",
)

EXTRA_STEPS = (
    "Dane i cel",
    "Braki danych",
    "Losowe cechy",
    "Losowe progi",
    "Budowa drzew",
    "Lisc drzewa",
    "Predykcja drzew",
    "Agregacja",
    "Stabilnosc",
    "Walidacja testowa",
    "Predykcja koncowa",
    "Zapis model pack",
)

BOOST_STEPS = (
    "Dane i cel",
    "Braki danych",
    "Pierwsza predykcja",
    "Blad resztowy",
    "Nowe male drzewo",
    "Krok uczenia",
    "Kolejne poprawki",
    "Suma poprawek",
    "Early stopping",
    "Walidacja testowa",
    "Predykcja koncowa",
    "Zapis model pack",
)

HIST_STEPS = (
    "Dane i cel",
    "Braki danych",
    "Koszyki wartosci",
    "Histogramy cech",
    "Pierwsza predykcja",
    "Gradient bledu",
    "Drzewo poprawek",
    "Regularyzacja",
    "Early stopping",
    "Walidacja testowa",
    "Predykcja koncowa",
    "Zapis model pack",
)

LOGISTIC_STEPS = (
    "Dane i klasy",
    "Braki danych",
    "Skalowanie",
    "Wagi klas",
    "Granica liniowa",
    "Funkcja softmax",
    "Prawdopodobienstwa",
    "Najlepsza klasa",
    "Regularizacja",
    "Walidacja testowa",
    "Predykcja koncowa",
    "Zapis model pack",
)

MH_STEPS = (
    "Dane zlecen",
    "Wskazniki",
    "Regula wyboru",
    "Kolejka startowa",
    "Symulacja czasu",
    "Czas zakonczenia",
    "Opoznienie Tj",
    "Suma STO",
    "Poprawka wariantu",
    "Porownanie metod",
    "Ranking STO",
    "Rekomendacja",
)

TABPFN_STEPS = (
    "Dane tabelaryczne",
    "Cel predykcji",
    "Czyszczenie cech",
    "Kodowanie tabeli",
    "Kontekst treningowy",
    "Model pretrenowany",
    "Inferencja na rekordzie",
    "Rozklad predykcji",
    "Niepewnosc wyniku",
    "Walidacja",
    "Kiedy uzyc",
    "Zapis workflow",
)

MODERN_STEPS = (
    "Dane i cel",
    "Walidacja tabeli",
    "Cechy X",
    "Podzial train/test",
    "Model bazowy",
    "Uczenie",
    "Predykcja",
    "Metryki",
    "Porownanie",
    "Ryzyko przeuczenia",
    "Kiedy uzyc",
    "Zapis workflow",
)


def _task_label(name: str) -> str:
    if name.startswith("Quality"):
        return "jakosc"
    if name.startswith("Delay"):
        return "opoznienie"
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


def _algorithm_kind(name: str) -> str:
    if name.endswith("_ET"):
        return "extra"
    if name.endswith("_GB") or name == "Delay":
        return "boost"
    if name.endswith("_HGB"):
        return "hist"
    if name.endswith("_LOG"):
        return "logistic"
    return "forest"


def _ml_steps(name: str) -> tuple[str, ...]:
    return {
        "forest": FOREST_STEPS,
        "extra": EXTRA_STEPS,
        "boost": BOOST_STEPS,
        "hist": HIST_STEPS,
        "logistic": LOGISTIC_STEPS,
    }[_algorithm_kind(name)]


def _ml_probabilities(name: str) -> tuple[tuple[str, float], ...]:
    if name.startswith("Quality"):
        return (("wysoka jakosc", 0.72), ("srednia", 0.20), ("ryzyko", 0.08))
    if name.startswith("Delay"):
        return (("niski delay", 0.61), ("sredni", 0.26), ("wysoki", 0.13))
    return (("strategia A", 0.58), ("strategia B", 0.27), ("strategia C", 0.15))


def _ml_result(name: str) -> str:
    if name.startswith("Quality"):
        return "pred_quality: 0.82"
    if name.startswith("Delay"):
        return "pred_delay: 3.4 h"
    return "schedule: A"


def _ml_metric(task: str) -> str:
    if task == "strategia":
        return "Accuracy / F1 / prawdopodobienstwo klasy"
    return "RMSE / MAE / R2 na train i test"


def _ml_model_type(task: str) -> str:
    if task == "strategia":
        return "Klasyfikator ML"
    return "Regresor ML"


def _ml_details(name: str, task: str) -> tuple[str, ...]:
    kind = _algorithm_kind(name)
    target = {
        "jakosc": "wartosc jakosci",
        "opoznienie": "liczbe godzin opoznienia",
        "strategia": "klase strategii harmonogramowania",
    }[task]
    if kind == "forest":
        return (
            f"Wczytujemy rekordy i wybieramy cel: {target}.",
            "Braki w kolumnach liczbowych sa uzupelniane mediana; drzewa nie potrzebuja skalowania cech.",
            "Kazde drzewo dostaje losowa probke danych, czyli bagging.",
            "Powstaje wiele drzew, a kazde moze zobaczyc troche inny fragment danych i cech.",
            "W wezle drzewo wybiera ceche i prog, ktore najlepiej zmniejszaja blad albo nieczystosc klas.",
            "Lisc przechowuje srednia wartosc regresji albo rozklad klas dla podobnych rekordow.",
            "Kazde drzewo osobno przewiduje wynik dla tego samego rekordu.",
            "Regresja usrednia wyniki drzew, a klasyfikacja glosuje albo usrednia prawdopodobienstwa.",
            "OOB sprawdza jakosc na rekordach, ktorych dane drzewo nie widzialo w swojej probce.",
            "Osobny test pokazuje, czy model generalizuje na danych niewidzianych.",
            "Predykcja koncowa trafia do raportu, solve albo pliku wynikowego.",
            "Model pack zapisuje pipeline, metadane i dane treningowe do kolejnego uruchomienia.",
        )
    if kind == "extra":
        return (
            f"Wczytujemy rekordy i wybieramy cel: {target}.",
            "Braki w kolumnach liczbowych sa uzupelniane mediana; skalowanie nie jest wymagane dla drzew.",
            "Kazde drzewo losuje zestaw cech kandydackich.",
            "Progi podzialu sa losowane mocniej niz w Random Forest, dlatego model jest szybki i roznorodny.",
            "Drzewa rosna na losowych decyzjach, a roznice miedzy nimi pomagaja tlumic szum.",
            "Lisc zbiera rekordy podobne wedlug losowo dobranych podzialow.",
            "Kazde drzewo daje osobna predykcje.",
            "Wyniki sa usredniane albo glosowane, tak jak w modelach ensemble.",
            "Patrzymy, czy mocna losowosc poprawia stabilnosc czy tylko dodaje szum.",
            "Test train/test pokazuje realna jakosc na nowych danych.",
            "Koncowy wynik jest srednia albo najczestsza klasa z wielu drzew.",
            "Model pack zapisuje gotowy pipeline i informacje potrzebne do solve.",
        )
    if kind == "boost":
        return (
            f"Wczytujemy rekordy i wybieramy cel: {target}.",
            "Braki sa uzupelniane mediana; klasyczny Gradient Boosting w tej aplikacji pracuje na cechach liczbowych.",
            "Model zaczyna od prostej predykcji bazowej, np. sredniej albo rozkladu klas.",
            "Liczymy blad aktualnej predykcji: to informacja, czego model jeszcze nie umie.",
            "Kolejne male drzewo uczy sie poprawiac wlasnie ten blad, a nie budowac caly model od zera.",
            "Learning rate zmniejsza sile poprawki, zeby model nie reagowal zbyt nerwowo.",
            "Proces powtarza sie wiele razy: kazde drzewo dopisuje mala korekte.",
            "Predykcja to suma predykcji bazowej i kolejnych poprawek.",
            "Early stopping zatrzymuje uczenie, gdy walidacja nie poprawia sie przez kilka rund.",
            "Test train/test pokazuje, czy boosting nie przeuczyl trudnych przypadkow.",
            "Koncowa predykcja jest wynikiem calej sekwencji poprawek.",
            "Model pack zapisuje boosting, parametry i dane potrzebne do odtworzenia wyniku.",
        )
    if kind == "hist":
        return (
            f"Wczytujemy rekordy i wybieramy cel: {target}.",
            "Braki sa uzupelniane, a model histogramowy sam buduje szybka reprezentacje wartosci.",
            "Wartosci cech sa zamieniane na koszyki, czyli przedzialy liczb.",
            "Zamiast sprawdzac kazda wartosc osobno, model liczy histogramy koszykow cech.",
            "Predykcja startuje od prostego punktu odniesienia.",
            "Model liczy gradient bledu, czyli kierunek, w ktorym trzeba poprawic predykcje.",
            "Drzewo poprawek wybiera koszyki, ktore najlepiej zmniejszaja blad.",
            "Regularyzacja ogranicza zbyt agresywne poprawki.",
            "Early stopping zatrzymuje uczenie, gdy walidacja przestaje rosnac.",
            "Test train/test sprawdza generalizacje na nowych rekordach.",
            "Koncowy wynik jest suma wielu histogramowych poprawek.",
            "Model pack zapisuje pipeline i metadane do pozniejszego solve.",
        )
    return (
        "Wczytujemy rekordy z etykietami schedule, np. strategia A, B albo C.",
        "Braki sa uzupelniane mediana, bo model liniowy potrzebuje pelnej macierzy cech.",
        "Cechy sa skalowane, bo regresja logistyczna jest wrazliwa na rozne jednostki i zakresy.",
        "Wagi klas pomagaja, gdy jedna strategia pojawia sie rzadziej niz inne.",
        "Model uczy prosta granice liniowa w przestrzeni cech.",
        "Softmax zamienia wyniki liniowe na prawdopodobienstwa klas schedule.",
        "Dla kazdej klasy schedule dostajemy prawdopodobienstwo.",
        "Wygrywa klasa z najwyzszym prawdopodobienstwem.",
        "Regularizacja ogranicza zbyt duze wagi i poprawia stabilnosc.",
        "Test train/test pokazuje, czy baseline jest uczciwym punktem odniesienia.",
        "Koncowa predykcja to wybrana klasa schedule dla harmonogramowania.",
        "Model pack zapisuje scaler, regresje logistyczna i metadane.",
    )


def _ml_pseudocode(name: str) -> tuple[str, ...]:
    kind = _algorithm_kind(name)
    if kind == "forest":
        return (
            "X, y = prepare_features(train_df)",
            "X = median_imputer.fit_transform(X)",
            "for tree in forest: sample = bootstrap(X, y)",
            "tree.fit(sample)",
            "split = best_threshold(feature_subset)",
            "leaf.value = mean_or_class_distribution(rows)",
            "partial = [tree.predict(row) for tree in forest]",
            "prediction = mean_or_vote(partial)",
            "oob_score = score_on_out_of_bag_rows()",
            "test_metrics = evaluate(test_df)",
            "result_df[target] = prediction",
            "save_model_pack(pipeline, metadata)",
        )
    if kind == "extra":
        return (
            "X, y = prepare_features(train_df)",
            "X = median_imputer.fit_transform(X)",
            "features = random_feature_subset()",
            "threshold = random_threshold(feature)",
            "tree.fit_with_random_splits(X, y)",
            "leaf.value = aggregate_leaf_rows()",
            "partial = [tree.predict(row) for tree in trees]",
            "prediction = mean_or_vote(partial)",
            "stability = compare_tree_votes(partial)",
            "test_metrics = evaluate(test_df)",
            "result_df[target] = prediction",
            "save_model_pack(pipeline, metadata)",
        )
    if kind in {"boost", "hist"}:
        return (
            "X, y = prepare_features(train_df)",
            "X = median_imputer.fit_transform(X)",
            "prediction = initial_baseline(y)",
            "residual = y - prediction",
            "weak_tree.fit(X, residual)",
            "prediction += learning_rate * weak_tree.predict(X)",
            "repeat_until_n_estimators_or_stop()",
            "final = sum_all_corrections(row)",
            "stop = validation_not_improving()",
            "test_metrics = evaluate(test_df)",
            "result_df[target] = final",
            "save_model_pack(pipeline, metadata)",
        )
    return (
        "X, y = prepare_schedule_features(train_df)",
        "X = median_imputer.fit_transform(X)",
        "X_scaled = scaler.fit_transform(X)",
        "weights = balanced_class_weights(y)",
        "logits = X_scaled @ coef + intercept",
        "proba = softmax(logits)",
        "class_scores = dict(zip(classes, proba))",
        "prediction = argmax(class_scores)",
        "model = regularized_logistic_fit(X_scaled, y)",
        "test_metrics = evaluate(test_df)",
        "result_df['strategy'] = prediction",
        "save_model_pack(pipeline, metadata)",
    )


def _mh_details(label: str, description: str) -> tuple[str, ...]:
    return (
        "Wczytujemy liste zlecen: czas obrobki p, termin d i cechy pomocnicze.",
        "Dla kazdego zlecenia liczymy wskazniki: zapas, p/d, krytycznosc albo ranking reguly.",
        f"Stosujemy metode {label}: {description}",
        "Powstaje kolejka startowa, czyli kandydat do realizacji na stanowisku.",
        "Symulujemy prace: pierwsze zlecenie zaczyna sie od czasu 0, kolejne czekaja.",
        "Po kazdym zleceniu liczymy Cj, czyli czas zakonczenia.",
        "Opoznienie Tj to max(0, Cj - dj), wiec zlecenie przed terminem nie dodaje kary.",
        "STO to suma dodatnich opoznien; im mniej, tym lepsza kolejka.",
        "Metody ulepszajace sprawdzaja zamiany, wstawienia albo losowe warianty.",
        "Ten sam zestaw zlecen liczymy roznymi metodami, zeby porownanie bylo uczciwe.",
        "Ranking wybiera najmniejsze STO i pokazuje, ktora regula wygrala.",
        "Najlepsza kolejka moze trafic do CSV, raportu albo drzewa rozwiazan w Visual.",
    )


def _mh_pseudocode() -> tuple[str, ...]:
    return (
        "jobs = load_jobs()",
        "features = compute_deadline_and_time_scores(jobs)",
        "ordered = apply_rule(features)",
        "queue = ordered",
        "time = 0",
        "finish[job] = time + p[job]",
        "lateness[job] = max(0, finish[job] - d[job])",
        "sto = sum(lateness)",
        "candidate = improve_or_keep(queue)",
        "scores = compare_methods(jobs)",
        "best = min(scores, key=sto)",
        "save_result(best.queue, best.sto)",
    )


def _tabpfn_details(task: str) -> tuple[str, ...]:
    target = "liczbe" if task != "schedule" else "klase"
    return (
        "Wczytujemy mala lub srednia tabele: kazdy wiersz to rekord, kolumny to cechy X.",
        f"Wybieramy cel y, czyli {target}, ktora model ma przewidziec dla nowych rekordow.",
        "Braki danych sa uzupelniane, a kolumny sa porzadkowane tak, aby backend dostal czysta macierz.",
        "TabPFN patrzy na problem jak na zadanie tabelaryczne: zestaw przykladow uczy kontekstu predykcji.",
        "Dane treningowe sa przekazywane jako kontekst, a nie jako dlugi klasyczny trening wielu epok.",
        "Silnik TabPFN korzysta z modelu pretrenowanego na wielu sztucznych problemach tabelarycznych.",
        "Dla nowego rekordu model porownuje go z kontekstem i przewiduje wynik w jednym przebiegu.",
        "Klasyfikacja zwraca prawdopodobienstwa klas, a regresja zwraca wartosc liczbowa.",
        "Patrzymy na pewnosc predykcji: rozklad klas, roznice wariantow albo stabilnosc wyniku.",
        "Walidacja train/test nadal jest potrzebna, bo nawet nowoczesny model moze nie pasowac do danych.",
        "TabPFN warto probowac, gdy masz dane tabelaryczne i chcesz mocny punkt odniesienia bez strojenia.",
        "Aplikacja zapisuje wynik workflow tak, aby dało sie porownac TabPFN z klasycznymi modelami.",
    )


def _tabpfn_pseudocode(task: str) -> tuple[str, ...]:
    estimator = "TabPFNClassifier" if task == "schedule" else "TabPFNRegressor"
    return (
        "X, y = prepare_tabular_dataset(df)",
        "X = median_imputer.fit_transform(X)",
        "task = detect_regression_or_classification(y)",
        f"model = {estimator}(device='cpu')",
        "model.fit(X_train, y_train)",
        "context = learned_from_training_table",
        "prediction = model.predict(X_new)",
        "proba = model.predict_proba(X_new)  # klasyfikacja",
        "uncertainty = inspect_prediction_distribution()",
        "metrics = evaluate(y_test, prediction)",
        "compare_with_classic_backend(metrics)",
        "save_result_and_metadata()",
    )


def _modern_details(task: str, algorithm: str) -> tuple[str, ...]:
    target = "klase harmonogramu" if task == "schedule" else "wartosc liczbowa"
    return (
        "Wczytujemy tabele i sprawdzamy, czy cechy sa kompletne, liczbowe i spojne.",
        f"Cel y to {target}; od tego zalezy, czy model jest regresorem czy klasyfikatorem.",
        "Aplikacja robi cechy X, uzupelnia braki i zachowuje ten sam podzial train/test do porownan.",
        f"Model {algorithm} dostaje dane treningowe i uczy wzorzec decyzyjny inny niz klasyczny pojedynczy model.",
        "Predykcja jest porownywana z wynikiem klasycznego ML oraz z baseline, zeby nie ufac tylko nazwie algorytmu.",
        "Walidacja pokazuje, czy model faktycznie pomaga, czy tylko lepiej wyglada na treningu.",
        "Patrzymy na metryki i stabilnosc: blad, pewnosc klas, przeuczenie, czas treningu i sens biznesowy.",
        "Nowoczesny model warto zapisac dopiero wtedy, gdy poprawia decyzje albo daje czytelny benchmark.",
        "Jesli dane sa male, sprawdz stabilnosc. Jesli sa duze, sprawdz czas i pamiec.",
        "W raporcie opisujemy nie tylko wynik, ale tez dlaczego taki model byl sensowny dla problemu.",
        "Najlepiej porownac kilka rodzin: boosting, siec neuronowa, stacking i TabPFN.",
        "Aplikacja zapisuje wynik tak, aby mozna bylo wrocic do modelu, metryk i wybranych danych.",
    )


def _modern_pseudocode(task: str, estimator: str) -> tuple[str, ...]:
    metric = "accuracy_or_f1" if task == "schedule" else "rmse_mae_r2"
    return (
        "X, y = prepare_features(df)",
        "X = median_imputer.fit_transform(X)",
        "X_train, X_test, y_train, y_test = split(X, y)",
        f"model = {estimator}(params)",
        "model.fit(X_train, y_train)",
        "prediction = model.predict(X_test)",
        f"metrics = {metric}(y_test, prediction)",
        "compare_with_baseline_and_tabpfn(metrics)",
        "save_model_and_report(metrics)",
    )


def _build_tabpfn_models() -> list[TheoryModel]:
    configs = (
        (
            "tabpfn_quality",
            "TabPFN Quality - jakosc",
            "TabPFN Q",
            "TabPFNRegressor",
            "jakosc",
            "Przewidziec jakosc bez recznego strojenia lasow i boostingu.",
            "RMSE / MAE / R2 + stabilnosc predykcji",
            (("wysoka jakosc", 0.69), ("srednia", 0.22), ("ryzyko", 0.09)),
            "TabPFN quality: 0.84",
        ),
        (
            "tabpfn_delay",
            "TabPFN Delay - opoznienie",
            "TabPFN D",
            "TabPFNRegressor",
            "opoznienie",
            "Przewidziec opoznienie jako liczbe godzin na podstawie tabeli cech.",
            "RMSE / MAE / R2 + blad na skrajnych przypadkach",
            (("niski delay", 0.57), ("sredni", 0.29), ("wysoki", 0.14)),
            "TabPFN delay: 2.9 h",
        ),
        (
            "tabpfn_schedule",
            "TabPFN Schedule - strategia",
            "TabPFN S",
            "TabPFNClassifier",
            "schedule",
            "Wybrac klase strategii harmonogramowania z prawdopodobienstwami.",
            "Accuracy / F1 / macierz pomylek / pewnosc klasy",
            (("strategia A", 0.54), ("strategia B", 0.31), ("strategia C", 0.15)),
            "TabPFN schedule: A",
        ),
    )
    models: list[TheoryModel] = []
    for key, title, short, algorithm, task, goal, metric, probabilities, result in configs:
        models.append(
            TheoryModel(
                key=key,
                family="tabpfn",
                title=title,
                short_title=short,
                subtitle=(
                    "Nowoczesny backend dla danych tabelarycznych: mniej recznego strojenia, "
                    "mocny benchmark dla malych i srednich tabel."
                ),
                model_type="Model foundation dla tabel",
                algorithm=algorithm,
                goal=goal,
                metric=metric,
                focus="Szybkie porownanie z klasycznym ML bez budowania wielu wariantow recznie.",
                steps=TABPFN_STEPS,
                step_details=_tabpfn_details(task),
                pseudocode=_tabpfn_pseudocode(task),
                next_steps=(
                    "Porownaj TabPFN z klasycznym backendem na tym samym podziale train/test.",
                    "Jesli wynik jest dobry, uzyj go jako mocnego benchmarku albo jako modelu roboczego.",
                    "Jesli dataset jest duzy, sprawdz czas dzialania i rozwaz klasyczny model drzewiasty.",
                ),
                tip=(
                    "TabPFN nie jest zwyklym drzewem ani boostingiem. Traktuj go jak gotowy, "
                    "pretrenowany model do tabel, ktory dostaje Twoje dane jako kontekst."
                ),
                probabilities=probabilities,
                result=result,
            )
        )
    modern_configs = (
        (
            "modern_xgboost_quality",
            "XGBoost Quality - jakosc",
            "XGB Q",
            "xgboost.XGBRegressor",
            "jakosc",
            "Gradient boosting z regularyzacja dla nieliniowej predykcji jakosci.",
            "RMSE / MAE / R2 + kontrola przeuczenia",
            (("poprawa", 0.61), ("bez zmian", 0.24), ("ryzyko", 0.15)),
            "XGBoost quality: 0.86",
        ),
        (
            "modern_mlp_delay",
            "MLP Delay - opoznienie",
            "MLP D",
            "sklearn.neural_network.MLPRegressor",
            "opoznienie",
            "Siec neuronowa dla opoznien, gdy relacje cech sa nieliniowe i trudne dla modelu liniowego.",
            "RMSE / MAE / R2 + skalowanie + stabilnosc",
            (("niskie", 0.49), ("srednie", 0.34), ("wysokie", 0.17)),
            "MLP delay: 2.7 h",
        ),
        (
            "modern_stacking_schedule",
            "Stacking Schedule - strategia",
            "Stack S",
            "sklearn.ensemble.StackingClassifier",
            "schedule",
            "Meta-model laczy kilka klasyfikatorow i wybiera strategie harmonogramu.",
            "Accuracy / F1 / macierz pomylek + stabilnosc klas",
            (("strategia A", 0.48), ("strategia B", 0.36), ("strategia C", 0.16)),
            "Stacking schedule: A",
        ),
    )
    for key, title, short, algorithm, task, goal, metric, probabilities, result in modern_configs:
        models.append(
            TheoryModel(
                key=key,
                family="tabpfn",
                title=title,
                short_title=short,
                subtitle=(
                    "Nowoczesny segment ML: porownanie boostingow, sieci, stacking i modeli tabelarycznych "
                    "na tych samych danych oraz metrykach."
                ),
                model_type="Nowoczesny model tabelaryczny",
                algorithm=algorithm,
                goal=goal,
                metric=metric,
                focus="Sprawdzic, czy mocniejsza rodzina modeli daje realna przewage nad baseline.",
                steps=MODERN_STEPS,
                step_details=_modern_details(task, algorithm),
                pseudocode=_modern_pseudocode(task, algorithm),
                next_steps=(
                    "Porownaj wynik z RandomForest, HistGradient i TabPFN.",
                    "Sprawdz, czy poprawa metryk nie wynika z przeuczenia.",
                    "Dopisz do raportu koszt: czas, stabilnosc i latwosc wyjasnienia.",
                ),
                tip=(
                    "Nowoczesny model nie jest automatycznie lepszy. W aplikacji wygrywa ten, "
                    "ktory po walidacji daje lepsza decyzje i da sie sensownie opisac w raporcie."
                ),
                probabilities=probabilities,
                result=result,
            )
        )
    return models


def _build_ml_models() -> list[TheoryModel]:
    models: list[TheoryModel] = []
    for spec in get_ml_model_specs():
        task = _task_label(spec.name)
        algorithm = _ml_algorithm(spec.name)
        models.append(
            TheoryModel(
                key=spec.name,
                family="ml",
                title=f"{spec.label} - {task}",
                short_title=spec.label.replace("Quality ", "Q ").replace("Schedule ", "S "),
                subtitle=spec.description,
                model_type=_ml_model_type(task),
                algorithm=algorithm,
                goal=f"Przewidziec {task} na podstawie cech zlecenia.",
                metric=_ml_metric(task),
                focus=spec.focus,
                steps=_ml_steps(spec.name),
                step_details=_ml_details(spec.name, task),
                pseudocode=_ml_pseudocode(spec.name),
                next_steps=(
                    "Nastepny krok pokazuje realny etap algorytmu, a nie ogolny opis wszystkich modeli.",
                    "Po przejsciu krokow zobaczysz, czy model usrednia drzewa, sumuje poprawki czy liczy klasy liniowo.",
                    "Porownaj model z wariantami z tej samej grupy: jakosc, opoznienie albo strategia.",
                ),
                tip=(
                    "Patrz na roznice: lasy usredniaja wiele drzew, boosting dodaje kolejne poprawki, "
                    "a regresja logistyczna uczy liniowa granice klas."
                ),
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
                title=f"{spec.label} - heurystyka STO",
                short_title=spec.name,
                subtitle=spec.description,
                model_type="Heurystyka / metaheurystyka",
                algorithm=spec.label,
                goal="Ulozyc kolejnosc zlecen tak, aby zmniejszyc sume dodatnich opoznien STO.",
                metric="STO = suma max(0, Cj - dj); mniej znaczy lepiej",
                focus=spec.focus,
                steps=MH_STEPS,
                step_details=_mh_details(spec.label, spec.description),
                pseudocode=_mh_pseudocode(),
                next_steps=(
                    "Nastepny krok przelicza kolejke i pokazuje, skad bierze sie STO.",
                    "Na koncu porownujemy wynik z innymi metodami na tych samych zleceniach.",
                    "Najlepszy wariant mozna przeniesc do raportu, CSV albo Visual.",
                ),
                tip="Heurystyka nie trenuje modelu ML. Ma jawna regule lub procedure szukania kolejnosci.",
                probabilities=(("STO", 0.23), ("czas", 0.42), ("bufor", 0.35)),
                result="Najmniejsze STO",
            )
        )
    return models


THEORY_MODELS: tuple[TheoryModel, ...] = tuple(
    _build_ml_models() + _build_mh_models() + _build_tabpfn_models()
)


def get_theory_models(family: ModelFamily | None = None) -> tuple[TheoryModel, ...]:
    if family is None:
        return THEORY_MODELS
    return tuple(model for model in THEORY_MODELS if model.family == family)


def find_theory_model(key: str) -> TheoryModel:
    for model in THEORY_MODELS:
        if model.key == key:
            return model
    return THEORY_MODELS[0]
