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
