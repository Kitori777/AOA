from __future__ import annotations

from AOA.gui.assistant_panel import AOAAssistantPanel


def test_prepare_spoken_text_summarizes_auto_report() -> None:
    text = (
        "AUTO MELDUNEK:\n"
        "Auto-raport 20260604_164834: etap=internet_learning, najlepszy=Quality_ET (-0.5437) "
        "| net: reached=5/5, fallback=0 | STO best=GENETIC (80.0)\n"
        "Brak istotnych zmian od poprzedniego cyklu."
    )

    speech = AOAAssistantPanel._prepare_spoken_text(text)

    assert "Mam nowy raport samonauki" in speech
    assert "Quality_ET" in speech
    assert len(speech) < 240


def test_prepare_spoken_text_cleans_markup_and_limits_length() -> None:
    text = "# Raport\n- Punkt pierwszy\n- Punkt drugi\nhttps://example.com " + ("tekst " * 200)

    speech = AOAAssistantPanel._prepare_spoken_text(text, max_chars=180)

    assert "https://" not in speech
    assert "#" not in speech
    assert "Pelny tekst masz w oknie rozmowy" in speech


def test_prepare_spoken_text_reads_explanation_and_short_steps() -> None:
    text = (
        "Jasne, tlumacze po ludzku.\n\n"
        "Wykres pokazuje zaleznosc ceny od odpadu.\n\n"
        "Jak to czytac:\n"
        "- Najpierw patrz na osie.\n"
        "- Kolor pokazuje termin.\n"
        "- Odstajace punkty sprawdz w Results.\n\n"
        "Co dalej:\n"
        "- Przejdz do Visual.\n"
        "- Otworz HTML.\n"
        "- Zapisz raport."
    )

    speech = AOAAssistantPanel._prepare_spoken_text(text, max_chars=420)

    assert "Jak to czytac" in speech
    assert "Najwazniejsze kroki" in speech
    assert "Zapisz raport" not in speech
    assert "ha te em el" in speech


def test_prepare_spoken_text_pronounces_workflow_naturally() -> None:
    text = "Uruchom workflow Analytics. Klasy: WorkflowResult, WorkflowPipeline; metody: __init__, run."

    speech = AOAAssistantPanel._prepare_spoken_text(text)

    assert "łork floł" in speech
    assert "WorkflowResult" not in speech
    assert "__init__" not in speech
