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
- Wybrac backend `classic` albo `tabpfn` oraz porownac go z nowoczesnymi
  segmentami: TabPFN, XGBoost, MLP i Stacking.
- Dodawac wlasne modele ML z bibliotek `sklearn` oraz, jesli zaleznosc jest
  zainstalowana, `xgboost`.
- Dodawac wlasne heurystyki STO z prostego wzoru score, np. `d - 1.5 * p`.
- Porownywac wiele modeli ML w jednym przeplywie pracy.
- Uruchamiac heurystyki STO i wybierac najlepsza kolejnosc zlecen.
- Liczyc i interpretowac metryki regresji oraz klasyfikacji.
- Rysowac wykresy w `Visual Lab` z bibliotek Matplotlib, Seaborn, Plotly,
  Altair i NetworkX.
- Otwierac interaktywne raporty HTML/D3, dashboardy i drzewa rozwiazan.
- Chowac i ponownie pokazywac galezie drzewa w HTML.
- Analizowac tabele w `Results Studio`: filtr, sortowanie, SQL, profil
  kolumn, braki danych i eksport CSV.
- Tworzyc raporty i workflowy w `Report Studio`: KPI, data quality,
  dashboard, report, notebook, segmenty, korelacje, outliery i akcje.
- Budowac wlasne raporty z sekcji, wynikow z innych plikow, wizualizacji
  i diagramow.
- Tworzyc diagramy w `Diagrams`: flowchart, UML, ERD, BPMN, sieci, mind map,
  org chart, data pipeline, supply chain, VSM, layout produkcji, diagram z opisu
  i eksport `.drawio`, SVG, Mermaid oraz HTML.
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
- `Report Studio` zostalo rozwiniete poza raporty: zawiera data quality,
  dashboardy, KPI, diagnostyke metryk, segment explorer, correlation explorer,
  outlier analysis, pivot summary, data dictionary, time trend i plan notebooka.
- Kreator raportow w Report dziala bardziej jak prosty edytor dokumentu:
  mozna dodawac sekcje, KPI, wykresy, rekomendacje i ogladac podglad.
- `Diagrams` ma lepszy edytor: przeciaganie elementow, menu pod prawym
  kliknieciem, kolory, duplikowanie, usuwanie, auto layout i czytelniejsze
  polaczenia.
- `Theory` rozdziela ML od heurystyk STO. ML pokazuje mechanike modeli, a STO
  pokazuje kolejke, czasy zakonczenia, opoznienia i ranking metod.
- `Theory` ma trzy sciezki: klasyczne ML, heurystyki STO oraz Nowoczesne ML
  z TabPFN, XGBoost, MLP i Stacking. Kazda rodzina ma osobny mechanizm animacji,
  wzor i interpretacje.
- `Main` ma kreator wlasnych modeli ML i kreator wlasnych heurystyk STO.
- `Diagrams` ma generator z opisu: uzytkownik wpisuje proces slowami albo
  strzalkami, a aplikacja dobiera szablon, ksztalty, kolory i etykiety polaczen.
- `Report` ma pelny Report Builder w osobnym oknie: zrodlo raportu, podglad
  strony/PDF, guide komend, biblioteka plikow oraz eksport HTML/MD/TeX/PDF.
- `Readme` jest tez panelem szybkiego startu: ma przyciski do release-check,
  menedzera plikow AOA, sampla w Main, pelnego Report Buildera i ALICE.
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
5. Przejdz do `Visual`, `Results`, `Report` albo `Theory`.

Najwazniejsze parametry generowania danych:

| Parametr | Typ | Przyklad | Zasada |
| --- | --- | --- | --- |
| `Liczba rekordow` | liczba calkowita | `5000` | musi byc dodatnia; im wiecej rekordow, tym stabilniejszy trening |
| `Liczba maszyn` | liczba calkowita | `1` | musi byc dodatnia |
| `Test size` | liczba ulamkowa | `0.2` | musi byc wieksze od `0` i mniejsze od `1`; `0.2` oznacza 20% danych testowych |
| `Seed` | liczba calkowita | `42` | ustala powtarzalnosc losowania |
| `Czas prod. min/max [h]` | liczba calkowita albo ulamkowa | `1`, `48` | minimum musi byc mniejsze od maksimum |
| `Bufor terminu min/max [h]` | liczba calkowita albo ulamkowa | `1`, `72` | bufor dodawany do terminu; minimum musi byc mniejsze od maksimum |

