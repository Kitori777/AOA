from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

DRAWIO_TEMPLATES = [
    "Blank",
    "Flowchart",
    "UML Class",
    "ERD Database",
    "BPMN Process",
    "Network Diagram",
    "Mind Map",
    "Org Chart",
    "Swimlane",
    "Sequence Diagram",
    "Data Pipeline",
    "System Architecture",
    "Decision Tree",
    "Kanban Board",
    "Production Line",
    "Warehouse Flow",
    "Quality Control",
    "ML Production Pipeline",
    "Logistics Route",
    "Maintenance Flow",
    "Value Stream Map",
    "Supply Chain",
    "Plant Layout",
    "Andon Incident",
    "Energy Media Flow",
    "Inventory Replenishment",
]

DRAWIO_SHAPES = [
    "rectangle",
    "rounded",
    "ellipse",
    "diamond",
    "hexagon",
    "parallelogram",
    "cylinder",
    "cloud",
    "document",
    "note",
    "actor",
    "database",
    "queue",
    "process",
    "decision",
    "terminator",
    "swimlane",
    "container",
    "machine",
    "warehouse",
    "conveyor",
    "inspection",
    "sensor",
    "robot",
    "truck",
    "buffer",
    "kpi",
    "risk",
    "model",
    "operator",
    "supplier",
    "customer",
    "station",
    "kanban",
    "pallet",
    "plc",
    "andon",
    "energy",
]


@dataclass
class DiagramNode:
    id: str
    label: str
    shape: str = "rounded"
    x: int = 80
    y: int = 80
    width: int = 160
    height: int = 72
    fill: str = "#ffffff"
    stroke: str = "#111827"


@dataclass
class DiagramEdge:
    source: str
    target: str
    label: str = ""


