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


def analyze_sto_models(job_ids_text, processing_text, deadlines_text, selected_methods):
    jobs = parse_jobs(job_ids_text, processing_text, deadlines_text)
    results = run_selected_sto_models(jobs, selected_methods)
    report = build_sto_report(jobs, results)

    saved_paths = []
    best_result = None
    best_path = None
    all_path = None
    if results:
        jobs_df = pd.DataFrame(
            {
                "sto_job_id": [job.job_id for job in jobs],
                "czas_produkcji_h": [job.processing_time for job in jobs],
                "termin_h": [job.deadline for job in jobs],
            }
        )
        best_result = min(results, key=lambda x: x["sto"])
        best_jobs_df = apply_sto_result_to_dataframe(jobs_df, best_result)
        result_frames = []
        for result in results:
            result_df = apply_sto_result_to_dataframe(jobs_df, result)
            result_frames.append(result_df)
            out_path = build_result_filename(f"sto_{result['method']}", "manual", suffix=".csv")
            save_csv(result_df, out_path)
            saved_paths.append(
                {
                    "method": result["method"],
                    "sto": result["sto"],
                    "path": out_path,
                    "tree_chart": "SolutionTree",
                }
            )
        best_path = build_result_filename("sto_best", "manual", suffix=".csv")
        save_csv(best_jobs_df, best_path)
        all_path = build_result_filename("sto_all", "manual", suffix=".csv")
        save_csv(pd.concat(result_frames, ignore_index=True, sort=False), all_path)

    return {
        "jobs": jobs,
        "results": results,
        "report": report,
        "saved_paths": saved_paths,
        "best_result": best_result,
        "best_path": best_path,
        "all_path": all_path,
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
        jobs_df = pd.DataFrame(
            {
                "sto_job_id": [job.job_id for job in jobs],
                "czas_produkcji_h": [job.processing_time for job in jobs],
                "termin_h": [job.deadline for job in jobs],
            }
        )
        best_result = min(results, key=lambda x: x["sto"])
        best_jobs_df = apply_sto_result_to_dataframe(jobs_df, best_result)
        result_frames = []
        for result in results:
            result_df = apply_sto_result_to_dataframe(jobs_df, result)
            result_frames.append(result_df)
            out_path = build_result_filename(
                f"sto_{result['method']}", Path(data_path).stem, suffix=".csv"
            )
            save_csv(result_df, out_path)
            saved_paths.append(
                {
                    "method": result["method"],
                    "sto": result["sto"],
                    "path": out_path,
                    "tree_chart": "SolutionTree",
                }
            )
        best_path = build_result_filename("sto_best", Path(data_path).stem, suffix=".csv")
        save_csv(best_jobs_df, best_path)
        all_path = build_result_filename("sto_all", Path(data_path).stem, suffix=".csv")
        save_csv(pd.concat(result_frames, ignore_index=True, sort=False), all_path)

    return {
        "jobs": jobs,
        "results": results,
        "report": report,
        "saved_paths": saved_paths,
        "best_result": best_result,
        "best_path": best_path,
        "all_path": all_path,
        "messages": ["✔ Rozwiązanie STO zakończone"],
    }
