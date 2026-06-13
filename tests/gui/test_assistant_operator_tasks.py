from __future__ import annotations

from AOA.gui.assistant_panel import collect_operator_tasks


def test_collect_operator_tasks_builds_ordered_multi_step_report_plan() -> None:
    tasks = collect_operator_tasks("przetestuj raport, potem pokaz xgboost i przejdz do results")

    assert tasks == ["analytics:test", "theory:xgboost", "results:open"]


def test_collect_operator_tasks_supports_smart_diagram_and_pdf_preview() -> None:
    tasks = collect_operator_tasks("zbuduj diagram z opisu i pokaz pdf raportu")

    assert tasks == ["drawio:smart_sample", "analytics:preview_pdf"]


def test_collect_operator_tasks_deduplicates_aliases() -> None:
    tasks = collect_operator_tasks("pokaz xgboost, theory xgboost i animacja xgboost")

    assert tasks == ["theory:xgboost"]


def test_collect_operator_tasks_creates_report_and_adds_blocks() -> None:
    tasks = collect_operator_tasks("stworz raport, dodaj ml do raportu i dodaj pipeline do raportu")

    assert tasks == ["analytics:create_report", "analytics:add_ml", "analytics:add_pipeline"]


def test_collect_operator_tasks_creates_diagram_and_quick_blocks() -> None:
    tasks = collect_operator_tasks("stworz diagram produkcji, dodaj maszyne i dodaj model ml")

    assert tasks == ["drawio:create_production", "drawio:add_machine", "drawio:add_ml_model"]


def test_collect_operator_tasks_prefers_specific_ml_report() -> None:
    tasks = collect_operator_tasks("stworz raport ml, dodaj wykres do raportu i eksportuj notebook")

    assert tasks == ["analytics:create_ml_report", "analytics:add_chart", "analytics:export_notebook"]


def test_collect_operator_tasks_prefers_specific_sto_report() -> None:
    tasks = collect_operator_tasks("stworz raport sto, dodaj kpi do raportu i csv akcji")

    assert tasks == ["analytics:create_sto_report", "analytics:add_kpi", "analytics:export_actions"]


def test_collect_operator_tasks_supports_assets_and_data_diagram_builder() -> None:
    tasks = collect_operator_tasks(
        "odswiez pliki raportu, dodaj plik do raportu, otworz kreator diagramu i diagram danych"
    )

    assert tasks == [
        "analytics:refresh_assets",
        "analytics:add_asset",
        "drawio:smart_builder",
        "drawio:create_data_pipeline",
    ]


def test_collect_operator_tasks_supports_new_theory_modern_models() -> None:
    tasks = collect_operator_tasks("pokaz mlp, pokaz stacking i pokaz schedule")

    assert tasks == ["theory:mlp", "theory:stacking", "theory:schedule"]


def test_collect_operator_tasks_supports_main_visual_and_results_actions() -> None:
    tasks = collect_operator_tasks(
        "pokaz parametry danych, pokaz modele main, otworz raport d3, pokaz braki danych, eksportuj widoczne wyniki"
    )

    assert tasks == [
        "main:focus_data",
        "main:focus_models",
        "visual:open_d3",
        "results:missing_report",
        "results:export_visible",
    ]


def test_collect_operator_tasks_supports_main_data_model_and_training_actions() -> None:
    tasks = collect_operator_tasks(
        "wczytaj sample do main, zaznacz quality, ustaw tabpfn i naucz modele"
    )

    assert tasks == [
        "main:sample_data",
        "main:select_quality",
        "main:backend_tabpfn",
        "main:train",
    ]


def test_collect_operator_tasks_supports_file_manager_and_release_checks() -> None:
    tasks = collect_operator_tasks("otworz pliki, release check i qa html")

    assert tasks == ["files:open", "app:release_check", "app:html_qa"]


def test_collect_operator_tasks_supports_history_compare_tutorials_and_samples() -> None:
    tasks = collect_operator_tasks(
        "historia treningow, porownaj modele, tutoriale krok po kroku i pokaz sample"
    )

    assert tasks == ["app:history", "app:model_compare", "app:tutorials", "app:samples"]


