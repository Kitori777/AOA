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

## 8. STO i wspolny sposob oceny kolejki

Heurystyki STO nie sa modelami ML: nie ucza wag ani drzew z danych treningowych.
Budują kolejność zleceń, po czym ten sam symulator przypisuje operacje do maszyn
i liczy wynik. Dzięki temu porównanie metod jest uczciwe.

Podstawowe oznaczenia:

```text
p_j = czas obrobki zlecenia j
d_j = termin zlecenia j
C_j = czas zakonczenia zlecenia j
T_j = max(0, C_j - d_j)
STO = suma_j T_j
```

Zlecenie zakończone przed terminem ma `T_j=0`, a nie ujemną premię. Domyślny
cel porównuje najpierw liczbę niewykonalnych zleceń, następnie `STO`, odpad,
makespan i stabilny identyfikator kolejności. Dostępne są również cele:

- `waste_then_deadline`: odpad, potem STO i makespan,
- `makespan_then_deadline`: makespan, potem STO i odpad,
- `balanced`: suma znormalizowanych składników STO, odpadu i makespanu.

W przykładach poniżej używamy jednej maszyny i czterech zleceń:

| Zlecenie | czas `p_j` | termin `d_j` |
|---|---:|---:|
| J1 | 6 | 10 |
| J2 | 4 | 11 |
| J3 | 2 | 8 |
| J4 | 7 | 18 |

### 8.1 MT / EDD — najbliższy termin

Wzór rankingu: `key(j)=(d_j,p_j,id_j)` rosnąco. Otrzymujemy
`J3 -> J1 -> J2 -> J4`. Czasy zakończenia to `2, 8, 12, 19`, więc tylko J2 i
J4 są spóźnione po 1 godzinie: `STO=2`. Metoda kosztuje `O(n log n)` i jest
dobrym szybkim punktem odniesienia, ale nie widzi wprost awarii ani długości
kolejnych operacji.

### 8.2 MO / SPT — najkrótsza operacja

Wzór: `key(j)=(p_j,d_j,id_j)` rosnąco. Kolejka to
`J3 -> J2 -> J1 -> J4`, a `STO=3`. SPT często zmniejsza średni czas oczekiwania
i szybko zwalnia kolejkę, ale może zbyt długo odkładać duże albo pilne zlecenie.

### 8.3 MZO / LPT — najdłuższa operacja

Wzór: `key(j)=(-p_j,d_j,id_j)`. Kolejka `J4 -> J1 -> J2 -> J3` daje w
przykładzie `STO=20`. LPT jest użyteczne, gdy długie operacje muszą ruszyć
wcześnie, lecz dla samego STO może opóźnić wiele krótkich zleceń.

### 8.4 MOPT — mały problem dokładnie, duży praktycznie

Ogólna definicja to `pi*=arg min_pi key(evaluate(pi))`. Do 8 zleceń AOA
sprawdza wszystkie permutacje. Dla prostego problemu jednomaszynowego do 18
zleceń używa programowania dynamicznego `O(n*2^n)`. Przy wielu maszynach,
ograniczeniach komponentów, innym celu albo większej kolejce przechodzi do
Random Restart. W przykładzie wybiera `J1 -> J3 -> J2 -> J4`, `STO=2`.
Dlatego dla małego problemu wynik może mieć status `OPTIMAL_CONFIRMED`, a dla
dużego jest najlepszym znalezionym wynikiem, nie dowodem optimum.

### 8.5 GENETIC — populacja i mutacje

Populacja startuje od EDD, SPT, LPT, kolejności wejściowej i wariantów losowych.
W każdym pokoleniu pozostaje najlepsza część populacji, a nowe osobniki powstają
przez zamianę dwóch pozycji. Cel ma postać
`pi*=arg min_{pi w populacji} key(evaluate(pi))`. Domyślnie używane jest 30
kolejek i 40 pokoleń; dla ponad 60 zleceń wartości są zmniejszane. Do 8 zleceń
silnik celowo wykonuje pełny przegląd. Przykład kończy się kolejką
`J1 -> J3 -> J2 -> J4`, `STO=2`.

