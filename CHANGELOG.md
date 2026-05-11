# CHANGELOG

## [0.5.1] - 2026-05-11

### Fixed

* Naprawiono przepływ metryk ML: `df_test` nie jest już martwym polem używanym tylko do statusu, lecz trafia do oceny modeli w CLI, GUI i warstwie usług.
* Metryki modeli ML są liczone i prezentowane osobno dla zbioru `train` oraz `test`.
* Dodano `gap R²`, aby użytkownik widział różnicę między dopasowaniem treningowym a wynikiem na holdoucie.
* Zmieniono komunikat oceny modeli tak, aby nie sugerował, że wysokie R² in-sample oznacza dobrą generalizację.
* Poprawiono strukturę `data/`: śledzone są tylko jawne dane przykładowe w `data/sample/`, a lokalnie generowane CSV nie powinny trafiać do commita.
* Zaktualizowano README i `docs/guide.md`, aby opisywały aktualną strukturę repozytorium i aktualny UI po zmianach z 0.5.0.

### Changed

* Rozbito `AOA.core.services` na realne moduły robocze; `services/__init__.py` jest teraz lekką fasadą importów, a nie drugą kopią logiki.
* Rozbito rejestry modeli `ml_models` i `mh_models` na osobne pliki `specs.py` oraz moduły budujące modele.
* Usunięto martwy plik `src/AOA/cli.py`, który był przesłaniany przez pakiet `src/AOA/cli/`.
* Uporządkowano ścieżki treningu i rozwiązywania modeli tak, aby nowe warianty ML działały przez jeden wspólny mechanizm.

### Added

* Dodano 12 wariantów modeli uczenia maszynowego: 4 jakości, 4 opóźnienia i 4 harmonogramowania.
* Dodano testy dla każdego wariantu ML, sprawdzające czy model jest w rejestrze, czy da się go wybrać i wytrenować oraz czy trafia do właściwego slotu w paczce modelu.
* Dodano testy sprawdzające, czy każdy model ML ma kartę w `TheoryPage` i pełną animację krokową.
* Dodano testy zabezpieczające przepływ `train/test` w metrykach oraz przekazywanie `df_test` przez `train_models_flow`.

### Improved

* Poprawiono `TheoryPage`: większy obszar animacji, czytelniejszy prawy panel, zwijany pasek boczny i bardziej kompaktowe przykładowe dane.
* Rozwinięto animacje modeli do 12 kroków, aby użytkownik mógł zrozumieć, co dzieje się z danymi w kolejnych etapach uczenia i predykcji.
* Poprawiono opisy modeli ML i heurystycznych, żeby lepiej tłumaczyły cel, zachowanie algorytmu i interpretację wyniku.

### Tests

* `uv run ruff check .`
* `uv run mypy src tests`
* `uv run pytest -q` → `214 passed`

## [0.5.0] - 2026-05-08

### Added

* Dodano interaktywną stronę `ReadmePage`, która prowadzi użytkownika krok po kroku przez pracę w aplikacji:
  * wybór trybu pracy,
  * przygotowanie albo wczytanie danych,
  * trenowanie modeli ML,
  * korzystanie z modeli STO,
  * rozwiązywanie danych zapisanym modelem,
  * analizę wyników i wizualizacji.
* Dodano nowy moduł `core/learning_content.py`, który przechowuje treści instruktażowe i teoretyczne poza warstwą GUI.
* Dodano rozbudowaną stronę `TheoryPage` z krótką teorią użytkową dla modeli i metryk:
  * RMSE, MAE i R² dla regresji,
  * Accuracy i F1 dla klasyfikacji,
  * przeuczenie modelu,
  * ważność cech,
  * modele jakości i opóźnień,
  * rekomendacje harmonogramu,
  * modele STO,
  * ranking priorytetów.
* Dodano generowanie prostych wykresów edukacyjnych dla modułów teoretycznych, aby użytkownik szybciej rozumiał zachowanie modeli.
* Dodano tryb `Visual Lab` do bardziej interaktywnej eksploracji danych.
* Dodano nowe typy wizualizacji danych:
  * `Dashboard`,
  * `Diagnostics`,
  * `Pair Explorer`,
  * `3D Scatter`,
  * `3D Surface`,
  * `Bubble Chart`,
  * `Heatmap Density`,
  * `Outlier Map`,
  * `Step View`,
  * `Column Ranking`.
