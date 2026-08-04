from __future__ import annotations

from pathlib import Path

import pandas as pd

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

    machine_column = next(
        (
            column
            for column in ["machine_id", "recommended_machine", "maszyna", "machine"]
            if column in source.columns
        ),
        None,
    )
    if machine_column is not None:
        jobs_df["machine_id"] = source[machine_column].values
    return jobs_df


def _visual_sto_dataframe(result_df: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in STO_VISUAL_COLUMNS if column in result_df.columns]
    return result_df[columns].copy() if columns else result_df.copy()


def analyze_sto_models(job_ids_text, processing_text, deadlines_text, selected_methods):
    jobs = parse_jobs(job_ids_text, processing_text, deadlines_text)
    results = run_selected_sto_models(jobs, selected_methods)
    report = build_sto_report(jobs, results)

    saved_paths = []
    best_result = None
    best_path = None
    all_path = None
    if results:
        jobs_df = _jobs_dataframe(jobs)
        best_result = min(results, key=lambda x: x["sto"])
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


def solve_sto_with_saved_model(model_path, data_path):
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

    jobs = dataframe_to_jobs(df)
    selected_methods = model_pack.get("selected_methods", [])
    if not selected_methods:
        raise ValueError("Zapisany model STO nie zawiera żadnych metod.")

    results = run_selected_sto_models(jobs, selected_methods)
    report = build_sto_report(jobs, results)
    saved_paths = []
    best_result = None
    best_path = None
    all_path = None
    if results:
        jobs_df = _jobs_dataframe(jobs, df)
        best_result = min(results, key=lambda x: x["sto"])
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
        "messages": ["✔ Rozwiązanie STO zakończone"],
    }
