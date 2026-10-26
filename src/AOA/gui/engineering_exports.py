"""Presentation and CSV export of already computed engineering results."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from AOA.core.esm_costs import OBJECTIVES
from AOA.core.esm_project import ESM_TIME_MODES

METHOD_LABELS = {
    "MT": "MT / EDD",
    "MO": "MO / SPT",
    "MZO": "MZO / LPT",
    "MOPT": "MOpt",
    "ECO_WASTE": "ECO Waste",
    "COMPONENT_READY_EDD": "Component Ready + EDD",
    "ROBUST_MC": "Robust Monte Carlo",
}

PROOF_LABELS = {
    "OPTIMAL_CONFIRMED": "optimum potwierdzone",
    "GAP_TO_OPTIMUM": "wynik gorszy od potwierdzonego optimum",
    "BEST_KNOWN": "najlepszy znany wynik; optimum niepotwierdzone",
    "CANDIDATE": "wynik heurystyczny; optimum niepotwierdzone",
    "PARTIAL_PLAN": "plan niepełny; brak potwierdzenia optimum pełnego planu",
    "RISK_ASSESSED": "ocena ryzyka; brak dowodu optimum probabilistycznego",
}


@dataclass(frozen=True)
class EngineeringContext:
    source_path: str
    machine_count: int
    time_mode: str
    source_sha256: str
    objective: str = "sto"
    cost_parameters_json: str = "{}"


def _context_row(context: EngineeringContext) -> dict:
    return {
        "plik_zrodlowy": context.source_path,
        "sha256_csv": context.source_sha256,
        "liczba_maszyn": context.machine_count,
        "interpretacja_czasu": context.time_mode,
        "kryterium": context.objective,
        "parametry_kosztow_json": context.cost_parameters_json,
    }


def _risk(result: dict) -> tuple[dict, str]:
    if "risk_validation_summary" in result:
        return result["risk_validation_summary"], "niezależna weryfikacja"
    return result.get("risk_summary", {}), "wybór kolejności"


def comparison_rows(results: list[dict], context: EngineeringContext) -> list[dict]:
    rows = []
    for rank, result in enumerate(results, 1):
        risk, series = _risk(result)
        available = risk.get("available", False)
        rows.append(
            {
                **_context_row(context),
                "miejsce": rank,
                "metoda": METHOD_LABELS[result["method"]],
                "kolejnosc": " -> ".join(result["order"]),
                "sto_min": result["sto"],
                "koszt_opoznien_jp": result.get("total_tardiness_cost", ""),
                "koniec_min": result["completion_total"],
                "odpad_kg": result.get("total_waste_kg", 0),
                "czas_obliczen_s": result.get("elapsed_s", ""),
                "status_optimum": result.get("optimality_status", ""),
                "opis_statusu": PROOF_LABELS.get(result.get("optimality_status", ""), "brak oceny"),
                "powod_zatrzymania_mopt": result.get("search_stop_reason", ""),
                "niezaplanowane_zlecenia": result.get("unscheduled_count", 0),
                "zablokowane_zlecenia": " -> ".join(result.get("blocked_jobs", [])),
                "p90_konca_min": risk.get("p90_makespan_min", "") if available else "",
                "p90_sto_min": risk.get("p90_lateness_min", "") if available else "",
                "sredni_koszt_jp": risk.get("mean_tardiness_cost", "") if available else "",
                "p90_kosztu_jp": risk.get("p90_tardiness_cost", "") if available else "",
                "seria_mc": series if available else "",
                "liczba_symulacji": risk.get("iterations", "") if available else "",
                "ziarno_mc": risk.get("seed", "") if available else "",
            }
        )
    return rows


def operation_rows(results: list[dict], context: EngineeringContext) -> list[dict]:
    rows = []
    for result in results:
        for step in result["steps"]:
            scheduled = step.get("scheduled", True)
            rows.append(
                {
                    **_context_row(context),
                    "metoda": METHOD_LABELS[result["method"]],
                    "status_optimum": result.get("optimality_status", ""),
                    "zlecenie": step["job_id"],
                    "stawka_jp_na_min": step.get("tardiness_cost_per_min", ""),
                    "tolerancja_min": step.get("allowed_tardiness_min", ""),
                    "koszt_opoznienia_jp": step.get("tardiness_cost", "") if scheduled else "",
                    "zaplanowane": "tak" if scheduled else "nie",
                    "powod_braku": step.get("unscheduled_reason", ""),
                    "maszyna": step.get("machine_id", "") if scheduled else "",
                    "start_min": step.get("start_time", "") if scheduled else "",
                    "koniec_min": step.get("completion_time", "") if scheduled else "",
                    "obrobka_min": step.get("processing_time", "") if scheduled else "",
                    "start_przezbrojenia_min": step.get("setup_start", "") if scheduled else "",
                    "przezbrojenie_min": step.get("setup_time", "") if scheduled else "",
                    "termin_min": step.get("deadline", ""),
                    "komponenty_od_min": step.get("components_ready_min", ""),
                    "opoznienie_po_ostatniej_maszynie_min": step.get("tardiness_positive", "")
                    if scheduled
                    else "",
                    "odpad_kg": step.get("waste_kg", "") if scheduled else "",
                }
            )
    return rows


def format_result_description(result: dict, context: EngineeringContext) -> str:
    status = PROOF_LABELS.get(result.get("optimality_status", ""), "brak oceny optimum")
    lines = [
        f"Metoda: {METHOD_LABELS[result['method']]}; {status}.",
        f"Dane: {context.source_path}",
        f"SHA-256 CSV: {context.source_sha256}",
        f"Maszyny: {context.machine_count}; {ESM_TIME_MODES[context.time_mode]}.",
        f"Kryterium: {OBJECTIVES[context.objective]}; koszt opóźnień: {result.get('total_tardiness_cost', 0):g} j.p.",
        "Stawki i tolerancje: "
        + "; ".join(
            f"{job_id}: {p['rate_per_min']:g} j.p./min, {p['grace_min']:g} min"
            for job_id, p in json.loads(context.cost_parameters_json).items()
        ),
        f"Kolejność: {' -> '.join(result['order'])}.",
        f"STO: {result['sto']:g} min; koniec produkcji: {result['completion_total']:g} min; "
        f"odpad: {result.get('total_waste_kg', 0):g} kg.",
    ]
    if "elapsed_s" in result:
        lines.append(f"Czas obliczeń: {result['elapsed_s']:.3f} s.")
    if result.get("search_stop_reason"):
        lines.append(f"MOpt — zatrzymanie: {result['search_stop_reason']}.")
    if result.get("unscheduled_count"):
        lines.append(
            f"Niezaplanowane zlecenia: {result['unscheduled_count']} "
            f"({', '.join(result.get('blocked_jobs', []))}). "
            "STO i koszt dotyczą tylko zaplanowanej części."
        )
    risk, series = _risk(result)
    if risk.get("available"):
        if "mean_tardiness_cost" in risk:
            lines.append(
                f"Monte Carlo — {series}: średni koszt {risk['mean_tardiness_cost']:.2f} j.p.; P90 kosztu {risk['p90_tardiness_cost']:.2f} j.p."
            )
        lines.append(
            f"Monte Carlo — {series}: {risk['iterations']} symulacji, ziarno {risk['seed']}; "
            f"P90 końca: {risk['p90_makespan_min']:.2f} min; "
            f"P90 STO: {risk['p90_lateness_min']:.2f} min. "
            "Gantt przedstawia harmonogram nominalny."
        )
    return "\n".join(lines)


def write_csv(path: str | Path, rows: list[dict], *, source_path: str) -> Path:
    """Write an Excel-friendly CSV atomically, preserving any previous file on failure."""
    target = Path(path).resolve()
    if target == Path(source_path).resolve():
        raise ValueError("Eksport nie może zastąpić źródłowego CSV.")
    if not rows:
        raise ValueError("Brak wyników do zapisania.")
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=target.parent,
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=";")
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        key: str(value).replace(".", ",") if isinstance(value, float) else value
                        for key, value in row.items()
                    }
                )
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target
