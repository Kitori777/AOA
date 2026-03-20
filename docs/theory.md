# 📘 TEORIA – Production Optimization

## 1. Wczytanie danych produkcyjnych i technicznych

System rozpoczyna działanie od wczytania danych produkcyjnych oraz technicznych zapisanych w pliku CSV.  
Dane obejmują między innymi informacje o:

- kształcie detalu,
- materiale,
- czasie produkcji,
- terminie realizacji,
- ilości odpadu,
- kosztach,
- wymiarach geometrycznych,
- wybranych parametrach technicznych procesu.

Na tym etapie użytkownik wybiera plik wejściowy, a system dokonuje wstępnej walidacji danych i umożliwia ich podgląd.  
Pozwala to upewnić się, że dane zostały poprawnie załadowane oraz nadają się do dalszej analizy.

---

## 2. Inżynieria cech (Feature Engineering)

Z surowych danych wejściowych system tworzy zestaw cech opisujących proces produkcyjny w sposób ilościowy i decyzyjny.  
Celem tego etapu jest zwiększenie informatywności danych oraz poprawa jakości uczenia modeli.

Tworzone cechy obejmują między innymi:

- kodowanie cech kategorialnych, takich jak kształt i materiał,
- normalizację odpadu względem wartości maksymalnej,
- relację czasu produkcji do dostępnego terminu realizacji,
- koszt czasu produkcji jako iloczyn ceny i czasu,
- presję terminu wynikającą z krótkiego czasu realizacji,
- pole powierzchni detalu obliczane na podstawie jego geometrii.

Dzięki temu modele uczą się nie tylko na wartościach surowych, ale również na zależnościach lepiej opisujących realny proces produkcyjny.

---

## 3. Modelowanie jakości i strategii – Random Forest

Do predykcji jakości produktu oraz wyboru strategii harmonogramowania system wykorzystuje algorytm **Random Forest**.

Jest to metoda uczenia zespołowego, w której wiele drzew decyzyjnych budowanych jest na losowych podzbiorach danych i cech.  
Każde drzewo generuje własną predykcję, a wynik końcowy wyznaczany jest jako:

- średnia predykcji w przypadku regresji, np. dla jakości produktu,
- głosowanie większościowe w przypadku klasyfikacji, np. dla wyboru strategii harmonogramowania.

Zaletą tego podejścia jest:

- dobra odporność na szum danych,
- mniejsze ryzyko przeuczenia niż w przypadku pojedynczego drzewa,
- możliwość modelowania zależności nieliniowych.

---

## 4. Predykcja opóźnień – Gradient Boosting

Do estymacji opóźnień produkcyjnych system wykorzystuje model **Gradient Boosting**.

Algorytm ten buduje kolejne drzewa decyzyjne sekwencyjnie.  
Każde następne drzewo uczy się korygować błędy popełnione przez wcześniejsze modele, dzięki czemu predykcja staje się coraz dokładniejsza.

Model ten dobrze sprawdza się w zadaniach regresyjnych, szczególnie wtedy, gdy zależności pomiędzy cechami są złożone i nieliniowe.

---

## 5. Optymalizacja harmonogramu produkcji

System implementuje kilka klasycznych strategii harmonogramowania, takich jak:

- **EDF (Earliest Deadline First)** – priorytet mają zlecenia z najbliższym terminem,
- **SPT (Shortest Processing Time)** – priorytet mają zlecenia o najkrótszym czasie realizacji,
- **LPT (Longest Processing Time)** – priorytet mają zlecenia o najdłuższym czasie realizacji,
- **Slack Time** – priorytet zależy od zapasu czasu do terminu realizacji.

Każdy harmonogram oceniany jest za pomocą funkcji celu, która uwzględnia:

- całkowity czas realizacji,
- łączną sumę opóźnień.

Dzięki temu możliwe jest porównanie kilku strategii i wybór wariantu najlepiej dopasowanego do aktualnych warunków produkcyjnych.

---

## 6. Wizualizacja danych i modeli

System umożliwia wizualizację danych oraz uproszczonych modeli decyzyjnych.  
Dostępne są między innymi:

- wykresy punktowe,
- wykresy liniowe,
- histogramy,
- boxploty,
- wykresy Gantta,
- macierze korelacji,
- macierze podobieństw,
- uproszczone drzewa decyzyjne.

Wizualizacje wspierają interpretację danych, ułatwiają analizę zależności oraz pomagają zrozumieć sposób działania modeli.

---

## 7. Prezentacja wyników i wsparcie decyzyjne

Wyniki działania systemu prezentowane są w formie czytelnych tabel, wykresów i komunikatów tekstowych.  
Użytkownik może uzyskać informacje dotyczące:

- przewidywanej jakości,
- przewidywanego opóźnienia,
- priorytetu zlecenia,
- sugerowanej strategii harmonogramowania.

Całość tworzy spójny system wspomagania decyzji, oparty na danych, analizie statystycznej oraz modelach uczenia maszynowego.

---

## 8. Znaczenie praktyczne projektu

Aplikacja może stanowić podstawę do budowy prostego systemu wspomagania decyzji w środowisku produkcyjnym.  
Pozwala ona:

- analizować dane procesowe,
- szacować jakość i ryzyko opóźnień,
- porównywać strategie harmonogramowania,
- wspierać wybór kolejności realizacji zleceń.

W obecnej wersji projekt ma charakter edukacyjno-analityczny, ale jego architektura może zostać w przyszłości rozwinięta o bardziej zaawansowane modele, dodatkowe źródła danych oraz integrację z rzeczywistymi procesami produkcyjnymi.
