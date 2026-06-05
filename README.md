# AOA - Aplikacja Optymalnego Algorytmowania

## Opis projektu

AOA to rozwijana aplikacja desktopowa i terminalowa napisana w Pythonie.
Jej celem jest wspomaganie analizy danych, trenowania modeli, porownywania
metod harmonogramowania, tworzenia raportow, wizualizacji, diagramow oraz
wyjasniania wynikow uzytkownikowi prostym jezykiem.

Projekt rozwija sie jako narzedzie produkcyjno-optymalizacyjne,
analityczne i edukacyjne. Uzytkownik moze wczytac wlasne dane tabelaryczne,
uruchomic modele ML albo heurystyki STO, obejrzec wyniki w tabelach,
zbudowac wykresy, wygenerowac HTML, przygotowac raport, narysowac diagram
i zapytac ALICE, co oznacza aktualny wynik.

Glowna zasada architektury pozostaje prosta:

- warstwa `core` odpowiada za logike aplikacji, dane, modele, STO, raporty,
  wizualizacje, ALICE i przygotowanie eksportow,
- warstwa `gui` odpowiada za interfejs graficzny i prowadzenie uzytkownika,
- warstwa `cli` pozwala uzywac aplikacji z terminala,
- katalog `docs` zawiera dokumentacje, teorie oraz baze wiedzy ALICE,
- katalog `tests` zawiera testy jednostkowe i przeplywowe,
- katalog `data` przechowuje dane lokalne, raporty HTML i eksporty,
- katalog `models` przechowuje zapisane modele,
- katalog `logs` przechowuje logi aplikacji i diagnostyke.

## Co mozna zrobic w aplikacji

- Wczytywac dane z plikow `.csv`, `.txt` i `.tsv`.
- Generowac przykladowe dane produkcyjne.
- Pracowac na dowolnych danych tabelarycznych, nie tylko produkcyjnych.
- Trenowac modele ML dla jakosci, opoznien i strategii harmonogramowania.
- Porownywac wiele modeli ML w jednym przeplywie pracy.
- Uruchamiac heurystyki STO i wybierac najlepsza kolejnosc zlecen.
- Liczyc i interpretowac metryki regresji oraz klasyfikacji.
- Rysowac wykresy w `Visual Lab` z bibliotek Matplotlib, Seaborn, Plotly,
  Altair i NetworkX.
- Otwierac interaktywne raporty HTML/D3, dashboardy i drzewa rozwiazan.
- Chowac i ponownie pokazywac galezie drzewa w HTML.
- Analizowac tabele w `Results Studio`: filtr, sortowanie, SQL, profil
  kolumn, braki danych i eksport CSV.
- Tworzyc raporty i workflowy w `Analytics Studio`: KPI, data quality,
  dashboard, report, notebook, segmenty, korelacje, outliery i akcje.
- Budowac wlasne raporty z sekcji, wynikow z innych plikow, wizualizacji
  i diagramow.
- Tworzyc diagramy w `Diagrams`: flowchart, UML, ERD, BPMN, sieci, mind map,
  org chart, data pipeline i eksport `.drawio`, SVG, Mermaid oraz HTML.
- Korzystac z `Theory`, ktora pokazuje animacje i prawdziwe dzialanie
  algorytmow krok po kroku.
- Korzystac z ALICE jako lokalnego mozgu aplikacji: przewodnika, tlumacza,
  raportujacej asystentki i pomocy glosowej.

## Najwazniejsze nowosci aktualnej wersji

- ALICE ma lokalna baze wiedzy `docs/alice_brain.json`, dzieki ktorej zna
  moduly aplikacji, procesy, algorytmy, wykresy, raporty, HTML, STO i checklisty
  przed publikacja na GitHubie.
- `Visual Lab` ma wybor biblioteki wykresow: Matplotlib, Seaborn, Plotly,
  Altair i NetworkX.
- Typy wykresow sa walidowane wzgledem biblioteki, zeby uzytkownik widzial
  tylko sensowne opcje.
- HTML dla `SolutionTree` wymusza renderer drzewa, nawet gdy wybrana jest
  biblioteka Plotly albo Altair.
- `SolutionTree` w HTML pozwala klikac wezly, chowac wybrane galezie i pokazac
  cale drzewo ponownie.
- Zielony kolor w drzewie oznacza najlepsza sciezke, a zolty wariant sprawdzony,
  pokonany albo taki, do ktorego algorytm wrocil po porownaniu.
- `Analytics Studio` zostalo rozwiniete poza raporty: zawiera data quality,
  dashboardy, KPI, diagnostyke metryk, segment explorer, correlation explorer,
  outlier analysis, pivot summary, data dictionary, time trend i plan notebooka.
