# Osiem przypadków do pracy inżynierskiej

Każdy zestaw ma 10 zleceń i trasę przez 3 maszyny. Dane są syntetyczne,
dobrane celowo dla określonego zjawiska. Nie są pomiarami fabryki ani próbą
pozwalającą oszacować częstość takich sytuacji. W interfejsie szukaj nazw
zaczynających się od `PRACA`; przykład ryzyka ma nazwę `ECO, komponenty i ryzyko`.

| CSV w `data/esm/examples/` | Pytanie do analizy |
|---|---|
| `esm_flow_10_urgent.csv` | Czy heurystyka może pokonać MOpt przerwany po 100 stanach? |
| `esm_flow_10_eco_trap.csv` | Czy dalsza poprawa może zmniejszyć odpad bez zwiększenia STO? |
| `esm_flow_10_component_wait.csv` | Dlaczego sama gotowość komponentów i dwa przebiegi poprawy nie wystarczą? |
| `esm_flow_10_intentional_idle.csv` | Kiedy świadome pozostawienie M1 bez pracy poprawia terminowość? |
| `esm_jobs_10_mixed_constraints.csv` | Czy mniejszy odpad może oznaczać gorsze STO? |
| `esm_flow_10_eco_components.csv` | Czy nominalne optimum musi mieć najmniejsze P90 opóźnień? |
| `esm_flow_10_multiple_optima.csv` | Czy różne kolejności mogą mieć identyczne optimum? |
| `esm_flow_10_blocked_components.csv` | Dlaczego mniejszego STO planu częściowego nie należy porównywać z pełnym? |

## Jak porównywać

Wszystkie metody przestrzegają tej samej trasy, gotowości i przezbrojeń.
Cel deterministyczny jest leksykograficzny: najpierw liczba niezaplanowanych
zleceń, potem STO, odpad, koniec produkcji. Niższy odpad przy wyższym STO
nie pokonuje więc potwierdzonego MOpt. Gdy plan jest niepełny, potwierdzenie
przeszukiwania dotyczy tylko dopuszczonej części.

Przykład z limitem: MOpt po 100 stanach ma STO 90 min, poprzedni Component
44 min, pełny MOpt 43 min. Nowy Component osiąga 43 min. Jest to eksperyment
z celowo małym budżetem, a nie zmiana domyślnych limitów aplikacji (10 s i 100000
stanów). Na drzewie sprawdź status korzenia i odróżnij odtworzony plan początkowy
od odwiedzonych gałęzi.

W pułapce ECO poprzedni wynik wynosi STO 86 min i 34 kg odpadu; po poprawie
STO pozostaje 86 min, a odpad maleje do 30 kg. W przykładzie Component STO
maleje ze 102 do 92 min. Oba końcowe wyniki można potwierdzić przez MOpt.
To wybrane przykłady poprawy, nie gwarancja poprawy na każdym wejściu.

W przykładzie przestoju Z1 jest długie i gotowe od początku, a pilne Z2 ma
komponenty dopiero od 5 min i termin 8 min. Rozpoczęcie od Z1 daje STO 35 min.
Poczekanie 5 min i wykonanie Z2 jako pierwszego pozwala uzyskać STO 0.

Robust ocenia ograniczoną pulę kolejności, nie wszystkie permutacje. Ranking
zachowuje poprzednie wyniki ECO/Component obok nowych: nominalna poprawa
nie usuwa w ten sposób alternatywy, która może lepiej znosić awarie. Ranking
wyboru wykorzystuje średnie STO i P90 z 1000 realizacji (ziarno 42), po czym
wybrany plan jest sprawdzany w osobnych 1000 realizacjach (43). Wynik tej
weryfikacji nie wybiera ponownie planu. Raport porównuje też ustalone plany
na 3000 realizacjach z ziarnem 43. P90 może się zmieniać między próbami.
W tym przykładzie MOpt ma nominalnie 96 min STO, a Robust 103 min; mniejsze
P90 opóźnień wybranej kolejności sprawdzamy osobno, nie utożsamiając tych celów.
Wspólny numer ziarna nie oznacza awarii przypisanych do tych samych operacji
w różnych kolejnościach. Profile MTBF/MTTR są założeniami syntetycznymi.

## Odtwarzanie i raport

Z katalogu projektu:

```powershell
.venv/Scripts/python.exe scripts/generate_esm_examples.py
.venv/Scripts/python.exe scripts/report_engineering_methods.py
```

Generator zapisuje stałe ziarna i kolejność losowania. Ośmiu przypadkom
odpowiada lista `THESIS_CASES` w generatorze. Raport trafia do
`output/engineering-case-studies/raport.html`; obok są `raport.md`, CSV,
JSON, Gantty PNG/SVG i drzewa PNG/SVG. JSON zawiera operacje, kolejności,
parametry, statusy oraz SHA-256 źródłowych CSV.

Porównanie „przed” odtwarza wcześniejszy refiner (dwa przebiegi wstawiania)
na tych samych nowych danych. Zapisano go w skrypcie raportu; podmiana działa
tylko wewnątrz jednowątkowego procesu raportowania. Dodatkowa weryfikacja
Monte Carlo nie wpływa na odtwarzany wybór. Czasy podano tylko dla obecnego
silnika, bez renderowania obrazów i bez uruchamiania GUI.

Widok drzewa ogranicza liczbę narysowanych węzłów, zachowując najlepszą
ścieżkę. Nie ogranicza zakresu obliczeń. Gantty są nominalne — nie przedstawiają
losowej realizacji awarii. Kliknięcie obrazu otwiera SVG do dokładnego oglądania.
