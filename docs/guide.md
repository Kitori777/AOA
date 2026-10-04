# AOA - Aplikacja Optymalnego Algorytmowania - instrukcja uzytkownika

Ten przewodnik opisuje aktualny sposob pracy w aplikacji AOA: od danych, przez
modele ML/STO/TabPFN, po wizualizacje, diagramy, raporty i pomoc ALICE.

## Auto Kolejka i plan tygodniowy

Auto Kolejka pracuje w dwóch etapach. Najpierw sprawdza kompletność komponentów
dla całego zlecenia, a następnie wyznacza kolejność operacji, maszynę oraz
dokładną godzinę rozpoczęcia. Odznaczenie maszyny oznacza awarię lub planowany
przestój; algorytm nie przydziela do niej nowych operacji.

W trybie `Ciągły` kolejka może zostać przeliczona po każdej zmianie danych.
W trybie `Tygodniowy` użyj kolejno:

1. `Przygotuj następny tydzień`, aby zapisać wersjonowany szkic.
2. Sprawdź tabelę operacji, maszyn i godzin.
3. `Zatwierdź tydzień`, aby przygotować niezmienny plan.

Od poniedziałku od 06:00 zatwierdzone operacje są zamrożone. Nowe zlecenia
trafiają poza aktywny horyzont 40 godzin. Awaria lub brak materiału powoduje
alert, ale nie przesuwa planu automatycznie. Jeśli zmiana jest konieczna, użyj
`Awaryjnie przeplanuj`, podaj powód i potwierdź utworzenie nowej wersji audytu.

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
- przy wielu maszynach plik danych zawiera `machine_id`, `t_start`, `t_end`
  i `lateness_h_sim`, zeby Visual mogl filtrowac wykresy po maszynie oraz
  rysowac Gantt bez dodatkowego pliku posredniego.

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
`GENETIC`, `SLACK`, `CR`, `NEH`, `LOCAL_SEARCH`, `RANDOM_RESTART` i
`ROBUST_MC`.

Zakladka `Theory -> Heurystyki` pokazuje dla kazdej z 16 metod jej rzeczywisty
wzor, kolejne kroki, pseudokod, koszt obliczen, ograniczenie oraz policzony
przyklad na tych samych czterech zleceniach. Dzieki temu widac nie tylko wynik,
ale tez dlaczego dwie metody mogly zbudowac inna kolejke. Pelny opis matematyczny
znajduje sie w `docs/theory.md`.

### Dwukolejka Auto Queue

Auto Queue planuje w dwoch etapach:

1. Kolejka komponentowa rezerwuje caly wymagany komplet. Zlecenie jest gotowe
   teraz, oczekuje do potwierdzonego czasu dostawy albo pozostaje niewykonalne,
   jezeli nie ma wystarczajacego zapasu ani potwierdzonej dostawy.
2. Kolejka wykonawcza dostaje tylko zlecenia z zabezpieczonym kompletem. Ustala
   kolejnosc operacji, maszyne, poczatek, koniec i opoznienie. Przyszla dostawa
   jest twardym najwczesniejszym czasem rozpoczecia.

W panelu stanu maszyn zaznaczenie oznacza maszyne sprawna. Odznaczona maszyna
zachowuje swoj numer, ale nie przyjmuje nowych operacji. Gdy wszystkie dozwolone
maszyny danej operacji sa niedostepne, pozycja pozostaje jawnie niewykonalna.

Przycisk `Profile maszyn` pozwala zaznaczyc jedna lub kilka maszyn i zmienic
ich wspolne parametry. Puste pole podczas edycji wielu pozycji pozostawia
dotychczasowa wartosc. Konfiguracja obejmuje predkosc, odpad, energie, koszt,
przezbrojenie, produkty, materialy, operacje, MTBF, MTTR i ryzyko po zmianie.
Profile sa zapisane w pliku `<kolejka>.machines.json`.

`ROBUST_MC` ocenia kolejki w 1000 scenariuszach awarii. Losowanie ma stale
ziarno, wiec ten sam plan i ustawienia daja ten sam wynik. Rozpoczeta praca jest
wstrzymywana i wznawiana po naprawie. `Wyniki maszyn` pokazuje srednia oraz
P50/P90/P95, stracone godziny, wykorzystanie i szacowane OEE.

Po analizie STO aplikacja zapisuje lekki plik `sto_visual`. To plik do Visual,
Results i raportow: zawiera model, zlecenie, maszyne, kolejnosc, start, koniec
i narastajace STO, ale nie przenosi ciezkiego `solution_tree_json`.

## 6. Projektant linii produkcyjnej