### 8.6 SLACK — najmniejszy zapas

Wskaźnik `slack_j=d_j-p_j` jest liczony statycznie dla chwili zero. Rosnące
wartości w przykładzie dają `J1 -> J3 -> J2 -> J4`, `STO=2`. Mały slack
oznacza mały bufor bezpieczeństwa. To nie jest wariant dynamiczny, który po
każdej operacji odejmuje jeszcze aktualny czas.

### 8.7 CR — Critical Ratio

AOA używa statycznego `CR_j=d_j/max(p_j,10^-9)` i sortuje rosnąco. Wynik
`J1 -> J4 -> J2 -> J3` ma `STO=17`. Małe CR oznacza bardziej krytyczne
zlecenie względem jego rozmiaru. Implementacja nie przelicza klasycznego
dynamicznego `(d_j-t)/p_j` po każdej operacji — zakładka Theory mówi o tym
wprost, aby nie sugerować innego algorytmu niż rzeczywiście wykonany.

### 8.8 Reguły łączone EDD_SPT, SPT_EDD i LPT_EDD

Są to jawne reguły z kryterium głównym i rozstrzyganiem remisów:

- `EDD_SPT`: `(d_j,p_j,id_j)`, wynik przykładu `STO=2`;
- `SPT_EDD`: `(p_j,d_j,id_j)`, wynik `STO=3`;
- `LPT_EDD`: `(-p_j,d_j,id_j)`, wynik `STO=20`.

W aktualnym silniku odpowiadają dokładnie kolejnościom MT, MO i MZO, ponieważ
te trzy metody bazowe już stosują takie same reguły remisów.

### 8.9 NEH-like — najlepsze miejsce w częściowej kolejce

Zlecenia są najpierw ustawiane malejąco po czasie. Następnie każde nowe
zlecenie jest wstawiane kolejno na każdą możliwą pozycję:

```text
pi_k = arg min_{pozycja 0..k} key(evaluate(pi_{k-1} + j_k))
```

Najlepsza częściowa kolejka przechodzi do następnego kroku. Koszt jest w
przybliżeniu `O(n^2 * E(n))`, gdzie `E(n)` oznacza koszt symulacji. Dla ponad
60 zleceń silnik używa długiego ziarna i Local Search. Przykład daje
`J1 -> J3 -> J2 -> J4`, `STO=2`.

### 8.10 LOCAL_SEARCH — sąsiednie poprawki

Metoda startuje od EDD i zamienia sąsiednie pozycje, jeżeli
`key(pi') < key(pi)`. Proces trwa do braku poprawy. Dla kolejki większej niż 40
zleceń ma maksymalnie dwa przejścia i reprezentatywny zestaw do 24 pozycji.
W przykładzie poprawia EDD do `J1 -> J3 -> J2 -> J4`, `STO=2`. Ograniczeniem
jest lokalne minimum: metoda nie przyjmuje chwilowego pogorszenia.

### 8.11 RANDOM_RESTART — wiele punktów startowych

Najpierw wybierany jest najlepszy wynik EDD, SPT, LPT i SLACK. Następnie metoda
losuje kolejki stałym ziarnem `123`, uruchamia dla każdej Local Search i
zachowuje najlepszą. Domyślnie wykonuje 80 restartów, ale dla dużych kolejek
automatycznie mniej. Przykład daje `J1 -> J3 -> J2 -> J4`, `STO=2`.
Stałe ziarno zapewnia powtarzalność, nie gwarancję optimum.

### 8.12 ECO_WASTE — termin i koszt zmian materiału

Powstają cztery kolejki startowe: grupowanie materiał/kształt, EDD, SPT oraz
gotowość komponentów z grupowaniem materiałowym. Każda jest poprawiana przez
Local Search, a wybór respektuje aktywny cel. Dla celu `waste_then_deadline`
odpad ma pierwszeństwo; dla celu domyślnego pierwszeństwo ma STO. Metoda ma sens
tylko wtedy, gdy pola materiału, kształtu, odpadu i przezbrojenia są wiarygodne.

