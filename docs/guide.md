# 📊 PRODUCTION OPTIMIZATION – INSTRUKCJA UŻYTKOWNIKA

═════════════════════════════════════════════════════

## 📋 PRZEGLĄD

Aplikacja umożliwia analizę danych produkcyjnych, trenowanie modeli uczenia maszynowego oraz wspomaganie decyzji związanych z planowaniem produkcji.

System wspiera przewidywanie:

- jakości produkcji,
- opóźnień realizacji,
- wyboru strategii harmonogramowania,
- priorytetów produkcyjnych,
- zależności występujących w danych.

### Obsługiwane modele ML

- **Random Forest** – predykcja jakości,
- **Gradient Boosting** – predykcja opóźnień,
- **Random Forest** – wybór strategii harmonogramowania.

═════════════════════════════════════════════════════

## 🎓 TRYB UCZENIA – trenowanie modeli

### 1. Wybór modelu

Użytkownik może wybrać jeden z trybów:

- **Quality** – przewidywanie jakości produkcji,
- **Delay** – przewidywanie opóźnienia realizacji,
- **Schedule** – przewidywanie strategii harmonogramowania,

### 2. Przygotowanie danych

Dane wejściowe w formacie CSV powinny zawierać kolumny:

- `cena`
- `odpad`
- `termin_dni`
- `czas_produkcji_h`
- `ksztalt`
- `material`
- `x`
- `y`
- `z`

Dane można:

- wygenerować losowo bezpośrednio w aplikacji,
- wczytać z własnego pliku CSV.

### 3. Start treningu

Aby rozpocząć trening:

- wybierz model lub modele do trenowania,
- kliknij przycisk **„Trenuj wybrany model”**,
- obserwuj komunikaty i postęp w polu logów.

### 4. Zapis modeli

Wytrenowane modele zapisywane są automatycznie:

- lokalizacja: `models/`
- domyślny plik: `model.pkl`

═════════════════════════════════════════════════════

## 🔍 TRYB ROZWIĄZANIA – predykcja i priorytety

### 1. Wybór modelu i danych

Aby wykonać predykcję:

- kliknij **„Rozwiąż istniejące modele”**,
- wskaż zapisany model `.pkl`,
- wybierz plik danych `.csv`.

### 2. Predykcje i priorytety

W zależności od zawartości pliku modelu aplikacja może obliczyć:

- `pred_quality` – przewidywaną jakość,
- `pred_delay` – przewidywane opóźnienie,
- `priority` – wskaźnik priorytetu wyznaczany jako relacja jakości do przewidywanego opóźnienia.

### 3. Wyniki

Wyniki:

- są wyświetlane w aplikacji,
- zapisywane są do pliku `wynik_priority.csv`,
- prezentują między innymi TOP 10 zleceń o najwyższym priorytecie.

═════════════════════════════════════════════════════

## 📈 WIZUALIZACJA DANYCH

### 1. Wczytanie pliku

Wybierz plik CSV zawierający dane, które chcesz analizować.

### 2. Wybór parametrów wykresu

Użytkownik może:

- wybrać kolumny dla osi **X** i **Y**,
- określić typ wykresu.

Dostępne typy wykresów:

- Scatter,
- Line,
- Histogram,
- Boxplot,
- Gantt,
- DecisionTree,
- CorrelationMatrix,
- SimilarityMatrix.

### 3. Generowanie wykresu

Aby utworzyć wykres:

- kliknij przycisk **„Rysuj”**,
- wykres zostanie wyświetlony w dolnym panelu aplikacji.

### 4. Zastosowanie wizualizacji

Wizualizacje pomagają analizować:

- zależności pomiędzy cechami,
- rozkłady danych,
- podobieństwa i korelacje,
- przebieg harmonogramu produkcji,
- uproszczoną strukturę modelu decyzyjnego.

═════════════════════════════════════════════════════

## 🧾 PODGLĄD DANYCH I TRANSFORMACJE

### 1. Wczytanie danych

- przejdź do zakładki **Results**,
- kliknij **„Wczytaj plik CSV”**,
- wybierz plik, który chcesz przeanalizować.

### 2. Wybór kolumn

Możesz zaznaczyć:

- wszystkie kolumny,
- tylko wybrane kolumny do analizy.

### 3. Dostępne transformacje danych

#### Surowe
Dane pozostają w oryginalnej postaci.

#### MinMax Normalizacja
Skalowanie wartości do przedziału 0–1.

#### Standaryzacja
Transformacja do średniej 0 i odchylenia standardowego 1.

#### Logarytm
Zmniejszenie wpływu wartości skrajnych przy użyciu funkcji `log1p`.

#### Skalowanie 0–1
Proste przeskalowanie każdej kolumny do przedziału 0–1.

### 4. Analiza danych

Po wybraniu kolumn i transformacji użytkownik może uruchomić:

- analizę regresyjną,
- analizę klasyfikacyjną.

Wyniki oraz wybrane dane są prezentowane w polu tekstowym.

═════════════════════════════════════════════════════

## 🛠️ ROZWIĄZYWANIE PROBLEMÓW

**„Brak danych”**  
Wczytaj lub wygeneruj plik CSV.

**„Nie wybrano kolumny”**  
Zaznacz co najmniej jedną kolumnę do analizy.

**Niska jakość predykcji**  
Zwiększ liczbę danych lub popraw ich jakość.

**Brak modelu**  
Upewnij się, że plik `model.pkl` znajduje się w katalogu `models/`.

═════════════════════════════════════════════════════

## 📁 LOKALIZACJA PLIKÓW

**Modele:**  
`models/model.pkl`

**Dane:**  
pliki CSV w katalogu projektu lub w folderze `data/`

**Wyniki:**  
`data/wynik_priority.csv`

**Dokumentacja:**  
`docs/guide.md`  
`docs/theory.md`
