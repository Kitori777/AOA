# Koszty opóźnień w trybie inżynierskim

Siedem metod może porównywać przepływ przez 1–8 maszyn (do 10 zleceń)
według rzeczywistych opóźnień STO albo kosztu opóźnień. Wszystkie metody
korzystają z tych samych czasów, gotowości komponentów, przezbrojeń i kar.

## Wzór i jednostki

`koszt_i = k_i × max(0, C_i − d_i − c_i)`

C oznacza zakończenie na ostatniej maszynie, d wymagany termin, c dopuszczalne
opóźnienie niepowodujące kary (wszystkie w minutach), a k stawkę w j.p./min.
Jednostka pieniężna j.p. może oznaczać np. zł, jeśli stawki podano w zł/min.
Źródła nie określają waluty. Suma kosztów jest sumą kar zleceń, a nie operacji.

Tolerancja nie zmienia rzeczywistego terminu. STO nadal wynosi sumę
`max(0, C − d)`. Stawka 1 i tolerancja 0 dają koszt liczbowo równy STO.
Stawka 0 oznacza brak kary. Odrzucane są wartości ujemne, NaN, nieskończoności
i obliczenia przekraczające zakres liczbowy. Zmiana liczby maszyn nie dzieli
stawki ani tolerancji; zmienia wyłącznie przygotowanie operacji.

## Obsługa

Na początku listy **Przykład**, tuż po głównym pliku, dostępnych jest siedem
pozycji **ART3**. Pierwsza z nich to **ART3 | 300 zamiast 330 | przykład 2, W2**.
Odpowiadają tabelom 1–4 dokumentu
`Art3 -v12pp.docx`. Wybór wczytuje oryginalne czasy, terminy, stawki i tolerancje,
ustawia jedną maszynę oraz cel kosztowy i zaznacza MOpt. W nazwie widnieje
sprawdzone minimum: 80, 60, 50, 30, 110, 160 i 300 j.p. Dla przykładu 2/W2
nazwa przypomina, że artykuł podaje 330. Kliknij **Oblicz i porównaj**, aby
porównać tę wartość z kolumną kosztu oraz statusem optimum w rzeczywistym wyniku.

1. Wczytaj dane. Główny `esm_jobs.csv` zachowuje swoje wartości oraz domyślny
   tryb STO i 3 maszyny. Opcjonalne kolumny `koszt_opoznienia_na_min` oraz
   `dopuszczalne_opoznienie_min` włączają kryterium kosztowe przy wczytaniu.
   Ich wartości domyślne to 1 i 0; puste pola korzystają z tych wartości.
2. Kliknij **Stawki i tolerancje…** przy opcji kosztowej. Formularz stosuje wszystkie zmiany
   dopiero po ich sprawdzeniu. Działa w pamięci i nie zapisuje źródłowego CSV.
   Zmiana danych lub ustawień wymaga ponownego otwarcia starego edytora.
3. W sekcji **Co chcesz minimalizować?** wybierz **Koszt opóźnień** i uruchom obliczenia.
   Zmiana parametrów lub kryterium unieważnia wcześniejsze wyniki i eksport.
4. Wyniki i opis pokazują osobno koszt i STO. Theory przejmuje parametry
   z edytora; wybranie innego pliku w Theory wczytuje parametry nowego źródła.
5. CSV wynikowy zawiera kryterium i pełny zapis stawek oraz tolerancji w
   `parametry_kosztow_json`. SHA-256 identyfikuje wczytany plik, a zmiany
   wprowadzone w programie zapisane są oddzielnie w tych parametrach.
   W operacjach kara pojawia się tylko po ostatniej maszynie.

Na Gantcie linia kropkowana oznacza d, a dodatkowa przerywana oznacza d + c,
gdy tolerancja jest dodatnia. Czerwone obramowanie nadal oznacza rzeczywiste
opóźnienie, także gdy kara wynosi zero. Wszystkie zakładki zachowują wspólną
skalę, kolory, kryterium i parametry kosztowe.

## Kryteria i potwierdzenie optimum

