# AOA – Aplikacja Optymalnego Algorytmowania

## Opis projektu

AOA to aplikacja desktopowa napisana w Pythonie, której celem jest wspomaganie analizy danych produkcyjnych, trenowania modeli uczenia maszynowego oraz porównywania wyników różnych metod analitycznych i wizualnych.

Projekt został przygotowany w architekturze modułowej, z wyraźnym podziałem na:

- warstwę `core`, odpowiedzialną za logikę aplikacji, przetwarzanie danych, modele, ewaluację i przygotowanie wyników,
- warstwę `gui`, odpowiedzialną wyłącznie za interfejs użytkownika,
- katalog `tests`, zawierający testy jednostkowe dla warstwy `core`,
- katalog `docs`, zawierający dokumentację użytkową i teoretyczną projektu.

Aplikacja umożliwia między innymi:

- generowanie przykładowych danych produkcyjnych,
- wczytywanie danych z plików CSV,
- trenowanie modeli ML dla jakości, opóźnień i strategii harmonogramowania,
- analizę wyników regresji i klasyfikacji,
- tworzenie wykresów i wizualizacji danych,
- zapis wyników do plików.

Projekt ma charakter rozwojowy i stanowi bazę pod dalszą rozbudowę o nowe algorytmy, dokładniejsze analizy oraz bardziej zaawansowane moduły wspomagania decyzji.

## Aktualna struktura repozytorium

```text
TOOLS/
├── docs/
│   ├── guide.md
│   └── theory.md
├── data/
├── models/
├── src/
│   └── AOA/
│       ├── __init__.py
│       ├── app.py
│       ├── config.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── constants.py
│       │   ├── data_generation.py
│       │   ├── data_io.py
│       │   ├── dataset_ops.py
│       │   ├── evaluation.py
│       │   ├── features.py
│       │   ├── models.py
│       │   ├── scheduling.py
│       │   ├── services.py
│       │   ├── visualization_service.py
│       │   └── diagrams/
│       ├── gui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   └── pages/
│       │       ├── __init__.py
│       │       ├── main_page.py
│       │       ├── readme_page.py
│       │       ├── results_page.py
│       │       ├── theory_page.py
│       │       └── visual_page.py
│       └── utils/
│           ├── __init__.py
│           ├── logging_utils.py
│           └── threading_utils.py
├── tests/
│   └── core/
│       ├── test_data_generation.py
│       ├── test_data_io.py
│       ├── test_features.py
│       ├── test_models.py
│       └── test_scheduling.py
├── CHANGELOG.md
├── README.md
├── pyproject.toml
└── uv.lock
```



## Segment 3 — uruchomienie projektu przez `uv`


## Jak uruchomić projekt

### Wersja z `uv`

#### 1. Przejdź do katalogu projektu


```bash
cd C:\Users\stasi\PycharmProjects\TOOLS
```

#### 2. Sprawdź wersje uv
```bash
py -m uv --version
```

#### 3. Zainstaluj zależności i zsynchronizuj środowisko
```bash
py -m uv sync
```

#### 4. Uruchom aplikację

W PowerShell:
```bash
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="C:\Users\stasi\PycharmProjects\TOOLS\src"
python -m AOA.app
```
W Git Bash:
```bash
.\.venv\Scripts\Activate.ps1
export PYTHONPATH="$PWD/src"
python -m AOA.app
```
#### 5. Uruchom testy

W PowerShell:
```bash
$env:PYTHONPATH="C:\Users\stasi\PycharmProjects\TOOLS\src"
pytest
```

W Git Bash:
```bash
export PYTHONPATH="$PWD/src"
pytest
```

---

## Segment 4 — uruchomienie projektu bez `uv`


### Wersja bez `uv`

#### 1. Przejdź do katalogu projektu

```bash
cd C:\Users\stasi\PycharmProjects\TOOLS
```

#### 2. Utwórz środowisko wirtualne
```bash
python -m venv .venv
```
#### 3. Aktywuj środowisko

PowerShell:
```bash
.\.venv\Scripts\Activate.ps1
```
Git Bash:
```bash
source .venv/Scripts/activate
```
#### 4. Zainstaluj zależności
```bash
pip install pandas numpy matplotlib seaborn customtkinter tabulate scipy scikit-learn pytest
```
#### 5. Ustaw PYTHONPATH

PowerShell:
```bash
$env:PYTHONPATH="C:\Users\stasi\PycharmProjects\TOOLS\src"
```
Git Bash:
```bash
export PYTHONPATH="$PWD/src"
```
#### 6. Uruchom aplikację
```bash
python -m AOA.app
```
#### 7. Uruchom testy
```bash
pytest
```


---

## Segment 5 — aktualny stan projektu


## Aktualny stan projektu

Na obecnym etapie projekt posiada już stabilny fundament techniczny i spełnia założenia pierwszego etapu rozwoju.

### Zrealizowane elementy

- wydzielenie warstwy `core`,
- oddzielenie logiki aplikacyjnej od GUI,
- modularna struktura projektu,
- obsługa generowania danych,
- obsługa wczytywania plików CSV,
- przygotowanie cech do modeli ML,
- trenowanie modeli:
  - Random Forest dla jakości,
  - Gradient Boosting dla opóźnień,
  - Random Forest dla strategii harmonogramowania,
- podstawowe operacje analityczne i ewaluacyjne,
- wizualizacje danych i modeli,
- dokumentacja użytkownika i dokumentacja teoretyczna,
- testy jednostkowe dla warstwy `core`,
- plik `CHANGELOG.md`,
- przygotowanie projektu do wersjonowania i release’ów.

### Aktualny charakter projektu

Projekt jest obecnie działającą aplikacją analityczno-edukacyjną, która pozwala:

- trenować modele na danych przykładowych lub własnych,
- analizować dane w interfejsie graficznym,
- generować podstawowe wizualizacje,
- przeglądać wyniki regresji i klasyfikacji,
- zapisywać wyniki do plików.

## Plan na kolejny update

- rozbudowa liczby dostępnych modeli,
- dodanie bardziej zaawansowanych wykresów,
- rozszerzenie testów jednostkowych,
- rozbudowa dokumentacji technicznej,

## Plany na updaty w przyszłym miesiącu
- dalsze oczyszczenie architektury i refaktoryzacja modułów,
- integracja z dodatkowymi źródłami danych lub modułami wspomagania użytkownika dla części teoretycznej,
- przebudowa struktury main oraz readme z aplikacji,
- kompletny overhaul struktury wizualnej, wprowadzenie początkowych dashboard oraz lepsza dla użytkownika strukura,
- więcej modeli oraz ciekawych wizualizacji,
- helpdesk z agentem/AIKA