* Dodano raport tekstowy przy wizualizacjach, pokazujący m.in. liczbę rekordów, kolumn, braki danych, statystyki X/Y/Z, obserwacje odstające i korelację.
* Dodano obsługę dowolnych danych tabelarycznych w widokach analitycznych, nie tylko danych produkcyjnych.
* Dodano wczytywanie plików `.csv`, `.txt` oraz `.tsv` z automatycznym przygotowaniem danych do podglądu i wizualizacji.
* Dodano nowy moduł `core/result_viewer_service.py` do filtrowania, sortowania, limitowania, profilowania i eksportowania widocznego widoku danych.
* Dodano przebudowaną stronę `ResultsPage` jako `Results Studio` / prosty viewer danych:
  * globalny filtr tekstowy,
  * sortowanie po kolumnach,
  * wybór kierunku sortowania,
  * limit liczby wierszy,
  * profil wybranej kolumny,
  * raport braków danych,
  * eksport widocznego widoku do CSV,
  * karty podsumowania zbioru.
* Dodano testy jednostkowe dla nowych treści edukacyjnych i serwisu wyników:
  * `tests/core/test_learning_content.py`,
  * `tests/core/test_result_viewer_service.py`.

### Changed

* Przebudowano `ReadmePage` z prostego czytnika dokumentacji na interaktywną instrukcję użytkownika.
* Przebudowano `TheoryPage`, aby skupiała się na najważniejszych rzeczach potrzebnych do użytkowania modeli, zamiast na długiej teorii oderwanej od aplikacji.
* Przebudowano `VisualPage` w kierunku bardziej nowoczesnego panelu eksploracji danych z wyborem X/Y/Z, raportem po prawej stronie i większą liczbą widoków.
* Przebudowano `ResultsPage`, usuwając z niej niedziałające elementy regresji i klasyfikacji oraz zastępując je funkcjami przeglądania i raportowania danych.
* Rozszerzono `core/visualization_service.py`, aby obsługiwał nowe typy wykresów i raportów bez przenoszenia logiki do GUI.
* Rozszerzono przepływ wczytywania danych wizualnych tak, aby aplikacja mogła pracować z bardziej ogólnymi plikami tabelarycznymi.
* Zmieniono opis projektu w README, aby odzwierciedlał nowy charakter aplikacji jako narzędzia analityczno-edukacyjnego.
* Zaktualizowano strukturę repozytorium w README o nowe moduły i testy.

### Fixed

* Naprawiono problem z ucinaniem treści na stronie `TheoryPage` przez zastosowanie większych przewijanych kart i lepszych długości zawijania tekstu.
* Poprawiono panel boczny i sekcje przewijane, aby dłuższe treści nie znikały poza widocznym obszarem.
* Poprawiono czytelność komunikatów i opisów w widokach edukacyjnych oraz analitycznych.
* Usunięto elementy ręcznego wejścia STO z głównego widoku, ponieważ po wprowadzeniu pełnego workflow modeli STO były nieadekwatne.
* Usunięto przyciski regresji i klasyfikacji z `ResultsPage`, ponieważ widok wyników ma obecnie pełnić rolę viewer/reporting studio, a nie uruchamiać niedokończone akcje ML.

### Improved

* Uporządkowano architekturę zmian: treści, raporty, profile danych i generowanie wykresów pozostają w warstwie `core`, a GUI odpowiada głównie za wyświetlanie i obsługę kliknięć.
* Poprawiono użyteczność aplikacji dla osoby, która dopiero poznaje moduły ML/STO i potrzebuje wyjaśnienia „co kliknąć” oraz „co oznacza wynik”.
* Poprawiono możliwość pracy z własnymi danymi użytkownika, także wtedy, gdy nie są to dane produkcyjne z domyślnego generatora.
* Zwiększono liczbę dostępnych wizualizacji i sposobów patrzenia na dane.
* Poprawiono czytelność raportów danych oraz interpretacji wykresów.
* Ułatwiono dalszą rozbudowę aplikacji w kierunku dashboardów, interaktywnych analiz i widoków podobnych do nowoczesnych narzędzi webowych.

### Documentation