def template_nodes_edges(template: str) -> tuple[list[DiagramNode], list[DiagramEdge]]:
    if template == "Flowchart":
        nodes = [
            DiagramNode("start", "Start", "terminator", 120, 50, 160, 58, "#dcfce7"),
            DiagramNode("load", "Load data", "process", 100, 140, 200, 72),
            DiagramNode("check", "Quality OK?", "decision", 118, 250, 164, 92, "#fef9c3"),
            DiagramNode("fix", "Clean data", "process", 410, 258, 200, 72, "#fef9c3"),
            DiagramNode("report", "Build report", "process", 100, 390, 200, 72),
            DiagramNode("end", "End", "terminator", 120, 500, 160, 58, "#dbeafe"),
        ]
        edges = [
            DiagramEdge("start", "load"),
            DiagramEdge("load", "check"),
            DiagramEdge("check", "fix", "no"),
            DiagramEdge("fix", "load"),
            DiagramEdge("check", "report", "yes"),
            DiagramEdge("report", "end"),
        ]
        return nodes, edges
    if template == "UML Class":
        nodes = [
            DiagramNode(
                "user", "User|id\\nname\\nemail|login()\\nlogout()", "rectangle", 80, 80, 210, 130
            ),
            DiagramNode(
                "report",
                "Report|title\\ncreated_at|render()\\nexport()",
                "rectangle",
                380,
                80,
                230,
                130,
            ),
            DiagramNode(
                "dataset",
                "Dataset|rows\\ncolumns|profile()\\nfilter()",
                "rectangle",
                230,
                300,
                240,
                130,
            ),
        ]
        return nodes, [
            DiagramEdge("user", "report", "creates"),
            DiagramEdge("report", "dataset", "uses"),
        ]
    if template == "ERD Database":
        nodes = [
            DiagramNode(
                "orders", "orders\\nPK id\\ncustomer_id\\ncreated_at", "database", 80, 90, 210, 120
            ),
            DiagramNode(
                "customers", "customers\\nPK id\\nname\\nsegment", "database", 390, 90, 210, 120
            ),
            DiagramNode(
                "items", "order_items\\nPK id\\norder_id\\nprice", "database", 235, 310, 230, 120
            ),
        ]
        return nodes, [
            DiagramEdge("customers", "orders", "1:N"),
            DiagramEdge("orders", "items", "1:N"),
        ]
    if template == "BPMN Process":
        nodes = [
            DiagramNode("event", "Event", "ellipse", 80, 170, 90, 70, "#dcfce7"),
            DiagramNode("task1", "Task", "rounded", 230, 160),
            DiagramNode("gate", "Gateway", "diamond", 440, 150, 110, 110, "#fef9c3"),
            DiagramNode("task2", "Approve", "rounded", 620, 90),
            DiagramNode("task3", "Reject", "rounded", 620, 250),
        ]
        return nodes, [
            DiagramEdge("event", "task1"),
            DiagramEdge("task1", "gate"),
            DiagramEdge("gate", "task2", "ok"),
            DiagramEdge("gate", "task3", "no"),
        ]
    if template == "Network Diagram":
        nodes = [
            DiagramNode("internet", "Internet", "cloud", 80, 180, 150, 90, "#dbeafe"),
            DiagramNode("fw", "Firewall", "hexagon", 300, 180, 140, 80, "#fee2e2"),
            DiagramNode("api", "API", "rounded", 520, 90),
            DiagramNode("db", "Database", "database", 520, 290),
        ]
        return nodes, [
            DiagramEdge("internet", "fw"),
            DiagramEdge("fw", "api"),
            DiagramEdge("api", "db"),
        ]
    if template == "Mind Map":
        nodes = [DiagramNode("center", "Main idea", "ellipse", 330, 240, 180, 90, "#dbeafe")]
        nodes += [
            DiagramNode("a", "Topic A", "rounded", 90, 90),
            DiagramNode("b", "Topic B", "rounded", 600, 90),
            DiagramNode("c", "Topic C", "rounded", 90, 420),
            DiagramNode("d", "Topic D", "rounded", 600, 420),
        ]
        return nodes, [DiagramEdge("center", node.id) for node in nodes if node.id != "center"]
    if template == "Org Chart":
        nodes = [
            DiagramNode("ceo", "CEO", "rounded", 330, 60, 170, 70, "#dbeafe"),
            DiagramNode("ops", "Operations", "rounded", 110, 210),
            DiagramNode("data", "Data", "rounded", 330, 210),
            DiagramNode("sales", "Sales", "rounded", 550, 210),
        ]
        return nodes, [
            DiagramEdge("ceo", "ops"),
            DiagramEdge("ceo", "data"),
            DiagramEdge("ceo", "sales"),
        ]
    if template == "Swimlane":
        nodes = [
            DiagramNode("lane1", "User", "swimlane", 40, 60, 780, 140, "#f8fafc"),
            DiagramNode("lane2", "System", "swimlane", 40, 220, 780, 140, "#f8fafc"),
            DiagramNode("lane3", "Data", "swimlane", 40, 380, 780, 140, "#f8fafc"),
            DiagramNode("request", "Request", "process", 180, 95),
            DiagramNode("validate", "Validate", "process", 360, 255),
            DiagramNode("save", "Save", "database", 560, 415),
        ]
        return nodes, [DiagramEdge("request", "validate"), DiagramEdge("validate", "save")]
    if template == "Sequence Diagram":
        nodes = [
            DiagramNode("user", "User", "actor", 80, 80, 100, 120),
            DiagramNode("app", "App", "rectangle", 300, 80, 130, 70),
            DiagramNode("api", "API", "rectangle", 520, 80, 130, 70),
            DiagramNode("db", "DB", "database", 730, 80, 120, 80),
        ]
        return nodes, [
            DiagramEdge("user", "app", "click"),
            DiagramEdge("app", "api", "request"),
            DiagramEdge("api", "db", "query"),
        ]
    if template == "Data Pipeline":
        nodes = [
            DiagramNode("source", "Source", "database", 60, 200),
            DiagramNode("extract", "Extract", "process", 260, 200),
            DiagramNode("clean", "Clean", "process", 460, 200),
            DiagramNode("model", "Model", "hexagon", 660, 200),
            DiagramNode("report", "Report", "document", 860, 200),
        ]
        return nodes, [
            DiagramEdge("source", "extract"),
            DiagramEdge("extract", "clean"),
            DiagramEdge("clean", "model"),
            DiagramEdge("model", "report"),
        ]
    if template == "System Architecture":
        nodes = [
            DiagramNode("ui", "Desktop UI", "container", 80, 90, 210, 110),
            DiagramNode("core", "Core services", "container", 380, 90, 230, 110),
            DiagramNode("files", "Files / CSV", "database", 700, 90, 180, 100),
            DiagramNode("html", "HTML reports", "document", 380, 300, 230, 110),
        ]
        return nodes, [
            DiagramEdge("ui", "core"),
            DiagramEdge("core", "files"),
            DiagramEdge("core", "html"),
            DiagramEdge("ui", "html"),
        ]
    if template == "Decision Tree":
        nodes = [
            DiagramNode("b1", "B1\\nStart", "rectangle", 360, 60, 180, 90, "#f0fdf4", "#16a34a"),
            DiagramNode("b2", "B2\\nOption z1", "rectangle", 160, 240),
            DiagramNode("b3", "B3\\nOption z2", "rectangle", 560, 240),
            DiagramNode("b4", "B4\\nBest", "rectangle", 160, 430, 180, 90, "#f0fdf4", "#16a34a"),
        ]
        return nodes, [
            DiagramEdge("b1", "b2", "z1"),
            DiagramEdge("b1", "b3", "z2"),
            DiagramEdge("b2", "b4", "z4"),
        ]
    if template == "Kanban Board":
        nodes = [
            DiagramNode("todo", "To do", "container", 50, 70, 230, 420, "#f8fafc"),
            DiagramNode("doing", "Doing", "container", 330, 70, 230, 420, "#f8fafc"),
            DiagramNode("done", "Done", "container", 610, 70, 230, 420, "#f8fafc"),
            DiagramNode("card1", "Task A", "note", 80, 140),
            DiagramNode("card2", "Task B", "note", 360, 140),
            DiagramNode("card3", "Task C", "note", 640, 140),
        ]
        return nodes, []
    if template == "Production Line":
        nodes = [
            DiagramNode("raw", "Surowiec\nwejscie", "warehouse", 60, 200, 170, 90, "#f8fafc"),
            DiagramNode("m1", "Maszyna 1\nciecie", "machine", 290, 190, 170, 110, "#dbeafe", "#2563eb"),
            DiagramNode("buffer", "Bufor WIP\nkolejka", "buffer", 520, 205, 150, 80, "#fef9c3", "#ca8a04"),
            DiagramNode("m2", "Maszyna 2\nmontaz", "machine", 730, 190, 170, 110, "#dbeafe", "#2563eb"),
            DiagramNode("qc", "Kontrola\njakosci", "inspection", 960, 190, 170, 110, "#dcfce7", "#16a34a"),
            DiagramNode("out", "Wyrob gotowy", "warehouse", 1190, 200, 170, 90, "#f0fdf4", "#16a34a"),
        ]
        return nodes, [
            DiagramEdge("raw", "m1", "partia"),
            DiagramEdge("m1", "buffer", "WIP"),
            DiagramEdge("buffer", "m2", "kolejka"),
            DiagramEdge("m2", "qc", "test"),
            DiagramEdge("qc", "out", "OK"),
        ]
    if template == "Warehouse Flow":
        nodes = [
            DiagramNode("inbound", "Przyjecie\npalet", "truck", 70, 170, 170, 100, "#dbeafe"),
            DiagramNode("scan", "Skan / WMS", "sensor", 300, 170, 160, 90, "#ede9fe", "#7c3aed"),
            DiagramNode("stock", "Magazyn\nlokacje", "warehouse", 530, 150, 190, 130, "#f8fafc"),
            DiagramNode("pick", "Picking", "operator", 790, 170, 160, 90, "#dcfce7"),
            DiagramNode("pack", "Pakowanie", "process", 1010, 170, 160, 90, "#fef9c3"),
            DiagramNode("ship", "Wysylka", "truck", 1230, 170, 170, 100, "#dcfce7", "#16a34a"),
        ]
        return nodes, [
            DiagramEdge("inbound", "scan"),
            DiagramEdge("scan", "stock"),
            DiagramEdge("stock", "pick"),
            DiagramEdge("pick", "pack"),
            DiagramEdge("pack", "ship"),
        ]
    if template == "Quality Control":
        nodes = [
            DiagramNode("sample", "Probka\nz produkcji", "document", 70, 170, 170, 90, "#f8fafc"),
            DiagramNode("measure", "Pomiar\nczujniki", "sensor", 310, 160, 170, 110, "#dbeafe"),
            DiagramNode("rules", "Czy OK?", "decision", 560, 150, 150, 130, "#fef9c3", "#ca8a04"),
            DiagramNode("rework", "Poprawka /\nrework", "risk", 790, 70, 180, 90, "#fee2e2", "#dc2626"),
            DiagramNode("release", "Zwolnij\npartie", "inspection", 790, 280, 180, 90, "#dcfce7", "#16a34a"),
            DiagramNode("report", "Raport QC", "document", 1040, 185, 170, 90, "#ede9fe", "#7c3aed"),
        ]
        return nodes, [
            DiagramEdge("sample", "measure"),
            DiagramEdge("measure", "rules"),
            DiagramEdge("rules", "rework", "NOK"),
            DiagramEdge("rework", "measure", "ponownie"),
            DiagramEdge("rules", "release", "OK"),
            DiagramEdge("release", "report"),
        ]
    if template == "ML Production Pipeline":
        nodes = [
            DiagramNode("data", "Dane CSV\nprodukcja", "database", 70, 190, 170, 100, "#f8fafc"),
            DiagramNode("features", "Cechy X\nczyszczenie", "process", 300, 190, 170, 90, "#dbeafe"),
            DiagramNode("train", "Trening ML\nfit(X,y)", "model", 530, 170, 190, 130, "#ede9fe", "#7c3aed"),
            DiagramNode("metrics", "Metryki\nRMSE/MAE/R2", "kpi", 790, 190, 180, 90, "#fef9c3", "#ca8a04"),
            DiagramNode("predict", "Predykcja\nnowe dane", "model", 1040, 170, 190, 130, "#dcfce7", "#16a34a"),
        ]
        return nodes, [
            DiagramEdge("data", "features"),
            DiagramEdge("features", "train"),
            DiagramEdge("train", "metrics"),
            DiagramEdge("metrics", "predict", "zaakceptuj"),
        ]
    if template == "Logistics Route":
        nodes = [
            DiagramNode("depot", "Depot", "warehouse", 80, 220, 160, 90, "#dbeafe"),
            DiagramNode("route", "Optymalizacja\ntrasy", "model", 330, 195, 190, 130, "#ede9fe", "#7c3aed"),
            DiagramNode("truck1", "Pojazd A", "truck", 610, 90, 170, 90, "#dcfce7"),
            DiagramNode("truck2", "Pojazd B", "truck", 610, 310, 170, 90, "#fef9c3"),
            DiagramNode("customer", "Klient /\npunkt dostawy", "operator", 890, 205, 180, 110, "#f8fafc"),
        ]
        return nodes, [
            DiagramEdge("depot", "route"),
            DiagramEdge("route", "truck1", "trasa 1"),
            DiagramEdge("route", "truck2", "trasa 2"),
            DiagramEdge("truck1", "customer"),
            DiagramEdge("truck2", "customer"),
        ]
    if template == "Maintenance Flow":
        nodes = [
            DiagramNode("sensor", "Alarm\nczujnika", "sensor", 80, 180, 160, 90, "#fee2e2", "#dc2626"),
            DiagramNode("triage", "Ocena\nryzyka", "risk", 310, 165, 170, 120, "#fef9c3", "#ca8a04"),
            DiagramNode("work", "Zlecenie\nutrzymania", "document", 560, 180, 180, 90, "#f8fafc"),
            DiagramNode("team", "Technik /\noperator", "operator", 820, 170, 170, 110, "#dbeafe"),
            DiagramNode("done", "Maszyna\nsprawna", "machine", 1080, 170, 180, 110, "#dcfce7", "#16a34a"),
        ]
        return nodes, [
            DiagramEdge("sensor", "triage"),
            DiagramEdge("triage", "work"),
            DiagramEdge("work", "team"),
            DiagramEdge("team", "done"),
        ]
    if template == "Value Stream Map":
        nodes = [
            DiagramNode("supplier", "Dostawca", "supplier", 60, 190, 160, 90, "#f8fafc"),
            DiagramNode("stock_in", "Zapas wej.\n2 dni", "buffer", 270, 200, 150, 76, "#fef9c3", "#ca8a04"),
            DiagramNode("cut", "Proces 1\nciecie\nCT 4 min", "station", 480, 180, 180, 110, "#dbeafe", "#2563eb"),
            DiagramNode("wip", "WIP\n18 szt.", "kanban", 720, 200, 150, 76, "#ffedd5", "#ea580c"),
            DiagramNode("assembly", "Proces 2\nmontaz\nCT 7 min", "station", 930, 180, 180, 110, "#dbeafe", "#2563eb"),
            DiagramNode("customer", "Klient", "customer", 1180, 190, 160, 90, "#dcfce7", "#16a34a"),
            DiagramNode("info", "Plan / MRP\nzamowienia", "document", 510, 40, 300, 80, "#ede9fe", "#7c3aed"),
        ]
        return nodes, [
            DiagramEdge("supplier", "stock_in", "dostawy"),
            DiagramEdge("stock_in", "cut"),
            DiagramEdge("cut", "wip", "partie"),
            DiagramEdge("wip", "assembly"),
            DiagramEdge("assembly", "customer", "wysylka"),
            DiagramEdge("customer", "info", "popyt"),
            DiagramEdge("info", "supplier", "plan"),
        ]
    if template == "Supply Chain":
        nodes = [
            DiagramNode("supplier", "Supplier\nmaterial", "supplier", 60, 180, 170, 100, "#f8fafc"),
            DiagramNode("inbound", "Inbound\ntransport", "truck", 300, 180, 170, 90, "#dbeafe"),
            DiagramNode("plant", "Plant\nprodukcja", "machine", 540, 165, 190, 120, "#dbeafe", "#2563eb"),
            DiagramNode("warehouse", "DC / magazyn", "warehouse", 800, 175, 190, 100, "#fef9c3", "#ca8a04"),
            DiagramNode("retail", "Klient / sklep", "customer", 1060, 180, 180, 100, "#dcfce7", "#16a34a"),
            DiagramNode("risk", "Ryzyko\nlead time", "risk", 545, 340, 180, 90, "#fee2e2", "#dc2626"),
        ]
        return nodes, [
            DiagramEdge("supplier", "inbound"),
            DiagramEdge("inbound", "plant"),
            DiagramEdge("plant", "warehouse"),
            DiagramEdge("warehouse", "retail"),
            DiagramEdge("risk", "plant", "alert"),
        ]
    if template == "Plant Layout":
        nodes = [
            DiagramNode("zone_a", "Strefa A\nciecie", "container", 70, 90, 260, 170, "#dbeafe", "#2563eb"),
            DiagramNode("zone_b", "Strefa B\nmontaz", "container", 410, 90, 260, 170, "#dcfce7", "#16a34a"),
            DiagramNode("zone_c", "Strefa C\npakowanie", "container", 750, 90, 260, 170, "#fef9c3", "#ca8a04"),
            DiagramNode("dock", "Dok / wysylka", "truck", 1090, 120, 180, 110, "#ffedd5", "#ea580c"),
            DiagramNode("forklift", "Transport\nwewn.", "truck", 410, 340, 190, 90, "#ede9fe", "#7c3aed"),
            DiagramNode("qc", "QC", "inspection", 750, 340, 160, 90, "#dcfce7", "#16a34a"),
        ]
        return nodes, [
            DiagramEdge("zone_a", "zone_b", "material"),
            DiagramEdge("zone_b", "zone_c", "WIP"),
            DiagramEdge("zone_c", "dock", "palety"),
            DiagramEdge("forklift", "zone_b"),
            DiagramEdge("qc", "zone_c"),
        ]
    if template == "Andon Incident":
        nodes = [
            DiagramNode("andon", "ANDON\nalarm", "andon", 80, 170, 160, 100, "#fee2e2", "#dc2626"),
            DiagramNode("stop", "Zatrzymaj\nlinie?", "decision", 310, 150, 150, 130, "#fef9c3", "#ca8a04"),
            DiagramNode("leader", "Lider\nreakcja", "operator", 560, 155, 170, 120, "#dbeafe", "#2563eb"),
            DiagramNode("cause", "Przyczyna\n5 why", "document", 810, 170, 180, 90, "#f8fafc"),
            DiagramNode("fix", "Akcja\nkorygujaca", "process", 1060, 170, 190, 90, "#dcfce7", "#16a34a"),
        ]
        return nodes, [
            DiagramEdge("andon", "stop"),
            DiagramEdge("stop", "leader", "tak"),
            DiagramEdge("leader", "cause"),
            DiagramEdge("cause", "fix"),
        ]
    if template == "Energy Media Flow":
        nodes = [
            DiagramNode("energy", "Energia\nwejscie", "energy", 70, 190, 170, 90, "#fef9c3", "#ca8a04"),
            DiagramNode("air", "Sprezone\npowietrze", "plc", 310, 90, 170, 90, "#dbeafe", "#2563eb"),
            DiagramNode("water", "Woda /\nchlodzenie", "plc", 310, 290, 170, 90, "#dbeafe", "#2563eb"),
            DiagramNode("machine", "Maszyna\nzuzycie", "machine", 590, 190, 190, 110, "#ede9fe", "#7c3aed"),
            DiagramNode("meter", "Liczniki\nkWh / m3", "sensor", 860, 190, 170, 90, "#dcfce7", "#16a34a"),
            DiagramNode("kpi", "KPI\nkoszt/szt.", "kpi", 1110, 190, 170, 90, "#fef9c3", "#ca8a04"),
        ]
        return nodes, [
            DiagramEdge("energy", "machine"),
            DiagramEdge("air", "machine"),
            DiagramEdge("water", "machine"),
            DiagramEdge("machine", "meter"),
            DiagramEdge("meter", "kpi"),
        ]
    if template == "Inventory Replenishment":
        nodes = [
            DiagramNode("demand", "Popyt\nsprzedaz", "customer", 60, 170, 170, 90, "#dcfce7", "#16a34a"),
            DiagramNode("forecast", "Prognoza\nML", "model", 300, 155, 180, 120, "#ede9fe", "#7c3aed"),
            DiagramNode("rop", "Punkt\nzamowienia", "kanban", 560, 170, 170, 90, "#fef9c3", "#ca8a04"),
            DiagramNode("po", "Zamowienie\nPO", "document", 800, 170, 170, 90, "#f8fafc"),
            DiagramNode("supplier", "Dostawca", "supplier", 1040, 170, 170, 90, "#dbeafe"),
            DiagramNode("stock", "Stan\nmagazynu", "warehouse", 560, 330, 180, 100, "#f8fafc"),
        ]
        return nodes, [
            DiagramEdge("demand", "forecast"),
            DiagramEdge("forecast", "rop"),
            DiagramEdge("rop", "po"),
            DiagramEdge("po", "supplier"),
            DiagramEdge("supplier", "stock"),
            DiagramEdge("stock", "rop", "poziom"),
        ]
    return [DiagramNode("n1", "Double click idea", "rounded", 120, 120)], []


