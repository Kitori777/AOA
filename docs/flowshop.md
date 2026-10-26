# Praca inżynierska: przepływ przez 1–8 maszyn

Główny plik: `data/esm/esm_jobs.csv`. Zachowuje jeden czas na zlecenie.
Po uruchomieniu strony wybrane są 3 maszyny i metody MT, MO, MZO, MOpt.
Program tworzy operacje w pamięci podczas obliczeń; CSV nie jest zmieniany.

## Jeden plik i liczba maszyn wybierana w programie

Przycisk **Utwórz wykresy Gantta (2 × 2)** uruchamia obliczenia, jeżeli nie ma
wyników dla wszystkich zaznaczonych metod. Następnie pokazuje wszystkie te
metody, po cztery na zakładkę: domyślne MT/MO/MZO/MOpt mieszczą się razem,
a wszystkie siedem metod na dwóch zakładkach. Wybór jednego wiersza w rankingu
nie ogranicza tego porównania. Wykresy skalują się razem z oknem i mają wspólną
skalę czasu oraz kolory również między zakładkami.
Każde zlecenie przechodzi kolejno przez wszystkie wybrane maszyny.
Nie są to maszyny równoległe przyjmujące po jednym całym zleceniu.

Wybór sposobu liczenia czasu pozwala porównać dwa jawne założenia:

* **Łączny czas podzielony na maszyny**: dla czasu p i m maszyn operacja na
  każdym etapie trwa p/m. Suma czasów operacji zlecenia pozostaje równa p.
* **Pełny czas na każdej maszynie**: każdy etap trwa p, więc suma wynosi m·p.

Te warianty są też dostępne na liście przykładów; oba czytają ten sam
`esm_jobs.csv`. Podział jest założeniem modelowym, a nie wyznaczeniem nieznanych
technologicznych czasów z pomiarów. Czasy nie są zaokrąglane przed obliczeniami.
Gotowość komponentów nadal blokuje M1, a STO naliczamy tylko po ostatnim etapie.
Pojedynczy czas przezbrojenia jest dzielony w wariancie łącznym i powtarzany
w wariancie pełnego czasu. Odpad całej linii nalicza się raz na zlecenie.

Przykłady posiadające kolumny czasów etapów domyślnie zachowują je bez zmian,
dzięki czemu przykłady artykułu odtwarzają swoje wyniki. Zmiana liczby maszyn
w interfejsie przełącza je na przeliczenie łącznego czasu przez program.
Dla danych z etapów sumujemy też bazowe czasy przezbrojeń przed podziałem.

W **Theory → ESM: 4 Gantty** pojawiają się MT, MO, MZO i MOpt w układzie 2 × 2.
Można wejść tam przyciskiem z trybu inżynierskiego, przekazując bieżący plik,
liczbę maszyn i sposób liczenia czasu. Cztery metody używają jednego snapshotu
danych i wspólnej skali oraz kolorów. Panel działa w tle; zmiana parametrów
unieważnia wykres i nie pozwala wyświetlić wyniku dla poprzednich danych.

## Model i wzory

Zlecenie j przechodzi przez każdą maszynę M1…Mm. Wszystkie maszyny stosują
tę samą kolejność zleceń (permutation flow shop). Operacje są nieprzerywalne,
każda maszyna wykonuje najwyżej jedną operację naraz. Zlecenie może czekać
między operacjami; czekanie nie blokuje poprzedniej maszyny. W podstawowych
przykładach zlecenia są gotowe w chwili 0 i czasy obejmują stałe przygotowanie.
Rozszerzony przykład dodaje jawne terminy gotowości i dodatkowe przezbrojenia.

Niech p[j,k] oznacza czas operacji, d[j] termin, C[j,k] chwilę zakończenia.
Dla ustalonej kolejności:

`C[j,k] = max(C[j-1,k], C[j,k-1]) + p[j,k]`, z zerowymi warunkami brzegowymi.

`T[j] = max(0, C[j,m] - d[j])`; `STO = suma T[j]`.

Najpierw minimalizujemy STO, potem odpad, następnie `Cmax = C[n,m]`. Przy braku
zmiennych odpadów jest to dotychczasowe kryterium STO/Cmax. Wcześniejsze etapy
nie naliczają dodatkowych kar za to samo zlecenie. Jeden kolor na Gantcie
oznacza to samo zlecenie na wszystkich maszynach. Czerwone obramowanie
ostatniej operacji wskazuje spóźnienie; pionowe linie to terminy.