* Zaktualizowano README o opis wersji `0.5.0`, nowe możliwości stron `Readme`, `Theory`, `Visual` i `Results` oraz zaktualizowaną strukturę projektu.
* Zaktualizowano CHANGELOG o pełny opis zmian w wersji `0.5.0`.
* Dopisano informację, że aplikacja obsługuje teraz nie tylko dane produkcyjne, ale również dowolne dane tabelaryczne w plikach CSV/TXT/TSV.
* Dopisano informację o nowych modułach `learning_content.py` i `result_viewer_service.py` oraz odpowiadających im testach.

## [0.4.0] - 2026-04-10

### Added

* Dodano eksperymentalny backend `TabPFN` dla modeli ML.
* Dodano nowy moduł `core/tabpfn_models.py`, odpowiedzialny za izolację integracji z `TabPFN`.
* Dodano obsługę backendów modeli ML:
  * `classic`,
  * `tabpfn`.
* Dodano możliwość wyboru backendu ML bezpośrednio z poziomu GUI.
* Dodano automatyczne zapisywanie informacji o backendzie w paczce modelu.
* Dodano obsługę modeli `TabPFN` w przepływie trenowania i rozwiązywania danych.
* Dodano obsługę limitu CPU dla `TabPFN`, w tym możliwość pracy na większych zbiorach danych po ustawieniu odpowiednich parametrów środowiskowych.
* Dodano nowy interfejs terminalowy `CLI` w pliku `src/AOA/cli.py`.
* Dodano komendy CLI do:
  * generowania danych,
  * trenowania modeli,
  * rozwiązywania zapisanym modelem,
  * uruchamiania analiz STO,
  * zapisu modeli STO,
  * rozwiązywania zapisanym modelem STO,
  * podglądu danych,
  * wyświetlania podsumowania konfiguracji,
  * wyświetlania statusu danych,
  * wykonywania pełnego workflow,
  * pracy w trybie interaktywnym.
* Dodano rozbudowaną pomoc `--help` dla CLI wraz z opisami komend i przykładami użycia.
* Dodano testy dla nowej warstwy `cli`, obejmujące:
  * parser i `main`,
  * komendy podstawowe,
  * workflow,
  * tryb interaktywny.
* Dodano testy dla integracji `TabPFN`.
* Dodano katalog `logs` do zapisu logów błędów.
* Dodano lub włączono użycie narzędzia `error_utils.py` do lepszego raportowania błędów.
* Dodano logowanie ścieżek plików wejściowych, modeli i wyników podczas rozwiązywania danych w GUI.
* Dodano czyszczenie poprzedniego stanu danych w GUI przed generowaniem lub wczytywaniem nowego zestawu.

### Changed

* Rozszerzono `core/models.py`, aby obsługiwał wiele backendów modeli przy zachowaniu zgodności z dotychczasowym workflow.
* Rozszerzono `core/services.py`, aby:
  * obsługiwał backend `tabpfn`,
  * zachowywał kompatybilność z dotychczasowymi testami,
  * lepiej rozdzielał logikę treningu, rozwiązywania i analizy wyników.
* Zmieniono logikę `solve_models_flow`, aby poprawnie obsługiwała modele `TabPFN` z zachowaniem nazw cech.
* Zmieniono sposób przygotowania danych do predykcji tak, aby uniknąć ostrzeżeń dotyczących braku nazw kolumn przy `TabPFN`.
* Rozbudowano `main_page.py`, aby:
  * obsługiwał wybór backendu ML,
  * czytelniej logował przebieg operacji,
  * lepiej raportował błędy,
  * poprawnie pokazywał ścieżki zapisanych wyników,
  * czyścił stan danych przed kolejnymi operacjami.
* Ujednolicono komunikaty statusu danych tak, aby lepiej odzwierciedlały aktualnie załadowany zbiór.
* Zmieniono sposób prezentacji logów w GUI, aby użytkownik widział dokładniej:
  * wybrany model,
  * wybrane dane,
  * typ paczki modelu,
  * backend modelu,
  * miejsce zapisu pliku wynikowego.
* Rozszerzono `pyproject.toml` o:
  * opcjonalne zależności eksperymentalne,
  * wpis skryptu `aoa-cli`.
* Zaktualizowano strukturę repozytorium o nowe moduły, testy i katalog logów.

### Fixed