def smart_diagram_from_description(
    description: str,
) -> tuple[list[DiagramNode], list[DiagramEdge], str, str]:
    """Build a starter diagram from a plain-language process description."""
    compact = description.lower()
    if any(word in compact for word in ["api", "system", "baza", "dashboard", "serwer"]):
        template = "System Architecture"
    elif any(word in compact for word in ["csv", "dane", "model", "metryk", "raport", "walid"]):
        template = "Data Pipeline"
    elif any(word in compact for word in ["dostaw", "magazyn", "transport", "wysyl", "logist"]):
        template = "Supply Chain"
    elif any(word in compact for word in ["qc", "jakosc", "produkc", "linia", "pakow"]):
        template = "Production Line"
    else:
        template = "Flowchart"

    raw_parts = re.split(r"\s*(?:->|=>|→|,|;|\n)\s*", description)
    parts = [part.strip(" .:-") for part in raw_parts if part.strip(" .:-")]
    if len(parts) < 2:
        parts = ["Start", description.strip(), "Wynik"]
    parts = parts[:10]

    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    for idx, part in enumerate(parts):
        shape, fill, stroke = smart_shape_style(part, idx, len(parts))
        node = DiagramNode(
            id=f"s{idx + 1}",
            label=part[:42],
            shape=shape,
            x=80 + idx * 230,
            y=150 if idx % 2 == 0 else 270,
            width=190 if shape not in {"database", "decision"} else 170,
            height=74 if shape != "decision" else 88,
            fill=fill,
            stroke=stroke,
        )
        nodes.append(node)
        if idx > 0:
            edges.append(DiagramEdge(f"s{idx}", node.id, smart_edge_label(parts[idx - 1], part)))
    return nodes, edges, template, "wybrano ksztalty, kolory i polaczenia z tekstu"


