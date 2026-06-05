from __future__ import annotations

import csv
import re
from collections.abc import Iterable
from html import escape, unescape
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}
HTML_EXTENSIONS = {".html", ".htm"}
TEXT_EXTENSIONS = {".txt", ".md", ".tex", ".log", ".json", ".py"}
TABLE_EXTENSIONS = {".csv", ".tsv"}


def default_report_template(title: str = "Wlasny raport AOA") -> str:
    return "\n".join(
        [
            rf"\title{{{title}}}",
            r"\section{Cel raportu}",
            "Opisz tutaj, co sprawdzasz i jaka decyzje ma wspierac raport.",
            "",
            r"\section{Dane i wyniki}",
            "Dodaj wynik analizy, tabele z plikow, wizualizacje albo diagramy.",
            "",
            r"\section{Wnioski}",
            r"\begin{itemize}",
            r"\item Najwazniejszy wniosek.",
            r"\item Rekomendowana akcja.",
            r"\end{itemize}",
            "",
        ]
    )


def analysis_block(title: str, body: str, recommended_chart: str = "") -> str:
    chart_line = f"Rekomendowany wykres: {recommended_chart}\n\n" if recommended_chart else ""
    return f"\\section{{{title}}}\n{chart_line}{body.strip()}\n"


def kpi_block(metric: str = "metryka", value: str = "wartosc", note: str = "interpretacja") -> str:
    return (
        "\\section{KPI}\n"
        f"\\textbf{{Metryka:}} {metric}\n\n"
        f"\\textbf{{Wartosc:}} {value}\n\n"
        f"\\textbf{{Interpretacja:}} {note}\n"
    )


def chart_block(title: str = "Wykres", chart_type: str = "Dashboard", path: str = "") -> str:
    reference = (
        f"\\includehtml{{{path}}}\n"
        if path
        else "Dodaj tutaj opis albo plik HTML/PNG/SVG wykresu.\n"
    )
    return f"\\section{{{title}}}\nRekomendowany typ: {chart_type}\n\n{reference}"


def recommendation_block() -> str:
    return "\n".join(
        [
            r"\section{Rekomendacje}",
            r"\begin{itemize}",
            r"\item Decyzja: wpisz najwazniejsza rekomendacje.",
            r"\item Dowod: wskaz wykres, tabele albo segment, ktory ja wspiera.",
            r"\item Ryzyko: dopisz ograniczenie danych lub zalozenie.",
            r"\item Nastepny krok: wpisz konkretna akcje po raporcie.",
            r"\end{itemize}",
            "",
        ]
    )


def render_report_preview_text(source: str, max_chars: int = 9000) -> str:
    html = latexish_to_html(source)
    text = re.sub(r"<h2[^>]*>", "\n## ", html)
    text = re.sub(r"<h3[^>]*>", "\n### ", text)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text).strip()
    return text[:max_chars] + ("\n... [podglad skrocony]" if len(text) > max_chars else "")


def file_block(path: str | Path, max_rows: int = 12) -> str:
    source = Path(path)
    suffix = source.suffix.lower()
    label = source.name
    if suffix in IMAGE_EXTENSIONS:
        return f"\\section{{Wizualizacja: {label}}}\n\\includegraphics{{{source}}}\n"
    if suffix in HTML_EXTENSIONS:
        return f"\\section{{Osadzony HTML: {label}}}\n\\includehtml{{{source}}}\n"
    if suffix in TABLE_EXTENSIONS:
        return (
            f"\\section{{Tabela z pliku: {label}}}\n{_table_preview(source, max_rows=max_rows)}\n"
        )
    if suffix in TEXT_EXTENSIONS or source.exists():
        return f"\\section{{Fragment z pliku: {label}}}\n\\begin{{verbatim}}\n{_read_text(source)}\n\\end{{verbatim}}\n"
    return f"\\section{{Plik: {label}}}\nNie udalo sie rozpoznac typu pliku: {source}\n"