* Naprawiono problem z doborem wersji `tabpfn` w konfiguracji zależności.
* Naprawiono problemy zgodności testów z nową logiką `services.py`.
* Naprawiono problem z nieprawidłowym argumentem `random_seed` przy generowaniu danych.
* Naprawiono logikę wyliczania i sortowania `priority`, aby była zgodna z oczekiwanym zachowaniem.
* Naprawiono problem z ostrzeżeniem `X does not have valid feature names` podczas predykcji modeli `TabPFN`.
* Naprawiono problem z rozjazdem pomiędzy konfiguracją GUI a stanem aktualnie załadowanych danych.
* Naprawiono sytuacje, w których GUI pokazywało stare dane po zmianie konfiguracji.
* Naprawiono zgodność testów CLI na różnych systemach operacyjnych, w tym różnice separatorów ścieżek Windows/Linux.
* Naprawiono komunikaty błędów tak, aby pokazywały realny wyjątek zamiast ogólnego komunikatu o nieoczekiwanym błędzie.
* Naprawiono kompatybilność funkcji pomocniczych z wcześniejszymi testami jednostkowymi.
* Naprawiono obsługę modeli zapisywanych z różnymi typami paczek (`ml`, `sto`) w przepływach GUI i CLI.

### Improved

* Zwiększono elastyczność architektury przez dodanie drugiego pełnego interfejsu aplikacji obok GUI.
* Zwiększono spójność pomiędzy GUI, CLI i warstwą `core`.
* Ułatwiono uruchamianie pełnych przepływów pracy bez interfejsu graficznego.
* Poprawiono czytelność logów i diagnostyki błędów.
* Zwiększono pokrycie testowe projektu o warstwę CLI i integrację backendu `TabPFN`.
* Ułatwiono dalszą rozbudowę projektu w kierunku automatyzacji i pracy skryptowej.
* Zwiększono czytelność obsługi modeli i przepływów dla użytkownika końcowego.
* Ułatwiono pracę z projektem zarówno w trybie desktopowym, jak i terminalowym.

### Documentation

* Zaktualizowano opis projektu w README, uwzględniając:
  * warstwę `cli`,
  * eksperymentalny backend `TabPFN`,
  * katalog `logs`,
  * rozszerzony zakres testów.
* Zaktualizowano sekcję aktualnego stanu projektu, uwzględniając:
  * obsługę CLI,
  * nowe testy,
  * rozwój architektury,
  * rozszerzenie funkcjonalności ML.
* Zaktualizowano opis struktury repozytorium o:
  * `src/AOA/cli.py`,
  * `src/AOA/core/tabpfn_models.py`,
  * `src/AOA/utils/error_utils.py`,
  * `tests/cli/`,
  * `tests/core/test_tabpfn_models.py`,
  * `logs/`.
* Uzupełniono dokumentację o informację, że aplikacja może być obsługiwana zarówno przez GUI, jak i z poziomu terminala.
* Krótko odświeżono README pod kątem zgodności z aktualnym stanem projektu i nowym workflow pracy.

## [0.3.0] - 2026-04-09

### Added

* Dodano rozszerzone testy jednostkowe dla warstwy `core`, obejmujące m.in.:
  * przepływy usługowe w `core/services.py`,
  * walidację konfiguracji generowania danych,
  * zapis i odczyt paczek modeli,
  * dodatkowe przypadki brzegowe dla `features`, `models`, `data_generation`, `scheduling`, `visualization_service` i `sto_models`.
* Dodano obsługę zapisywania konfiguracji modeli STO jako osobnych paczek modeli, analogicznie do modeli ML.
* Dodano możliwość późniejszego rozwiązywania danych z pliku CSV na podstawie wcześniej zapisanego modelu STO.
* Dodano generowanie osobnych plików wynikowych dla każdego uruchomionego modelu STO.
* Dodano zapis najlepszego wyniku STO do osobnego pliku wynikowego.
* Dodano kolumny wynikowe STO do plików CSV, w tym:
  * `sto_model`,
  * `sto_order`,
  * `sto_start`,
  * `sto_end`,
  * `sto_lateness`,
  * `sto_tardiness_positive`,
  * `sto_cumulative`,
  * `sto_total_for_model`.