- Kreator raportow w Analytics dziala bardziej jak prosty edytor dokumentu:
  mozna dodawac sekcje, KPI, wykresy, rekomendacje i ogladac podglad.
- `Diagrams` ma lepszy edytor: przeciaganie elementow, menu pod prawym
  kliknieciem, kolory, duplikowanie, usuwanie, auto layout i czytelniejsze
  polaczenia.
- `Theory` rozdziela ML od heurystyk STO. ML pokazuje mechanike modeli, a STO
  pokazuje kolejke, czasy zakonczenia, opoznienia i ranking metod.
- ALICE lepiej odpowiada na pytania typu: "co robi Main", "jak dziala STO",
  "jak rysuje SolutionTree", "jakie biblioteki wykresow sa dostepne" oraz
  "co sprawdzic przed wersja na GitHuba".

## Najwazniejsze moduly

### Main

`Main` jest centrum obliczen. Tutaj uzytkownik przygotowuje lub wczytuje dane,
wybiera modele ML/STO, uruchamia trening, analizuje przebieg i zapisuje wyniki.

Typowy przeplyw:

1. Wczytaj dane albo wygeneruj dane przykladowe.
2. Wybierz modele ML albo metody STO.
3. Uruchom trening lub analize.
4. Sprawdz metryki i komunikaty.
5. Przejdz do `Visual`, `Results`, `Analytics` albo `Theory`.

### Visual Lab

`Visual Lab` jest laboratorium wykresow i interaktywnego HTML.
Uzytkownik wybiera kolumny X/Y/Z, typ wykresu i biblioteke.

Dostepne biblioteki:

- `Matplotlib` - bazowy podglad desktopowy,
- `Seaborn` - wykresy statystyczne, regresja, KDE, ECDF, violin i pair plot,
- `Plotly` - interaktywny HTML dla scatter, line, histogram, bar, pie, 3D,
  dashboardow i podobnych widokow,
- `Altair` - deklaratywne wykresy Vega-Lite w HTML,
- `NetworkX` - grafy zaleznosci i drzewa.

Wspierane sa m.in.:

- `Production Dashboard`,
- `Dashboard`,
- `Diagnostics`,
- `Model Diagnostics`,
- `Pair Explorer`,
- `Pair Plot`,
- `Joint Plot`,
- `3D Scatter`,
- `3D Surface`,
- `Bubble Chart`,
- `Heatmap Density`,
- `KDE Plot`,
- `ECDF Plot`,
- `Violin Plot`,
- `Regression Plot`,
- `Outlier Map`,
- `DBSCAN Anomaly`,
- `PCA State Segments`,
- `LDA vs t-SNE`,
- `KMeans vs GMM`,
- `Step View`,
- `Priority Timeline`,
- `Area Chart`,
- `Treemap`,
- `Sunburst`,
- `Funnel`,
- `Waterfall`,
- `Radar Chart`,
- `Missingness Map`,
- `Column Ranking`,
- `Stacked Bar`,
- `Binned Scatter`,
- `Faceted Scatter`,
- `Interactive Brush`,
- `Bar Chart`,
- `Pie Chart`,
- `Scatter`,
- `Line`,
- `Histogram`,
- `Boxplot`,
- `Count Plot`,
- `Strip Plot`,
- `Swarm Plot`,
- `Point Plot`,
- `Bar Estimate`,
- `Gantt`,
- `SolutionTree`,
- `ML Decision Tree`,
- `Network Graph`,
- `Circular Network`,
- `Spring Network`,
- `Shell Network`,
- `Kamada-Kawai Network`,
- `Tree Network`,
- `CorrelationMatrix`,
- `SimilarityMatrix`.

`SolutionTree` pokazuje drzewo wariantow rozwiazania. W HTML mozna kliknac
wezel, schowac galaz, pokazac cale drzewo i porownac kolory:

- zielony - najlepsza sciezka,
- zolty - wariant sprawdzony, pokonany albo odzyskany,
- bialy - pozostale warianty.

### Results Studio

`Results Studio` jest widokiem pracy z tabela. Pozwala:

- wczytywac dane,
- filtrowac rekordy,
- sortowac kolumny,
- limitowac liczbe wierszy,
- sprawdzac profil kolumn,
- analizowac braki i duplikaty,
- uruchamiac zapytania SQL,
- eksportowac wyniki do CSV.

To najlepsze miejsce do sprawdzania rekordow, ktore odstaja na wykresach.

### Analytics Studio

`Analytics Studio` jest panelem raportow, KPI, diagnostyki i workflowow
analitycznych. Nie jest tylko miejscem wyboru opcji - uruchamia analize,
generuje raporty, HTML, notebooki i liste akcji.

Dostepne workflowy i obszary:

- `Index`,
- `Analyze Data Quality`,
- `Build Dashboard`,
- `Build Report`,
- `Design KPIs`,
- `Metric Diagnostics`,
- `Market Sizing`,
- `Visualize Data`,
- `Executive Summary`,
- `Opportunity Sizing`,
- `Chart QA`,
- `Risk & Caveats`,
- `Action Plan`,
- `Jupyter Notebook Plan`,
- `Statistical Summary`,
- `Segment Explorer`,
- `Correlation Explorer`,
- `Outlier Analysis`,
- `Pivot Summary`,
- `Data Dictionary`,
- `Time Trend`.

Raporty mozna skladac z sekcji, KPI, wykresow, rekomendacji, wynikow z innych
plikow oraz podgladu podobnego do prostego edytora dokumentu.

### Diagrams

`Diagrams` jest interaktywnym edytorem diagramow. Uzytkownik moze:

- wybrac szablon,
- dodawac ksztalty,
- przeciagac elementy myszka,
- laczyc elementy,
- edytowac tekst dwuklikiem,
- otworzyc menu prawym kliknieciem,
- zmieniac kolory,
- duplikowac i usuwac elementy,
- uzyc auto layout,
- eksportowac `.drawio`, SVG, Mermaid i HTML.

Szablony obejmuja m.in.:

- `Blank`,
- `Flowchart`,
- `UML Class`,
- `ERD Database`,
- `BPMN Process`,
- `Network Diagram`,
- `Mind Map`,
- `Org Chart`,
- `Swimlane`,
- `Sequence Diagram`,
- `Data Pipeline`,
- `System Architecture`,
- `Decision Tree`,
- `Kanban Board`.

### Theory

`Theory` jest edukacyjnym widokiem animacji i teorii algorytmow.
Najwazniejsza zasada: ML i STO sa rozdzielone.

Modele ML ucza zaleznosci z danych:

- `Random Forest` - wiele drzew, bagging, agregacja i OOB,
- `ExtraTrees` - mocniej losowe progi podzialu,
- `Gradient Boosting` - kolejne drzewa poprawiaja blad,
- `HistGradient Boosting` - boosting na koszykach wartosci,
- `Logistic Regression` - skalowanie, wagi, softmax i klasy.

Heurystyki STO nie trenuja wag ani drzew. One ukladaja kolejke zlecen i licza:

```text
Cj = czas zakonczenia zlecenia j
dj = termin zlecenia j
Tj = max(0, Cj - dj)
STO = suma Tj
```

Im mniejsze `STO`, tym lepsza kolejnosc.

### ALICE

ALICE jest asystentka aplikacji. Jej zadaniem jest prowadzic uzytkownika po
aplikacji, tlumaczyc wyniki i proponowac kolejne kroki.

ALICE potrafi:

- odpowiedziec, do czego sluzy aplikacja,
- wyjasnic, co robi `Main`, `Visual`, `Results`, `Analytics`, `Diagrams`
  i `Theory`,
- opisac dzialanie modeli ML,
- opisac heurystyki STO,
- tlumaczyc wykresy i raporty HTML,
- wyjasnic kolory w `SolutionTree`,
- podpowiadac workflow krok po kroku,
- czytac odpowiedzi glosowo,
- korzystac z lokalnej bazy wiedzy `docs/alice_brain.json`,
- opcjonalnie korzystac z endpointu LLM przez zmienne srodowiskowe.

## Modele ML

Dostepnych jest 12 klasycznych wariantow ML.

### Modele jakosci

- `Quality` - Random Forest Regressor,
- `Quality_ET` - ExtraTrees Regressor,
- `Quality_GB` - Gradient Boosting Regressor,
- `Quality_HGB` - HistGradient Boosting Regressor.

### Modele opoznien

- `Delay` - Gradient Boosting Regressor,
- `Delay_RF` - Random Forest Regressor,
- `Delay_ET` - ExtraTrees Regressor,
- `Delay_HGB` - HistGradient Boosting Regressor.

### Modele strategii harmonogramowania

- `Schedule` - Random Forest Classifier,
- `Schedule_ET` - ExtraTrees Classifier,
- `Schedule_GB` - Gradient Boosting Classifier,
- `Schedule_LOG` - Logistic Regression baseline.

Metryki regresji:

- `RMSE`,
- `MAE`,
- `R2`.

Metryki klasyfikacji:

- `Accuracy`,
- `F1`,
- prawdopodobienstwa klas.

## Heurystyki STO

Dostepne metody:

- `MT` / `EDD` - najpierw najwczesniejszy termin,
- `MO` / `SPT` - najpierw najkrotszy czas obrobki,
- `MZO` / `LPT` - najpierw najdluzszy czas obrobki,
- `MOPT` - dokladne szukanie najlepszego STO,
- `GENETIC` - selekcja, krzyzowanie i mutacja kolejek,
- `SLACK` - najmniejszy zapas czasu,
- `CR` - critical ratio,
- `EDD_SPT` - termin, a remisy rozstrzyga krotszy czas,
- `SPT_EDD` - krotki czas, a remisy rozstrzyga termin,
- `LPT_EDD` - dlugi czas, potem termin,
- `NEH` - wstawianie kolejnych zlecen w najlepsze miejsce,
- `LOCAL_SEARCH` - lokalne zamiany sasiadow,
- `RANDOM_RESTART` - wiele losowych startow.

## Aktualna struktura repozytorium

```text
TOOLS/
|-- docs/
|   |-- alice_brain.json
|   |-- architecture.md
|   |-- guide.md
|   |-- theory.md
|   |-- workflows.md
|   `-- alice_sources/
|-- data/
|   `-- sample/
|-- logs/
|-- models/
|-- src/
|   `-- AOA/
|       |-- app.py
|       |-- config.py
|       |-- cli/
|       |-- core/
|       |   |-- assistant_service.py
|       |   |-- data_analytics_service.py
|       |   |-- drawio_service.py
|       |   |-- visualization_service.py
|       |   |-- ml_models/
|       |   |-- mh_models/
|       |   |-- mlstack/
|       |   |-- diagrams/
|       |   `-- services/
|       |-- gui/
|       |   |-- assistant_panel.py
|       |   |-- main_window.py
|       |   `-- pages/
|       |       |-- analytics_page.py
|       |       |-- drawio_page.py
|       |       |-- readme_page.py
|       |       |-- results_page.py
|       |       |-- visual_page.py
|       |       `-- theory_page/
|       `-- utils/
|-- tests/
|   |-- cli/
|   |-- core/
|   `-- gui/
|-- README.md
|-- CHANGELOG.md
|-- pyproject.toml
`-- uv.lock
```

Pliki generowane lokalnie przez aplikacje, np. raporty HTML, wyniki treningu,
dane tymczasowe i eksporty, powinny pozostawac lokalne i nie trafiac przypadkiem
do commitow.

## Jak uruchomic projekt

### Wersja z `uv`

#### 1. Sklonuj repozytorium i przejdz do katalogu projektu

```bash
git clone git@github.com:UZ-FENS/passthebranch-Kitori2137.git
cd passthebranch-Kitori2137
```

#### 2. Zainstaluj zaleznosci

```bash
uv sync --dev
```

#### 3. Uruchom aplikacje desktopowa

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

#### 1. Utworz i aktywuj srodowisko wirtualne

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 2. Zainstaluj projekt

```bash
pip install -e .[dev]
```

#### 3. Uruchom aplikacje

```bash
python -m AOA.app
```

#### 4. Uruchom testy

```bash
pytest
```

## CLI

Przykladowe komendy:

```bash
uv run aoa-cli --help
uv run aoa-cli generate
uv run aoa-cli train --models Quality,Delay
uv run aoa-cli sto --models MT,MO,GENETIC
uv run aoa-cli workflow
```

## Baza wiedzy ALICE

ALICE ma lokalny plik wiedzy:

```text
docs/alice_brain.json
```

Kazdy wpis zawiera:

- `id` - identyfikator tematu,
- `aliases` - hasla i pytania, po ktorych ALICE rozpoznaje temat,
- `answer` - odpowiedz bazowa,
- `steps` - kroki dla uzytkownika.

Dzieki temu przed publikacja na GitHubie mozna latwo dopisywac nowe pytania
i odpowiedzi bez przepisywania calej logiki asystenta.

## Aktualny stan projektu

Projekt ma dzialajacy fundament techniczny:

- aplikacje desktopowa,
- interfejs CLI,
- modele ML,
- heurystyki STO,
- wizualizacje,
- eksport HTML,
- Analytics Studio,
- Diagrams,
- Theory,
- ALICE,
- dokumentacje,
- testy jednostkowe i przeplywowe.

Ostatnio sprawdzony pelny zestaw testow przechodzil w liczbie ponad 360 testow.

## Plan na kolejne aktualizacje

- Dalsze rozwijanie bazy wiedzy ALICE o pytania uzytkownikow z realnego uzycia.
- Lepszy tryb release-check przed publikacja na GitHubie.
- Dalszy QA HTML dla kazdego typu wykresu i kazdej biblioteki.
- Porownywarka wielu zapisanych modeli ML.
- Historia treningow i historia workflowow.
- Wieksza liczba przykladowych plikow danych.
- Bardziej rozbudowane tutoriale krok po kroku w `docs/`.
