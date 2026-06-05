from __future__ import annotations

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
    return [DiagramNode("n1", "Double click idea", "rounded", 120, 120)], []


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
