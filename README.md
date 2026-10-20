# AOA — planowanie i optymalizacja produkcji

![Logo AOA](src/AOA/assets/brand/aoa_logo.svg)

AOA jest lokalną aplikacją desktopową i terminalową do planowania produkcji,
porównywania heurystyk harmonogramowania, analizy danych oraz przygotowywania
raportów. Projekt działa offline, zapisuje dane użytkownika lokalnie i nie wymaga
zewnętrznej usługi do podstawowej pracy.

- Aktualna wersja: **0.11.2**
- Python: **3.11–3.14**
- Interfejs: **CustomTkinter**
- Repozytorium: **https://github.com/Kitori777/AOA**

## Najważniejsze możliwości

- Osobny tryb **Praca inżynierska** dla projektu ESM: MT/EDD, MO/SPT,
  MZO/LPT, MOpt, ECO Waste, Component Ready + EDD i Robust Monte Carlo
  dla przepływu przez **1–8 maszyn**, do **10 zleceń**.
  Główny plik to `data/esm/esm_jobs.csv`: jeden czas na zlecenie, początkowo
  wybrane są 3 maszyny. Program przygotowuje operacje podczas obliczeń,
  bez zmiany CSV. Domyślnie dzieli łączny czas na etapy; drugi przykład pokazuje
  pełny czas na każdej maszynie. Drzewo, ranking i Gantt używają tego samego
  modelu przepływu. Główny przycisk **Utwórz wykresy Gantta (2 × 2)** pokazuje
  wszystkie zaznaczone metody, po cztery na zakładkę. Okno dopasowuje wykresy
  do rozmiaru ekranu. W Theory dostępne jest też porównanie MT/MO/MZO/MOpt.
  Wszystkie panele mają wspólną skalę czasu i kolory zleceń.
  Zestawy „Podstawowe 4”, „Dodatkowe 3” i „Wszystkie” przyspieszają wybór metod.
  Gotowe wyniki i operacje można zapisać do CSV dla Excela, opis skopiować do
  schowka, a wszystkie zakładki Ganttów wyeksportować do PNG i SVG.
  Rozszerzony przykład `esm_flow_10_eco_components.csv` zawiera gotowość
  komponentów, materiały, odpad i przezbrojenia na każdej z trzech maszyn.
  Osiem opisanych studiów przypadku obejmuje też przerwany MOpt, opłacalny
  przestój, konflikt STO–odpad i plan niepełny. ECO/Component poprawiają
  kolejności do zbieżności lub limitu ocen, a Robust sprawdza zwycięzcę
  na osobnej serii symulacji. Opis: [przypadki do pracy](docs/engineering-cases.md).
- Auto Kolejka z porównaniem wszystkich zarejestrowanych heurystyk STO.
- Indywidualne profile maszyn: wydajność, możliwości, koszt, energia, odpad i niezawodność.
- Dwustopniowe planowanie:
  1. kontrola kompletności komponentów,
  2. przydział operacji do maszyn i wyznaczenie dokładnych godzin.
- Reakcja na niedostępność maszyny bez ukrywania niewykonalnych operacji.
- Tryb ciągły oraz zatwierdzany plan tygodniowy.
- `ROBUST_MC` i 1000-scenariuszowa analiza Monte Carlo awarii oraz przestojów.
- Theory z osobnym wzorem, przykładem, pseudokodem i ograniczeniami każdej z 16 heurystyk.
- Zależności między operacjami, dozwolone maszyny i zamrożone pozycje planu.
- Analizy scenariuszy „co-jeśli”, historia przebiegów i audyt zmian.
- Modele jakości, opóźnień i strategii harmonogramowania.
- Visual Lab, Results Studio, raporty HTML/PDF i diagramy.
- Lokalna asystentka ALICE objaśniająca wyniki i obsługę programu.
- GUI oraz rozbudowane polecenia CLI do automatyzacji pracy.

## Auto Kolejka