def build_custom_report_html(source: str, title: str = "AOA Custom Report") -> str:
    body = latexish_to_html(source)
    return (
        "<!doctype html><html lang='pl'><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title>"
        "<style>"
        "body{margin:0;background:#eef4fb;color:#0f172a;font-family:Segoe UI,Arial,sans-serif;}"
        "header{background:#0f2a44;color:white;padding:30px 42px;border-bottom:5px solid #1f8fff;}"
        "main{max-width:1120px;margin:0 auto;padding:28px 32px 48px;}"
        "section{background:white;border:1px solid #cbd5e1;border-radius:10px;margin:18px 0;padding:20px 24px;box-shadow:0 8px 22px #0f172a12;}"
        "h1,h2,h3{margin:0 0 12px;}p{line-height:1.58;margin:8px 0;}ul{line-height:1.55;}"
        "pre{white-space:pre-wrap;background:#0f172a;color:#e2e8f0;border-radius:8px;padding:14px;overflow:auto;}"
        "table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;}th,td{border:1px solid #cbd5e1;padding:8px;text-align:left;}th{background:#dbeafe;}"
        "img{max-width:100%;border:1px solid #cbd5e1;border-radius:8px;background:white;}"
        "iframe{width:100%;height:720px;border:1px solid #cbd5e1;border-radius:8px;background:white;}"
        "code{background:#e2e8f0;border-radius:5px;padding:2px 5px;font-family:Consolas,monospace;}"
        ".title-card{background:linear-gradient(135deg,#eff6ff,#ffffff);border:1px solid #bfdbfe;border-radius:12px;padding:28px;margin:18px 0;}"
        ".toc{background:#f8fafc;border:1px solid #dbeafe;border-radius:10px;padding:16px 18px;margin:18px 0;}"
        ".toc a{color:#075985;text-decoration:none}.toc ol{margin:8px 0 0 20px;line-height:1.65;}"
        ".note,.callout{background:#eff6ff;border-left:5px solid #1f8fff;padding:12px 14px;border-radius:8px;}"
        ".callout-tip{background:#ecfdf5;border-left-color:#22c55e}.callout-warning{background:#fffbeb;border-left-color:#f59e0b}.callout-danger{background:#fef2f2;border-left-color:#ef4444}"
        ".math{font-family:Cambria Math,STIX Two Math,Times New Roman,serif;background:#f8fafc;border:1px solid #dbeafe;border-radius:8px;padding:12px 14px;margin:12px 0;overflow:auto;}"
        ".math-inline{font-family:Cambria Math,STIX Two Math,Times New Roman,serif;background:#eff6ff;border-radius:5px;padding:1px 5px;}"
        ".caption{font-size:13px;color:#475569;text-align:center;margin-top:-4px;}"
        ".footnote{font-size:12px;color:#475569;vertical-align:super;}"
        ".checklist{list-style:none;margin-left:-18px}.checklist input{margin-right:8px;}"
        ".page-break{break-after:page;border-top:2px dashed #cbd5e1;margin:28px 0;padding-top:8px;color:#64748b;font-size:12px;text-transform:uppercase;}"
        "blockquote{border-left:5px solid #94a3b8;margin:12px 0;padding:8px 14px;background:#f8fafc;color:#334155;}"
        "</style></head><body>"
        f"<header><h1>{escape(_extract_title(source) or title)}</h1><p>Raport skladany w AOA Report Builder.</p></header>"
        f"<main>{body}</main></body></html>"
    )