def test_collect_operator_tasks_supports_release_segments_templates_and_contract() -> None:
    tasks = collect_operator_tasks(
        "pokaz kolejne segmenty rozwoju, szablony raportow i kontrakt danych"
    )

    assert tasks == ["app:segments", "app:report_templates", "app:data_contract"]


def test_collect_operator_tasks_supports_quality_review_commands() -> None:
    tasks = collect_operator_tasks("ocen diagram, sprawdz raport, ocen model i audyt workflow")

    assert tasks == ["app:quality_review"]


def test_collect_operator_tasks_supports_main_bulk_model_selection() -> None:
    tasks = collect_operator_tasks("odznacz modele, zaznacz wszystkie ml i zaznacz podstawowe sto")

    assert tasks == [
        "main:clear_models",
        "main:select_all_ml",
        "main:select_basic_sto",
    ]


def test_collect_operator_tasks_prefers_specific_training_command() -> None:
    tasks = collect_operator_tasks("trenuj tabpfn quality i uruchom trening")

    assert tasks == ["main:backend_tabpfn", "main:train_tabpfn_quality"]


def test_collect_operator_tasks_supports_visual_file_and_prompt_actions() -> None:
    tasks = collect_operator_tasks(
        "wczytaj dane do visual, dobierz wykres, scatter z opisu, histogram z opisu, dashboard z opisu"
    )

    assert tasks == [
        "visual:load_file",
        "visual:auto_chart",
        "visual:prompt_scatter",
        "visual:prompt_histogram",
        "visual:prompt_dashboard",
    ]


def test_collect_operator_tasks_prefers_visual_load_over_main_load() -> None:
    tasks = collect_operator_tasks("wczytaj dane z pliku do visual i wybierz wykres za mnie")

    assert tasks == ["visual:load_file", "visual:auto_chart"]


def test_collect_operator_tasks_supports_results_file_and_sql_examples() -> None:
    tasks = collect_operator_tasks(
        "wczytaj sample do results, pokaz sql przyklad, sql statystyki, sql braki i sql top"
    )

    assert tasks == [
        "results:load_sample",
        "results:sql_preview",
        "results:sql_summary",
        "results:sql_missing",
        "results:sql_top",
    ]


def test_collect_operator_tasks_supports_report_workflows_and_sql_exports() -> None:
    tasks = collect_operator_tasks(
        "uruchom wszystkie raporty, wygeneruj html analytics, pokaz builder raportu, eksportuj wynik sql"
    )

    assert tasks == [
        "analytics:run_all",
        "analytics:export_full_html",
        "analytics:focus_builder",
        "results:export_sql",
    ]


def test_collect_operator_tasks_supports_learning_paths_and_help() -> None:
    tasks = collect_operator_tasks("lekcja ml, lekcja raportow, lekcja diagramow, co powinienem kliknac, otworz pomoc")

    assert tasks == [
        "learning:ml_path",
        "learning:report_path",
        "learning:diagram_path",
        "app:guide_next",
        "app:help",
    ]


def test_collect_operator_tasks_understands_natural_chart_and_lesson_requests() -> None:
    tasks = collect_operator_tasks("zrob mi wykres i daj lekcje ml")

    assert tasks == ["visual:draw", "learning:ml_path"]


def test_collect_operator_tasks_supports_twenty_common_diagram_commands() -> None:
    prompt = (
        "stworz diagram bpmn, diagram uml, diagram erd, diagram sieci, swimlane, "
        "diagram sekwencji, org chart, mind map, diagram decyzji, kanban board, "
        "diagram magazynu, diagram qc, diagram mlops, maintenance flow, vsm, "
        "supply chain, plant layout, andon incident, diagram zapasow, diagram energii"
    )

    tasks = collect_operator_tasks(prompt)

    assert tasks == [
        "drawio:create_bpmn",
        "drawio:create_uml",
        "drawio:create_erd",
        "drawio:create_network",
        "drawio:create_swimlane",
        "drawio:create_sequence",
        "drawio:create_org",
        "drawio:create_mindmap",
        "drawio:create_decision",
        "drawio:create_kanban",
        "drawio:create_warehouse",
        "drawio:create_quality",
        "drawio:create_ml_pipeline",
        "drawio:create_maintenance",
        "drawio:create_vsm",
        "drawio:create_supply",
        "drawio:create_plant",
        "drawio:create_andon",
        "drawio:create_inventory",
        "drawio:create_energy",
    ]