Auto Kolejka korzysta z pliku `schedule.csv`. Jeśli obok znajdują się pliki
`bom.csv` i `inventory.csv`, aplikacja najpierw sprawdza oraz rezerwuje
komponenty dla całego zlecenia. Dopiero zlecenia możliwe do wykonania są
przekazywane do dokładnego harmonogramowania operacji.

### Kolejka 1 — komponenty

Każde zlecenie otrzymuje jeden z trzech stanów:

| Stan | Znaczenie |
|---|---|
| `READY` | wszystkie komponenty są dostępne teraz |
| `WAITING_COMPONENTS` | komplet będzie dostępny w potwierdzonym terminie |
| `UNSCHEDULABLE` | brak komponentu lub potwierdzonej dostawy |

Brak jednej pozycji nie zatrzymuje pozostałych zleceń. Problem pozostaje
widoczny w kolejce i w liczniku braków.

### Kolejka 2 — maszyny i czas

Drugi etap wybiera kolejność, maszynę oraz godzinę rozpoczęcia każdej operacji.
Uwzględnia między innymi:

- terminy realizacji i priorytety,
- poprzedniki operacji,
- czas produkcji i przezbrojenia,
- dostępność komponentów,
- listę dozwolonych maszyn,
- maszyny oznaczone jako niedziałające,
- zamrożone i rozpoczęte operacje.

Ranking heurystyk jest liczony na podstawie dokładnego planu operacji, dlatego
liczba niewykonalnych pozycji w rankingu i tabeli maszyn jest zgodna.

### Profile maszyn i produkty

Przycisk **Profile maszyn** otwiera edytor jednej lub wielu zaznaczonych maszyn.
Można wspólnie albo indywidualnie zmienić:

- prędkość, odpad, energię, koszt godziny i czas przezbrojenia,
- obsługiwane produkty, materiały i operacje,
- planowany czas pracy,
- MTBF, MTTR oraz ryzyko i czas przestoju po przezbrojeniu.

Profile są zapisywane obok kolejki jako `schedule.csv.machines.json`. Zmiana
liczby maszyn zachowuje istniejące profile i uzupełnia brakujące ustawieniami
domyślnymi. Niezgodna maszyna nie przyjmuje operacji i jest jawnie pokazana jako
ograniczenie, zamiast otrzymać zlecenie przez cichy fallback.

### Monte Carlo i efektywność

Metoda **Robust Monte Carlo** porównuje kandydatów z istniejących heurystyk w
1000 powtarzalnych scenariuszach. Symulacja obejmuje zwykłe awarie opisane przez
MTBF/MTTR oraz podwyższone ryzyko po przezbrojeniu. Rozpoczęta operacja jest
wstrzymywana i kontynuowana po naprawie.

Przycisk **Wyniki maszyn** pokazuje produktywność, przezbrojenia, bezczynność,
wykorzystanie, dostępność, wydajność, jakość, szacowane OEE, koszt, odpad,
energię oraz średni/P50/P90/P95 czas przestoju. P90 pozwala planować z zapasem,
a eksport CSV zachowuje pełną tabelę.

## Plan tygodniowy

Tryb tygodniowy upraszcza pracę planisty, oddzielając stabilny tydzień
produkcyjny od planów, które nadal można optymalizować.

Domyślna polityka:

- początek tygodnia: poniedziałek, 06:00,
- kalendarz: pięć dni po osiem godzin,
- strefa czasowa: `Europe/Warsaw`,
- horyzont produkcyjny: 40 godzin.

Przepływ pracy:

1. Wybierz tryb **Tygodniowy**.
2. Użyj **Przygotuj następny tydzień**.
3. Sprawdź operacje, maszyny i godziny.
4. Użyj **Zatwierdź tydzień**.
5. Po rozpoczęciu tygodnia jego operacje są automatycznie zamrażane.
6. Nowe zlecenia są planowane dopiero poza aktywnym horyzontem.

Awaria maszyny lub nowy brak materiałowy generuje alert, ale nie przesuwa
samoczynnie zatwierdzonego planu. Zmiana aktywnego tygodnia wymaga działania
**Awaryjnie przeplanuj**, potwierdzenia i podania powodu. Poprzednia wersja
pozostaje w historii audytu.