def smart_shape_style(label_text: str, index: int, total: int) -> tuple[str, str, str]:
    text = label_text.lower()
    if index == 0 and any(
        word in text for word in ["start", "wejsc", "dostaw", "klient", "uzytkownik"]
    ):
        return "terminator", "#dcfce7", "#16a34a"
    if index == total - 1 and any(
        word in text for word in ["wynik", "raport", "wysyl", "koniec", "dashboard"]
    ):
        return "terminator", "#dbeafe", "#2563eb"
    if any(word in text for word in ["czy", "ok", "decyz", "warunek", "quality"]):
        return "decision", "#fef9c3", "#ca8a04"
    if any(word in text for word in ["baza", "csv", "dane", "database", "sql"]):
        return "database", "#ede9fe", "#7c3aed"
    if any(word in text for word in ["model", "ml", "tabpfn", "predyk"]):
        return "model", "#ede9fe", "#7c3aed"
    if any(word in text for word in ["qc", "jakosc", "kontrola", "test"]):
        return "inspection", "#dcfce7", "#16a34a"
    if any(word in text for word in ["ryzyk", "blad", "alert", "awaria"]):
        return "risk", "#fee2e2", "#dc2626"
    if any(word in text for word in ["magazyn", "warehouse"]):
        return "warehouse", "#f1f5f9", "#111827"
    if any(word in text for word in ["transport", "wysyl", "trasa"]):
        return "truck", "#dbeafe", "#2563eb"
    return "process", "#dbeafe", "#2563eb"


