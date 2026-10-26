# Przykłady kosztów uporządkowane według artykułu

Każdy CSV zawiera dane jednego wariantu W. Nazwa wskazuje artykuł, przykład, wariant i sprawdzone minimum kosztu. Dane liczbowe zachowano bez zmian.

## ART3 — jedna maszyna

Źródło: Art3 -v12pp.docx. Folder **ART3_1_maszyna** zawiera osobno **Przyklad_1** (4 zlecenia) i **Przyklad_2** (5 zleceń).

| Przykład i wariant | Co sprawdzasz | CSV |
|---|---|---|
| Przykład 1, W1 | Brak tolerancji; stawki 1; minimum 80 | [ART3_Przyklad_1_W1_koszt_80.csv](ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W1_koszt_80.csv) |
| Przykład 1, W2 | Tolerancja 10 min; stawki 1; minimum 60 | [ART3_Przyklad_1_W2_koszt_60.csv](ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W2_koszt_60.csv) |
| Przykład 1, W3 | Tolerancja 20 min; minimum 50 | [ART3_Przyklad_1_W3_koszt_50.csv](ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W3_koszt_50.csv) |
| Przykład 1, W4 | Tolerancja 30 min; minimum 30 | [ART3_Przyklad_1_W4_koszt_30.csv](ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W4_koszt_30.csv) |
| Przykład 1, W5 | Tolerancja 10 min i stawka Z3 = 10; minimum 110 | [ART3_Przyklad_1_W5_koszt_110.csv](ART3_1_maszyna/Przyklad_1/ART3_Przyklad_1_W5_koszt_110.csv) |
| Przykład 2, W1 | Pięć zleceń; stawki 1; minimum 160 | [ART3_Przyklad_2_W1_koszt_160.csv](ART3_1_maszyna/Przyklad_2/ART3_Przyklad_2_W1_koszt_160.csv) |
| Przykład 2, W2 | Tabela 4; różne stawki; poprawne minimum 300 zamiast 330 | [ART3_Przyklad_2_W2_koszt_300_zamiast_330.csv](ART3_1_maszyna/Przyklad_2/ART3_Przyklad_2_W2_koszt_300_zamiast_330.csv) |

Dla wyniku **300 zamiast 330** otwórz folder **ART3_1_maszyna → Przyklad_2**, a w nim **ART3_Przyklad_2_W2_koszt_300_zamiast_330.csv**. To te same dane, na których kolejność z artykułu daje 330. MOpt znajduje lepszą kolejność Z1 → Z3 → Z5 → Z4 → Z2 z kosztem 300. Nie są potrzebne dwa różne pliki dla 300 i 330.

## DYLEWSKI — dwie maszyny

Źródło: Art-Dylewski_J_D.docx. Folder **DYLEWSKI_2_maszyny** zawiera trzy przykłady.

| Folder | Zlecenia | Warianty i minimalne koszty |
|---|---:|---|
| Przyklad_1 | 3 | W1: 9, W2: 9, W3: 16 |
| Przyklad_2 | 3 | W1: 11, W2: 16 |
| Przyklad_3 | 8 | W1: 154, W2: 183, W3: 219, W4: 248 |

Nazwy CSV zaczynają się od DYLEWSKI_Przyklad i zawierają wariant oraz koszt. Wybierz dwie maszyny i oryginalne czasy etapów z pliku.

W aplikacji wybór przykładu ustawia liczbę maszyn i cel kosztowy oraz zaznacza MOpt. Wiersze U1/U2/U3 w artykule opisują różne kolejności dla danych wariantu W; nie są osobnymi zestawami danych. Manifest zachowuje źródło, numery tabel, parametry wariantu i rozbieżność 300/330.