### 8.13 COMPONENT_READY_EDD — kompletność przed kolejką

Najpierw BOM rezerwuje partie FIFO, również z potwierdzonych przyszłych dostaw.
Dla wykonalnego zlecenia:

```text
R_j = godzina dostępności ostatniego wymaganego komponentu
S_j = max(dostępność maszyny, R_j) + przezbrojenie
key ziarna = (R_j,d_j,p_j,w_j,id_j)
```

Silnik porównuje cztery ziarna i poprawia je lokalnie. Zlecenie bez komponentu
i bez dostawy otrzymuje `UNSCHEDULABLE` i pozostaje jawnie na końcu wyniku.
Nie jest pomijane. W prostym przykładzie wszystkie komponenty są gotowe, więc
wynik to `J1 -> J3 -> J2 -> J4`, `STO=2`.

### 8.14 ROBUST_MC — Monte Carlo awarii

Metoda buduje unikalne kandydaty z MT, MO, MZO, SLACK, CR, NEH, Local Search,
ECO_WASTE i COMPONENT_READY_EDD. Każdą kolejkę ocenia w 1000 scenariuszach ze
stałym ziarnem `42`.

Liczba zwykłych awarii podczas operacji jest losowana jako:

```text
N ~ Poisson(p / MTBF)
```

Czas naprawy ma rozkład lognormalny skalibrowany tak, aby jego średnia była
`MTTR`. Po przezbrojeniu może dodatkowo wystąpić awaria Bernoulliego w zadanym
oknie ryzyka. Operacja zostaje zatrzymana i wznowiona po naprawie; zachowana
jest kolejność zleceń i maszyn.

Wynik ostrożny dla czasu zakończenia to:

```text
risk = E[M] + alpha * max(0, P90(M) - E[M])
alpha = 0.5
```

Analogicznie liczony jest ostrożny wynik opóźnień. Raport pokazuje średnią,
P50, P90, P95, prawdopodobieństwo co najmniej jednej awarii i przestój każdej
maszyny. Dla danych przykładowych metoda wybiera
`J3 -> J1 -> J2 -> J4`, `STO=2`. Wynik jest tak wiarygodny jak wpisane MTBF,
MTTR i ryzyko po przezbrojeniu; obecny model zakłada niezależne awarie maszyn.

## 9. Jak czytac Theory w aplikacji

Zakladka `Theory` pokazuje kroki osobno dla kazdego typu algorytmu:

- lasy: wiele drzew i agregacja,
- ExtraTrees: mocniej losowe progi,
- boosting: kolejne poprawki bledow,
- HistGradient: koszyki wartosci i histogramy,
- regresja logistyczna: skalowanie, wagi, softmax,
- STO: osobny wzór wybranej heurystyki, kolejka przykładowa, czasy zakończenia,
  opóźnienia, koszt obliczeń i ograniczenie metody.

Sekcja pod animacją pokazuje, co dzieje się w aktualnym kroku, wzór,
policzony przykład, pseudokod, koszt obliczeń i ograniczenia metody. Całą stronę
można przewijać jednym pionowym paskiem.

## 10. Rozwoj niezawodnosci etapami

1. **Kalibracja danych** — wyliczanie MTBF, MTTR i rozkładu napraw z historii
   rzeczywistych zdarzeń zamiast polegania wyłącznie na ręcznych wartościach.
2. **Pewność Monte Carlo** — przedziały ufności i kontrola, czy 1000 iteracji
   wystarcza dla stabilnego P90/P95.
3. **Kalendarze utrzymania ruchu** — zmiany robocze, planowane przeglądy,
   dostępność ekip serwisowych i części zamiennych.
4. **Awarie zależne** — wspólne zasilanie, jedna przyczyna zatrzymująca kilka
   maszyn i ograniczona liczba równoległych napraw.
5. **Backtesting** — porównanie planu z wykonaniem, pomiar błędu prognozy i
   kontrolowana aktualizacja parametrów maszyn.
