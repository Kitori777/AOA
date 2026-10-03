from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from AOA.config import DATA_DIR, MODELS_DIR
from AOA.core.machine_efficiency import build_machine_efficiency, efficiency_summary
from AOA.core.monte_carlo import MonteCarloConfig, simulate_schedule_risk
from AOA.core.production_line import (
    ProductionLineResult,
    ProductionLineSpec,
    simulate_production_line,
)
from AOA.core.production_line_designer import ProductionLineDraft

from .files import sanitize_filename

PRODUCTION_LINES_DIR = MODELS_DIR / "production_lines"
PRODUCTION_LINE_VISUAL_COLUMNS = [
    "line_id",
    "sto_job_id",
    "job_order",
    "station_id",
    "station_order",
    "machine_id",
    "t_start",
    "t_end",
    "termin_h",
    "cost",
    "waste",
    "quality",
]

PRODUCTION_LINE_SUMMARY_COLUMNS = [
    "line_id",
    "sto_job_id",
    "job_order",
    "line_completion_h",
    "line_deadline_h",
    "line_lateness_h",
    "line_quality",
    "line_cost_total",
    "line_waste_total",
]


def save_production_line_spec(spec: ProductionLineSpec, path: str | Path | None = None) -> Path:
    normalized = spec.normalized()
    target = (
        Path(path)
        if path
        else PRODUCTION_LINES_DIR / f"{sanitize_filename(normalized.line_id)}.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(target, json.dumps(normalized.to_dict(), indent=2, ensure_ascii=False))
    return target


def save_production_line_project(
    project: ProductionLineDraft,
    path: str | Path | None = None,
) -> Path:
    target = (
        Path(path) if path else PRODUCTION_LINES_DIR / f"{sanitize_filename(project.line_id)}.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(target, json.dumps(project.to_dict(), indent=2, ensure_ascii=False))
    return target


def load_production_line_spec(path: str | Path) -> ProductionLineSpec:
    payload = _load_project_payload(path)
    return ProductionLineSpec.from_dict(payload)


def load_production_line_project(path: str | Path) -> ProductionLineDraft:
    return ProductionLineDraft.from_dict(_load_project_payload(path))


def build_production_line_summary(
    spec: ProductionLineSpec,
    jobs: pd.DataFrame,
    result: ProductionLineResult,
) -> pd.DataFrame:
    """Return one ML/Results-friendly row per source job with simulated outcomes."""
    source = jobs.reset_index(drop=True).copy()
    outcomes = result.job_summary.sort_values("job_order", kind="stable").reset_index(drop=True)
    if len(source) != len(outcomes):
        raise ValueError("Podsumowanie linii nie odpowiada liczbie zlecen wejsciowych.")
    source = source.drop(columns=PRODUCTION_LINE_SUMMARY_COLUMNS, errors="ignore")
    source.insert(0, "job_order", outcomes["job_order"].astype(int))
    source.insert(0, "sto_job_id", outcomes["sto_job_id"].astype(str))
    source.insert(0, "line_id", spec.normalized().line_id)
    source["line_completion_h"] = outcomes["t_end"].to_numpy()
    source["line_deadline_h"] = outcomes["termin_h"].to_numpy()
    source["line_lateness_h"] = outcomes["lateness_h"].to_numpy()
    source["line_quality"] = outcomes["quality"].to_numpy()
    source["line_cost_total"] = outcomes["cost_total"].to_numpy()
    source["line_waste_total"] = outcomes["waste_total"].to_numpy()
    leading = [column for column in PRODUCTION_LINE_SUMMARY_COLUMNS if column in source.columns]
    remaining = [column for column in source.columns if column not in leading]
    return source[leading + remaining]


def run_production_line_flow(
    spec: ProductionLineSpec,
    jobs: pd.DataFrame,
    *,
    output_dir: str | Path | None = None,
    project: ProductionLineDraft | None = None,
) -> dict[str, Any]:
    result: ProductionLineResult = simulate_production_line(spec, jobs)
    normalized = spec.normalized()
    destination = Path(output_dir) if output_dir else DATA_DIR
    destination.mkdir(parents=True, exist_ok=True)
    PRODUCTION_LINES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_id = f"{stamp}_{uuid4().hex[:8]}"
    safe_line_id = sanitize_filename(normalized.line_id)
    csv_path = destination / f"production_line_visual_{safe_line_id}_{run_id}.csv"
    summary_path = destination / f"production_line_summary_{safe_line_id}_{run_id}.csv"
    efficiency_path = destination / f"machine_efficiency_{safe_line_id}_{run_id}.csv"
    risk_path = destination / f"monte_carlo_runs_{safe_line_id}_{run_id}.csv"
    spec_path = PRODUCTION_LINES_DIR / f"{safe_line_id}.json"
    visual_events = result.events[PRODUCTION_LINE_VISUAL_COLUMNS].copy()
    summary = build_production_line_summary(normalized, jobs, result)
    risk = simulate_schedule_risk(
        result.machine_events,
        normalized.machines,
        MonteCarloConfig(),
    )
    efficiency = build_machine_efficiency(result.machine_events, normalized.machines, risk)
    _write_production_line_artifacts(
        spec_path=spec_path,
        spec_payload=project.to_dict() if project is not None else normalized.to_dict(),
        visual_path=csv_path,
        visual_events=visual_events,
        summary_path=summary_path,
        summary=summary,
        efficiency_path=efficiency_path,
        efficiency=efficiency,
        risk_path=risk_path,
        risk_runs=risk.runs,
    )
    return {
        "spec": normalized,
        "project": project,
        "spec_path": spec_path,
        "visual_path": csv_path,
        "summary_path": summary_path,
        "efficiency_path": efficiency_path,
        "risk_path": risk_path,
        "events": result.events,
        "machine_events": result.machine_events,
        "visual_events": visual_events,
        "job_summary": result.job_summary,
        "summary": summary,
        "efficiency": efficiency,
        "efficiency_summary": efficiency_summary(efficiency),
        "monte_carlo": risk,
        "risk_summary": risk.summary,
        "kpis": result.kpis,
        "messages": [
            f"Zapisano projekt linii: {spec_path}",
            f"Lekki CSV do Visual: {csv_path}",
            f"Podsumowanie zlecen do Results/Report/ML: {summary_path}",
            f"Efektywnosc maszyn: {efficiency_path}",
            f"Symulacje Monte Carlo: {risk_path}",
        ],
    }


def _write_production_line_artifacts(
    *,
    spec_path: Path,
    spec_payload: dict[str, Any],
    visual_path: Path,
    visual_events: pd.DataFrame,
    summary_path: Path,
    summary: pd.DataFrame,
    efficiency_path: Path,
    efficiency: pd.DataFrame,
    risk_path: Path,
    risk_runs: pd.DataFrame,
) -> None:
    token = uuid4().hex
    temporary_paths = {
        spec_path: spec_path.with_name(f".{spec_path.name}.{token}.tmp"),
        visual_path: visual_path.with_name(f".{visual_path.name}.{token}.tmp"),
        summary_path: summary_path.with_name(f".{summary_path.name}.{token}.tmp"),
        efficiency_path: efficiency_path.with_name(f".{efficiency_path.name}.{token}.tmp"),
        risk_path: risk_path.with_name(f".{risk_path.name}.{token}.tmp"),
    }
    published: list[Path] = []
    try:
        temporary_paths[spec_path].write_text(
            json.dumps(spec_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        visual_events.to_csv(temporary_paths[visual_path], index=False)
        summary.to_csv(temporary_paths[summary_path], index=False)
        efficiency.to_csv(temporary_paths[efficiency_path], index=False)
        risk_runs.to_csv(temporary_paths[risk_path], index=False)
        for path in (visual_path, summary_path, efficiency_path, risk_path):
            temporary_paths[path].replace(path)
            published.append(path)
        temporary_paths[spec_path].replace(spec_path)
    except Exception:
        for path in temporary_paths.values():
            path.unlink(missing_ok=True)
        for path in published:
            path.unlink(missing_ok=True)
        raise


def _load_project_payload(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Plik linii produkcyjnej musi zawierac obiekt JSON.")
    return payload


def _atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)