* Dodano czytelniejsze logowanie przebiegu analiz STO oraz informacji o zapisanych plikach wynikowych.
* Dodano rozróżnienie paczek modeli według typu (`ml` / `sto`), aby zachować spójny workflow rozwiązywania.

### Changed

* Ujednolicono workflow pracy z modelami STO tak, aby działał podobnie do modeli ML:
  * najpierw zapis modelu,
  * później wybór modelu,
  * następnie wybór danych wejściowych,
  * na końcu zapis wyniku.
* Zmieniono nazewnictwo plików wynikowych tak, aby najpierw wskazywały model, potem dane źródłowe i datę zapisu, np.:
  * `wynik_priority_genetic_nazwa_danych_YYYYMMDD_HHMMSS.csv`,
  * `wynik_priority_best_genetic_nazwa_danych_YYYYMMDD_HHMMSS.csv`.
* Rozszerzono `core/services.py`, aby rozdzielał logikę modeli ML i STO w bardziej jawny i przewidywalny sposób.
* Rozbudowano logikę raportowania STO, aby lepiej pokazywać ranking modeli, szczegóły kolejności oraz wynik najlepszego rozwiązania.
* Zmieniono zachowanie GUI w `main_page.py`, aby zapis i późniejsze użycie modeli STO było bardziej intuicyjne.
* Rozszerzono obsługę postępu dla treningu modeli ML, tak aby użytkownik widział bardziej szczegółowy przebieg wykonywania operacji.

### Fixed

* Naprawiono niespójność pomiędzy logiką rozwiązywania modeli ML i STO.
* Naprawiono sytuację, w której wyniki harmonogramowania mogły pojawiać się mimo braku wybranego modelu `Schedule`.
* Poprawiono warunki zapisu wyników tak, aby użytkownik otrzymywał pliki jednoznacznie powiązane z użytym modelem.
* Poprawiono obsługę walidacji danych wejściowych przy rozwiązywaniu danych na podstawie zapisanych modeli STO.
* Poprawiono testy jednostkowe po zmianach w strukturze raportów STO i sposobie generowania wyników.
* Poprawiono zgodność testów z aktualną logiką `services.py`, w tym z dynamicznym budowaniem nazw plików wynikowych.

### Improved

* Zwiększono spójność architektury pomiędzy modelami ML i heurystykami STO.
* Ułatwiono użytkownikowi identyfikację, który plik wynikowy odpowiada konkretnemu modelowi i konkretnemu zestawowi danych.
* Poprawiono czytelność logów operacyjnych w GUI.
* Zwiększono pokrycie testowe kluczowych ścieżek działania aplikacji.
* Ułatwiono dalszy rozwój mechanizmu wersjonowania i publikacji wydań.


## [0.2.2] - 2026-04-02

### Fixed
- Dodano walidację dodatnich wartości dla parametrów liczbowych używanych w generowaniu danych oraz w analizie STO.
- Zablokowano możliwość podawania wartości ujemnych lub zerowych w polach, które powinny przyjmować wyłącznie wartości dodatnie.
- Dodano komunikat walidacyjny dla nieprawidłowych danych wejściowych:
  - „Głuptasie, czemu wpisujesz ujemne rzeczy. Wpisuj dodatnie”.
- Naprawiono problem powodujący wywalanie aplikacji podczas treningu modeli w `main_page.py`.
- Naprawiono problem powodujący wywalanie aplikacji przy opcji **„Rozwiąż istniejące modele”**.
- Naprawiono obsługę wątków w `main_page.py`, tak aby komunikaty GUI były aktualizowane bezpiecznie z użyciem metod wykonywanych w głównym wątku.
- Naprawiono problem z `DecisionTree` w `visual_page`, wynikający z nieprawidłowego przygotowania figury do renderowania.
- Naprawiono błąd importu w `sto_models.py`, powodujący circular import i uniemożliwiający uruchomienie aplikacji.

### Added
- Dodano centralne parsowanie i walidację konfiguracji generowania danych w warstwie `core/services.py`.
- Dodano funkcję `generate_and_store_datasets_from_config()` do obsługi konfiguracji przekazywanej z GUI.
- Dodano bezpieczne pomocnicze metody do obsługi logów i komunikatów błędów wywoływanych z worker threadów w `main_page.py`.

