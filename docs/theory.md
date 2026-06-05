# Teoria AOA: ML, harmonogramowanie STO i interpretacja wynikow

Ten dokument opisuje, jak dzialaja algorytmy pokazywane w zakladce `Theory`.
Najwazniejsza zasada: nie wszystkie modele ML dzialaja tak samo. Random Forest i
ExtraTrees sa zespolami wielu niezaleznych drzew, Gradient Boosting buduje drzewa
po kolei jako poprawki bledow, HistGradient robi to szybciej na koszykach wartosci,
a regresja logistyczna jest liniowym klasyfikatorem.

## 1. Dane i cechy

Aplikacja wczytuje dane tabelaryczne z GUI, CSV, TXT albo TSV. Dla modeli ML
tworzony jest zestaw cech liczbowych, np. czas produkcji, termin, koszt,
material, odpad albo syntetyczne wskazniki procesu. Braki danych sa uzupelniane
mediana.

Drzewa decyzyjne, Random Forest, ExtraTrees i boosting drzewiasty nie potrzebuja
skalowania cech w taki sam sposob jak modele liniowe. Skalowanie ma znaczenie
szczegolnie dla regresji logistycznej oraz modeli opartych o odleglosci lub
marginesy.

## 2. Regresja a klasyfikacja

Modele `Quality*` i `Delay*` sa regresorami. Ich wynik jest liczba:

- jakosc, np. `pred_quality = 0.82`,
- opoznienie, np. `pred_delay = 3.4 h`.

Modele `Schedule*` sa klasyfikatorami. Ich wynik jest klasa strategii, np.
`MT`, `MO` albo `MZO`, czesto z prawdopodobienstwami klas.

Metryki regresji:

- `RMSE` mocno karze duze bledy,
- `MAE` pokazuje przecietny blad w prostszej interpretacji,
- `R2` pokazuje, ile zmiennosci celu wyjasnia model.

Metryki klasyfikacji:

- `Accuracy` pokazuje udzial poprawnych klas,
- `F1` laczy precyzje i czulosc, szczegolnie przy nierownych klasach.

## 3. Random Forest

Random Forest buduje wiele drzew na losowych probkach danych. Kazde drzewo uczy
sie osobno, a potem wyniki sa laczone:

- w regresji wynik jest srednia z wielu drzew,
- w klasyfikacji wynik jest glosowaniem albo srednia prawdopodobienstw klas.

To jest bagging. Jego sens polega na zmniejszeniu niestabilnosci pojedynczego
drzewa. Random Forest moze tez uzywac kontroli OOB, czyli oceny na rekordach,
ktorych dane drzewo nie dostalo w swojej probce.

## 4. ExtraTrees

ExtraTrees jest podobny do Random Forest, ale wprowadza mocniejsza losowosc.
Drzewa losuja nie tylko probki/cechy, ale tez progi podzialu. Dzieki temu model
czesto jest szybki i odporny na szum, ale trzeba sprawdzic train/test, czy
losowosc faktycznie pomaga dla danego zbioru.

## 5. Gradient Boosting

Gradient Boosting nie buduje drzew niezaleznie. Dziala sekwencyjnie:

1. startuje od prostej predykcji bazowej,
2. liczy blad,
3. buduje male drzewo, ktore poprawia ten blad,
4. dodaje poprawke z mala sila (`learning_rate`),
5. powtarza proces wiele razy.

Predykcja koncowa jest suma predykcji bazowej i kolejnych poprawek. Dlatego
boosting potrafi dobrze lapac trudne zaleznosci, ale moze sie przeuczyc, jesli
liczba drzew albo glebokosc sa zbyt duze. W aplikacji stosowane jest early
stopping tam, gdzie dany model to wspiera.

## 6. HistGradient Boosting

HistGradient Boosting to szybka odmiana boostingu. Zamiast sprawdzac kazda
wartosc cechy osobno, zamienia wartosci na koszyki i liczy histogramy. To
przyspiesza uczenie na wiekszych danych i nadal zachowuje logike boostingu:
kolejne drzewa poprawiaja bledy poprzedniego wyniku.

## 7. Regresja logistyczna

`Schedule_LOG` nie jest drzewem. To liniowy baseline klasyfikacyjny:

- dane sa imputowane,
- cechy sa skalowane,
- model uczy wagi cech,
- softmax zamienia wyniki liniowe na prawdopodobienstwa klas,
- wygrywa klasa z najwyzszym prawdopodobienstwem.

Regresja logistyczna jest prostsza niz modele drzewiaste, ale bardzo przydatna
jako punkt odniesienia. Jesli prosty model dziala podobnie dobrze jak zlozony,
to dane moga miec prosta strukture.

## 8. STO i heurystyki harmonogramowania

Heurystyki STO nie sa modelami ML. One nie ucza sie wag ani drzew. Ich zadaniem
jest ulozenie kolejki zlecen i policzenie opoznien.

Dla kazdego zlecenia:

```text
Cj = czas zakonczenia zlecenia j
dj = termin zlecenia j
Tj = max(0, Cj - dj)
STO = suma Tj
```

Im mniejsze `STO`, tym lepsza kolejnosc.

Przyklady metod:

- `MT / EDD` sortuje po terminie,
- `MO / SPT` sortuje po krotkim czasie obrobki,
- `MZO / LPT` zaczyna od dlugich zlecen,
- `MOPT` szuka dokladnie najlepszej kolejnosci,
- `GENETIC` ulepsza populacje kolejnosci przez mutacje i krzyzowanie,
- `LOCAL_SEARCH` poprawia kolejke lokalnymi zamianami,
- `RANDOM_RESTART` probuje wielu startow i wybiera najlepszy wynik.

## 9. Jak czytac Theory w aplikacji

Zakladka `Theory` pokazuje kroki osobno dla kazdego typu algorytmu:

- lasy: wiele drzew i agregacja,
- ExtraTrees: mocniej losowe progi,
- boosting: kolejne poprawki bledow,
- HistGradient: koszyki wartosci i histogramy,
- regresja logistyczna: skalowanie, wagi, softmax,
- STO: kolejka, czasy zakonczenia, opoznienia i ranking.

Panel po prawej pokazuje, co dzieje sie w aktualnym kroku, mini-pseudokod,
stan przykladu i wyjasnienie, dlaczego etap ma znaczenie.
