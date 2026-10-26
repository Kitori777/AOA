# Lokalne raporty i wykresy

Kontrolę kosztów odtwarza `scripts/check_engineering_costs.py`:
[porównanie CSV](engineering-costs/comparison.csv), [operacje CSV](engineering-costs/operations.csv),
[drzewo MOpt](engineering-costs/tree-cost.png), [wynik kontroli](engineering-costs/verification.json).
Opis: [koszty opóźnień](../docs/engineering-costs.md).

Minimalizację odpadu odtwarza `scripts/check_engineering_waste.py`:
[raport 3 × 10](engineering-waste/raport.md), [Gantty 1–4](engineering-waste/gantt-1.png),
[Gantty 5–7](engineering-waste/gantt-2.png), [kontrola GUI](engineering-waste/verification.json).
Opis: [kryterium odpadu](../docs/engineering-waste.md).

Ustawienia produkcji, celu i wyboru metod sprawdza `scripts/check_engineering_settings.py`:
[wynik kontroli układu i przycisków](engineering-settings/verification.json).
Opcja `--preview` otwiera ten sam panel do obejrzenia. Lokalny
[podgląd panelu](engineering-settings/panel-wide.png) pochodzi z natywnego okna.

[Raport kosztowy 3 × 10 i wariantów źródłowych](engineering-costs/raport.md)
odtwarza `scripts/report_engineering_costs.py`. [Wyniki JSON](engineering-costs/results.json)
zawierają parametry oraz status optimum; [warianty publikacji](engineering-costs/paper-variants.csv)
zestawiają wyniki obliczeń z wartościami w dokumentach.

Ten indeks jest częścią repozytorium. Wygenerowane raporty, obrazy i wyniki
pozostają lokalne i są pomijane przez Git. Po świeżym pobraniu projektu pliki
wskazane poniżej mogą jeszcze nie istnieć.

## Ostatni zapis okna Ganttów 2 × 2

- [Cztery podstawowe metody — PNG](engineering-grid/main-button-four-methods.png)
  · [SVG](engineering-grid/main-button-four-methods.svg).
- [Metody dodatkowe — druga zakładka przy wyborze siedmiu metod — PNG](engineering-grid/main-button-seven-methods-page2.png)
  · [SVG](engineering-grid/main-button-seven-methods-page2.svg).
- [Zapis kontroli widoku i danych](engineering-grid/verification.json).

Obrazy pochodzą z okna otwieranego głównym przyciskiem w trybie inżynierskim.
Odtworzenie obrazów przez kontrolę interfejsu, z katalogu projektu:

```powershell
.venv/Scripts/python.exe scripts/check_engineering_workspace.py
```

Skrypt uruchamia kontrolę GUI i nadpisuje obrazy w `engineering-grid`.
Pozostałe pliki kontrolne w folderze są zapisami wcześniejszych sprawdzeń;
nie należy zakładać, że każde uruchomienie odświeża je wszystkie.

## Raporty i materiały historyczne

Kontrola nowych ułatwień obsługi zapisuje [porównanie CSV](engineering-qol/comparison.csv)
i [operacje CSV](engineering-qol/operations.csv) oraz foldery eksportu wszystkich
zakładek w [engineering-qol](engineering-qol/). Materiały odtwarza ten sam skrypt
`scripts/check_engineering_workspace.py`; każde uruchomienie eksportu Ganttów
tworzy nowy folder z czasem w nazwie.

| Folder | Zawartość | Punkt wejścia |
|---|---|---|
| `engineering-case-studies` | Osiem przypadków, porównania metod, Gantty i drzewa. | [HTML](engineering-case-studies/raport.html), [Markdown](engineering-case-studies/raport.md), [wyniki CSV](engineering-case-studies/wyniki.csv) |
| `engineering` | Wcześniejszy raport przepływu przez wiele maszyn. | [HTML](engineering/raport.html), [Markdown](engineering/raport.md), [wyniki CSV](engineering/wyniki.csv) |
| `engineering-three-methods` | Wcześniejsze porównanie ECO Waste, Component Ready + EDD i Robust Monte Carlo. | [HTML](engineering-three-methods/raport.html), [Markdown](engineering-three-methods/raport.md), [wyniki CSV](engineering-three-methods/wyniki.csv) |
| `engineering-runtime` | Wcześniejsze porównania dla 1, 2 i 3 maszyn. | [1 maszyna](engineering-runtime/gantty-2x2-1-maszyny.png), [2 maszyny](engineering-runtime/gantty-2x2-2-maszyny.png), [3 maszyny](engineering-runtime/gantty-2x2-3-maszyny.png), [wyniki JSON](engineering-runtime/wyniki.json) |

Są to zapisane wyniki wcześniejszych uruchomień. Zmiana kodu lub danych nie
aktualizuje ich automatycznie. Przed wykorzystaniem liczb w pracy porównaj
parametry i sumy kontrolne w odpowiednich JSON-ach, a w razie potrzeby odtwórz
raport. Nazwa folderu nie jest potwierdzeniem zgodności z obecną wersją programu.

Raporty korzystające z obecnych CSV można odtworzyć następująco:

```powershell
# Osiem przypadków; nadpisuje engineering-case-studies.
.venv/Scripts/python.exe scripts/report_engineering_methods.py

# Raport przepływu; nadpisuje engineering.
.venv/Scripts/python.exe scripts/report_esm_flowshop.py
```

Nie uruchamiaj generatora danych tylko po to, aby obejrzeć raport: generator
zapisuje pliki przykładów. Opis danych: [indeks ESM](../data/esm/README.md).
Interpretacja przypadków: [dokumentacja](../docs/engineering-cases.md).

Pliki pozostają w dotychczasowych folderach, dzięki czemu wcześniejsze
odnośniki do wykresów i raportów nadal działają.
