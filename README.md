# AOA – Aplikacja Optymalnego Algorytmowania

## Opis projektu

AOA to rozwijana aplikacja desktopowa i terminalowa napisana w Pythonie. Jej celem jest wspomaganie analizy danych, uczenia modeli, porównywania metod harmonogramowania oraz prezentowania wyników w formie czytelnych tabel, raportów i wykresów.

Od wersji `0.5.1` projekt rozwija się nie tylko jako narzędzie produkcyjno-optymalizacyjne, ale również jako aplikacja analityczno-edukacyjna. Użytkownik może wczytać własne dane tabelaryczne, obejrzeć je w widoku podobnym do prostego CSV viewera, przygotować raport, uruchomić wizualizację oraz sprawdzić krótkie wyjaśnienia modeli i metryk.

Projekt zachowuje architekturę modułową:

- warstwa `core` odpowiada za logikę aplikacji, generowanie i przetwarzanie danych, trenowanie modeli, ewaluację wyników, harmonogramowanie, raporty, treści edukacyjne i przygotowanie danych do wizualizacji,
- warstwa `gui` odpowiada za graficzny interfejs użytkownika i nie powinna przechowywać logiki biznesowej,
- warstwa `cli` umożliwia obsługę aplikacji z poziomu terminala,
- katalog `tests` zawiera testy jednostkowe i testy przepływów,
- katalog `docs` zawiera dokumentację użytkową i teoretyczną,
- katalog `logs` przechowuje logi błędów i informacje diagnostyczne.

Aplikacja umożliwia między innymi:

- generowanie przykładowych danych produkcyjnych,
- wczytywanie danych z plików `.csv`, `.txt` i `.tsv`,
- pracę także na dowolnych danych tabelarycznych, nie tylko produkcyjnych,
- trenowanie modeli ML dla jakości, opóźnień i strategii harmonogramowania,
- korzystanie z klasycznych modeli `scikit-learn` oraz eksperymentalnego backendu `TabPFN`,
- ocenę modeli za pomocą metryk takich jak RMSE, MAE, R², Accuracy i F1,
- uruchamianie metod harmonogramowania STO i porównywanie ich wyników,
- tworzenie wykresów 2D i 3D,
- przeglądanie danych w przebudowanym `Results Studio`,
- filtrowanie, sortowanie, limitowanie, profilowanie i eksport widocznego widoku danych,
- korzystanie z interaktywnej instrukcji użytkownika na stronie `Readme`,
- korzystanie ze strony `Theory`, która prostym językiem wyjaśnia zachowanie modeli, metryk i algorytmów,
- zapis modeli, raportów i wyników do plików,
- obsługę pełnych przepływów pracy zarówno z poziomu GUI, jak i z terminala.


## Najważniejsze poprawki w wersji 0.5.1

* Metryki ML pokazują teraz osobno wynik na zbiorze treningowym i testowym.
* `df_test` jest realnie przekazywany do treningu i oceny modeli w CLI oraz GUI.
* Dodano 12 wariantów modeli ML oraz testy dla każdego z nich.
* `TheoryPage` ma większą, czytelniejszą animację oraz zwijany panel boczny.
* Pakiety `services`, `ml_models` i `mh_models` są rozbite na mniejsze pliki, a `__init__.py` pełnią rolę lekkich fasad.

## Najważniejsze nowości w wersji 0.5.0

### Interaktywna instrukcja użytkownika

Strona `Readme` została przebudowana z prostego widoku dokumentacji na interaktywną instrukcję. Użytkownik może przechodzić po kolejnych krokach i sprawdzać:

- co robi dany moduł,
- gdzie kliknąć,
- po co wykonywany jest dany etap,
- na co uważać przy danych, modelach, STO i wynikach.

### Theory Page — teoria użytkowa modeli

Strona `Theory` pokazuje najważniejsze pojęcia potrzebne do korzystania z aplikacji:

- regresja i metryki RMSE/MAE/R²,
- klasyfikacja i metryki Accuracy/F1,
- przeuczenie modelu,
- ważność cech,
- modele jakości i opóźnień,
- strategia harmonogramowania,
- STO,
- priorytet zlecenia.

Każdy moduł ma krótki zapis matematyczny, opis prostym językiem, praktyczną interpretację i wykres pokazujący intuicję działania.

### Visual Lab — wizualizacje i raporty

