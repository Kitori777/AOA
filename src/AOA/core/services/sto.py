from __future__ import annotations

from pathlib import Path

import pandas as pd

from AOA.core.component_inventory import annotate_component_readiness
from AOA.core.data_io import load_csv, save_csv
from AOA.core.models import load_model_pack
from AOA.core.sto_models import (
    apply_sto_result_to_dataframe,
    build_sto_report,
    dataframe_to_jobs,
    parse_jobs,
    run_selected_sto_models,
)

from .files import build_result_filename

STO_VISUAL_COLUMNS = [
    "sto_model",
    "sto_job_id",
    "czas_produkcji_h",
    "termin_h",
    "machine_id",
    "sto_order",
    "sto_start",
    "sto_end",
    "sto_lateness",
    "sto_tardiness_positive",
    "sto_cumulative",
    "sto_total_for_model",
    "sto_setup_h",
    "sto_waste_kg",
    "sto_energy_kwh",
    "produkt_id",
    "ilosc_szt",
    "components_ready_h",
    "material_wait_h",
    "missing_components",
    "stock_status",
    "stock_reservation",
    "scheduled",
]


def _jobs_dataframe(jobs, source_df: pd.DataFrame | None = None) -> pd.DataFrame:
    jobs_df = pd.DataFrame(
        {
            "sto_job_id": [job.job_id for job in jobs],
            "czas_produkcji_h": [job.processing_time for job in jobs],
            "termin_h": [job.deadline for job in jobs],
        }
    )
    if source_df is None or source_df.empty:
        return jobs_df

    source = source_df.reset_index(drop=True)
    if len(source) != len(jobs_df):
        return jobs_df

    for column in source.columns:
        if column not in jobs_df.columns:
            jobs_df[column] = source[column].values
    return jobs_df


def _visual_sto_dataframe(result_df: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in STO_VISUAL_COLUMNS if column in result_df.columns]
    return result_df[columns].copy() if columns else result_df.copy()


def analyze_sto_models(
    job_ids_text, processing_text, deadlines_text, selected_methods, n_machines=1
):
    jobs = parse_jobs(job_ids_text, processing_text, deadlines_text)
    results = run_selected_sto_models(jobs, selected_methods, n_machines=n_machines)
    report = build_sto_report(jobs, results)

    saved_paths = []
    best_result = None
    best_path = None
    all_path = None
    if results:
        jobs_df = _jobs_dataframe(jobs)
        best_result = results[0]
        best_jobs_df = apply_sto_result_to_dataframe(jobs_df, best_result)
        result_frames = []
        for result in results:
            result_df = apply_sto_result_to_dataframe(jobs_df, result)
            visual_df = _visual_sto_dataframe(result_df)
            result_frames.append(visual_df)
            out_path = build_result_filename(f"sto_{result['method']}", "manual", suffix=".csv")
            save_csv(visual_df, out_path)
            saved_paths.append(
                {
                    "method": result["method"],
                    "sto": result["sto"],
                    "path": out_path,
                    "tree_chart": "SolutionTree",
                }
            )
        best_path = build_result_filename("sto_best", "manual", suffix=".csv")
        save_csv(_visual_sto_dataframe(best_jobs_df), best_path)
        all_path = build_result_filename("sto_visual", "manual", suffix=".csv")
        save_csv(pd.concat(result_frames, ignore_index=True, sort=False), all_path)

    return {
        "jobs": jobs,
        "results": results,
        "report": report,
        "saved_paths": saved_paths,
        "best_result": best_result,
        "best_path": best_path,
        "all_path": all_path,
        "visual_path": all_path,
        "messages": ["✔ Analiza STO zakończona"],
    }


