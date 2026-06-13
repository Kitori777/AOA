from __future__ import annotations

from AOA.core.assistant_service import AssistantService


def test_alice_explains_quality_model_instead_of_sto() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Jak zachowuje sie model Quality")

    assert "Model Quality" in answer
    assert "Random Forest" in answer or "Quality RF" in answer
    assert "Modele STO/heurystyczne" not in answer


def test_alice_explains_algorithm_followup() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Ale jak sam algorytm dziala?")

    assert "Random Forest" in answer
    assert "Gradient Boosting" in answer


def test_alice_knows_diagrams_and_analytics_pages() -> None:
    service = AssistantService()

    diagrams, _hits, _from_airi = service.answer("Co moge zrobic w diagrams?")
    analytics, _hits, _from_airi = service.answer("Co robi analytics?")

    assert "przeciagasz" in diagrams.lower()
    assert "eksportujesz" in diagrams.lower()
    assert "workflow" in analytics.lower()
    assert "html" in analytics.lower()


def test_alice_adds_plain_reading_guide_for_visual_questions() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Jak czytac wykres HTML w Visual?")

    assert "Jak to czytac:" in answer
    assert "Najpierw patrz na osie" in answer
    assert "Co dalej:" in answer


def test_alice_adds_plain_reading_guide_for_tree_questions() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Wytlumacz mi drzewo SolutionTree")

    assert "Jak to czytac:" in answer
    assert "Zolty element" in answer
    assert "Zielona sciezka" in answer


def test_alice_does_not_confuse_theory_ml_with_sto_methods() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer(
        "Czemu animacja w Theory pokazuje MT MO przy machine learning?"
    )

    assert "nie wolno ich mieszac" in answer
    assert "ML uczy zaleznosci" in answer
    assert "MT, MO i MZO to metody/reguly STO" in answer


def test_alice_keeps_diagrams_html_under_diagrams_context() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Jak poprawic diagram i wyeksportowac HTML?")

    assert "Diagrams to interaktywny panel" in answer
    assert "Auto layout" in answer
    assert "Przejdz do Diagrams" in answer
    assert "Przejdz do Visual" not in answer


def test_alice_explains_smart_diagrams_from_description() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Jak zrobic diagram z opisu?")

    assert "Z opisu" in answer
    assert "dobierze szablon" in answer
    assert "Auto layout" in answer


def test_alice_casual_prompt_does_not_dump_code_signatures() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("powiedz cos")

    assert "Jestem ALICE" in answer
    assert "klasy:" not in answer.lower()
    assert "metody:" not in answer.lower()
    assert "WorkflowResult" not in answer


def test_alice_introduces_herself_with_app_guidance() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Opowiedz o sobie")

    assert "Jestem ALICE" in answer
    assert "Main" in answer
    assert "Visual" in answer
    assert "Theory" in answer
    assert "Nie mam do tego" not in answer


def test_alice_explains_project_overview_for_casual_question() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("siemka opowiedz cos o projekcie")

    assert "AOA" in answer
    assert "Main" in answer
    assert "Report" in answer
    assert "Theory" in answer
    assert "Nie mam do tego" not in answer


def test_alice_lists_capability_categories_for_short_question() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Co umiesz")

    assert "Tryb terminalowy ALICE" in answer
    assert "Pliki i porzadek" in answer
    assert "Release i QA" in answer
    assert "Production Optimization" not in answer


def test_alice_explains_file_cleanup_category() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("co mozesz zrobic z plikami")

    assert "menedzer plikow" in answer.lower()
    assert "podglad" in answer.lower()
    assert "Usunac" in answer


def test_alice_explains_history_samples_and_tutorials_category() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer(
        "co mozesz zrobic z historia treningow, porownaniem modeli i tutorialami"
    )

    assert "Historia, sample, porownania" in answer
    assert "porownaj modele" in answer
    assert "wczytaj sample do Main" in answer
    assert "instrukcja krok po kroku" in answer