Widok `Visual` został rozbudowany w kierunku laboratorium eksploracji danych. Użytkownik może wybierać kolumny X/Y/Z i przełączać typy wykresów, m.in.:

- `Dashboard`,
- `Diagnostics`,
- `Pair Explorer`,
- `3D Scatter`,
- `3D Surface`,
- `Bubble Chart`,
- `Heatmap Density`,
- `Outlier Map`,
- `Step View`,
- `Column Ranking`,
- klasyczne wykresy `Scatter`, `Line`, `Histogram`, `Boxplot`,
- macierze korelacji i podobieństwa.

Po prawej stronie widoczny jest raport, który podsumowuje dane, statystyki wybranych kolumn, obserwacje odstające i korelację.

### Results Studio — viewer i raport danych

Strona `Results` została przebudowana jako początek prostego, nowoczesnego viewera danych. Zamiast niedokończonych przycisków regresji i klasyfikacji widok skupia się na pracy z tabelą:

- globalny filtr tekstowy,
- sortowanie po wybranej kolumnie,
- wybór kierunku sortowania,
- limit liczby wierszy,
- profil wybranej kolumny,
- raport braków danych,
- eksport widocznego widoku do CSV,
- karty podsumowania liczby wierszy, kolumn, braków i duplikatów.

## Aktualna struktura repozytorium

```text
TOOLS/
├── docs/
│   ├── guide.md
│   └── theory.md
├── data/
│   └── sample/
│       ├── production.csv
│       ├── train.csv
│       └── test.csv
├── logs/
├── models/
├── src/
│   └── AOA/
│       ├── __init__.py
│       ├── app.py
│       ├── config.py
│       ├── messages.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── helpers.py
│       │   ├── interactive.py
│       │   ├── main.py
│       │   ├── parser.py
│       │   └── commands/
│       │       ├── generate.py
│       │       ├── preview.py
│       │       ├── solve.py
│       │       ├── sto.py
│       │       ├── train.py
│       │       └── workflow.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── constants.py
│       │   ├── data_generation.py
│       │   ├── data_io.py
│       │   ├── dataset_ops.py
│       │   ├── evaluation.py
│       │   ├── features.py
│       │   ├── learning_content.py
│       │   ├── models.py
│       │   ├── result_viewer_service.py
│       │   ├── scheduling.py
│       │   ├── sto_models.py
│       │   ├── tabpfn_models.py
│       │   ├── visualization_service.py
│       │   ├── diagrams/
│       │   └── services/
│       │       ├── __init__.py
│       │       ├── analysis.py
│       │       ├── common.py
│       │       ├── files.py
│       │       ├── io_ops.py
│       │       ├── sto.py
│       │       ├── summary.py
│       │       └── training.py
│       ├── gui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   └── pages/
│       │       ├── __init__.py
│       │       ├── main_page/
│       │       ├── theory_page/
│       │       ├── readme_page.py
│       │       ├── results_page.py
│       │       └── visual_page.py
│       └── utils/
│           ├── __init__.py
│           ├── error_utils.py
│           ├── logging_utils.py
│           └── threading_utils.py
├── tests/
│   ├── cli/
│   └── core/
├── CHANGELOG.md
├── README.md
├── pyproject.toml
└── uv.lock
```

Dane przykładowe są trzymane wyłącznie w `data/sample/`. Pliki generowane lokalnie przez aplikację (`data/dane_*.csv`, `data/train_*.csv`, `data/test_*.csv`, wyniki solve/STO) są ignorowane przez `.gitignore`, żeby nie trafiały przypadkowo do commitów.

## Rozszerzone modele ML i heurystyki STO

W bieżącej wersji panel wyboru modeli został rozszerzony tak, aby użytkownik mógł porównywać różne podejścia dla podobnych celów. W trybie `classic` dostępnych jest 12 wariantów ML:

- `Quality`, `Quality_ET`, `Quality_GB`, `Quality_HGB` — cztery modele regresyjne dla jakości, patrzące odpowiednio na stabilność lasu, większą losowość ExtraTrees, poprawianie błędów przez boosting oraz szybki boosting histogramowy.
- `Delay`, `Delay_RF`, `Delay_ET`, `Delay_HGB` — cztery modele regresyjne dla opóźnień, skupione na ryzyku przekroczenia terminu i dużych błędach.
- `Schedule`, `Schedule_ET`, `Schedule_GB`, `Schedule_LOG` — cztery klasyfikatory strategii harmonogramowania, od modeli drzewiastych po prosty baseline liniowy.

