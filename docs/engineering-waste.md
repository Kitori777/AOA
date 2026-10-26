# Minimalizacja odpadu w trybie inżynierskim

W sekcji **Co chcesz minimalizować?** wybierz **Odpad**, zaznacz
**ECO Waste** i uruchom obliczenia. Możesz zaznaczyć również pozostałe metody,
aby porównać je na tych samych danych. Obsługiwane jest 1–8 maszyn i do
10 zleceń. Domyślnym kryterium nadal jest STO; wybór celu nie zapisuje CSV.

## Kolejność celów

1. Mniej niezaplanowanych zleceń.
2. Mniejszy całkowity odpad w kg.
3. Mniejsza suma rzeczywistych opóźnień STO w minutach.
4. Wcześniejszy koniec produkcji.

ECO oraz Component poprawiają kolejność względem tego porównania. MT/EDD,
MO/SPT i MZO/LPT zachowują swoje reguły, a ich harmonogramy otrzymują ocenę
według wybranego kryterium. MOpt przeszukuje kolejności z poprawnymi dolnymi
granicami i dominacją dla tego samego celu. Drzewo pokazuje odpad oraz granice
w kg, a ranking, Theory, Gantty 2×2 i eksport zachowują wybrane kryterium.
Zmiana celu unieważnia wcześniejsze wyniki.

## Obliczenia

`odpad = suma(odpad_bazowy_i + współczynnik_zmiany × odpad_przezbrojenia_i)`

Współczynnik wynosi 0 dla jednakowego materiału i kształtu, 0,45 przy zmianie
samego kształtu, 1 przy zmianie samego materiału i 1,2 przy zmianie obu.
Dotyczy parametrów kolejnego zlecenia. Pierwsze zlecenie nie ma odpadu
przezbrojenia, ponieważ model nie określa początkowego stanu linii.

Odpad naliczany jest raz na zlecenie, po ostatniej maszynie; nie mnożymy go
przez liczbę maszyn. Zlecenia zablokowane nie są wykonywane. Plan z takimi
zleceniami jest oznaczony jako niepełny. Nieprawidłowe wartości i sumy
przekraczające zakres liczbowy kończą obliczenia komunikatem błędu.

Gdy odpad nie zależy od kolejności, rozstrzygają STO i czas zakończenia.
Stawki oraz tolerancje kosztowe pozostają widoczne, lecz nie rozstrzygają
remisów w trybie odpadu. Kilogramy, minuty i pieniądze nie są sumowane.

Robust wybiera najpierw mniejszy deterministyczny odpad, następnie miarę
ryzyka opóźnień (średnia + 0,5 × dodatnia różnica P90 i średniej), a potem
miarę ryzyka końca produkcji. Obecny model awarii zatrzymuje i wznawia pracę;
nie dodaje braków materiałowych ani ponownej obróbki. Niezależna seria
symulacji ocenia wybraną kolejność, bez ponownego wyboru zwycięzcy.

## Przykład 3 × 10 i status optimum

W istniejącym `tests/fixtures/esm/esm_jobs_10_mixed_constraints.csv`:

| Wynik | Odpad [kg] | STO [min] |
|---|---:|---:|
| ECO według STO | 30 | 55 |
| ECO według odpadu | 18 | 197 |
| MOpt według odpadu | 18 | 175 |

Zmniejszenie odpadu o 40% wiąże się z większym opóźnieniem. MOpt potwierdza
minimum 18 kg i lepiej rozstrzyga remis niż ECO. Dlatego sam równy odpad
nie uprawnia do nadania ECO statusu pełnego optimum z uwzględnieniem remisów.
Po wyczerpaniu limitu MOpt wynik pozostaje niepotwierdzony. Robust nie dowodzi
globalnego optimum probabilistycznego.

`scripts/check_engineering_waste.py` odtwarza przykład poprzez przyciski GUI,
zapisuje raport, siedem harmonogramów na dwóch stronach 2×2, drzewo oraz CSV
w `output/engineering-waste`. Sprawdza też Theory, zmianę kryterium i
niezmienność danych wejściowych. Testy `tests/core/test_esm_waste.py`
porównują solver z niezależnym pełnym przeglądem małych przypadków dla
każdej liczby maszyn od 1 do 8, także z gotowością, przezbrojeniami i blokadami.
