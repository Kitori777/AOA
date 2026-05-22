from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Literal

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

LearningChartKind = Literal[
    "overview",
    "regression_metrics",
    "classification_metrics",
    "overfitting",
    "feature_importance",
    "quality",
    "delay",
    "schedule",
    "sto",
    "priority",
]


@dataclass(frozen=True)
class GuideStep:
    title: str
    goal: str
    clicks: tuple[str, ...]
    explanation: str
    good_to_know: tuple[str, ...]


@dataclass(frozen=True)
class TheoryModule:
    key: LearningChartKind
    title: str
    formula: str
    explanation: str
    interpretation: tuple[str, ...]


GUIDE_STEPS: tuple[GuideStep, ...] = (
    GuideStep(
        "1. Start: wybór trybu pracy",
        "Wybierasz, czy przygotować dane, nauczyć modele, użyć zapisanego modelu albo obejrzeć raport z danych.",
        ("Wejdź w Main.", "Zaznacz modele ML albo STO.", "Najpierw wygeneruj albo wczytaj dane."),
        "Aplikacja działa jako przepływ: dane → nauka modelu → ocena modelu → użycie modelu na nowych danych.",
        (
            "Zacznij od Quality i Delay.",
            "STO zapisujesz jako model algorytmiczny i uruchamiasz później na CSV.",
        ),
    ),
    GuideStep(
        "2. Dane wejściowe",
        "Tworzysz albo wczytujesz zlecenia produkcyjne, na których model ma się uczyć.",
        (
            "Ustaw liczbę rekordów i test_size.",
            "Wybierz kształty oraz materiały.",
            "Kliknij Generuj dane albo Wczytaj dane CSV.",
        ),
        "Dane są podstawą całej aplikacji. Jeżeli w danych są dziwne wartości, model też może pokazywać dziwne wyniki.",
        (
            "Więcej rekordów zwykle daje stabilniejszy model.",
            "test_size odkłada część danych do sprawdzenia modelu.",
        ),
    ),
    GuideStep(
        "3. Trenowanie modeli ML",
        "Modele uczą się przewidywać jakość, opóźnienie albo rekomendowaną strategię.",
        (
            "Zaznacz Quality, Delay albo Schedule.",
            "Kliknij Uruchom / zapisz wybrane modele.",
            "Sprawdź log i metryki RMSE, MAE, R², Accuracy/F1.",
        ),
        "Quality i Delay są regresją, a Schedule klasyfikacją. W trybie classic dostępnych jest 12 wariantów modeli: osobne podejścia dla jakości, opóźnień i strategii. Po treningu aplikacja raportuje, jak dobrze model odtworzył zależności z danych.",
        (
            "RMSE/MAE im niżej, tym lepiej.",
            "R² im bliżej 1, tym lepiej.",
            "Accuracy/F1 są dla klasyfikacji.",
        ),
    ),
    GuideStep(
        "4. Modele STO",
        "STO porównuje kolejności zleceń i wybiera wariant z mniejszym opóźnieniem.",
        (
            "Zaznacz MT, MO, MZO, MOPT albo inne heurystyki: Slack, Critical Ratio, NEH, Local Search.",
            "Zapisz model STO.",
            "Później uruchom zapisany model na CSV.",
        ),
        "STO nie uczy się jak model ML. Liczy sumę dodatnich opóźnień dla różnych kolejności i pozwala porównać klasyczne reguły, warianty mieszane oraz proste metody przeszukiwania.",
        ("STO = 0 oznacza brak spóźnień.", "Niższe STO oznacza lepszą kolejność."),
    ),
    GuideStep(
        "5. Rozwiązywanie na zapisanym modelu",
        "Używasz wcześniej zapisanego modelu do wyliczenia predykcji i priorytetów.",
        (
            "Kliknij Rozwiąż zapisany model na wybranych danych.",
            "Wybierz model z models/.",
            "Wybierz CSV i sprawdź plik wynikowy.",
        ),
        "Po predykcji aplikacja tworzy kolumny pred_quality, pred_delay oraz priority.",
        ("Model i dane muszą mieć zgodne kolumny.", "Wynik można później obejrzeć w Visual."),
    ),
    GuideStep(
        "6. Wizualizacje i raport danych",
        "Wizualizacje pokazują wykres i krótką diagnostykę danych.",
        (
            "Przejdź do Visual.",
            "Wczytaj CSV.",
            "Wybierz kolumny X/Y i typ wykresu.",
            "Użyj paska narzędzi do zoomu, przesuwania i zapisu.",
        ),
        "Visual łączy wykres z raportem: korelacja, braki danych, zakresy i obserwacje odstające.",
        (
            "Dashboard daje szybki przegląd.",
            "Diagnostics pokazuje reszty i dopasowanie.",
            "CorrelationMatrix pomaga wykryć silne relacje.",
        ),
    ),
    GuideStep(
        "7. Results Studio i CSV loader",
        "Przeglądasz wynikowy CSV, wybierasz liczbę widocznych rekordów i eksportujesz dokładnie ten widok, który jest potrzebny.",
        (
            "Przejdź do Results.",
            "Wczytaj CSV z danymi albo wynikami solve.",
            "Ustaw preset wierszy albo wpisz własną liczbę rekordów.",
            "Użyj filtra, sortowania, zakresu min/max albo największych/najmniejszych wartości.",
        ),
        "Results Studio jest praktycznym czytnikiem CSV: pozwala szybko zawęzić dane, sprawdzić jakość pliku, profil kolumny i przygotować mniejszy wycinek do dalszej analizy.",
        (
            "Pole własnej liczby wierszy ma pierwszeństwo przed presetem.",
            "Eksport CSV zapisuje tylko aktualnie widoczne rekordy.",
            "Karty u góry pokazują pełny stan pliku i liczbę widocznych wierszy.",
        ),
    ),
)