def smart_edge_label(previous: str, current: str) -> str:
    del previous
    current_lower = current.lower()
    if any(word in current_lower for word in ["walid", "kontrola", "qc", "test"]):
        return "sprawdz"
    if any(word in current_lower for word in ["model", "predyk", "metryk"]):
        return "ucz/ocen"
    if any(word in current_lower for word in ["raport", "dashboard"]):
        return "pokaz"
    if any(word in current_lower for word in ["transport", "wysyl"]):
        return "przekaz"
    return "dalej"


def _drawio_style(node: DiagramNode) -> str:
    base = {
        "rectangle": "whiteSpace=wrap;html=1;",
        "rounded": "rounded=1;whiteSpace=wrap;html=1;",
        "ellipse": "ellipse;whiteSpace=wrap;html=1;",
        "diamond": "rhombus;whiteSpace=wrap;html=1;",
        "hexagon": "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;",
        "parallelogram": "shape=parallelogram;whiteSpace=wrap;html=1;",
        "cylinder": "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;",
        "database": "shape=cylinder;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;",
        "queue": "shape=internalStorage;whiteSpace=wrap;html=1;",
        "cloud": "ellipse;shape=cloud;whiteSpace=wrap;html=1;",
        "document": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;",
        "note": "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;",
        "actor": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;",
        "process": "rounded=1;whiteSpace=wrap;html=1;",
        "decision": "rhombus;whiteSpace=wrap;html=1;",
        "terminator": "rounded=1;arcSize=50;whiteSpace=wrap;html=1;",
        "swimlane": "swimlane;whiteSpace=wrap;html=1;startSize=34;",
        "container": "rounded=1;whiteSpace=wrap;html=1;container=1;collapsible=0;",
        "machine": "shape=process;whiteSpace=wrap;html=1;",
        "warehouse": "shape=mxgraph.flowchart.off-page_reference;whiteSpace=wrap;html=1;",
        "conveyor": "shape=process;whiteSpace=wrap;html=1;rounded=1;",
        "inspection": "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;",
        "sensor": "ellipse;whiteSpace=wrap;html=1;",
        "robot": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;",
        "truck": "shape=mxgraph.transport.truck;html=1;whiteSpace=wrap;",
        "buffer": "shape=internalStorage;whiteSpace=wrap;html=1;",
        "kpi": "shape=card;whiteSpace=wrap;html=1;",
        "risk": "shape=warning;whiteSpace=wrap;html=1;",
        "model": "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;",
        "operator": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;",
        "supplier": "shape=mxgraph.flowchart.off-page_reference;whiteSpace=wrap;html=1;",
        "customer": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;",
        "station": "shape=process;whiteSpace=wrap;html=1;",
        "kanban": "shape=card;whiteSpace=wrap;html=1;",
        "pallet": "shape=process;whiteSpace=wrap;html=1;rounded=1;",
        "plc": "shape=component;whiteSpace=wrap;html=1;",
        "andon": "shape=warning;whiteSpace=wrap;html=1;",
        "energy": "shape=lightning;whiteSpace=wrap;html=1;",
    }.get(node.shape, "rounded=1;whiteSpace=wrap;html=1;")
    return f"{base}fillColor={node.fill};strokeColor={node.stroke};"