Warto zapamietac:

- `Quality` i `Delay` to regresja, czyli model przewiduje liczbe.
- `Schedule` to klasyfikacja, czyli model wybiera klase lub strategie.
- Dla modeli liniowych, SVM, KNN i MLP zwykle warto wybrac skalowanie `standard`
  albo `robust`.
- Dla drzew, RandomForest, ExtraTrees, GradientBoosting, HistGradient i XGBoost
  skalowanie zwykle nie jest konieczne.
- `TabPFN` ma walidacje danych: sprawdza rozmiar X/y, braki, `NaN`, `inf`,
  minimalna liczbe rekordow oraz minimum dwie klasy przy klasyfikacji.

### Wlasne modele ML

W `Main` mozna kliknac `+ Wlasny model ML` i zapisac konfiguracje do
`models/custom_ml_models.json`. Po zapisie model pojawia sie na liscie i jest
trenowany razem z pozostalymi modelami.

Najprostszy sposob:

1. Wybierz gotowy preset, np. RandomForest, ExtraTrees, SVR, KNN, Ridge,
   HistGradient, LogisticRegression albo XGBoost.
2. Wybierz zadanie: jakosc/regresja, opoznienie/regresja albo harmonogram/klasyfikacja.
3. Zostaw albo popraw parametry JSON.
4. Zapisz model.
5. Zaznacz go na liscie i uruchom trening.

Parametry JSON sa przekazywane bezposrednio do klasy modelu. Przyklady:

```json
{
  "n_estimators": 300,
  "min_samples_leaf": 2,
  "random_state": 42,
  "n_jobs": -1
}
```

```json
{
  "C": 12.0,
  "epsilon": 0.08,
  "gamma": "scale"
}
```

Typowe reguly:

- `n_estimators`, `max_depth`, `min_samples_leaf`, `max_iter`, `n_neighbors`,
  `random_state` i `n_jobs` sa zwykle liczbami calkowitymi.
- `learning_rate`, `alpha`, `C`, `epsilon`, `subsample`, `max_features`,
  `l2_regularization` sa zwykle liczbami ulamkowymi.
- `gamma`, `kernel`, `weights`, `class_weight`, `strategy` sa zwykle tekstem.
- `xgboost.XGBRegressor` i `xgboost.XGBClassifier` sa dostepne, jesli pakiet
  `xgboost` jest zainstalowany w srodowisku.

### Wlasne heurystyki STO

W `Main` mozna kliknac `+ Wlasna heurystyka STO`. Heurystyka nie trenuje modelu,
tylko liczy score dla kazdego zlecenia i sortuje rosnaco.

Dostepne zmienne:

- `p` - czas wykonania zlecenia,
- `d` - termin zlecenia,
- `slack` - zapas czasu, czyli `d - p`,
- `cr` - critical ratio,
- `urgency` - wzgledna pilnosc,
- `i` - numer zlecenia,
- `n` - liczba zlecen.

Przyklady wzorow:

```text
d
p
d - p
d / p
d - 1.5 * p
0.7 * d + 0.3 * p
```

Im mniejszy score, tym wczesniej zlecenie trafia do kolejki.

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

### Report Studio

`Report Studio` jest panelem raportow, KPI, diagnostyki i workflowow
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

Pelny `Report Builder` otwiera sie w osobnym oknie i dziala jak uproszczony
Overleaf/LaTeX:

- po lewej piszesz zrodlo raportu,
- w srodku widzisz podglad strony/ukladu PDF,
- po prawej masz guide komend i biblioteke plikow z `Visual`, `Diagrams`,
  `Report` i `Reports`,
- przyciski dodaja gotowe sekcje: cel, KPI, wykres, ML analiza, STO analiza,
  pipeline, ryzyka, rekomendacje, pliki, obraz, HTML i kod,
- eksport obejmuje HTML, Markdown, TeX i PDF.

### Diagrams

