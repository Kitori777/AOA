# AOA – Aplikacja Optymalnego Algorytmowania

## Opis projektu

AOA to rozwijana aplikacja desktopowa i terminalowa napisana w Pythonie. Jej celem jest wspomaganie analizy danych, uczenia modeli, porównywania metod harmonogramowania oraz prezentowania wyników w formie czytelnych tabel, raportów i wykresów.

Od wersji `0.6.0` projekt rozwija się nie tylko jako narzędzie produkcyjno-optymalizacyjne, ale również jako aplikacja analityczno-edukacyjna. Użytkownik może wczytać własne dane tabelaryczne, obejrzeć je w widoku podobnym do prostego CSV viewera, przygotować raport, uruchomić wizualizację oraz sprawdzić krótkie wyjaśnienia modeli i metryk.

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


## Najważniejsze zmiany w wersji 0.6.0

* Pełny przepływ ML `train -> save -> load -> solve` działa dla wszystkich 12 wariantów `classic` opisanych w README.
* Poprawiono wczytywanie zapisanych modeli scikit-learn opartych o `GradientBoosting*` i `HistGradientBoosting*`.
* Naprawiono modele `Schedule*` w `solve`: symulacja harmonogramu dostaje teraz dane, a model przewiduje strategię na przygotowanych cechach.
* CLI korzysta z tego samego rejestru modeli co GUI, więc terminal i interfejs graficzny pokazują spójny zestaw modeli.
* Buildery modeli ML zostały przebudowane na pipeline'y scikit-learn z imputacją braków danych i lepszymi domyślnymi parametrami.
* Modele mogą korzystać z pamięci treningowej: zapisane paczki przechowują dane treningowe, które kolejne treningi mogą dołączyć do nowych rekordów.
* `Visual Lab` ma osobne renderery D3 dla wszystkich wyborów wykresów, w tym macierzy korelacji, podobieństwa, Pair Explorer, heatmapy, bubble chart, outlier map, 3D i drzewa decyzyjnego.
* `Results Studio` ma prostszy CSV loader: tryb, kolumna, preset liczby wierszy i własna liczba rekordów.
* `TheoryPage` ma bardziej kompaktowy pasek kroków i większy obszar animacji, żeby łatwiej zatrzymać i przeanalizować aktualny etap.


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

Modele heurystyczne STO zostały rozszerzone do zestawu 13 metod: `MT`, `MO`, `MZO`, `MOPT`, `GENETIC`, `SLACK`, `CR`, `EDD_SPT`, `SPT_EDD`, `LPT_EDD`, `NEH`, `LOCAL_SEARCH`, `RANDOM_RESTART`. Każda metoda ma opis, na co patrzy: termin, czas obróbki, zapas, dokładne minimum STO, krytyczność, wariant wstawiania lub lokalne poprawki kolejności.

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
- 12 klasycznych wariantów ML:
  - `Quality`, `Quality_ET`, `Quality_GB`, `Quality_HGB`,
  - `Delay`, `Delay_RF`, `Delay_ET`, `Delay_HGB`,
  - `Schedule`, `Schedule_ET`, `Schedule_GB`, `Schedule_LOG`,
- pełny przepływ `train -> save -> load -> solve` dla modeli ML,
- pipeline'y ML z imputacją braków danych i spójnym przygotowaniem cech,
- pamięć treningowa modeli ML oparta o zapisane paczki modeli,
- eksperymentalny backend `TabPFN`,
- metryki jakości uczenia modeli ML,
- heurystyczne modele STO:
  - `MT`,
  - `MO`,
  - `MZO`,
  - `MOPT`,
  - `GENETIC`,
  - `SLACK`,
  - `CR`,
  - `EDD_SPT`,
  - `SPT_EDD`,
  - `LPT_EDD`,
  - `NEH`,
  - `LOCAL_SEARCH`,
  - `RANDOM_RESTART`,
- zapis i późniejsze używanie modeli STO,
- interaktywna instrukcja na stronie `Readme`,
- teoria użytkowa na stronie `Theory`,
- rozbudowane wizualizacje, raporty i pełniejsze wykresy D3 na stronie `Visual`,
- przebudowany viewer danych na stronie `Results`,
- podstawowe operacje analityczne i ewaluacyjne,
- obsługa pełnych przepływów pracy w GUI i CLI,
- logowanie błędów do katalogu `logs`,
- testy jednostkowe i testy przepływów,
- plik `CHANGELOG.md`,
- przygotowanie projektu do wersjonowania oraz release’ów.

## Plan na kolejne aktualizacje

- kreator dashboardów w `Visual Lab`, pozwalający zapisywać własne układy paneli i wracać do nich później,
- bardziej zaawansowane filtry kolumnowe w `Results Studio`, np. warunki tekstowe, zakresy dat, profile kategorii i zapis presetów filtrów,
- eksport raportów do HTML/PDF wraz z tabelą, wykresami i opisem jakości danych,
- porównywarka wielu zapisanych modeli ML: metryki, różnice predykcji, stabilność i historia treningu,
- panel historii treningów pokazujący, z jakich wcześniejszych paczek korzystała pamięć modelu,
- rozszerzenie pamięci treningowej o kontrolowane strategie: limit wieku danych, ręczne wykluczanie paczek i walidację jakości historii,
- asystent użytkownika / helpdesk w aplikacji, który po opisaniu celu podpowie właściwy moduł i przygotuje konfigurację analizy,
- opcjonalna integracja z agentami albo projektem AIRI jako przyszły tryb wspomagania użytkownika,
- dalsza optymalizacja kodu i wydajności GUI,
- rozbudowa dokumentacji o scenariusze krok po kroku oraz przykładowe pliki wejściowe dla ML, STO, Visual i Results.