def _component_paths(data_path, bom_path=None, inventory_path=None):
    data_dir = Path(data_path).resolve().parent
    bom_candidate = Path(bom_path) if bom_path else data_dir / "bom.csv"
    inventory_candidate = Path(inventory_path) if inventory_path else data_dir / "inventory.csv"
    explicit = bool(bom_path or inventory_path)
    if bom_candidate.is_file() and inventory_candidate.is_file():
        return bom_candidate, inventory_candidate
    if explicit or bom_candidate.exists() or inventory_candidate.exists():
        raise ValueError("Dane komponentow wymagaja obu plikow: bom.csv i inventory.csv.")
    return None, None


def solve_sto_with_saved_model(model_path, data_path, bom_path=None, inventory_path=None):
    if not model_path:
        raise ValueError("Nie wybrano pliku modelu STO.")
    if not data_path:
        raise ValueError("Nie wybrano pliku danych STO.")

    model_pack = load_model_pack(model_path)
    if model_pack.get("pack_kind") != "sto":
        raise ValueError("Wybrany plik nie jest modelem STO.")

    df = load_csv(data_path)
    if df.empty:
        raise ValueError("Plik danych jest pusty.")

    resolved_bom, resolved_inventory = _component_paths(
        data_path, bom_path=bom_path, inventory_path=inventory_path
    )
    component_messages = []
    if resolved_bom and resolved_inventory:
        reservation_columns = ["termin_h"]
        if "zlecenie_id" in df.columns:
            reservation_columns.append("zlecenie_id")
        reservation_input = df.sort_values(reservation_columns, kind="stable")
        df = annotate_component_readiness(
            reservation_input,
            load_csv(resolved_bom),
            load_csv(resolved_inventory),
        )
        component_messages.append(
            f"✔ Komponenty: {resolved_bom.name} + {resolved_inventory.name}"
        )
    else:
        df = annotate_component_readiness(df, None, None)
        component_messages.append("ℹ Brak BOM/magazynu: komponenty przyjete jako gotowe w godzinie 0")

    jobs = dataframe_to_jobs(df, job_id_col="zlecenie_id" if "zlecenie_id" in df else None)
    selected_methods = model_pack.get("selected_methods", [])
    if not selected_methods:
        raise ValueError("Zapisany model STO nie zawiera żadnych metod.")

    n_machines = int(
        model_pack.get("n_machines") or max(1, df.get("machine_id", pd.Series([1])).nunique())
    )
    results = run_selected_sto_models(jobs, selected_methods, n_machines=n_machines)
    report = build_sto_report(jobs, results)
    saved_paths = []
    best_result = None
    best_path = None
    all_path = None
    if results:
        jobs_df = _jobs_dataframe(jobs, df)
        best_result = results[0]
        best_jobs_df = apply_sto_result_to_dataframe(jobs_df, best_result)
        result_frames = []
        for result in results:
            result_df = apply_sto_result_to_dataframe(jobs_df, result)
            visual_df = _visual_sto_dataframe(result_df)
            result_frames.append(visual_df)
            out_path = build_result_filename(
                f"sto_{result['method']}", Path(data_path).stem, suffix=".csv"
            )
            save_csv(visual_df, out_path)
            saved_paths.append(
                {
                    "method": result["method"],
                    "sto": result["sto"],
                    "path": out_path,
                    "tree_chart": "SolutionTree",
                }
            )
        best_path = build_result_filename("sto_best", Path(data_path).stem, suffix=".csv")
        save_csv(_visual_sto_dataframe(best_jobs_df), best_path)
        all_path = build_result_filename("sto_visual", Path(data_path).stem, suffix=".csv")
        save_csv(pd.concat(result_frames, ignore_index=True, sort=False), all_path)

    return {
        "jobs": jobs,
        "results": results,
        "report": report,
        "saved_paths": saved_paths,
        "best_result": best_result,
        "best_path": best_path,
        "all_path": all_path,
        "visual_path": all_path,
        "messages": ["✔ Rozwiązanie STO zakończone", *component_messages],
        "bom_path": resolved_bom,
        "inventory_path": resolved_inventory,
    }