`Diagrams` jest interaktywnym edytorem diagramow. Uzytkownik moze:

- wybrac szablon,
- wygenerowac diagram z opisu slownego przez `Z opisu`,
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
- `Production Line`,
- `Value Stream Map`,
- `Supply Chain`,
- `Plant Layout`,
- `Andon Response`,
- `Energy Flow`,
- `Inventory Replenishment`.

Generator `Z opisu` rozpoznaje m.in. procesy produkcyjne, dane/ML, systemy,
logistyke i supply chain. Przyklad:

```text
Dostawca -> magazyn -> kontrola jakosci -> produkcja -> model ML -> raport
```

Aplikacja dobiera typ diagramu, ksztalty, kolory i etykiety polaczen. Potem
mozna uzyc `Auto layout`, poprawic teksty, dodac kontener albo wyeksportowac
diagram do `.drawio`, SVG, Mermaid lub HTML.

### Theory

`Theory` jest edukacyjnym widokiem animacji i teorii algorytmow.
Najwazniejsza zasada: ML i STO sa rozdzielone.

Modele ML ucza zaleznosci z danych:

- `Random Forest` - wiele drzew, bagging, agregacja i OOB,
- `ExtraTrees` - mocniej losowe progi podzialu,
- `Gradient Boosting` - kolejne drzewa poprawiaja blad,
- `HistGradient Boosting` - boosting na koszykach wartosci,
- `Logistic Regression` - skalowanie, wagi, softmax i klasy.

Nowoczesne ML w `Theory` pokazuje osobne animacje:

- `TabPFN` - tabela jako kontekst, pretrenowany prior i predykcja bez recznego
  strojenia,
- `XGBoost` - sekwencyjne drzewa korekcyjne, learning rate i kara za zlozonosc
  drzewa,
- `MLP` - skalowanie, warstwy neuronowe, aktywacje, blad i backprop,
- `Stacking` - kilka modeli bazowych, predykcje out-of-fold i meta-model.

Najwazniejsze wzory:

```text
RandomForest/ExtraTrees: y_hat = mean(tree_i(x)) albo glosowanie klas
GradientBoosting/HistGradient: F_m(x) = F_{m-1}(x) + eta * h_m(x)
XGBoost: F_m(x) = F_{m-1}(x) + eta * tree_m(x) + kara Omega(tree)
MLP: a_l = sigma(W_l * a_{l-1} + b_l)
Stacking: y_hat = meta(pred_1(x), pred_2(x), ...)
TabPFN: y_hat = f_PFN(X_train, y_train, x_new)
LogisticRegression: P(class|X) = softmax(Xw + b)
```

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
- wyjasnic, co robi `Main`, `Visual`, `Results`, `Report`, `Diagrams`
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
git clone git@github.com/Kitori777/AOA.git
cd AOA
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

### ALICE jako operator aplikacji

ALICE moze dzialac jak prosty terminal z jezykiem naturalnym. Przyklady:

- `co umiesz` - pokazuje kategorie mozliwosci i komend,
- `wczytaj sample do Main` - przygotowuje dane treningowe,
- `zaznacz Quality`, `zaznacz wszystkie ML`, `ustaw TabPFN` - ustawia modele,
- `naucz modele` - uruchamia trening aktualnego wyboru po potwierdzeniu,
- `wczytaj sample do Visual`, `dobierz wykres`, `otworz raport D3` - steruje wykresami,
- `wczytaj sample do Results`, `SQL statystyki`, `SQL braki` - testuje tabele i SQL,
- `stworz raport ML`, `podglad PDF`, `dodaj KPI do raportu` - pomaga w Report,
- `stworz diagram BPMN`, `diagram MLOps`, `diagram magazynu` - buduje schematy,
- `otworz pliki` - pokazuje wygenerowane pliki z podgladem i bezpiecznym usuwaniem,
- `release check` i `qa html` - prowadzi przez kontrole przed publikacja.

Akcje ciezsze, np. trening modeli albo samonauka, wymagaja potwierdzenia,
jesli nie wlaczono auto-potwierdzania.

## Menedzer plikow AOA

Aplikacja ma podglad i usuwanie plikow generowanych lokalnie:

- dane CSV/TXT/TSV,
- raporty HTML/MD/TeX/PDF,
- dashboardy i wykresy HTML/SVG/PNG,
- konfiguracje JSON,
- zapisane modele `.pkl`.

Pliki sa pokazywane z bezpiecznych katalogow `data/`, `models/` i `docs/`.
Przed usunieciem uzytkownik widzi podglad i musi potwierdzic decyzje.
Menedzer otworzysz z Main, Visual albo przez ALICE komenda `otworz pliki`.

## QA HTML i release-check

Przed publikacja warto wykonac:

- testy jednostkowe i przeplywowe,
- kontrola Main: generowanie danych, custom ML/STO, TabPFN, trening,
- kontrola Visual: kazdy typ HTML, dashboard, SolutionTree, eksport,
- kontrola Results: wczytanie danych, SQL, filtry, CSV,
- kontrola Report: pelny builder, PDF preview, biblioteka plikow, eksporty,
- kontrola Diagrams: szablony, kolory, auto layout, SVG/Mermaid/HTML,
- kontrola Theory: ML, heurystyki, TabPFN/nowoczesne ML,
- kontrola ALICE: `co umiesz`, `co mozesz w Main`, `co mozesz w Report`,
- kontrola plikow: podglad wygenerowanych artefaktow i sprzatanie.

Interaktywne HTML powinny miec podstawowe pole manewru: pelny ekran,
eksport danych/konfiguracji, tooltipy, reset i czytelne osie bez nachodzenia.

## Aktualny stan projektu

Projekt ma dzialajacy fundament techniczny:

- aplikacje desktopowa,
- interfejs CLI,
- modele ML,
- heurystyki STO,
- wizualizacje,
- eksport HTML,
- Report Studio,
- Diagrams,
- Theory,
- ALICE,
- dokumentacje,
- testy jednostkowe i przeplywowe.

Ostatnio sprawdzony pelny zestaw testow przechodzil w liczbie ponad 360 testow.


## Segmenty rozwoju wprowadzone jako fundament 0.8.0

Te obszary maja juz wspolne opisy, testy, ALICE playbooki albo dane startowe.
Nie kazdy jest jeszcze osobnym wielkim ekranem, ale aplikacja ma fundament pod
ich dalsze rozwijanie bez przepisywania architektury:

- `ALICE Reviewer`: ocena diagramu, raportu, wykresu, modelu i calego workflow
  na podstawie checklisty jakosci.
- `Scenario Lab`: zapisywanie kilku scenariuszy parametrow danych i porownanie,
  ktory zestaw daje najlepszy wynik.
- `Model Registry UI`: pelna karta kazdego modelu z metrykami, data treningu,
  parametrami JSON, plikiem `.pkl` i notatka uzytkownika.
- `Workflow History`: widok osi czasu: dane -> modele -> wykresy -> raporty ->
  eksporty, z mozliwoscia powtorzenia workflow.
- `Dataset Library`: gotowe datasety testowe, np. produkcja, logistyka,
  magazyn, jakosc, harmonogram i serwis.
- `Report Templates`: gotowe raporty: executive summary, ML validation,
  STO comparison, data quality, release-check i incident review.
- `Diagram QA`: automatyczna kontrola diagramu: brak startu/konca, nieopisane
  decyzje, samotne elementy, krzyzujace sie polaczenia i brak legendy.
- `Chart QA`: kontrola osi, jednostek, legendy, outlierow, interakcji HTML i
  czytelnosci etykiet po eksporcie.
- `Data Contract`: opis wymaganych kolumn, typow, zakresow wartosci i zasad
  walidacji przed treningiem.
- `Assistant Playbooks`: gotowe tryby ALICE: nauczyciel, operator, recenzent,
  analityk raportu, kontroler release i przewodnik po modelach.

Powiazane komendy ALICE:

- `ocen diagram`, `ocen raport`, `ocen wykres`, `ocen model`, `audyt workflow`,
- `jakie kolejne segmenty rozwoju mamy`,
- `jakie sa szablony raportow`,
- `pokaz kontrakt danych`,
- `release check`, `qa html`, `pokaz historie`, `porownaj modele`.

