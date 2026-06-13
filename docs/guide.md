# AOA - Aplikacja Optymalnego Algorytmowania - instrukcja uzytkownika

Ten przewodnik opisuje aktualny sposob pracy w aplikacji AOA: od danych, przez
modele ML/STO/TabPFN, po wizualizacje, diagramy, raporty i pomoc ALICE.

## 1. Najszybszy przeplyw pracy

1. Wejdz w `Main`.
2. Wczytaj plik CSV/TXT/TSV albo wygeneruj dane przykladowe.
3. Ustaw parametry generowania danych.
4. Wybierz modele ML, backend TabPFN albo heurystyki STO.
5. Uruchom trening lub analize.
6. Sprawdz metryki w logu i w `Results`.
7. Zobacz wykresy w `Visual`.
8. Zbuduj diagram procesu w `Diagrams`.
9. Przygotuj raport w `Report`.
10. Jesli nie wiesz, co oznacza wynik, zapytaj `ALICE`.

## 2. Parametry generowania danych

| Pole | Typ | Przyklad | Co oznacza |
| --- | --- | --- | --- |
| Liczba rekordow | calkowita | `5000` | ile wierszy danych wygenerowac |
| Liczba maszyn | calkowita | `1` | ile maszyn uwzglednic w danych |
| Test size | ulamkowa 0-1 | `0.2` | jaka czesc danych idzie na test |
| Seed | calkowita | `42` | powtarzalnosc losowania |
| Czas prod. min/max [h] | calkowita albo ulamkowa | `1`, `48` | zakres czasu produkcji |
| Bufor terminu min/max [h] | calkowita albo ulamkowa | `1`, `72` | zapas dodawany do terminu |

Zasady walidacji:

- liczba rekordow, liczba maszyn i seed musza byc liczbami calkowitymi,
- `test_size` musi byc wieksze od `0` i mniejsze od `1`,
- minimum czasu/bufora musi byc mniejsze od maksimum,
- czasy i bufory moga byc ulamkowe, np. `1.5`.

## 3. Modele ML

`Quality` i `Delay` sa regresja, bo przewiduja liczbe. Metryki to `RMSE`,
`MAE` i `R2`.

`Schedule` jest klasyfikacja, bo wybiera klase lub strategie harmonogramu.
Metryki to m.in. `Accuracy`, `F1` i prawdopodobienstwa klas.

Klasyczne modele:

- Random Forest,
- ExtraTrees,
- Gradient Boosting,
- HistGradient Boosting,
- Logistic Regression dla harmonogramu.

Backend `TabPFN`:

- Quality/Delay uzywa `TabPFNRegressor`,
- Schedule uzywa `TabPFNClassifier`,
- przed treningiem aplikacja sprawdza rozmiar X/y, braki, NaN, inf, minimalna
  liczbe rekordow i minimum dwie klasy przy klasyfikacji.

Nowoczesne modele w Theory:

- `TabPFN` - kontekst tabelaryczny i pretrenowany prior,
- `XGBoost` - boosting z kara za zlozonosc drzewa,
- `MLP` - siec neuronowa, skalowanie, aktywacje i backprop,
- `Stacking` - kilka modeli bazowych i meta-model.

## 4. Wlasny model ML

Kliknij `+ Wlasny model ML`, jesli chcesz dodac model, ktorego nie ma na liscie.

Najprostsza sciezka:

1. Wybierz preset, np. RandomForest, ExtraTrees, SVR, KNN, Ridge, HistGradient,
   LogisticRegression albo XGBoost.
2. Wybierz zadanie: jakosc/regresja, opoznienie/regresja albo harmonogram/klasyfikacja.
3. Wybierz estymator.
4. Wybierz skalowanie: `none`, `standard` albo `robust`.
5. Ustaw parametry JSON.
6. Kliknij `Zapisz model`.
7. Zaznacz nowy model na liscie i uruchom trening.

Przyklady parametrow:

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

Typy parametrow:

- calkowite: `n_estimators`, `max_depth`, `min_samples_leaf`, `max_iter`,
  `n_neighbors`, `random_state`, `n_jobs`,
- ulamkowe: `learning_rate`, `alpha`, `C`, `epsilon`, `subsample`,
  `max_features`, `l2_regularization`,
- tekstowe: `gamma`, `kernel`, `weights`, `class_weight`, `strategy`.

XGBoost jest dostepny jako `xgboost.XGBRegressor` albo
`xgboost.XGBClassifier`, jesli pakiet `xgboost` jest zainstalowany.

## 5. Heurystyki STO

STO porownuje kolejnosci zlecen. Dla kolejki liczone sa:

```text
C_j = czas zakonczenia zlecenia j
d_j = termin zlecenia j
T_j = max(0, C_j - d_j)
STO = suma T_j
```

Im mniejsze STO, tym lepsza kolejka.

Dostepne metody obejmuja m.in. `MT/EDD`, `MO/SPT`, `MZO/LPT`, `MOPT`,
`GENETIC`, `SLACK`, `CR`, `NEH`, `LOCAL_SEARCH` i `RANDOM_RESTART`.

## 6. Wlasna heurystyka STO

Kliknij `+ Wlasna heurystyka STO`, jesli chcesz opisac wlasna regule sortowania.
Heurystyka liczy score dla kazdego zlecenia i sortuje rosnaco.

Dostepne zmienne:

- `p` - czas wykonania,
- `d` - termin,
- `slack` - zapas czasu,
- `cr` - critical ratio,
- `urgency` - pilnosc,
- `i` - numer zlecenia,
- `n` - liczba zlecen.

Przyklady:

```text
d
p
d - p
d / p
d - 1.5 * p
0.7 * d + 0.3 * p
```

## 7. Visual

`Visual` sluzy do wykresow i HTML. Dostepne biblioteki to Matplotlib, Seaborn,
Plotly, Altair i NetworkX. Mozesz tworzyc dashboardy, diagnostyki, heatmapy,
wykresy 3D, Gantt, SolutionTree, sieci, korelacje i mapy brakow.

`SolutionTree` w HTML pozwala klikac wezly, chowac galezie, resetowac widok i
porownywac warianty. Zielony oznacza najlepsza sciezke, zolty wariant sprawdzony
lub porownany.

## 8. Diagrams

`Diagrams` pozwala budowac flowchart, UML, ERD, BPMN, data pipeline, supply
chain, VSM, plant layout, andon, energy flow i inne schematy.

Mozesz:

- dodawac ksztalty i gotowe bloki,
- przeciagac elementy,
- edytowac tekst dwuklikiem,
- zmieniac kolory i style,
- laczyc elementy,
- uzyc `Auto layout`,
- eksportowac `.drawio`, SVG, Mermaid i HTML.

Przycisk `Z opisu` buduje diagram ze zdania, np.:

```text
Dostawca -> magazyn -> QC -> produkcja -> model ML -> raport
```

## 9. Report i Report Builder

`Report` uruchamia workflowy: data quality, dashboard, raport, KPI, metric
diagnostics, market sizing, notebook, correlation explorer, outlier analysis i
inne.

Pelny `Report Builder` otwiera osobne okno:

- po lewej piszesz raport,
- w srodku widzisz podglad strony/PDF,
- po prawej masz guide komend i pliki projektu,
- mozesz wstawic sekcje, KPI, ML, STO, pipeline, ryzyka, wykresy, diagramy,
  obrazy, HTML i kod,
- eksportujesz HTML, Markdown, TeX albo PDF.

## 10. ALICE

ALICE jest przewodnikiem po aplikacji. Mozesz pytac:

- co robi konkretny modul,
- jaki model wybrac,
- czym jest SVM, XGBoost, TabPFN albo STO,
- jak czytac wykres,
- jak zrobic diagram,
- jak napisac raport,
- jak przejsc caly pipeline od danych do decyzji.

ALICE korzysta z lokalnej bazy `docs/alice_brain.json` oraz z dokumentacji
projektu.