### Changed
- Przeniesiono dodatkową walidację pól wejściowych z GUI do warstwy `core`, aby zachować brak logiki biznesowej w `main_page.py`.
- Uporządkowano obsługę błędów w `main_page.py`, tak aby spodziewane błędy danych były oddzielone od błędów nieoczekiwanych.
- Usprawniono przepływ generowania danych, treningu i rozwiązywania modeli z zachowaniem architektury opartej na `core/services.py`.
- Usprawniono analizę STO tak, aby błędne dane wejściowe były walidowane spójnie z resztą aplikacji.

### Improved
- Zwiększono stabilność działania głównej zakładki aplikacji.
- Poprawiono odporność aplikacji na błędy użytkownika przy wpisywaniu danych liczbowych.
- Poprawiono kompatybilność modułów analitycznych i wizualizacyjnych po rozbudowie projektu o modele STO.

## [0.2.1] - 2026-03-31

### Fixed
- Naprawiono obsługę błędów w `main_page.py`, tak aby błędy danych były odróżniane od błędów nieoczekiwanych.
- Ograniczono użycie ogólnego `except Exception as e` jako jedynej formy obsługi błędów.
- Dodano zapisywanie pełnego tracebacka do plików logów dla nieoczekiwanych wyjątków.
- Poprawiono diagnostykę problemów podczas:
  - generowania danych,
  - wczytywania plików CSV,
  - treningu modeli,
  - rozwiązywania istniejących modeli,
  - analizy modeli STO.

### Added
- Dodano nowy moduł `utils/error_utils.py`.
- Dodano funkcję zapisu błędów do plików w katalogu `logs/`.
- Dodano kontekst błędu do logów, aby łatwiej identyfikować miejsce awarii.
- Dodano katalog `logs/` do `.gitignore`.

### Changed
- Zmieniono komunikaty błędów wyświetlane użytkownikowi w `main_page.py`.
- Dla błędów spodziewanych, takich jak błędne dane wejściowe, aplikacja pokazuje teraz bardziej precyzyjne komunikaty.
- Dla błędów nieoczekiwanych aplikacja pokazuje ogólny komunikat użytkownikowi, a szczegóły zapisuje do logu.
- Usprawniono logowanie zdarzeń w zakładce głównej, tak aby użytkownik widział informację o zapisaniu szczegółów błędu do pliku.

### Improved
- Zwiększono czytelność i użyteczność komunikatów błędów.
- Ułatwiono debugowanie i dalsze rozwijanie aplikacji.
- Poprawiono odporność interfejsu GUI na trudniejsze do przewidzenia błędy wykonania.
- Poprawiono README o usunięcie z uv "py -m"

## [0.2.0] - 2026-03-30

### Added
- Dodano obsługę heurystycznych modeli STO w osobnym module `core/sto_models.py`.
- Dodano modele STO:
  - `MT` – sortowanie według terminu realizacji,
  - `MO` – sortowanie według najkrótszego czasu wykonania,
  - `MZO` – sortowanie według najdłuższego czasu wykonania,
  - `GENETIC` – model genetyczny / optymalizacyjny minimalizujący STO.
- Dodano raportowanie wyników STO, w tym:
  - kolejność zleceń dla każdego modelu,
  - wartość STO,
  - przebieg liczenia krok po kroku,
  - wskazanie najlepszego i najgorszego modelu.
- Dodano nowe testy jednostkowe dla:
  - `dataset_ops`,
  - `services`,
  - `sto_models`,
  - `visualization_service`.

### Changed
- Przebudowano `main_page.py` i rozszerzono interfejs o:
  - wybór wielu modeli ML jednocześnie,
  - konfigurację liczby rekordów,
  - konfigurację liczby maszyn,
  - konfigurację zakresu czasu produkcji,
  - konfigurację zakresu bufora terminu,
  - wybór kształtów i materiałów,
  - panel podsumowania aktualnych ustawień,
  - panel statusu danych,
  - podgląd danych w zakładce głównej,
  - sekcję analizy STO wraz z polem wynikowym.
- Zmieniono generowanie danych tak, aby użytkownik mógł samodzielnie określać parametry wejściowe.
- Zmieniono logikę terminów z `termin_dni` na `termin_h`.
- Zmieniono przygotowanie danych tak, aby `termin_h` był zawsze większy od `czas_produkcji_h`.
- Zmieniono sposób zapisu modeli:
  - modele nie są już zapisywane wyłącznie jako `model.pkl`,
  - nazwa pliku modelu zawiera wybrane modele, parametry generowania, wybrane kształty, wybrane materiały oraz znacznik czasu.