THEORY_MODULES: tuple[TheoryModule, ...] = (
    TheoryModule(
        "overview",
        "Mapa modeli",
        "dane → cechy → model → metryki → decyzja",
        "Model zamienia dane na decyzję użytkową: jakość, opóźnienie, strategię albo kolejność. W aplikacji dostępne są różne rodziny modeli, żeby porównać stabilny las, boosting, ExtraTrees, model liniowy oraz heurystyki STO.",
        (
            "Najpierw sprawdzaj dane.",
            "Po treningu czytaj metryki.",
            "Wynik interpretuj razem z wykresem.",
        ),
    ),
    TheoryModule(
        "regression_metrics",
        "Regresja: RMSE, MAE i R²",
        "RMSE = sqrt(mean((y - ŷ)^2)), MAE = mean(|y - ŷ|), R² ∈ (-∞, 1]",
        "Quality i Delay przewidują liczby. RMSE mocniej karze duże błędy, MAE pokazuje średni błąd, a R² pokazuje, ile zmienności danych model wyjaśnia.",
        (
            "RMSE niższe = mniej dużych pomyłek.",
            "MAE niższe = mniejszy przeciętny błąd.",
            "R² blisko 1 = dobry opis danych.",
        ),
    ),
    TheoryModule(
        "classification_metrics",
        "Klasyfikacja: Accuracy i F1",
        "Accuracy = poprawne / wszystkie, F1 = 2·precision·recall/(precision+recall)",
        "Schedule wybiera klasę. Accuracy pokazuje skuteczność ogólną, a F1 jest lepsze przy nierównych klasach.",
        (
            "Accuracy jest intuicyjne.",
            "F1 łączy precyzję i czułość.",
            "Dla Schedule patrz na stabilność decyzji.",
        ),
    ),
    TheoryModule(
        "overfitting",
        "Przeuczenie",
        "błąd_train ↓, ale błąd_test ↑",
        "Przeuczenie oznacza, że model pamięta dane treningowe, ale słabo działa na nowych danych.",
        (
            "Idealny trening nie zawsze oznacza dobry model.",
            "Potrzebne są dane testowe.",
            "Porównuj train i test.",
        ),
    ),
    TheoryModule(
        "feature_importance",
        "Ważność cech",
        "model ≈ f(cena, odpad, czas, termin, materiał, kształt, ...)",
        "Ważność cech pokazuje, które kolumny najmocniej wpływają na decyzję modelu.",
        (
            "Silna cecha nie zawsze oznacza przyczynę.",
            "Dziwne dominujące cechy sugerują kontrolę danych.",
            "To dodatek do metryk.",
        ),
    ),
    TheoryModule(
        "quality",
        "Quality — jakość",
        "ŷ_quality = średnia predykcji wielu drzew",
        "Modele jakości porównują kilka sposobów patrzenia na dane: Random Forest stabilizuje wynik, ExtraTrees zwiększa losowość, a boosting poprawia kolejne błędy.",
        (
            "Sprawdzaj RMSE/MAE.",
            "Wykres predykcja kontra rzeczywistość pomaga wykryć błąd.",
            "Model dobrze łapie zależności nieliniowe.",
        ),
    ),
    TheoryModule(
        "delay",
        "Delay — opóźnienie",
        "ŷ_delay = F₀(x) + η·h₁(x) + η·h₂(x) + ...",
        "Modele opóźnień porównują boosting, lasy losowe, ExtraTrees i wariant histogramowy, żeby lepiej uchwycić ryzyko przekroczenia terminu.",
        (
            "RMSE jest ważne, bo mocno karze duże pomyłki.",
            "Duże błędy opóźnienia są kosztowne.",
            "Warto kontrolować rozkład reszt.",
        ),
    ),
    TheoryModule(
        "schedule",
        "Schedule — strategia",
        "strategia = argmax P(klasa | cechy)",
        "Modele Schedule porównują klasyfikatory drzewiaste, boosting oraz lekki model liniowy, czyli sprawdzają różne sposoby wyboru strategii z największym prawdopodobieństwem.",
        (
            "To rekomendacja, nie gwarancja.",
            "Przy klasach nierównych F1 jest ważniejsze.",
            "Decyzje powinny być stabilne na podobnych danych.",
        ),
    ),
    TheoryModule(
        "sto",
        "STO — kolejność",
        "STO = Σ max(0, Cᵢ - Dᵢ)",
        "STO liczy sumę dodatnich opóźnień dla kolejności zleceń.",
        (
            "STO = 0 oznacza brak spóźnień.",
            "Niższe STO = lepsza kolejność.",
            "To metryka algorytmiczna.",
        ),
    ),
    TheoryModule(
        "priority",
        "Priorytet użytkowy",
        "priority = 0.7·pred_quality + 0.3/(1 + pred_delay)",
        "Priorytet łączy przewidywaną jakość i ryzyko opóźnienia.",
        (
            "Służy do sortowania.",
            "Jakość ma tu większą wagę.",
            "Wagi można zmienić pod inny cel biznesowy.",
        ),
    ),
)


