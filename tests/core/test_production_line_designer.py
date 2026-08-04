from __future__ import annotations

import pytest

from AOA.core.production_line import ProductionLineSpec, StationSpec
from AOA.core.production_line_designer import (
    PROJECT_SCHEMA_VERSION,
    LineConnection,
    ProductionLineDraft,
)


def test_designer_can_add_edit_reorder_delete_and_export_line() -> None:
    draft = ProductionLineDraft(stations=[StationSpec("cut", "Ciecie")])

    template = draft.new_station_template()
    assert template.station_id == "S2"
    draft.save_station(StationSpec("pack", "Pakowanie", 2, "2"))
    assert [station.station_id for station in draft.stations] == ["cut", "pack"]
    assert draft.selected_index == 1

    draft.save_station(StationSpec("pack", "Pakowanie premium", 3, "1.5"))
    assert draft.stations[1].resources == 3
    assert draft.move_selected(-1)
    assert [station.station_id for station in draft.stations] == ["pack", "cut"]

    removed = draft.delete_selected()
    assert removed is not None and removed.station_id == "pack"
    assert [station.station_id for station in draft.stations] == ["cut"]
    assert draft.to_spec().stations[0].station_id == "cut"


def test_designer_loads_project_and_rejects_invalid_edit_transactionally() -> None:
    draft = ProductionLineDraft(stations=[StationSpec("old", "Stare")])
    spec = ProductionLineSpec(
        "new-line",
        "Nowa linia",
        (StationSpec("s1", "Start"), StationSpec("s2", "Koniec")),
    )
    draft.load_spec(spec)

    assert draft.line_id == "new-line"
    assert [station.station_id for station in draft.stations] == ["s1", "s2"]
    draft.select(1)
    before = list(draft.stations)
    with pytest.raises(ValueError, match="unikalne"):
        draft.save_station(StationSpec("s1", "Duplikat"))
    assert draft.stations == before


def test_designer_handles_selection_boundaries_without_mutating_line() -> None:
    draft = ProductionLineDraft(stations=[StationSpec("s1", "Start")])

    assert not draft.move_selected(1)
    assert draft.delete_selected() is None
    with pytest.raises(IndexError, match="numer stanowiska"):
        draft.select(3)


def test_graph_connections_define_order_independently_from_canvas_position() -> None:
    draft = ProductionLineDraft(
        stations=[
            StationSpec("middle", "Srodek"),
            StationSpec("end", "Koniec"),
            StationSpec("start", "Start"),
        ],
        connections=[
            LineConnection("start", "middle"),
            LineConnection("middle", "end"),
        ],
        initialize_serial=False,
    )
    draft.move_station("start", 900, 500)
    draft.move_station("end", 20, 20)

    assert draft.ordered_station_ids() == ["start", "middle", "end"]
    assert [station.station_id for station in draft.to_spec().stations] == [
        "start",
        "middle",
        "end",
    ]


def test_graph_user_can_add_and_connect_station_manually() -> None:
    draft = ProductionLineDraft(stations=[StationSpec("s1", "Start")])
    draft.add_station(StationSpec("s2", "Koniec"), x=420, y=200)

    valid, message = draft.graph_status()
    assert not valid
    assert "Polacz wszystkie" in message

    draft.connect("s1", "s2")
    assert draft.graph_status() == (True, "Linia gotowa: s1 -> s2")
    assert draft.layouts["s2"].x == 420
    assert draft.layouts["s2"].y == 200


def test_graph_rejects_branch_cycle_and_self_connection() -> None:
    draft = ProductionLineDraft(
        stations=[StationSpec("a", "A"), StationSpec("b", "B"), StationSpec("c", "C")],
        connections=[],
        initialize_serial=False,
    )
    draft.connect("a", "b")

    with pytest.raises(ValueError, match="wyjsciowe"):
        draft.connect("a", "c")
    with pytest.raises(ValueError, match="cykl"):
        draft.connect("b", "a")
    with pytest.raises(ValueError, match="samo ze soba"):
        draft.connect("c", "c")


def test_graph_rename_and_delete_preserve_consistent_layout_and_edges() -> None:
    draft = ProductionLineDraft(
        stations=[StationSpec("a", "A"), StationSpec("b", "B")],
    )
    draft.select_by_id("b")
    draft.update_selected_station(StationSpec("finish", "Koniec", 2, "1"))

    assert "b" not in draft.layouts
    assert "finish" in draft.layouts
    assert draft.connections == [LineConnection("a", "finish")]

    draft.delete_selected()
    assert draft.connections == []
    assert "finish" not in draft.layouts


def test_graph_project_round_trip_and_legacy_migration() -> None:
    draft = ProductionLineDraft()
    draft.move_station("S2", 460, 280)
    payload = draft.to_dict()
    restored = ProductionLineDraft.from_dict(payload)

    assert payload["schema_version"] == PROJECT_SCHEMA_VERSION
    assert restored.layouts["S2"].y == 280
    assert restored.connections == draft.connections
    assert restored.ordered_station_ids() == ["S1", "S2", "S3"]

    legacy = ProductionLineDraft.from_dict(
        ProductionLineSpec(
            "legacy",
            "Legacy",
            (StationSpec("one", "One"), StationSpec("two", "Two")),
        ).to_dict()
    )
    assert legacy.ordered_station_ids() == ["one", "two"]
    assert legacy.layouts["two"].x > legacy.layouts["one"].x


def test_incomplete_graph_can_be_saved_but_not_converted_for_simulation() -> None:
    draft = ProductionLineDraft(
        stations=[StationSpec("a", "A"), StationSpec("b", "B")],
        connections=[],
        initialize_serial=False,
    )

    payload = draft.to_dict()

    assert payload["connections"] == []
    with pytest.raises(ValueError, match="Polacz wszystkie"):
        draft.to_spec()


def test_invalid_new_station_save_is_transactional() -> None:
    draft = ProductionLineDraft(stations=[StationSpec("start", "Start")])
    draft.new_station_template()
    before_stations = list(draft.stations)
    before_connections = list(draft.connections)

    with pytest.raises(ValueError, match="nieznana zmienna"):
        draft.save_station(StationSpec("bad", "Bad", duration_formula="secret + 1"))

    assert draft.stations == before_stations
    assert draft.connections == before_connections
    assert draft.selected_index is None


def test_project_rejects_unsupported_future_schema() -> None:
    payload = ProductionLineDraft().to_dict()
    payload["schema_version"] = PROJECT_SCHEMA_VERSION + 1

    with pytest.raises(ValueError, match="nowszego formatu"):
        ProductionLineDraft.from_dict(payload)
