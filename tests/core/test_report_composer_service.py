from __future__ import annotations

from AOA.core.report_composer_service import (
    analysis_block,
    build_custom_report_html,
    build_custom_report_pdf,
    chart_block,
    file_block,
    kpi_block,
    latexish_to_html,
    recommendation_block,
    render_report_preview_text,
)


def test_latexish_to_html_renders_sections_lists_and_markup() -> None:
    source = "\n".join(
        [
            r"\title{Test}",
            r"\section{Wyniki}",
            r"\textbf{Mocny} wniosek.",
            r"\begin{itemize}",
            r"\item Pierwszy punkt",
            r"\item Drugi punkt",
            r"\end{itemize}",
        ]
    )

    html = latexish_to_html(source)

    assert "<h2 id='wyniki'>Wyniki</h2>" in html
    assert "<strong>Mocny</strong>" in html
    assert "<li>Pierwszy punkt</li>" in html


def test_latexish_to_html_renders_math_and_quarto_helpers() -> None:
    source = "\n".join(
        [
            r"\section{Metryki}",
            r"Wzor inline: $STO = \sum max(0, C_j - d_j)$",
            r"\equation{RMSE = sqrt(mean((y - yhat)^2))}",
            r"$$ MAE = mean(abs(y - yhat)) $$",
            r"::: {.callout-tip} To jest najwazniejszy wniosek.",
            r"> Zalozenie do interpretacji.",
        ]
    )

    html = latexish_to_html(source)

    assert "math-inline" in html
    assert "<div class='math'>RMSE" in html
    assert "<div class='math'>MAE" in html
    assert "callout-tip" in html
    assert "<blockquote>Zalozenie do interpretacji.</blockquote>" in html


def test_latexish_to_html_renders_overleaf_helpers() -> None:
    source = "\n".join(
        [
            r"\title{Raport}",
            r"\maketitle",
            r"\tableofcontents",
            r"\section{Cel}",
            r"\label{sec:cel}",
            r"Uzyj \code{fit()} i zobacz \ref{sec:cel}.",
            r"- [x] Dane wczytane",
            r"- [ ] Wnioski sprawdzone",
            r"\includegraphics{chart.png}",
            r"\caption{Wykres kontrolny}",
            r"\pagebreak",
            r"\url{https://example.com}",
            r"Przypis \footnote{zrodlo danych}.",
        ]
    )

    html = latexish_to_html(source)

    assert "title-card" in html
    assert "Spis tresci" in html
    assert "id='cel'" in html
    assert "<code>fit()</code>" in html
    assert "class='checklist'" in html
    assert "checked" in html
    assert "class='caption'>Wykres kontrolny" in html
    assert "page-break" in html
    assert "https://example.com" in html
    assert "footnote" in html


def test_build_custom_report_html_embeds_visual_references(tmp_path) -> None:
    image = tmp_path / "chart.svg"
    image.write_text("<svg></svg>", encoding="utf-8")
    source = "\n".join(
        [r"\title{Raport}", r"\section{Wizualizacja}", rf"\includegraphics{{{image}}}"]
    )

    html = build_custom_report_html(source, "Raport")

    assert "AOA Report Builder" in html
    assert "chart.svg" in html
    assert "<img" in html


def test_build_custom_report_pdf_writes_pdf(tmp_path) -> None:
    source = "\n".join([r"\title{Raport PDF}", r"\section{Wyniki}", "Najwazniejszy wniosek."])
    path = build_custom_report_pdf(source, tmp_path / "raport.pdf", title="Raport PDF")

    content = path.read_bytes()

    assert content.startswith(b"%PDF-")
    assert b"%%EOF" in content


def test_file_block_turns_csv_into_report_table(tmp_path) -> None:
    table = tmp_path / "wyniki.csv"
    table.write_text("model,score\nQuality,0.8\nDelay,0.6\n", encoding="utf-8")

    block = file_block(table)

    assert r"\section{Tabela z pliku: wyniki.csv}" in block
    assert "| model | score |" in block
    assert "| Quality | 0.8 |" in block


def test_analysis_block_contains_recommended_chart() -> None:
    block = analysis_block("Raport", "Tresc", "Dashboard")

    assert r"\section{Raport}" in block
    assert "Rekomendowany wykres: Dashboard" in block


def test_report_builder_blocks_and_preview_text() -> None:
    source = "\n".join(
        [
            kpi_block("cena", "123", "rosnie"),
            chart_block("Wykres ceny", "Line"),
            recommendation_block(),
        ]
    )

    preview = render_report_preview_text(source)

    assert "## KPI" in preview
    assert "Metryka:" in preview
    assert "## Wykres ceny" in preview
    assert "Rekomendacje" in preview