Pełny plan ma pierwszeństwo przed planem z brakującymi zleceniami. Następnie
porównujemy STO albo koszt, odpad i koniec produkcji. Minuty i pieniądze
nie są dodawane. Odpad i czas rozstrzygają remisy. Dla planu częściowego
koszt i STO dotyczą tylko dopuszczonych zleceń; nie potwierdzamy optimum
pełnego planu.

Opcjonalna [minimalizacja odpadu](engineering-waste.md) stosuje inną kolejność:
odpad, STO, koniec produkcji. Nie zmienia to obliczeń kar ani danych wejściowych.

MT/EDD, MO/SPT i MZO/LPT zachowują reguły kolejności i otrzymują dodatkową
ocenę kosztową. ECO i Component poprawiają kolejność według wybranego celu.
MOpt używa granic i dominacji właściwych dla tego celu. Granica ważona nie
przypisuje dowolnie posortowanych stawek do innych zleceń. Po wyczerpaniu
limitu wynik pozostaje niepotwierdzony. Drzewo pokazuje nasze przeszukiwanie
w przód, a wartości granic mają jednostkę wybranego kryterium.

Robust liczy koszt każdego zlecenia w każdej realizacji awarii, po ostatniej
operacji. W trybie kosztowym wybiera według miary:
`średni koszt + 0,5 × max(0, P90 kosztu − średni koszt)`.
W trybie STO zachowuje dotychczasową miarę opóźnień. Wynik nie jest dowodem
globalnego optimum ryzyka: oceniana jest ograniczona pula kolejności.
Wybór wykorzystuje 1000 realizacji (ziarno 42), a niezależna ocena zwycięzcy
kolejne 1000 (43). Ocena nie wybiera ponownie planu. P90 w tabeli pochodzi
z tej niezależnej serii. Koszt nie jest mnożnikiem sumy minut opóźnienia.

Symulator niezawodności nadal używa godzin. Opcjonalne parametry kar jawnie
używają minut; koszt nie jest mnożony przez 60 przy prezentacji. Wywołanie
symulatora bez parametrów kar zachowuje dotychczasowe kolumny i wyniki.
Obliczenia używają liczb zmiennoprzecinkowych i porównania kryteriów z
dotychczasową dokładnością 9 miejsc. Zwykle wyświetlamy koszt do dwóch miejsc;
nie sumujemy wcześniej zaokrąglonych kar operacji.

## Źródła i przykłady

[16 wariantów z dokumentów](../data/esm/article/costs/README.md) zachowuje czasy,
terminy i parametry z tabel. Dla przykładu 2/W2 pierwszego dokumentu niezależny
przegląd znajduje minimum 300, podczas gdy źródło podaje 330. Obie wartości
są zachowane w manifeście. Pozostałe minima potwierdzono.

W przykładzie 1/W5 (1 maszyna, tolerancja 10 min, stawka Z3 równa 10,
pozostałe 1) minimum STO to 80 min, ale koszt tej kolejności wynosi 600 j.p.
Minimum kosztu to 110 j.p. dla Z2 → Z3 → Z1 → Z4, przy STO 130 min.

Dokumenty dotyczą jednej i dwóch maszyn. Obsługa 3–8 maszyn, komponentów,
przezbrojeń i awarii jest rozszerzeniem naszego programu.

Testy obejmują pełny przegląd wszystkich kolejności 16 wariantów, małe losowe
przypadki 1/2/3/8 maszyn, zerowe stawki, różne tolerancje i przezbrojenia.
Rzeczywisty edytor, Theory, eksport oraz niezmienność danych sprawdza:

```powershell
.venv/Scripts/python.exe scripts/check_engineering_costs.py
```

Wyniki i obrazy są zapisywane w `output/engineering-costs`.

Raport odtwarzający 16 minimów oraz eksperyment z 3 maszynami i 10 zleceniami:

```powershell
.venv/Scripts/python.exe scripts/report_engineering_costs.py
```

Raport nakłada stawki i tolerancje na istniejący przykład w pamięci. Użyte
wartości zapisuje w `results.json` i CSV, a wynik w `raport.md`, wraz z obiema
stronami Ganttów i drzewem. Źródłowy CSV pozostaje identyczny.
