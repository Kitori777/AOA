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
        "Wybierasz, czy przygotować dane, trenować modele, uruchamiać heurystyki STO albo analizować wyniki.",
        (
            "Wejdź w Main.",
            "Najpierw wczytaj lub wygeneruj dane.",
            "Dopiero potem wybieraj modele ML/STO.",
        ),
        "Aplikacja działa jako przepływ: dane -> trening/heurystyka -> analiza -> eksport.",
        (
            "Najszybszy start: sample CSV + modele Quality/Delay.",
            "Do harmonogramowania używaj sekcji STO i porównuj kilka metod naraz.",
        ),
    ),
    GuideStep(
        "2. Dane wejściowe",
        "Przygotowujesz zbiór, na którym modele i heurystyki będą liczyć wyniki.",
        (
            "Ustaw liczbę rekordów i parametry generatora albo wybierz CSV.",
            "Sprawdź, czy masz kolumny: cena, odpad, termin_h, czas_produkcji_h.",
            "Po wczytaniu zweryfikuj podsumowanie po prawej stronie.",
        ),
        "Jakość danych wejściowych bezpośrednio wpływa na jakość predykcji i ranking metod STO.",
        (
            "Większa próbka zwykle daje stabilniejsze metryki.",
            "Braki i duplikaty najpierw poprawiaj w Results Studio.",
        ),
    ),
    GuideStep(
        "3. Trenowanie modeli ML",
        "Modele uczą się przewidywać jakość, opóźnienie i strategię harmonogramowania.",
        (
            "Zaznacz modele z grup Quality/Delay/Schedule.",
            "Uruchom trening i sprawdź metryki.",
            "Porównuj score + odchylenie, nie tylko pojedynczy wynik.",
        ),
        "W aplikacji masz 12 wariantów modeli klasycznych. Najlepszy wybór to kompromis: wynik + stabilność.",
        (
            "RMSE/MAE: im niżej, tym lepiej.",
            "R²: im bliżej 1, tym lepiej.",
            "Dla Schedule patrz na Accuracy i F1.",
        ),
    ),
    GuideStep(
        "4. Heurystyki STO",
        "Porównujesz kolejności zleceń i minimalizujesz sumę dodatnich opóźnień (STO).",
        (
            "Wybierz kilka metod jednocześnie (np. MT, MOPT, NEH, LOCAL_SEARCH).",
            "Uruchom porównanie i sprawdź najlepszy STO.",
            "Zapisz wynik i przejdź do Visual, żeby zobaczyć drzewo/ścieżkę.",
        ),
        "STO to ranking wariantów harmonogramu, nie trening modelu ML.",
        (
            "Niższe STO oznacza lepszą kolejność.",
            "Porównuj też stabilność metody między różnymi próbkami danych.",
        ),
    ),
    GuideStep(
        "5. Rozwiązywanie na zapisanym modelu",
        "Używasz zapisanego modelu do predykcji i priorytetyzacji nowych rekordów.",
        (
            "Kliknij rozwiązywanie na zapisanym modelu.",
            "Wybierz paczkę modelu z katalogu models/.",
            "Wczytaj CSV i sprawdź wynikowy plik oraz kolumny predykcji.",
        ),
        "Po predykcji aplikacja tworzy m.in. pred_quality, pred_delay i priority.",
        (
            "Model i dane muszą mieć zgodne kolumny.",
            "Wyniki najlepiej analizować dalej w Visual i Results.",
        ),
    ),
    GuideStep(
        "6. Visual Lab",
        "Budujesz wykresy 2D/3D i dashboardy diagnostyczne do szybkiej analizy danych.",
        (
            "Wybierz X/Y/Z i typ wykresu.",
            "Kliknij Aktualizuj wykres po zmianie ustawień.",
            "Użyj Otwórz D3 HTML do interaktywnej analizy i filtrów.",
        ),
        "Visual pokazuje wykres + raport statystyczny, korelacje, outliery i porównania metod.",
        (
            "Dla drzew i heurystyk korzystaj z większego obszaru wykresu i zoomu.",
            "Dla Gantta sprawdzaj kolejność zadań i obciążenie maszyn.",
        ),
    ),
    GuideStep(
        "7. Results Studio + SQL",
        "Przeglądasz dane tabelarycznie i uruchamiasz zapytania SQL bez opuszczania aplikacji.",
        (
            "Wczytaj CSV i ustaw liczbę widocznych rekordów.",
            "Przełącz na kartę SQL i wykonaj zapytanie.",
            "Eksportuj widok tabeli lub wynik SQL do CSV.",
        ),
        "Masz osobny widok wyników SQL, historię zapytań, autouzupełnianie kolumn i profil jakości danych.",
        (
            "SQL nie nadpisuje głównej tabeli wynikowej.",
            "Używaj filtrów, gdy chcesz szybko zawęzić dane przed eksportem.",
        ),
    ),
    GuideStep(
        "8. Analytics Studio",
        "Uruchamiasz gotowe workflowy analityczne: jakosc danych, KPI, dashboard, raport, segmenty, korelacje, outliery, trendy i plan notebooka.",
        (
            "Wejdz w Analytics.",
            "Wczytaj dane albo uzyj danych juz przygotowanych w aplikacji.",
            "Wybierz workflow, metryke i wymiar.",
            "Kliknij Uruchom analize albo Wykonaj wszystko.",
            "Zapisz wynik jako HTML, notebook albo CSV akcji.",
        ),
        "Analytics nie jest tylko lista opcji. To panel, w ktorym wykonujesz realna analize i dostajesz tekst, rekomendowany wykres, podsumowanie oraz nastepne akcje.",
        (
            "Data Quality sprawdza braki, duplikaty i profil kolumn.",
            "Metric Diagnostics tlumaczy, co moze napedzac zmiane metryki.",
            "Segment Explorer, Correlation Explorer i Outlier Analysis pomagaja znalezc miejsca warte sprawdzenia.",
            "Wykres rekomendowany w Analytics najlepiej narysowac potem w Visual.",
        ),
    ),
    GuideStep(
        "9. Report Builder: HTML, PDF, MD i TeX",
        "Budujesz wlasny raport z sekcji, wynikow analiz, plikow, KPI, wykresow, rekomendacji i podgladu podobnego do prostego edytora dokumentu.",
        (
            "W Analytics kliknij Report Builder.",
            "Dodaj aktualny wynik, plik, sekcje, KPI, wykres albo rekomendacje.",
            "Edytuj tresc po lewej i czytaj podglad po prawej.",
            "Uzyj Eksport HTML dla wersji interaktywnej.",
            "Uzyj Eksport PDF, gdy chcesz gotowy plik do oddania lub wyslania.",
        ),
        "Report Builder dziala jak lekki LaTeX/Overleaf w aplikacji: zapisujesz tresc w prostym formacie, widzisz podglad i eksportujesz do formatu, ktory pasuje do pracy.",
        (
            "HTML najlepiej nadaje sie do interaktywnych wykresow i osadzonych widokow.",
            "PDF jest czytelnym raportem tekstowym do dokumentacji.",
            "MD i TeX sa dobre, gdy chcesz dalej edytowac raport poza aplikacja.",
            "Do raportu mozna dodawac wyniki z innych plikow, np. CSV, MD, TXT, PNG, SVG albo HTML.",
        ),
    ),
    GuideStep(
        "10. Diagrams Studio",
        "Tworzysz schematy procesow, UML, ERD, BPMN, pipeline danych, architekture, mapy mysli i diagramy decyzyjne.",
        (
            "Wejdz w Diagrams.",
            "Wybierz szablon albo zacznij od pustego diagramu.",
            "Dodaj ksztalt, przesun go myszka i polacz z innym elementem.",
            "Kliknij prawym przyciskiem, zeby edytowac tekst, kolor, duplikowac albo usunac element.",
            "Eksportuj diagram do .drawio, SVG, Mermaid albo HTML.",
        ),
        "Diagrams sluzy do robienia rzeczy, nie tylko ogladania. Mozesz ulozyc proces analityczny, pokazac przeplyw danych, narysowac logike raportu albo przygotowac schemat do dokumentacji.",
        (
            "Flowchart jest dobry do procesow krok po kroku.",
            "UML i ERD sa dobre do struktury systemu oraz danych.",
            "BPMN i Swimlane pomagaja pokazac role oraz odpowiedzialnosci.",
            "Mermaid przydaje sie do README i dokumentacji na GitHubie.",
        ),
    ),
    GuideStep(
        "11. Theory: animacje ML i STO",
        "Uczysz sie, jak naprawde dzialaja modele ML oraz heurystyki STO, bez mieszania tych dwoch swiatow.",
        (
            "Wejdz w Theory.",
            "Wybierz tryb ML, gdy chcesz zrozumiec predykcje i trening.",
            "Wybierz Heurystyki, gdy chcesz zrozumiec kolejkowanie zlecen i STO.",
            "Przechodz animacje krok po kroku albo wlacz autoplay.",
            "Czytaj panel z pseudokodem, opisem kroku i stanem przykladu.",
        ),
        "ML uczy zaleznosci z danych: cechy, cel, trening, walidacja, predykcja. STO uklada kolejnosc zlecen i liczy czasy zakonczenia oraz opoznienia. To dwa rozne mechanizmy i instrukcja pokazuje je osobno.",
        (
            "Random Forest usrednia wiele drzew, ExtraTrees losuje progi, a boosting poprawia bledy.",
            "Schedule to klasyfikacja strategii, a nie zwykla regresja.",
            "STO liczy Cj, Tj i sume dodatnich opoznien.",
            "Quality, Delay i Schedule sa tez widoczne w Theory jako osobne przyklady.",
        ),
    ),
    GuideStep(
        "12. ALICE Assistant",
        "ALICE odpowiada na pytania o procesy, prowadzi krok po kroku i może uruchamiać akcje operatora.",
        (
            "Kliknij ALICE i zadaj pytanie naturalnym językiem.",
            "Włącz Tryb operatora dla sekwencji akcji.",
            "Ustaw profil odpowiedzi: krótko / normalnie / ekspercko.",
            "Zapytaj o Main, Visual, Results, Analytics, Diagrams, Theory, PDF, HTML albo samonauke.",
        ),
        "ALICE korzysta z wiedzy o aplikacji, kodzie i raportach samonauki, żeby dawać praktyczne wskazówki.",
        (
            "Możesz pytać: jak przejść proces, gdzie kliknąć, co poprawić w modelach.",
            "Przy ciężkich akcjach używaj potwierdzenia bezpieczeństwa.",
            "Samonauka jest wylaczona automatycznie po starcie aplikacji; wlacz ja dopiero wtedy, gdy chcesz raport uczenia.",
            "Przed GitHubem nie commituj lokalnych logow i cache HTML z alice_sources.",
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