def get_guide_steps() -> tuple[GuideStep, ...]:
    return GUIDE_STEPS


def get_theory_modules() -> tuple[TheoryModule, ...]:
    return THEORY_MODULES


def find_theory_module(key: str) -> TheoryModule:
    for module in THEORY_MODULES:
        if module.key == key:
            return module
    return THEORY_MODULES[0]


def build_learning_figure(kind: LearningChartKind) -> Figure:
    fig = Figure(figsize=(7.4, 4.4), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)

    if kind == "overview":
        steps = ["Dane", "Cechy", "Model", "Metryki", "Decyzja"]
        values = list(range(1, 6))
        ax.plot(values, [1.0, 1.35, 1.15, 1.55, 1.25], marker="o", linewidth=2)
        ax.set_xticks(values, steps)
        ax.set_yticks([])
        ax.set_title("Od danych do decyzji")
    elif kind == "regression_metrics":
        ax.bar(["słaby", "średni", "dobry"], [0.32, 0.16, 0.06], label="RMSE")
        ax.set_title("Regresja: niższy błąd = lepiej")
        ax.set_ylabel("RMSE")
    elif kind == "classification_metrics":
        ax.bar(["Accuracy", "Precision", "Recall", "F1"], [0.86, 0.81, 0.78, 0.79])
        ax.set_ylim(0, 1)
        ax.set_title("Klasyfikacja: metryki skuteczności")
    elif kind == "overfitting":
        complexity = list(range(1, 11))
        train = [0.42 * exp(-0.35 * x) + 0.03 for x in complexity]
        test = [0.28 * exp(-0.25 * x) + 0.02 + max(0, x - 5) ** 2 * 0.012 for x in complexity]
        ax.plot(complexity, train, marker="o", label="train")
        ax.plot(complexity, test, marker="o", label="test")
        ax.set_title("Przeuczenie: train spada, test rośnie")
        ax.legend()
    elif kind == "feature_importance":
        ax.barh(["odpad", "czas", "termin", "materiał", "cena"], [0.31, 0.24, 0.18, 0.15, 0.12])
        ax.set_title("Ważność cech")
    elif kind == "quality":
        observed = [0.62, 0.68, 0.71, 0.69, 0.76, 0.79, 0.81, 0.78, 0.84, 0.87]
        predicted = [0.61, 0.67, 0.70, 0.71, 0.75, 0.78, 0.80, 0.80, 0.83, 0.86]
        ax.scatter(observed, predicted)
        ax.plot([0.6, 0.9], [0.6, 0.9], linewidth=2)
        ax.set_title("Quality: predykcja kontra rzeczywistość")
    elif kind == "delay":
        ax.plot(list(range(10)), [20 * exp(-0.28 * i) + 1.5 for i in range(10)], marker="o")
        ax.set_title("Delay: błąd maleje w kolejnych etapach")
    elif kind == "schedule":
        ax.bar(["MT", "MO", "MZO", "GEN"], [0.42, 0.24, 0.11, 0.23])
        ax.set_ylim(0, 1)
        ax.set_title("Schedule: prawdopodobieństwo klas")
    elif kind == "sto":
        ax.bar(["MT", "MO", "MZO", "GEN"], [10, 20, 90, 8])
        ax.set_title("STO: mniej znaczy lepiej")
    elif kind == "priority":
        delays = list(range(10))
        ax.plot(delays, [0.7 * 0.85 + 0.3 / (1 + d) for d in delays], marker="o")
        ax.set_title("Priorytet maleje przy większym opóźnieniu")
    ax.grid(True, alpha=0.3)
    return fig