Tryb **Ciągły** zachowuje dotychczasowe zachowanie i przelicza kolejkę po zmianie
danych, ustawień lub stanu maszyny.

## Szybki start

### Wymagania

- Windows 10/11, Linux lub macOS,
- Python 3.11–3.14,
- zalecany menedżer środowiska `uv`.

### Instalacja z `uv`

```powershell
git clone https://github.com/Kitori777/AOA.git
cd AOA
uv sync --all-groups
uv run aoa
```

Projekt można nadal uruchamiać bezpośrednio z głównego pliku, bez budowania
wersji desktopowej:

```powershell
.\.venv\Scripts\python.exe app.py
```

Dwukrotne kliknięcie `app.py` również korzysta z lokalnego środowiska `.venv`;
okno aplikacji nie zależy wtedy od czasu trwania sesji terminala lub Codex.

Uruchomienie CLI:

```powershell
uv run aoa-cli --help
```

### Instalacja bez `uv`

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
aoa
```

### Diagnostyka okna Tcl/Tk

Jeżeli importy i testy działają, ale okno nie startuje z komunikatem o
`init.tcl`, uruchom test tej samej instalacji Pythona:

```powershell
.\.venv\Scripts\python.exe scripts\check_desktop_runtime.py
```

Wynik `status: OK` potwierdza jednocześnie zgodność binariów Tcl/Tk i możliwość
utworzenia natywnego okna. Jeżeli skrypt informuje, że Python widzi `init.tcl`,
ale Tcl nie może odczytać ścieżki, należy powtórzyć test poza sandboxem lub
innym mechanizmem izolacji. Nie należy kopiować katalogu `tcl` z innej wersji
Pythona: skrypty i biblioteki muszą mieć tę samą wersję, np. 8.6.14.

Zweryfikowany zestaw deweloperski Python 3.14.3 + Tcl/Tk 8.6.14 poprawnie
uruchamia okno AOA. Sam komunikat z procesu ograniczonego nie jest więc dowodem
uszkodzenia projektu ani powodem do obniżania wersji Pythona.

Narzędzia deweloperskie:

```powershell
python -m pip install pytest pytest-cov ruff mypy pre-commit pyinstaller
```

## Dane projektu ESM

Główny zestaw to `data/esm/esm_jobs.csv`, z jednym czasem na zlecenie.
Liczbę maszyn oraz sposób liczenia etapów wybiera się w programie.
Osobny przykład syntetyczny `data/esm/examples/esm_flow_10_three_machines.csv`
zawiera 3 maszyny i 10 zleceń z gotowymi czasami etapów. Przykładowy wiersz:

```csv
zlecenie,czas_m1_min,czas_m2_min,czas_m3_min,termin_min
Z1,10,11,23,82
```

MT sortuje po terminie, MO po rosnącej sumie czasów operacji, MZO po malejącej,
a MOpt szuka minimum sumy dodatnich opóźnień po ostatniej maszynie. Przy remisie
wybierany jest krótszy czas zakończenia całej produkcji. MOpt ma limit 10 sekund
i 100 000 stanów; wyczerpanie limitu oznacza wynik bez potwierdzenia optimum.

Katalog `examples` zawiera wąskie gardło M2, pilne zlecenia, równorzędne
optima i pełne 8 maszyn. `data/esm/article` zawiera PDF MPER 2017-0026 oraz
cztery przykłady z jego tabel. [Spis danych](data/esm/README.md).
Sześć starszych rozszerzonych przykładów zastąpiono danymi przepływowymi,
zachowując nazwy plików dla istniejących skrótów. Nazwy w aplikacji opisują
aktualną zawartość. Dane odtwarza `scripts/generate_esm_examples.py`.

Można wybrać mniej etapów niż zapisano w CSV: używane są pierwsze M1…Mm,
a termin dotyczy ostatniego wybranego etapu. Aby użyć więcej etapów, trzeba
wczytać plik z ich czasami; aplikacja nie dopisuje fikcyjnych czasów.
Szczegóły modelu i ograniczenia: [Przepływ ESM](docs/flowshop.md).

Zachowany bazowy przykład jednej maszyny, `data/esm/esm_jobs.csv`:

```csv
zlecenie,czas_obrobki_min,termin_min
Z1,10,150
Z2,20,30
Z3,100,110
Z4,50,60
```

Tryb pracy inżynierskiej przyjmuje od 1 do 10 zleceń, wymaga dodatnich czasów
i terminów oraz unikalnych identyfikatorów. Dane są liczone w minutach.

## Dane wejściowe Auto Kolejki

Minimalny plik `schedule.csv`:

```csv
zlecenie_id,czas_produkcji_h,termin_h,status
Z-001,4,12,NEW
Z-002,2.5,8,NEW
```

Najważniejsze pola rozszerzone:

| Pole | Zastosowanie |
|---|---|
| `operation_id` | unikalny identyfikator operacji |
| `predecessors` | identyfikatory poprzedników rozdzielone `\|` |
| `dozwolone_maszyny` | numery maszyn, np. `1\|3` |
| `produkt_id`, `ilosc_szt` | wejście do kontroli BOM i magazynu |
| `czas_przezbrojenia_h` | czas przygotowania maszyny |
| `components_ready_h` | godzina potwierdzonej gotowości materiałów |
| `frozen`, `started` | blokada lub rozpoczęcie operacji |
| `fixed_machine_id` | przypisana maszyna dla pozycji zablokowanej |
| `fixed_start_h` | niezmienna godzina startu |
| `status` | `NEW`, `PLANNED`, `IN_PROGRESS`, `DONE` lub `BLOCKED` |

Auto Kolejka potrafi również otworzyć bazowy `data/esm/esm_jobs.csv`; wartości minutowe
są wtedy przeliczane na godziny. Rozszerzone dane produkcyjne można nadal
wczytać ręcznie, ale nie są dołączane do instalatora. CSV przepływu z kolumnami
`czas_m1_min` itd. są przeznaczone dla trybu pracy inżynierskiej.

## CLI

Główne grupy poleceń:

```text
generate      generowanie danych
train         trening modeli ML lub STO
solve         użycie zapisanego modelu
sto-run       ręczna analiza harmonogramowania
workflow      pełny przepływ generate → train → solve
analytics     analiza danych bez GUI
report        budowanie raportu
diagram       generowanie diagramu
alice         pytanie do ALICE
interactive   interaktywny tryb terminalowy
```

Przykład:

```powershell
uv run aoa-cli sto-run `
  --jobs Z1,Z2,Z3 `
  --times 10,20,100 `
  --deadlines 150,30,110 `
  --methods MT,MO,MZO