def test_alice_reviews_diagram_report_chart_and_model() -> None:
    service = AssistantService()

    diagram, _hits, _from_airi = service.answer("ocen diagram czy jest git")
    report, _hits, _from_airi = service.answer("sprawdz raport przed eksportem pdf")
    chart, _hits, _from_airi = service.answer("ocen wykres html")
    model, _hits, _from_airi = service.answer("ocen model tabpfn po treningu")

    assert "Cel" in diagram
    assert "Start i koniec" in diagram
    assert "Minimalny dobry raport AOA" in report
    assert "Ryzyka" in report
    assert "Osie" in chart
    assert "Interakcja HTML" in chart
    assert "Typ zadania" in model
    assert "Baseline" in model


def test_alice_final_coverage_answers_core_areas() -> None:
    service = AssistantService()
    prompts = [
        "co umiesz",
        "co mozesz w Main",
        "co mozesz w Visual",
        "co mozesz w Results",
        "co mozesz w Report",
        "co mozesz w diagramach",
        "co mozesz w Theory",
        "co mozesz z plikami",
        "release check",
        "co mozesz z historia treningow i sample",
        "audyt workflow",
    ]

    for prompt in prompts:
        answer, _hits, _from_airi = service.answer(prompt)
        assert "Nie mam do tego" not in answer
        assert len(answer) > 80


def test_alice_explains_development_segments_templates_and_data_contract() -> None:
    service = AssistantService()

    segments, _hits, _from_airi = service.answer("jakie kolejne segmenty rozwoju mamy")
    templates, _hits, _from_airi = service.answer("jakie sa szablony raportow")
    contract, _hits, _from_airi = service.answer("pokaz kontrakt danych i wymagane kolumny")

    assert "ALICE Reviewer" in segments
    assert "Scenario Lab" in segments
    assert "Model Registry UI" in segments
    assert "ml_validation" in templates
    assert "release_check" in templates
    assert "czas_h" in contract
    assert "NaN/inf" in contract


def test_alice_small_talk_does_not_trigger_explainer_prefix() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Czesc, jak sie masz?")

    assert "Mam sie dobrze" in answer
    assert not answer.startswith("Jasne, tlumacze")


def test_alice_explains_main_as_user_workflow() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Powiedz co robi sie w MAIN")

    assert "Main to miejsce startowe" in answer
    assert "Wczytaj plik" in answer
    assert "Visual" in answer


def test_alice_brain_explains_solution_tree_drawing() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Jak rysuje SolutionTree i czemu jest zolty kolor?")

    assert "SolutionTree pokazuje warianty" in answer
    assert "Zielony" in answer
    assert "Zolty" in answer
    assert "Schowaj wybrana galaz" in answer


def test_alice_brain_explains_chart_libraries() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Jakie biblioteki wykresow obsluguje aplikacja?")

    assert "Matplotlib" in answer
    assert "Seaborn" in answer
    assert "Plotly" in answer
    assert "NetworkX" in answer


def test_alice_brain_knows_release_quality_checks() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Co sprawdzic przed wersja na githuba?")

    assert "GitHuba" in answer
    assert "pelne testy" in answer.lower()
    assert "HTML" in answer


def test_alice_explains_custom_sklearn_algorithms_and_parameters() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer(
        "Co to jest SVM i co znacza komendy sklearn.svm.SVR oraz parametry JSON?"
    )

    assert "SVR/SVM" in answer
    assert "sklearn.svm.SVR" in answer
    assert "parametry" in answer.lower()
    assert "n_estimators" in answer


def test_alice_explains_operator_mode_actions() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Co mozesz stworzyc i przetestowac w trybie operatora?")

    assert "trybie operatora" in answer
    assert "przetestuj raport" in answer
    assert "stworz raport" in answer
    assert "stworz raport ML" in answer
    assert "eksportuj notebook" in answer
    assert "stworz diagram produkcji" in answer
    assert "stworz diagram danych" in answer
    assert "pokaz XGBoost" in answer
    assert "pokaz MLP" in answer
    assert "pokaz braki danych" in answer
    assert "lekcja ML" in answer
    assert "przetestuj Main" in answer


