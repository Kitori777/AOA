# Dane trybu pracy inżynierskiej

* `esm_jobs.csv` — główny plik, jeden czas na zlecenie. Zawartość zachowana.
* `article/` — źródłowy PDF MPER 2017-0026 i cztery jego przykłady CSV.
* `examples/` — przykłady syntetyczne, w tym zestawy do porównywania metod
  na 3 maszynach i 10 zleceniach. Nie są danymi z artykułu ani pomiarami fabryki.

Program automatycznie wyszukuje CSV w podfolderach. Zmiana liczby maszyn
przelicza harmonogram w pamięci i nie zapisuje zmian w danych.
Przykłady artykułu domyślnie używają oryginalnych czasów M1 i M2.

Przycisk **Utwórz wykresy Gantta (2 × 2)** pokazuje wszystkie wybrane metody,
po cztery na zakładkę. Cztery podstawowe metody mieszczą się na jednej;
wszystkie siedem metod na dwóch. Wykresy mają wspólną skalę i kolory zleceń.

Podział łącznego czasu i pełny czas na każdym etapie są przykładami założeń
programu dla tego samego głównego pliku, a nie dodatkowymi kopiami CSV.