## Podstawowe algorytmy

| Metoda | Ustalanie kolejności | Gwarancja |
|---|---|---|
| MT / EDD | rosnący termin | heurystyka |
| MO / SPT | rosnąca suma czasów na wybranych maszynach | heurystyka |
| MZO / LPT | malejąca suma czasów na wybranych maszynach | heurystyka |
| MOpt | podział i ograniczenia, dolne granice, dominacja | optimum po ukończeniu przeglądu |
| ECO Waste | grupowanie materiałów/kształtów i poprawianie kolejności według STO/odpadu/Cmax | heurystyka |
| Component Ready + EDD | gotowe komponenty, termin, następnie poprawianie kolejności | heurystyka |
| Robust Monte Carlo | wybór spośród kandydatów według ryzyka opóźnień | ocena ryzyka, bez dowodu optimum |

MOpt zaczyna od najlepszej reguły oraz poprawiania przez przenoszenie zleceń.
Następnie rozbudowuje prefiksy kolejności od początku. Granica opóźnień
uwzględnia niezależne najwcześniejsze zakończenia pozostałych zleceń oraz
optymistyczne zakończenia uporządkowane na podstawie najkrótszych operacji.
Przypisanie ich do rosnących terminów daje dolną granicę sumy kar.
Granica Cmax uwzględnia pracę pozostałą na każdej maszynie.

Dla identycznego zbioru pozostałych zleceń oraz ostatniego zlecenia, jeśli
przezbrojenia/odpad zależą od kolejności, odrzucamy stan z nie mniejszym STO
i odpadem oraz nie wcześniejszą dostępnością każdej maszyny. Rekurencja
czasów jest monotoniczna, więc taki stan nie da lepszego wyniku.

Limit domyślny: 10 sekund i 100 000 odwiedzonych stanów. Zapis szczegółowego
śladu obejmuje do 2500 stanów i pełną najlepszą ścieżkę. Widok wybiera do 45
węzłów w GUI. To niezależne limity: rozmiar rysunku nie ucina optymalizacji.
Pomocnicza poprawa rozwiązania początkowego jest wykonywana także przy
zerowym budżecie przeszukiwania. Solver nie wylicza wszystkich remisujących
kolejności i nie gwarantuje leksykograficznie pierwszego optimum.

Zielony oznacza najlepszą ścieżkę, żółty stan sprawdzony, a czerwony rzeczywiste
odcięcie przez granicę lub dominację. Gdy najlepszy wynik pochodzi z rozwiązania
początkowego, odtworzone prefiksy są tak oznaczone. Status w korzeniu mówi,
czy optimum potwierdzono. Gałąź ukryta przez limit widoku nie oznacza odcięcia.

## Zgodność z artykułem

Źródło: A. Jardzioch, R. Dylewski, “Determining the minimum sum of production
order delays in a two-machine system”, MPER 8(3), 2017, 31–39,
DOI 10.1515/mper-2017-0026. Folder `data/esm/article` zawiera źródłowy PDF
i pliki `esm_paper_01.csv`…`04.csv`, które przepisują
dane z tabel 1, 3, 5 i 7. Minimalne STO: 9, 6, 1, 0 minut.

Publikacja używa określenia blokowania/czekania na M2, lecz wyniki tabel
i harmonogramy odtwarzamy powyższą rekurencją z czekaniem między etapami.
Nie jest to odrębny wariant bez bufora blokujący poprzednią maszynę.
Rozszerzenie na m maszyn stosuje własne, weryfikowane granice i rozgałęzianie
od początku; nie przedstawia dwumaszynowego wzoru publikacji jako dowodu dla m.

## Dane, warianty i granice

CSV UTF-8: `zlecenie`, ciąg `czas_m1_min`…`czas_mm_min`, `termin_min`.
Każdy czas i termin musi być dodatni i skończony, identyfikatory unikalne.
Wymagane są czasy wszystkich etapów. Nie ma dopisywania fikcyjnych maszyn.
Wybranie m mniejszego niż liczba kolumn używa pierwszych m etapów; termin
odnosi się wtedy do ostatniego wybranego etapu. Dla porównań raportowych
używamy wszystkich etapów zapisanych w danym scenariuszu.

Przykłady są syntetyczne, oprócz jawnie oznaczonych danych publikacji.
Nazwy wcześniejszych CSV zachowano dla skrótów. Aktualne opisy widać na liście
przykładów. `esm_jobs_10_mixed_constraints.csv` przedstawia teraz konflikt
STO–odpad, a `esm_flow_10_urgent.csv` porównanie MOpt z limitem i bez przerwania.
Regeneracja: `python scripts/generate_esm_examples.py`.

