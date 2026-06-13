from __future__ import annotations

from AOA.core.drawio_service import (
    DRAWIO_TEMPLATES,
    build_drawio_xml,
    build_html_preview,
    build_mermaid,
    build_svg,
    save_diagram,
    smart_diagram_from_description,
    template_nodes_edges,
)


def test_every_drawio_template_has_nodes() -> None:
    for template in DRAWIO_TEMPLATES:
        nodes, edges = template_nodes_edges(template)

        assert nodes, template
        node_ids = {node.id for node in nodes}
        assert all(edge.source in node_ids and edge.target in node_ids for edge in edges)


def test_drawio_exports_contain_expected_markers() -> None:
    nodes, edges = template_nodes_edges("Flowchart")

    xml = build_drawio_xml(nodes, edges)
    mermaid = build_mermaid(nodes, edges)
    svg = build_svg(nodes, edges)
    html = build_html_preview(nodes, edges)

    assert "<mxfile" in xml
    assert "mxGraphModel" in xml
    assert "Start" in xml
    assert mermaid.startswith("flowchart TD")
    assert "start" in mermaid
    assert "<svg" in svg
    assert "marker-end" in svg
    assert "<!doctype html>" in html
    assert "<svg" in html
    assert "Schowaj etykiety" in html
    assert "AOA Diagrams - interaktywny podglad HTML" in html
    assert "addEventListener('mousemove'" in html


def test_flowchart_template_has_readable_default_layout() -> None:
    nodes, edges = template_nodes_edges("Flowchart")
    by_id = {node.id: node for node in nodes}

    main_ids = ["start", "load", "check", "report", "end"]
    main_centers = [by_id[node_id].x + by_id[node_id].width / 2 for node_id in main_ids]

    assert max(main_centers) - min(main_centers) <= 4
    assert by_id["start"].label == "Start"
    assert by_id["fix"].label == "Clean data"
    assert by_id["fix"].x > by_id["check"].x + by_id["check"].width
    assert [edge.label for edge in edges if edge.source == "check"] == ["no", "yes"]


def test_save_diagram_writes_supported_formats(tmp_path) -> None:
    nodes, edges = template_nodes_edges("ERD Database")
    formats = {
        "drawio": "diagram.drawio",
        "svg": "diagram.svg",
        "mermaid": "diagram.mmd",
        "html": "diagram.html",
    }

    for fmt, filename in formats.items():
        output = save_diagram(tmp_path / filename, nodes, edges, fmt)

        assert output.exists()
        assert output.read_text(encoding="utf-8").strip()


def test_smart_diagram_from_description_builds_data_pipeline() -> None:
    nodes, edges, template, note = smart_diagram_from_description(
        "CSV -> walidacja danych -> cechy X -> model ML -> metryki -> raport"
    )

    assert template == "Data Pipeline"
    assert len(nodes) == 6
    assert len(edges) == 5
    assert nodes[0].shape == "database"
    assert any(node.shape == "model" for node in nodes)
    assert edges[0].label == "sprawdz"
    assert edges[-1].label == "pokaz"
    assert "ksztalty" in note


def test_smart_diagram_from_description_builds_supply_chain() -> None:
    nodes, edges, template, _note = smart_diagram_from_description(
        "Dostawca -> magazyn -> transport -> klient"
    )

    assert template == "Supply Chain"
    assert [node.shape for node in nodes] == ["terminator", "warehouse", "truck", "process"]
    assert [edge.label for edge in edges] == ["dalej", "przekaz", "dalej"]


def test_smart_diagram_from_description_has_safe_fallback() -> None:
    nodes, edges, template, _note = smart_diagram_from_description("opis bez strzalek")

    assert template == "Flowchart"
    assert [node.label for node in nodes] == ["Start", "opis bez strzalek", "Wynik"]
    assert len(edges) == 2