def build_drawio_xml(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    mxfile = Element("mxfile", {"host": "AOA", "modified": "", "agent": "AOA DrawIO Studio"})
    diagram = SubElement(mxfile, "diagram", {"id": "aoa-diagram", "name": "Page-1"})
    model = SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1400",
            "dy": "900",
            "grid": "1",
            "gridSize": "10",
            "page": "1",
            "pageWidth": "1169",
            "pageHeight": "827",
        },
    )
    root = SubElement(model, "root")
    SubElement(root, "mxCell", {"id": "0"})
    SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    for node in nodes:
        cell = SubElement(
            root,
            "mxCell",
            {
                "id": node.id,
                "value": escape(node.label),
                "style": _drawio_style(node),
                "vertex": "1",
                "parent": "1",
            },
        )
        SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(node.x),
                "y": str(node.y),
                "width": str(node.width),
                "height": str(node.height),
                "as": "geometry",
            },
        )
    for idx, edge in enumerate(edges, start=1):
        cell = SubElement(
            root,
            "mxCell",
            {
                "id": f"e{idx}",
                "value": escape(edge.label),
                "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;",
                "edge": "1",
                "parent": "1",
                "source": edge.source,
                "target": edge.target,
            },
        )
        SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    return tostring(mxfile, encoding="unicode")