- Zaktualizowano `guide.md` o:
  - nowy sposób generowania danych,
  - opis modeli STO,
  - opis nowych parametrów treningu i zapisu modeli.
- Zaktualizowano `README.md`:
  - poprawiono instrukcję uruchamiania projektu,
  - dodano poprawny sposób uruchamiania przez `uv`,
  - uproszczono opis instalacji bez `uv`,
  - zaktualizowano strukturę repozytorium,
  - zaktualizowano opis aktualnego stanu projektu.

### Fixed
- Naprawiono układ głównej zakładki tak, aby wszystkie sekcje były dostępne i czytelne.
- Przywrócono możliwość podglądu wygenerowanych lub wczytanych danych w zakładce głównej.
- Poprawiono organizację GUI tak, aby warstwa prezentacji korzystała z gotowych funkcji z `core`, bez umieszczania tam logiki biznesowej.
- Poprawiono strukturę projektu i dokumentacji pod kątem uruchamiania bez ręcznego ustawiania `PYTHONPATH`.

### Improved
- Uporządkowano podział odpowiedzialności między `core` i `gui`.
- Rozszerzono architekturę projektu o osobny moduł dla modeli STO.
- Zwiększono elastyczność eksperymentowania z danymi, modelami i porównywaniem różnych podejść do harmonogramowania.
- Poprawiono przygotowanie projektu do dalszej rozbudowy i kolejnych wersji.

## [0.1.1] - 2026-03-23

### Fixed
- Usunięto logikę biznesową z warstwy GUI w kluczowych modułach aplikacji.
- Przeniesiono operacje generowania i zapisu danych z `gui/pages/main_page.py` do warstwy `core/services.py`.
- Przeniesiono przygotowanie danych do wizualizacji oraz budowę wykresów do `core/visualization_service.py` i modułów pomocniczych w `core/diagrams/`.
- Ograniczono rolę `visual_page.py` do pobrania parametrów od użytkownika i wyświetlenia gotowej figury.
- Przeniesiono analizę danych i przygotowanie wyników z `results_page.py` do funkcji serwisowych w warstwie `core`.
- Ograniczono `results_page.py` do zbierania wyborów użytkownika i prezentacji gotowego wyniku.
- Uporządkowano przepływ ładowania danych tak, aby GUI korzystało wyłącznie z gotowych funkcji udostępnionych przez warstwę `core`.

### Changed
- Zaktualizowano `README.md` i uporządkowano jego strukturę.
- Dodano nowy układ dokumentacji w `README.md`:
  - opis projektu,
  - aktualna struktura repozytorium,
  - instrukcja uruchomienia projektu z `uv`,
  - instrukcja uruchomienia projektu bez `uv`,
  - aktualny stan projektu,
  - plany na kolejny update.
- Doprecyzowano opis architektury projektu oraz aktualny zakres funkcjonalności.
- Uproszczono tryby treningu w GUI przez usunięcie opcji **„Oba”** z wyboru modeli w zakładce głównej.
- Zmieniono interfejs tak, aby użytkownik wybierał wyłącznie pojedynczy tryb treningu: `Quality`, `Delay` albo `Schedule`.

### Improved
- Poprawiono czytelność i spójność architektury projektu.
- Wzmocniono zgodność projektu z wymaganiem oddzielenia logiki aplikacyjnej od warstwy prezentacji.
- Ułatwiono dalszy rozwój aplikacji przez lepszy podział odpowiedzialności między `core` i `gui`.
- Uporządkowano dokumentację projektu, aby była bardziej czytelna i gotowa do prezentacji lub dalszego rozwijania.

## [0.1.0] - 2026-03-20
### Added
- Wyodrębniono warstwę core.
- Dodano moduły data_generation, features, scheduling, models, data_io.
- Dodano testy jednostkowe dla core.
- Rozdzielono GUI od logiki biznesowej.

### Fixed
- Uporządkowano przepływ generowania i podziału danych.
- Ograniczono logikę wykonywaną bezpośrednio w GUI.