CSV `czas_obrobki_min` uruchamia przepływ z podziałem czasu w programie.
Wszystkie siedem metod jest dostępne także dla danych przepływowych.
Ograniczenia dowolnego wyboru dozwolonych maszyn pozostają niedostępne:
przepływ ma stałą trasę M1…Mm, a nie przydział do maszyn równoległych.

## Trzy dodatkowe metody: przykład 3 maszyn / 10 zleceń

Testy i raporty korzystają z `tests/fixtures/esm/esm_flow_10_eco_components.csv`.
To zestaw syntetyczny, poza listą przykładów programu. Podstawowe dane
artykułów pozostają w `data/esm`.

* `components_ready_min` blokuje start przygotowania na M1 do wskazanej chwili.
  `UNSCHEDULABLE` oznacza trwały brak komponentów: żaden etap tego zlecenia
  nie jest uruchamiany. Wynik wskazuje brakujące zlecenia i plan częściowy.
* `czas_przezbrojenia_m1_min`…`czas_przezbrojenia_mm_min` określają bazowe
  dodatkowe przygotowanie na każdym etapie. Brakujące opcjonalne etapy mają 0.
  Bez tych kolumn `czas_przezbrojenia_min` jest wspólną wartością dla każdego
  etapu. Pierwsze zlecenie nie ma dodatkowego przezbrojenia. Zmiana materiału
  daje mnożnik 1, samego kształtu 0.45, obu naraz 1.2; bez zmiany mnożnik to 0.
* Przygotowanie jest nieantycypacyjne: zaczyna się dopiero po zwolnieniu
  maszyny i zakończeniu poprzedniego etapu danego zlecenia.
* `odpad_kg` naliczamy raz na wykonane zlecenie. `odpad_przezbrojenia_kg`
  oznacza łączny odpad zmiany dla całej linii, pomnożony przez powyższy mnożnik;
  nie jest ponownie dodawany na każdej maszynie.

Te zasady obowiązują wszystkie porównywane metody, także MT/MO/MZO/MOpt.
MOpt na rozszerzonych danych stosuje kontekst ostatniego zlecenia w dominacji
i dodatkową granicę odpadu. Potwierdzenie dla dopuszczonych zleceń nie oznacza
wykonalności całego zamówienia, jeśli inne zlecenia mają brak komponentów.

Robust MC porównuje różne kolejności w 1000 symulacjach, z ziarnem 42.
Pula obejmuje również wcześniejsze wyniki ECO/Component sprzed dodatkowych
przebiegów poprawiania: nominalne optimum nie musi minimalizować ryzyka.
Wybraną kolejność ocenia ponownie na osobnej serii 1000 symulacji, z ziarnem 43.
Ta seria nie wybiera nowego zwycięzcy. Kolumna P90 w GUI pochodzi z weryfikacji,
a szczegóły pokazują obie serie i przybliżony przedział 95% dla średniego STO.
Przedział nie opisuje pojedynczego wykonania ani niepewności parametrów modelu.
Domyślne profile są syntetyczne: MTBF=80 h, MTTR=2 h oraz 3% ryzyka po
przezbrojeniu z oknem 2 h i przestojem 1 h. Te wartości nie są pomiarami
konkretnej fabryki. Do silnika symulacji przekazujemy godziny, a wyniki
przeliczamy na minuty; poprawiono również adapter starego CSV inżynierskiego.
Awaria wstrzymuje i wznawia operację; jej opóźnienie propaguje się na dalsze
etapy. Ryzyko oceniamy przy ustalonej kolejności, bez dynamicznego przeplanowania.

Kryterium wyboru Robust MC to: brak niezaplanowanych zleceń, następnie
średnie STO + 0.5 × max(0, P90 STO - średnie STO), następnie odpad i analogiczna
miara czasu zakończenia. Główna tabela nadal porównuje nominalne STO/odpad/Cmax;
obok pokazuje P90 czasu zakończenia, a opis wyniku także średnie/P90 STO.
Gantt jest nominalny i nie przedstawia jednej wylosowanej awarii.
Brak dopuszczonych operacji oznacza brak oceny ryzyka, nie zerowe ryzyko.

Nie zmieniono logiki Main, Auto Kolejki ani wspólnego symulatora niezawodności.
Raport ośmiu przypadków odtwarza `scripts/report_engineering_methods.py` i zapisuje
go w `output/engineering-case-studies`. [Opis przykładów](engineering-cases.md).