def build_mermaid(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    lines = ["flowchart TD"]
    for node in nodes:
        label = node.label.replace("\n", "<br/>").replace('"', "'")
        if node.shape in {"diamond", "decision"}:
            lines.append(f'  {node.id}{{"{label}"}}')
        elif node.shape in {"ellipse", "terminator"}:
            lines.append(f'  {node.id}(("{label}"))')
        else:
            lines.append(f'  {node.id}["{label}"]')
    for edge in edges:
        label = f"|{edge.label}|" if edge.label else ""
        lines.append(f"  {edge.source} -->{label} {edge.target}")
    return "\n".join(lines) + "\n"


def build_svg(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    max_x = max((node.x + node.width for node in nodes), default=900) + 80
    max_y = max((node.y + node.height for node in nodes), default=600) + 80
    node_by_id = {node.id: node for node in nodes}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{max_x}" height="{max_y}" viewBox="0 0 {max_x} {max_y}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#111827"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
    ]
    for edge in edges:
        source = node_by_id.get(edge.source)
        target = node_by_id.get(edge.target)
        if not source or not target:
            continue
        x1, y1 = source.x + source.width / 2, source.y + source.height / 2
        x2, y2 = target.x + target.width / 2, target.y + target.height / 2
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#111827" stroke-width="2.2" marker-end="url(#arrow)"/>'
        )
        if edge.label:
            parts.append(
                f'<text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 - 8}" font-size="13" font-weight="700" fill="#111827">{escape(edge.label)}</text>'
            )
    for node in nodes:
        rx = 18 if node.shape in {"rounded", "process", "terminator", "container"} else 0
        if node.shape in {"ellipse", "terminator"}:
            parts.append(
                f'<ellipse cx="{node.x + node.width / 2}" cy="{node.y + node.height / 2}" rx="{node.width / 2}" ry="{node.height / 2}" fill="{node.fill}" stroke="{node.stroke}" stroke-width="2.5"/>'
            )
        elif node.shape in {"diamond", "decision"}:
            cx, cy = node.x + node.width / 2, node.y + node.height / 2
            points = f"{cx},{node.y} {node.x + node.width},{cy} {cx},{node.y + node.height} {node.x},{cy}"
            parts.append(
                f'<polygon points="{points}" fill="{node.fill}" stroke="{node.stroke}" stroke-width="2.5"/>'
            )
        else:
            parts.append(
                f'<rect x="{node.x}" y="{node.y}" width="{node.width}" height="{node.height}" rx="{rx}" fill="{node.fill}" stroke="{node.stroke}" stroke-width="2.5"/>'
            )
        label_lines = node.label.split("\\n") if "\\n" in node.label else node.label.split("\n")
        for idx, line in enumerate(label_lines[:5]):
            parts.append(
                f'<text x="{node.x + node.width / 2}" y="{node.y + 28 + idx * 18}" text-anchor="middle" font-size="14" font-weight="{700 if idx == 0 else 500}" fill="#111827">{escape(line)}</text>'
            )
    parts.append("</svg>")
    return "\n".join(parts)


