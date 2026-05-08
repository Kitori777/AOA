from __future__ import annotations

from AOA.core.evaluation import (
    append_metrics_row,
    calculate_classification_metrics,
    calculate_regression_metrics,
    fill_missing_values,
    transform_numeric_columns,
)


def prepare_results_analysis(
    df,
    selected_cols=None,
    transformation=None,
    target=None,
    mode=None,
):
    if df is None or df.empty:
        raise ValueError("Brak danych do analizy")

    if selected_cols is not None or target is not None or mode is not None:
        if not selected_cols:
            raise ValueError("Nie wybrano kolumn do analizy")

        df_to_show = df[selected_cols].copy()
        df_to_show = fill_missing_values(df_to_show)
        df_to_show = transform_numeric_columns(df_to_show, transformation or "Surowe")

        if target not in df_to_show.columns:
            raise ValueError("Nieprawidłowy target")

        if mode == "regresja":
            metrics = calculate_regression_metrics(df_to_show, target)
        elif mode == "klasyfikacja":
            metrics = calculate_classification_metrics(df_to_show, target)
        else:
            raise ValueError("Nieznany tryb analizy")

        df_to_show = append_metrics_row(df_to_show, metrics)
        return {
            "df": df_to_show,
            "text": df_to_show.to_string(index=True),
        }

    metrics_rows = []

    if "pred_quality" in df.columns and "odpad" in df.columns:
        metrics_rows.append(
            {
                "model": "Quality",
                "metrics": calculate_regression_metrics(
                    df[["pred_quality", "odpad"]].rename(columns={"pred_quality": "feature"}),
                    "odpad",
                ),
            }
        )

    if "pred_delay" in df.columns and "lateness_h_sim" in df.columns:
        metrics_rows.append(
            {
                "model": "Delay",
                "metrics": calculate_regression_metrics(
                    df[["pred_delay", "lateness_h_sim"]].rename(columns={"pred_delay": "feature"}),
                    "lateness_h_sim",
                ),
            }
        )

    if "recommended_machine" in df.columns and "machine_id" in df.columns:
        metrics_rows.append(
            {
                "model": "Schedule",
                "metrics": calculate_classification_metrics(
                    df[["recommended_machine", "machine_id"]].rename(
                        columns={"recommended_machine": "feature"}
                    ),
                    "machine_id",
                ),
            }
        )

    return metrics_rows