ECO i Component w modelu przepływowym zaczynają od wcześniejszej poprawy
wstawianiem (po dwa przebiegi dla trzech wybranych startów), potem kontynuują
wstawianie i zamiany do lokalnej zbieżności lub limitu 3000 różnych ocen
kolejności na metodę. Cache jest lokalny dla wywołania. Wynik pozostaje
heurystyczny; osiągnięcie optimum można potwierdzić przez porównanie z ukończonym MOpt.

Nie zmieniono zainstalowanej aplikacji ani instalatora. Istniejące pliki w
katalogu danych zainstalowanej aplikacji nadal nie są automatycznie nadpisywane.

## Sprawdzenie

### Wygodna praca z wynikami

1. Wybierz przykład lub wskaż CSV. Po ręcznej edycji ścieżki kliknij **Wczytaj**.
   Podgląd i poprzednie wyniki zostają wyczyszczone, aby nie użyć danych innego
   pliku. Pod tabelą wejściową widać faktycznie wczytany plik i ustawienia.
2. Wybierz **Podstawowe 4**, **Dodatkowe 3** albo **Wszystkie**; możesz też
   zaznaczać metody pojedynczo. Zmiana zestawu wymaga nowego porównania.
3. Uruchom obliczenia. Animowany pasek oznacza pracę, a licznik pokazuje czas od
   uruchomienia, bez szacowania procentu ukończenia. Przycisk obliczeń pozostaje
   nieaktywny do zakończenia zadania. Zmiana danych podczas pracy unieważnia
   poprzedni wynik; nie przerywa obliczeń silnika.
4. **Zapisz porównanie CSV** eksportuje ranking wszystkich obliczonych metod.
   **Zapisz operacje CSV** zapisuje operacje każdej metody wraz z maszyną,
   czasami, przezbrojeniami i opóźnieniem po ostatniej maszynie. Zablokowane
   zlecenie ma powód braku i puste czasy, zamiast pozornego wykonania w chwili 0.
5. Zaznacz wiersz rankingu i kliknij **Kopiuj opis wyniku**. Opis zawiera
   kolejność, kryteria, parametry i status optimum. Dla planu niepełnego zaznacza,
   że STO dotyczy tylko zaplanowanej części. Przerwany MOpt nie otrzymuje
   potwierdzenia optimum, a Robust nie otrzymuje dowodu optimum ryzyka.
6. W oknie Ganttów kliknij **Zapisz wszystkie Gantty** i wybierz folder.
   Powstanie osobny folder `esm_gantty_<czas>` z PNG i SVG każdej zakładki 2 × 2.
   Eksport obejmuje także zakładki, które nie są aktualnie widoczne.

CSV wynikowy ma kodowanie UTF-8 z BOM, separator średnik i przecinek dziesiętny,
aby łatwo otwierał się w polskim Excelu. Eksport zawiera ścieżkę źródła, SHA-256
wczytanych bajtów, liczbę maszyn i kod interpretacji czasu (`total`, `per_machine`
lub `file`). Wartości ryzyka pochodzą z niezależnej weryfikacji, jeżeli jest
dostępna; kolumny serii, liczby symulacji i ziarna wskazują ich pochodzenie.

Eksport i kopiowanie korzystają z gotowego wyniku, bez ponownego obliczania.
CSV zapisywany jest przez plik tymczasowy, więc nieudany zapis nie zastępuje
poprzedniego raportu. Dane w `data/esm` oraz własny źródłowy CSV są chronione
przed zastąpieniem eksportem. Anulowanie okna wyboru niczego nie zapisuje.
Jeśli plik zmienisz w innym programie, kliknij **Wczytaj**, by użyć nowej treści;
dotychczasowe wyniki nadal opisują wcześniej wczytany zestaw.

### Zakres weryfikacji

Testy obejmują cztery przykłady artykułu, niezależny pełny przegląd małych
przypadków dla 1/2/3/8 maszyn, brak nakładania operacji i naruszeń kolejności,
sumowanie kar tylko na ostatnim etapie, limity, błędne CSV, spójność drzewa
i wszystkie dołączone scenariusze. Osobno sprawdzamy rzeczywiste okno Tk.

Raport z obliczeniami i obrazami generuje `scripts/report_esm_flowshop.py`.
Zmierzony czas silnika nie jest pomiarem uruchamiania ani renderowania GUI.
