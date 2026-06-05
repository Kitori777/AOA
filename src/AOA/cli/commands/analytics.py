from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from AOA.config import DATA_DIR
from AOA.core.assistant_service import AssistantService
from AOA.core.data_analytics_service import run_analytics_workflow
from AOA.core.drawio_service import save_diagram, template_nodes_edges
from AOA.core.report_composer_service import (
    build_custom_report_html,
    build_custom_report_pdf,
    default_report_template,
    render_report_preview_text,
)

from ..helpers import hr, logger, resolve_existing_file


def command_analytics(args: argparse.Namespace) -> int:
    data_path = resolve_existing_file(args.data, "pliku CSV")
    df = pd.read_csv(data_path)
    result = run_analytics_workflow(df, args.workflow, args.metric, args.dimension)

    hr("ANALYTICS")
    logger.info("%s", result.title)
    logger.info("Rekomendowany wykres: %s", result.recommended_chart)
    logger.info("%s", result.body)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "html":
            source = f"\\title{{{result.title}}}\n\n\\section{{Wynik}}\n{result.body}\n"
            output.write_text(
                build_custom_report_html(source, title=result.title), encoding="utf-8"
            )
        else:
            output.write_text(f"# {result.title}\n\n{result.body}\n", encoding="utf-8")
        logger.info("OUTPUT: %s", output)
    return 0


def command_report(args: argparse.Namespace) -> int:
    source_path = Path(args.source) if args.source else None
    if source_path:
        source_path = resolve_existing_file(str(source_path), "zrodla raportu")
        source = source_path.read_text(encoding="utf-8")
    else:
        source = default_report_template(args.title)

    if args.preview:
        hr("PODGLAD RAPORTU")
        logger.info("%s", render_report_preview_text(source))

    output = Path(args.output) if args.output else _default_report_path(args.format)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "html":
        output.write_text(build_custom_report_html(source, title=args.title), encoding="utf-8")
    elif args.format == "pdf":
        build_custom_report_pdf(source, output, title=args.title)
    else:
        output.write_text(source, encoding="utf-8")
    hr("REPORT BUILDER")
    logger.info("OUTPUT: %s", output)
    return 0


def command_diagram(args: argparse.Namespace) -> int:
    nodes, edges = template_nodes_edges(args.template)
    output = Path(args.output) if args.output else _default_diagram_path(args.format)
    output.parent.mkdir(parents=True, exist_ok=True)
    save_diagram(output, nodes, edges, args.format)
    hr("DIAGRAM")
    logger.info("Szablon: %s", args.template)
    logger.info("Format: %s", args.format)
    logger.info("OUTPUT: %s", output)
    return 0


def command_alice(args: argparse.Namespace) -> int:
    answer, hits, from_airi = AssistantService().answer(args.question)
    hr("ALICE")
    logger.info("%s", answer)
    if args.sources:
        logger.info("")
        logger.info("Zrodla / dopasowania:")
        for hit in hits[: args.sources]:
            logger.info("- %s (%.3f)", hit.source, hit.score)
    if from_airi:
        logger.info("")
        logger.info("Uzyto dodatkowej wiedzy z AIRI/local sources.")
    return 0


def _default_report_path(fmt: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / "reports" / f"cli_report_{stamp}.{fmt}"


def _default_diagram_path(fmt: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "mmd" if fmt == "mermaid" else fmt
    return DATA_DIR / "diagrams" / f"cli_diagram_{stamp}.{suffix}"