def test_alice_handles_small_talk_without_random_model_dump() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Czesc, jak sie masz?")

    assert "Mam sie dobrze" in answer
    assert "zrob mi wykres" in answer
    assert "MT / EDD" not in answer
    assert "MZO" not in answer


def test_alice_lists_terminal_functions() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("wypisz jakie masz funkcje")

    assert "Tryb terminalowy ALICE" in answer
    assert "Kategorie komend" in answer
    assert "Dane i modele" in answer
    assert "Wykresy i Visual" in answer
    assert "Results i SQL" in answer
    assert "Raporty" in answer
    assert "Diagramy" in answer
    assert "Theory i lekcje" in answer
    assert "co mozesz w diagramach" in answer
    assert "Nie mam do tego" not in answer


def test_alice_lists_diagram_category_details() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("co mozesz zrobic w diagramach?")

    assert "Diagramy - co moge zrobic" in answer
    assert "BPMN" in answer
    assert "UML" in answer
    assert "ERD" in answer
    assert "MLOps" in answer
    assert "stworz diagram BPMN" in answer
    assert "diagram magazynu" in answer


def test_alice_lists_report_category_details() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("jakie komendy masz do raportow i pdf?")

    assert "Raporty - co moge zrobic" in answer
    assert "Report Builder" in answer
    assert "PDF" in answer
    assert "KPI" in answer
    assert "stworz raport ML" in answer
    assert "eksportuj notebook" in answer


def test_alice_lists_results_category_details() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("jakie komendy do Results, SQL i CSV?")

    assert "Results i SQL - co moge zrobic" in answer
    assert "wczytaj sample do Results" in answer
    assert "braki danych" in answer
    assert "zapytanie SQL" in answer
    assert "SQL statystyki" in answer
    assert "eksportuj wynik SQL" in answer


def test_alice_lists_visual_file_and_prompt_actions() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("co mozesz w Visual z plikami i wykresami?")

    assert "Visual - co moge zrobic" in answer
    assert "wczytaj dane do Visual" in answer
    assert "dobierz wykres" in answer
    assert "scatter z opisu" in answer
    assert "dashboard z opisu" in answer


def test_alice_lists_main_model_category_details() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("co umiesz w Main z modelami i treningiem?")

    assert "Dane i modele - co moge zrobic" in answer
    assert "wczytac sample do Main" in answer or "Wczytac sample do Main" in answer
    assert "Zaznaczyc modele" in answer
    assert "ustaw TabPFN" in answer
    assert "naucz modele" in answer
    assert "trenuj Quality" in answer
    assert "Quality/Delay to regresja" in answer
    assert "Schedule to klasyfikacja" in answer
    assert "XGBoost" in answer
    assert "dodaj wlasny model ML" in answer


def test_alice_explains_main_operator_training_commands() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("Jak mozesz wczytac dane do Main i nauczyc modele?")

    assert "wczytaj sample do Main" in answer
    assert "zaznacz Quality" in answer
    assert "ustaw TabPFN" in answer
    assert "naucz modele" in answer
    assert "trenuj TabPFN Quality" in answer


def test_alice_lists_theory_category_details() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("co mozesz w Theory i lekcjach?")

    assert "Theory i lekcje - co moge zrobic" in answer
    assert "classic ML" in answer
    assert "heurystyki STO" in answer
    assert "TabPFN" in answer
    assert "pokaz XGBoost" in answer


def test_alice_lists_navigation_category_details() -> None:
    service = AssistantService()

    answer, _hits, _from_airi = service.answer("jakie masz komendy do sterowania aplikacja?")

    assert "Sterowanie aplikacja - co moge zrobic" in answer
    assert "Przejsc do modulu" in answer
    assert "podswietlic panel" in answer.lower()
    assert "przetestuj raport" in answer