def build_html_preview(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    svg = build_svg(nodes, edges)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>AOA Diagrams Preview</title>
  <style>
    body {{ margin:0; font-family:Segoe UI, Arial, sans-serif; background:#0f172a; color:#e5eef9; }}
    header {{ padding:16px 22px; background:#0b1220; border-bottom:1px solid #1e3a5f; }}
    h1 {{ margin:0 0 8px; font-size:22px; }}
    .toolbar {{ display:flex; gap:10px; flex-wrap:wrap; }}
    button {{ background:#1f8fff; color:white; border:0; border-radius:8px; padding:9px 14px; cursor:pointer; font-weight:700; }}
    main {{ height:calc(100vh - 96px); overflow:auto; background:#f8fafc; }}
    svg {{ display:block; min-width:100%; cursor:grab; }}
    svg.dragging {{ cursor:grabbing; }}
    text.hidden-label {{ display:none; }}
  </style>
</head>
<body>
  <header>
    <h1>AOA Diagrams - interaktywny podglad HTML</h1>
    <div class="toolbar">
      <button id="labels">Schowaj etykiety</button>
      <button id="reset">Reset widoku</button>
      <button id="fit">Do poczatku</button>
    </div>
  </header>
  <main id="viewport">{svg}</main>
  <script>
    const viewport = document.getElementById('viewport');
    const svg = viewport.querySelector('svg');
    let labelsHidden = false;
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let scrollLeft = 0;
    let scrollTop = 0;
    document.getElementById('labels').addEventListener('click', () => {{
      labelsHidden = !labelsHidden;
      svg.querySelectorAll('text').forEach(t => t.classList.toggle('hidden-label', labelsHidden));
      document.getElementById('labels').textContent = labelsHidden ? 'Pokaz etykiety' : 'Schowaj etykiety';
    }});
    document.getElementById('reset').addEventListener('click', () => {{
      viewport.scrollTo({{ left: 0, top: 0, behavior: 'smooth' }});
      labelsHidden = false;
      svg.querySelectorAll('text').forEach(t => t.classList.remove('hidden-label'));
      document.getElementById('labels').textContent = 'Schowaj etykiety';
    }});
    document.getElementById('fit').addEventListener('click', () => viewport.scrollTo({{ left: 0, top: 0, behavior: 'smooth' }}));
    viewport.addEventListener('mousedown', event => {{
      dragging = true;
      svg.classList.add('dragging');
      startX = event.pageX;
      startY = event.pageY;
      scrollLeft = viewport.scrollLeft;
      scrollTop = viewport.scrollTop;
    }});
    window.addEventListener('mouseup', () => {{
      dragging = false;
      svg.classList.remove('dragging');
    }});
    window.addEventListener('mousemove', event => {{
      if (!dragging) return;
      viewport.scrollLeft = scrollLeft - (event.pageX - startX);
      viewport.scrollTop = scrollTop - (event.pageY - startY);
    }});
  </script>
</body>
</html>"""


def save_diagram(
    path: str | Path, nodes: list[DiagramNode], edges: list[DiagramEdge], fmt: str
) -> Path:
    output = Path(path)
    if fmt == "drawio":
        output.write_text(build_drawio_xml(nodes, edges), encoding="utf-8")
    elif fmt == "svg":
        output.write_text(build_svg(nodes, edges), encoding="utf-8")
    elif fmt == "mermaid":
        output.write_text(build_mermaid(nodes, edges), encoding="utf-8")
    elif fmt == "html":
        output.write_text(build_html_preview(nodes, edges), encoding="utf-8")
    else:
        raise ValueError(f"Nieznany format eksportu: {fmt}")
    return output
