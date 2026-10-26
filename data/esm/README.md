# Dane trybu pracy inżynierskiej

**Drzewo z wynikiem 300 zamiast 330:** wybierz
[ART3_Przyklad_2_W2_koszt_300_zamiast_330.csv](article/costs/ART3_1_maszyna/Przyklad_2/ART3_Przyklad_2_W2_koszt_300_zamiast_330.csv).
W programie jest to **ART3 | 300 zamiast 330 | przykład 2, W2 | tabela 4**.
Wybór ustawia jedną maszynę, koszt opóźnień i zaznacza MOpt.
Kliknij **Oblicz i porównaj**, a potem **Utwórz drzewo MOpt**.

* `esm_jobs.csv` — główny plik, jeden czas na zlecenie. Zawartość zachowana.
* `article/` — źródłowy PDF MPER 2017-0026 i cztery jego przykłady CSV.
* `article/costs/` — [16 wariantów kosztowych](article/costs/README.md) z dwóch dokumentów Word, z opisem rozbieżności w jednym wyniku źródłowym.
  Pliki są fizycznie rozdzielone na `ART3_1_maszyna` i `DYLEWSKI_2_maszyny`,
  a wewnątrz na `Przyklad_1`, `Przyklad_2` i ewentualnie `Przyklad_3`.
W tym katalogu są wyłącznie główny plik i 20 przykładów z publikacji.
Przypadki syntetyczne przeniesiono do `tests/fixtures/esm`; nie są pokazywane
na liście przykładów programu. Folder `examples` został usunięty z danych.

Program automatycznie wyszukuje CSV w podfolderach. Zmiana liczby maszyn
przelicza harmonogram w pamięci i nie zapisuje zmian w danych.
Przykłady artykułu domyślnie używają oryginalnych czasów M1 i M2.

Przycisk **Utwórz wykresy Gantta (2 × 2)** pokazuje wszystkie wybrane metody,
po cztery na zakładkę. Cztery podstawowe metody mieszczą się na jednej;
wszystkie siedem metod na dwóch. Wykresy mają wspólną skalę i kolory zleceń.

Sposób liczenia czasu nadal można zmienić ręcznie. Odtwarzanie publikacji
wymaga liczby maszyn oraz czasów zgodnych z wybranym artykułem.
