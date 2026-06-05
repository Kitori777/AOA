# Architecture

## High-level structure

Projekt jest podzielony na trzy warstwy:

- `AOA.core`: logika domenowa i serwisy aplikacyjne.
- `AOA.gui`: warstwa prezentacji (CustomTkinter).
- `AOA.cli`: warstwa terminalowa, używająca tej samej logiki `core`.

To pozwala rozwijać GUI i CLI niezależnie, bez duplikowania reguł biznesowych.

## Package responsibilities

### `AOA.core`

- generowanie, ładowanie i walidacja danych tabelarycznych,
- przygotowanie cech, trening i inferencja modeli ML,
- heurystyki STO i raportowanie wyników,
- budowanie danych pod widoki `Visual` i `Results`,
- serwisy orkiestracji (`core/services`) używane przez GUI i CLI.

### `AOA.gui`

- układ okien i stron aplikacji,
- obsługa akcji użytkownika,
- renderowanie podglądów i raportów,
- brak logiki domenowej poza lekką walidacją UX.

### `AOA.cli`

- parser poleceń i przepływy terminalowe,
- wywoływanie tych samych serwisów co GUI.

## Data flow

1. Dane wejściowe (`csv/txt/tsv`) są ładowane przez `core.data_io`.
2. Serwisy `core.services` przygotowują dane do treningu / solve / STO.
3. Wyniki trafiają do GUI/CLI jako komunikaty i DataFrame.
4. GUI/CLI odpowiada tylko za prezentację i zapis działań użytkownika.

## Current design rules

- logika mapowania kolumn i transformacji danych jest utrzymywana w `core.services`,
- GUI nie powinno implementować obliczeń ML/STO,
- nowe funkcje powinny najpierw dostać testy w `tests/core`,
- pliki wynikowe i modele są zapisywane przez serwisy `core/services/*`.

## Production-readiness checklist

- modularny podział (`core`/`gui`/`cli`) jest zachowany,
- testy jednostkowe obejmują krytyczne przepływy,
- błędy są logowane do `logs/`,
- wejście danych jest walidowane przed treningiem i solve,
- nowe mapowanie kolumn jest testowane i wspólne dla GUI.


## Warstwa mlstack (modulowa)
- core/mlstack/models: wspolny interfejs fit/predict/score/export.
- core/mlstack/pipelines: gotowe workflow (dane -> model -> metryki -> raport).
- core/mlstack/evaluation: benchmarki k-fold i regresja jakosci modeli.
- core/mlstack/visual: helpery raportowe pod UI i HTML.