```

## Architektura

```text
src/AOA/
├── app.py                 punkt wejścia GUI
├── cli/                   polecenia terminalowe
├── core/
│   ├── planning/          operacje, walidacja, harmonogram i plany tygodniowe
│   ├── optimization/      cele oraz heurystyki optymalizacyjne
│   ├── history/           przebiegi i łańcuch audytu
│   ├── reliability/       kopie, diagnostyka i odzyskiwanie
│   ├── storage/           atomowy zapis lokalny i granica synchronizacji
│   ├── machine_catalog.py profile, możliwości i niezawodność maszyn
│   ├── product_routing.py trasy produktów i dozwolone maszyny
│   ├── monte_carlo.py     symulacja ryzyka i percentyle
│   ├── machine_efficiency.py  wykorzystanie i szacowane OEE
│   ├── queue_service.py   dwukolejka i zapis wyników
│   └── component_inventory.py
├── gui/                   strony i okna CustomTkinter
├── platform/              ścieżki wersji źródłowej i instalowanej
└── settings.py            trwałe ustawienia aplikacji
```

Warstwy są rozdzielone tak, aby planowanie można było testować bez uruchamiania
interfejsu. GUI wywołuje te same serwisy, które są dostępne dla CLI i testów.

Więcej informacji: [`docs/architecture.md`](docs/architecture.md),
[`docs/guide.md`](docs/guide.md) i [`docs/theory.md`](docs/theory.md).

## Dane i prywatność

AOA domyślnie pracuje offline. Wersja instalowana zapisuje dane robocze w
`%LOCALAPPDATA%\AOA`, a ustawienia w `%APPDATA%\AOA`. Pliki dołączone do
instalacji są traktowane jako zasoby tylko do odczytu.

Integracja SharePoint pozostaje wyłączona, dopóki użytkownik nie włączy usług
online. Sam adapter nie oznacza automatycznego przesyłania danych.

Plany tygodniowe są zapisywane wersjami. Zatwierdzenie i awaryjne przeplanowanie
trafiają do łańcucha audytu zabezpieczonego skrótami.

## Jakość i testowanie

```powershell
uv run pytest -q --basetemp=.pytest-run\full
uv run ruff check src tests
uv run mypy
python -m compileall -q src
```

Testy obejmują logikę planowania, komponenty, niedostępność maszyn, trwałość
danych, scenariusze, GUI, przykłady wszystkich heurystyk oraz zgodność starszych
przepływów.

## Budowanie wersji Windows

Skrypty wydania znajdują się w `scripts`, a definicje pakowania w `packaging`.

```powershell
.\scripts\build_desktop.ps1
.\scripts\smoke_desktop.ps1
```

Samo utworzenie instalatora nie jest traktowane jako pełna weryfikacja wydania.
Przed publikacją należy uruchomić test wersji spakowanej, instalację oraz
porównanie kontrolnych plików źródłowych i zainstalowanych.

## Struktura repozytorium

| Katalog | Zawartość |
|---|---|
| `src/AOA` | kod aplikacji |
| `tests` | testy automatyczne |
| `data/esm` | [główny CSV, przykłady i artykuł PDF](data/esm/README.md) |
| `docs` | [indeks instrukcji, teorii i architektury](docs/README.md) |
| `scripts` | budowanie, smoke testy i generatory |
| `packaging` | konfiguracja PyInstaller i Inno Setup |
| `models` | lokalne modele użytkownika, bez publikowania w Git |
| `output` | [indeks lokalnych raportów, drzew i Ganttów](output/README.md) |
| `tmp` | pliki robocze do usunięcia po zakończeniu pracy |
| `build`, `dist` | pliki budowania, spakowana aplikacja i instalatory |
| `.aoa`, `.aoa-backups` | lokalny stan aplikacji i kopie bezpieczeństwa |

Katalogi `build`, `dist`, `tmp`, wygenerowana zawartość `output`, cache testów,
logi i wyniki `*_latest.csv` są artefaktami lokalnymi i nie należą do historii
repozytorium. Indeks `output/README.md` jest wersjonowany; same raporty pozostają
na komputerze, dlatego po świeżym pobraniu repozytorium ich odnośniki mogą jeszcze
nie mieć plików docelowych. Sposoby odtworzenia opisano w indeksie.

Po zakończeniu testów można usuwać `.pytest-run`, `.pytest_cache`, `.mypy_cache`,
`.ruff_cache` i foldery `__pycache__`; narzędzia odtworzą je przy kolejnym użyciu.
Plików z `data/esm`, modeli, stanu aplikacji i kopii bezpieczeństwa nie należy
traktować jak pamięci podręcznej. Zawartość `tmp` trzeba sprawdzić przed usunięciem.

## Rozwój projektu

1. Utwórz gałąź roboczą.
2. Dodaj lub zaktualizuj testy razem ze zmianą zachowania.
3. Uruchom pytest, Ruff i mypy.
4. Opisz zmianę w `CHANGELOG.md`.
5. Nie dodawaj modeli `.pkl`, danych użytkownika, logów ani artefaktów budowania.

Projekt nie zawiera obecnie osobnego pliku licencji. Przed redystrybucją lub
wykorzystaniem komercyjnym należy uzgodnić warunki z właścicielem repozytorium.