Po wygenerowaniu albo wczytaniu danych kliknij w Main
`Projektuj i uruchom wlasna linie produkcyjna`.

1. Dodaj stanowisko przyciskiem `+ Stanowisko` i przeciagnij blok w wybrane miejsce.
2. Zaznacz blok, kliknij `Polacz` albo jego prawy uchwyt, a nastepnie kliknij
   stanowisko docelowe. To strzalki ustalaja kolejnosc obliczen.
3. Dla kazdego stanowiska ustaw liczbe rownoleglych maszyn.
4. Uzyj `Maszyny i trasy`, aby zmienic parametry fizycznych maszyn, ich
   mozliwosci oraz kolejnosc operacji dla produktow.
5. Przypisz wymagany wzor czasu i opcjonalne wzory kosztu, odpadu i jakosci.
6. Uzyj auto-ukladu, zoomu albo menu kontekstowego, jezeli diagram jest duzy.
7. Sprawdz status pod plotnem. Symulacja wymaga jednej spojnej sciezki bez
   cykli i rozgalezien.
8. Zapisz projekt albo uruchom symulacje. Niedokonczony diagram mozna zapisac,
   ale przycisk uruchomienia pozostanie zablokowany.
9. Wczytaj `production_line_visual_*.csv` w Visual. Dedykowany dashboard zostanie
   wybrany automatycznie.
10. Wczytaj `production_line_summary_*.csv` w Results albo Report, gdy potrzebujesz
   jednego wiersza na zlecenie. Plik zachowuje cechy wejsciowe i dodaje wynik
   calej linii, dlatego moze tez wejsc do przygotowania danych ML.

Symulator wybiera najwczesniej dostepna maszyne stanowiska. Operacja zaczyna sie
w chwili `max(gotowosc zlecenia, dostepnosc maszyny)`. Konfiguracja i wzory sa
zapisane osobno w JSON, dlatego wynikowy CSV zawiera tylko fakty potrzebne do
wykresow i obliczenia KPI. Zmiana zasobow, kolejnosci albo wzorow ma bezposredni
wplyw na czas, przepustowosc, opoznienia, koszt, odpad i jakosc. Kazdy przebieg
ma unikalne pliki, a nieudany zapis nie pozostawia czesciowego zestawu wynikow.

Projektant obsluguje obecnie linie szeregowe, rownolegle maszyny, rozne trasy
produktow, przezbrojenia oraz awarie. Nie modeluje jeszcze dowolnych rozgalezien,
buforow ani petli powrotnej. Projekt JSON w wersji 3 zapisuje wspolrzedne,
strzalki, profile maszyn i trasy. Pliki wersji 1-2 sa zgodne wstecznie, a liczba
zasobow jest automatycznie migrowana do indywidualnych profili maszyn.
Pola aktualnie zaznaczonego stanowiska sa zatwierdzane takze przy zapisie projektu
i uruchomieniu symulacji, wiec ostatnia zmiana wzoru nie zostanie pominieta.
Plik deklarujacy nowsza, nieobslugiwana wersje schematu jest odrzucany z czytelnym
komunikatem zamiast cichego zgadywania jego znaczenia.

## 7. Wlasna heurystyka STO

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

## 8. Visual

`Visual` sluzy do wykresow i HTML. Dostepne biblioteki to Matplotlib, Seaborn,
Plotly, Altair i NetworkX. Mozesz tworzyc dashboardy, diagnostyki, heatmapy,
wykresy 3D, Gantt, SolutionTree, sieci, korelacje i mapy brakow.

Typ wykresu mozna wybrac z listy albo z kafelkowego selektora. Lista kafelkow
dopasowuje sie do biblioteki, wiec pokazuje tylko sensowne warianty.

`SolutionTree` w HTML pozwala klikac wezly, chowac galezie, resetowac widok i
porownywac warianty. Zielony oznacza najlepsza sciezke, zolty wariant sprawdzony
lub porownany.

## 9. Diagrams

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

## 10. Report i Report Builder

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

## 11. ALICE

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

Glos jest wlaczony domyslnie i startuje automatycznie po odpowiedzi. Tryb `Auto`
uzywa polskiego `gTTS`, a przy braku internetu przechodzi na lokalny glos Windows.
Mozesz tez recznie wybrac `Google`, `Windows` albo `Voicebox`, ustawic glosnosc,
przetestowac glos i zatrzymac aktualna wypowiedz. Google dostaje tylko oczyszczony
tekst przeznaczony do przeczytania. Tymczasowy dzwiek jest usuwany po odtworzeniu,
a kolejne odpowiedzi nie nakladaja sie na siebie.
