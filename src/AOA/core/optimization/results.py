from __future__ import annotations

import json

import pandas as pd

from AOA.core.optimization.models import Job


def format_steps_table(steps: list[dict]) -> str:
    if not steps:
        return "brak kroków"
    headers = [
        "Lp", "Zlecenie", "Maszyna", "Komponenty h", "Stan", "Czas", "Termin",
        "Start", "Koniec", "Opóźnienie", "T+", "STO nar.",
    ]
    rows = [
        [
            str(step["lp"]), str(step["job_id"]), str(step.get("machine_id", 1)),
            f"{step.get('components_ready_h', 0.0):.3f}", str(step.get("stock_status", "READY")),
            f"{step['processing_time']:.3f}", f"{step['deadline']:.3f}",
            f"{step['start_time']:.3f}", f"{step['completion_time']:.3f}",
            f"{step['lateness']:.3f}", f"{step['tardiness_positive']:.3f}",
            f"{step['sto_running']:.3f}",
        ]
        for step in steps
    ]
    widths = [max(len(header), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)]

    def fmt_row(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    lines = [fmt_row(headers), "-+-".join("-" * width for width in widths)]
    lines.extend(fmt_row(row) for row in rows)
    return "\n".join(lines)


def apply_sto_result_to_dataframe(
    df: pd.DataFrame, result: dict, job_id_col: str = "sto_job_id"
) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("Brak danych do zapisania wyniku STO.")
    out = df.copy().reset_index(drop=True)
    if job_id_col not in out.columns:
        out[job_id_col] = [f"JOB_{i + 1}" for i in range(len(out))]
    step_map = {step["job_id"]: step for step in result["steps"]}
    out = out.set_index(job_id_col)
    ordered_ids = [job_id for job_id in result["order"] if job_id in out.index]
    out = out.loc[ordered_ids].copy()
    out["sto_model"] = result["method"]
    field_map = {
        "sto_order": "lp", "sto_start": "start_time", "sto_end": "completion_time",
        "sto_lateness": "lateness", "sto_tardiness_positive": "tardiness_positive",
        "sto_cumulative": "sto_running", "machine_id": "machine_id", "sto_setup_h": "setup_time",
        "sto_waste_kg": "waste_kg", "sto_energy_kwh": "energy_kwh",
        "components_ready_h": "components_ready_h", "material_wait_h": "material_wait_h",
        "missing_components": "missing_components", "stock_status": "stock_status",
        "stock_reservation": "stock_reservation", "scheduled": "scheduled",
    }
    defaults = {
        "machine_id": 1, "setup_time": 0.0, "waste_kg": 0.0, "energy_kwh": 0.0,
        "components_ready_h": 0.0, "material_wait_h": 0.0, "missing_components": "",
        "stock_status": "READY", "stock_reservation": "[]", "scheduled": True,
    }
    for output_name, step_name in field_map.items():
        out[output_name] = [step_map[job_id].get(step_name, defaults.get(step_name)) for job_id in ordered_ids]
    out["sto_total_for_model"] = result["sto"]
    out["solution_node_id"] = [f"B{index + 1}" for index in range(len(out))]
    out["solution_parent_id"] = [""] + out["solution_node_id"].tolist()[:-1]
    out["solution_label"] = out["solution_node_id"]
    out["solution_details"] = [
        f"job={job_id}; start={step_map[job_id]['start_time']}; end={step_map[job_id]['completion_time']}; STO={step_map[job_id]['sto_running']}"
        for job_id in ordered_ids
    ]
    out["solution_edge_label"] = ["" if index == 0 else f"rank {index + 1}" for index in range(len(out))]
    out["solution_level"] = list(range(len(out)))
    out["solution_order"] = list(range(1, len(out) + 1))
    tree_records = [{
        "id": "B1", "parent": "", "label": "B1",
        "details": f"model={result['method']}; STO={result['sto']}; jobs={len(ordered_ids)}",
        "edge_label": "",
    }]
    next_id, selected_parent, remaining = 2, "B1", ordered_ids[:]
    for rank, selected_job_id in enumerate(ordered_ids, start=1):
        selected_step = step_map[selected_job_id]
        selected_node_id = f"B{next_id}"
        next_id += 1
        tree_records.append({
            "id": selected_node_id, "parent": selected_parent, "label": selected_node_id,
            "details": f"selected={selected_job_id}; rank={rank}; end={selected_step['completion_time']}; STO={selected_step['sto_running']}",
            "edge_label": f"z{rank}:{selected_job_id}",
        })
        for alt_job_id in [job_id for job_id in remaining if job_id != selected_job_id][:2]:
            alt_step = step_map[alt_job_id]
            alt_node_id = f"B{next_id}"
            next_id += 1
            tree_records.append({
                "id": alt_node_id, "parent": selected_parent, "label": alt_node_id,
                "details": f"alt={alt_job_id}; p={alt_step['processing_time']}; d={alt_step['deadline']}; T+={alt_step['tardiness_positive']}",
                "edge_label": f"alt:{alt_job_id}",
            })
        selected_parent = selected_node_id
        remaining = [job_id for job_id in remaining if job_id != selected_job_id]
    out["solution_tree_json"] = ""
    out.loc[out.index[0], "solution_tree_json"] = json.dumps(tree_records, ensure_ascii=False)
    return out.reset_index()


def build_sto_report(jobs: list[Job], results: list[dict]) -> str:
    lines = ["ANALIZA STO", "===========", "", "Dane wejściowe:"]
    lines.extend(f"- {job.job_id}: czas={job.processing_time:g}, termin={job.deadline:g}" for job in jobs)
    lines.extend(["", "Ranking modeli od najlepszego do najgorszego:"])
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index}. {result['method']} | STO={result['sto']:.3f} | Czas całk.={result['completion_total']:.3f} | "
            f"Odpad={result['total_waste_kg']:.3f} kg | Maszyny={result['machine_count']} | "
            f"Max T+={result['max_positive_delay']:.3f} | Niewykonalne={result['unscheduled_count']}"
        )
    if results:
        best, worst = results[0], results[-1]
        lines.extend(["", "Najbardziej optymalny wynik:", f"- Model: {best['method']}",
                      f"- Kolejność: {', '.join(best['order'])}", f"- STO: {best['sto']:.3f}",
                      "", "Najgorszy wynik:", f"- Model: {worst['method']}",
                      f"- Kolejność: {', '.join(worst['order'])}", f"- STO: {worst['sto']:.3f}"])
    for index, result in enumerate(results, start=1):
        lines.extend([
            "", "=" * 72, f"{index}. MODEL STO: {result['method']}", "=" * 72,
            f"Kolejność: {', '.join(result['order'])}", f"STO: {result['sto']:.3f}",
            f"Odpad: {result['total_waste_kg']:.3f} kg", f"Liczba maszyn: {result['machine_count']}",
            f"Zlecenia niewykonalne materialowo: {result['unscheduled_count']}",
            f"Czas całkowity: {result['completion_total']:.3f}",
            f"Maksymalne dodatnie opóźnienie: {result['max_positive_delay']:.3f}", "",
            "Szczegóły przypisania krok po kroku:", result["table_text"],
        ])
    return "\n".join(lines)