def build_custom_report_pdf(
    source: str,
    output_path: str | Path,
    title: str = "AOA Custom Report",
) -> Path:
    """Export the report preview to a small, dependency-free PDF."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report_title = _extract_title(source) or title
    lines = [
        report_title,
        "=" * min(len(report_title), 72),
        "",
        *render_report_preview_text(source).splitlines(),
    ]
    path.write_bytes(_build_text_pdf(lines))
    return path


def latexish_to_html(source: str) -> str:
    lines = source.splitlines()
    report_title = _extract_title(source)
    headings = _collect_headings(lines)
    heading_index = 0
    html_parts: list[str] = []
    in_list = False
    in_pre = False
    section_open = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    def close_section() -> None:
        nonlocal section_open
        close_list()
        if section_open:
            html_parts.append("</section>")
            section_open = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            if not in_pre:
                html_parts.append("")
            continue
        if stripped.startswith(r"\title"):
            continue
        if stripped == r"\begin{verbatim}":
            close_list()
            html_parts.append("<pre>")
            in_pre = True
            continue
        if stripped == r"\end{verbatim}":
            html_parts.append("</pre>")
            in_pre = False
            continue
        if in_pre:
            html_parts.append(escape(line))
            continue
        if stripped == r"\maketitle":
            close_list()
            html_parts.append(
                f"<div class='title-card'><h1>{escape(report_title or 'Raport')}</h1>"
                "<p>Raport przygotowany w AOA Report Builder.</p></div>"
            )
            continue
        if stripped == r"\tableofcontents":
            close_list()
            html_parts.append(_table_of_contents_html(headings))
            continue
        if stripped == r"\pagebreak":
            close_list()
            html_parts.append("<div class='page-break'>Nowa strona w eksporcie PDF / druku</div>")
            continue
        if stripped in {r"\begin{table}", r"\end{table}", r"\begin{center}", r"\end{center}"}:
            close_list()
            continue
        label = _command_arg(stripped, "label")
        if label is not None:
            html_parts.append(f"<span id='{escape(_slugify(label))}'></span>")
            continue
        caption = _command_arg(stripped, "caption")
        if caption is not None:
            close_list()
            html_parts.append(f"<p class='caption'>{_inline_markup(caption)}</p>")
            continue
        equation = _command_arg(stripped, "equation")
        if equation is not None:
            close_list()
            html_parts.append(f"<div class='math'>{escape(equation)}</div>")
            continue
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            close_list()
            html_parts.append(f"<div class='math'>{escape(stripped[2:-2].strip())}</div>")
            continue
        callout = re.match(r":::\s*\{\.callout-(note|tip|warning|danger)\}\s*(.*)$", stripped)
        if callout:
            close_list()
            kind = callout.group(1)
            body = callout.group(2).strip() or kind
            html_parts.append(f"<div class='callout callout-{kind}'>{_inline_markup(body)}</div>")
            continue
        if stripped.startswith("> "):
            close_list()
            html_parts.append(f"<blockquote>{_inline_markup(stripped[2:])}</blockquote>")
            continue
        section = _command_arg(stripped, "section")
        if section is not None:
            close_section()
            html_parts.append("<section>")
            heading_id = headings[heading_index][2] if heading_index < len(headings) else ""
            heading_index += 1
            html_parts.append(f"<h2 id='{escape(heading_id)}'>{escape(section)}</h2>")
            section_open = True
            continue
        subsection = _command_arg(stripped, "subsection")
        if subsection is not None:
            close_list()
            if not section_open:
                html_parts.append("<section>")
                section_open = True
            heading_id = headings[heading_index][2] if heading_index < len(headings) else ""
            heading_index += 1
            html_parts.append(f"<h3 id='{escape(heading_id)}'>{escape(subsection)}</h3>")
            continue
        graphic = _command_arg(stripped, "includegraphics")
        if graphic is not None:
            close_list()
            html_parts.append(
                f"<p><img src='{escape(_file_src(graphic))}' alt='{escape(Path(graphic).name)}'></p>"
            )
            continue
        html_file = _command_arg(stripped, "includehtml")
        if html_file is not None:
            close_list()
            html_parts.append(
                f"<iframe src='{escape(_file_src(html_file))}' title='{escape(Path(html_file).name)}'></iframe>"
            )
            continue
        if stripped in {r"\begin{itemize}", r"\end{itemize}"}:
            if stripped.endswith("itemize}") and "end" in stripped:
                close_list()
            continue
        if stripped.startswith(r"\item"):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            item = stripped.replace(r"\item", "", 1).strip()
            html_parts.append(f"<li>{_inline_markup(item)}</li>")
            continue
        checklist = re.match(r"- \[( |x|X)\]\s+(.+)$", stripped)
        if checklist:
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            checked = " checked" if checklist.group(1).lower() == "x" else ""
            html_parts.append(
                f"<li class='checklist'><input type='checkbox' disabled{checked}>"
                f"{_inline_markup(checklist.group(2))}</li>"
            )
            continue
        if stripped.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline_markup(stripped[2:])}</li>")
            continue
        if stripped.startswith("### "):
            close_list()
            heading_id = headings[heading_index][2] if heading_index < len(headings) else ""
            heading_index += 1
            html_parts.append(f"<h3 id='{escape(heading_id)}'>{escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            close_section()
            html_parts.append("<section>")
            heading_id = headings[heading_index][2] if heading_index < len(headings) else ""
            heading_index += 1
            html_parts.append(f"<h2 id='{escape(heading_id)}'>{escape(stripped[3:])}</h2>")
            section_open = True
            continue
        if stripped.startswith("# "):
            continue
        close_list()
        if "|" in stripped and stripped.count("|") >= 2:
            html_parts.append(_markdown_table_to_html(stripped))
        else:
            html_parts.append(f"<p>{_inline_markup(stripped)}</p>")
    close_section()
    return "\n".join(part for part in html_parts if part != "")


def _build_text_pdf(lines: Iterable[str]) -> bytes:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap_pdf_line(line))
    if not wrapped:
        wrapped = ["Pusty raport."]

    lines_per_page = 48
    pages = [wrapped[idx : idx + lines_per_page] for idx in range(0, len(wrapped), lines_per_page)]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # filled after page object numbers are known
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_object_numbers: list[int] = []
    for page_lines in pages:
        page_no = len(objects) + 1
        content_no = page_no + 1
        page_object_numbers.append(page_no)
        stream = _pdf_text_stream(page_lines)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_no} 0 R >>"
            ).encode("ascii")
        )
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    page_refs = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[1] = f"<< /Type /Pages /Kids [{page_refs}] /Count {len(page_object_numbers)} >>".encode(
        "ascii"
    )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{idx} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def _wrap_pdf_line(line: str, width: int = 92) -> list[str]:
    clean = re.sub(r"\s+", " ", line.replace("\t", "    ")).strip()
    if not clean:
        return [""]
    parts: list[str] = []
    while len(clean) > width:
        split_at = clean.rfind(" ", 0, width + 1)
        if split_at <= 0:
            split_at = width
        parts.append(clean[:split_at].rstrip())
        clean = clean[split_at:].strip()
    parts.append(clean)
    return parts


def _pdf_text_stream(lines: list[str]) -> bytes:
    chunks = ["BT", "/F1 10 Tf", "14 TL", "48 790 Td"]
    for idx, line in enumerate(lines):
        if idx:
            chunks.append("T*")
        chunks.append(f"<{_pdf_hex_text(line)}> Tj")
    chunks.append("ET")
    return "\n".join(chunks).encode("ascii")


def _pdf_hex_text(text: str) -> str:
    normalized = text.replace("\r", " ").replace("\n", " ")
    return (
        "FEFF".encode("ascii")
        + normalized.encode("utf-16-be", errors="replace").hex().upper().encode("ascii")
    ).decode("ascii")


def _command_arg(line: str, command: str) -> str | None:
    match = re.match(rf"\\{command}(?:\[[^\]]*\])?\{{(.+)\}}\s*$", line)
    return match.group(1).strip() if match else None


def _extract_title(source: str) -> str:
    for line in source.splitlines():
        title = _command_arg(line.strip(), "title")
        if title:
            return title
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _collect_headings(lines: list[str]) -> list[tuple[int, str, str]]:
    headings: list[tuple[int, str, str]] = []
    seen: dict[str, int] = {}
    for raw_line in lines:
        stripped = raw_line.strip()
        title = _command_arg(stripped, "section")
        level = 2
        if title is None:
            title = _command_arg(stripped, "subsection")
            level = 3
        if title is None and stripped.startswith("## "):
            title = stripped[3:].strip()
            level = 2
        if title is None and stripped.startswith("### "):
            title = stripped[4:].strip()
            level = 3
        if not title:
            continue
        slug = _slugify(title)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        headings.append((level, title, slug))
    return headings


def _table_of_contents_html(headings: list[tuple[int, str, str]]) -> str:
    if not headings:
        return "<nav class='toc'><strong>Spis tresci</strong><p>Brak sekcji do pokazania.</p></nav>"
    items = []
    for level, title, slug in headings:
        indent = " style='margin-left:18px'" if level > 2 else ""
        items.append(f"<li{indent}><a href='#{escape(slug)}'>{escape(title)}</a></li>")
    return "<nav class='toc'><strong>Spis tresci</strong><ol>" + "".join(items) + "</ol></nav>"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip().lower()).strip("-")
    return slug or "section"


def _inline_markup(text: str) -> str:
    out = escape(text)
    out = re.sub(r"\\textbf\{([^{}]+)\}", r"<strong>\1</strong>", out)
    out = re.sub(r"\\emph\{([^{}]+)\}", r"<em>\1</em>", out)
    out = re.sub(r"\\code\{([^{}]+)\}", r"<code>\1</code>", out)
    out = re.sub(r"\\url\{([^{}]+)\}", r"<a href='\1'>\1</a>", out)
    out = re.sub(r"\\footnote\{([^{}]+)\}", r"<span class='footnote'>[\1]</span>", out)
    out = re.sub(
        r"\\ref\{([^{}]+)\}",
        lambda match: f"<a href='#{escape(_slugify(match.group(1)))}'>{match.group(1)}</a>",
        out,
    )
    out = re.sub(
        r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"<span class='math-inline'>\1 / \2</span>", out
    )
    out = re.sub(r"\\sqrt\{([^{}]+)\}", r"<span class='math-inline'>sqrt(\1)</span>", out)
    out = re.sub(r"\\eqref\{([^{}]+)\}", r"<span class='math-inline'>(\1)</span>", out)
    out = re.sub(r"\$([^$]+)\$", r"<span class='math-inline'>\1</span>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)
    return out


def _file_src(path_text: str) -> str:
    path = Path(path_text.strip().strip('"'))
    try:
        if path.exists():
            return path.resolve().as_uri()
    except Exception:
        pass
    return path_text


def _read_text(path: Path, max_chars: int = 6000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return f"Nie udalo sie odczytac pliku: {exc}"
    return text[:max_chars] + ("\n... [skrocono]" if len(text) > max_chars else "")


def _table_preview(path: Path, max_rows: int = 12) -> str:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
    except Exception as exc:
        return f"Nie udalo sie odczytac tabeli: {exc}"
    if not rows:
        return "Pusta tabela."
    rows = rows[: max_rows + 1]
    widths = [
        max(len(row[idx]) if idx < len(row) else 0 for row in rows)
        for idx in range(max(len(r) for r in rows))
    ]
    rendered = []
    for row_idx, row in enumerate(rows):
        padded = [(row[idx] if idx < len(row) else "").strip() for idx in range(len(widths))]
        rendered.append("| " + " | ".join(padded) + " |")
        if row_idx == 0:
            rendered.append("| " + " | ".join("---" for _ in widths) + " |")
    return "\n".join(rendered)


def _markdown_table_to_html(line: str) -> str:
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    return "<table><tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in cells) + "</tr></table>"