Modele heurystyczne STO zostały rozszerzone do zestawu 12 metod: `MT`, `MO`, `MZO`, `GENETIC`, `SLACK`, `CR`, `EDD_SPT`, `SPT_EDD`, `LPT_EDD`, `NEH`, `LOCAL_SEARCH`, `RANDOM_RESTART`. Każda metoda ma opis, na co patrzy: termin, czas obróbki, zapas, krytyczność, wariant wstawiania lub lokalne poprawki kolejności.

Architektura została przygotowana modułowo: definicje modeli ML znajdują się w `src/AOA/core/ml_models/`, a definicje heurystyk w `src/AOA/core/mh_models/`. Dzięki temu można później dopisywać kolejne warianty bez przeciążania głównych plików aplikacji.

## Jak uruchomić projekt

### Wersja z `uv`

#### 1. Sklonuj repozytorium i przejdź do katalogu projektu

```bash
git clone git@github.com:Kitori777/AOA.git
cd AOA
```

#### 2. Zainstaluj zależności

```bash
uv sync --dev
```

#### 3. Uruchom aplikację desktopową

```bash
uv run python -m AOA.app
```

#### 4. Uruchom CLI

```bash
uv run aoa-cli --help
```

#### 5. Uruchom testy

```bash
uv run pytest
```

### Wersja bez `uv`

#### 1. Sklonuj repozytorium i przejdź do katalogu projektu

```bash
git clone git@github.com:Kitori777/AOA.git
cd AOA
```

#### 2. Utwórz i aktywuj środowisko wirtualne

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 3. Zainstaluj projekt

```bash
pip install -e .
```

#### 4. Uruchom aplikację

```bash
python -m AOA.app
```

#### 5. Uruchom testy

```bash
pytest
```

## Aktualny stan projektu

Projekt posiada działający fundament techniczny i obejmuje aplikację desktopową, interfejs terminalowy, warstwę testów oraz pierwsze moduły edukacyjno-analityczne. Główna zasada architektury pozostaje bez zmian: logika aplikacji znajduje się w `core`, a GUI jest warstwą prezentacji i obsługi użytkownika.

### Zrealizowane elementy

- wydzielenie warstwy `core`,
- oddzielenie logiki aplikacyjnej od GUI,
- dodanie warstwy `cli`,
- modularna struktura projektu oparta o układ `src/`,
- generowanie danych testowych,
- wczytywanie danych CSV/TXT/TSV,
- obsługa dowolnych danych tabelarycznych w widokach `Visual` i `Results`,
- przygotowanie cech do modeli ML,
- trenowanie wielu modeli jednocześnie,
- automatyczny zapis modeli do osobnych plików,
- klasyczne modele ML:
  - Random Forest dla jakości,
  - Gradient Boosting dla opóźnień,
  - Random Forest dla strategii harmonogramowania,
- eksperymentalny backend `TabPFN`,
- metryki jakości uczenia modeli ML,
- heurystyczne modele STO:
  - `MT`,
  - `MO`,
  - `MZO`,
  - `GENETIC`,
- zapis i późniejsze używanie modeli STO,
- interaktywna instrukcja na stronie `Readme`,
- teoria użytkowa na stronie `Theory`,
- rozbudowane wizualizacje i raporty na stronie `Visual`,
- przebudowany viewer danych na stronie `Results`,
- podstawowe operacje analityczne i ewaluacyjne,
- obsługa pełnych przepływów pracy w GUI i CLI,
- logowanie błędów do katalogu `logs`,
- testy jednostkowe i testy przepływów,
- plik `CHANGELOG.md`,
- przygotowanie projektu do wersjonowania oraz release’ów.

## Plan na kolejne aktualizacje

- dalszy rozwój `Visual Lab` w kierunku bardziej interaktywnych wykresów,
- mocniejsze dashboardy i karty diagnostyczne,
- dalszy rozwój `Results Studio` w stronę pełnego narzędzia do pracy z plikami CSV,
- dodanie bardziej zaawansowanych filtrów kolumnowych,
- eksport raportów do osobnych plików,
- lepsze porównywanie wyników wielu modeli,
- rozwój helpdesku / asystenta użytkownika,
- dalsza optymalizacja kodu i wydajności GUI,
- rozbudowa dokumentacji i przykładów użycia.
