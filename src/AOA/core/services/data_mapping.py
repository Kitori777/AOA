from __future__ import annotations

import pandas as pd

DEFAULT_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "cena": ("cena", "price", "cost"),
    "odpad": ("odpad", "waste", "scrap"),
    "termin_h": ("termin_h", "termin", "deadline", "due", "due_date"),
    "czas_produkcji_h": ("czas_produkcji_h", "czas", "processing_time", "duration", "time"),
    "ksztalt": ("ksztalt", "shape", "geometry"),
    "material": ("material", "fabric", "material_type"),
    "x": ("x", "width"),
    "y": ("y", "height"),
    "z": ("z", "thickness", "depth"),
    "sto_job_id": ("sto_job_id", "job_id", "id", "zlecenie"),
}

ML_REQUIRED_FIELDS: tuple[str, ...] = (
    "cena",
    "odpad",
    "termin_h",
    "czas_produkcji_h",
    "ksztalt",
    "material",
    "x",
    "y",
    "z",
)

STO_REQUIRED_FIELDS: tuple[str, ...] = ("czas_produkcji_h", "termin_h")

NUMERIC_FIELDS: tuple[str, ...] = ("cena", "odpad", "termin_h", "czas_produkcji_h", "x", "y", "z")

DEFAULT_VALUES: dict[str, object] = {
    "ksztalt": "kwadrat",
    "material": "mikrofibra",
    "x": 30.0,
    "y": 30.0,
    "z": 0.3,
}


def required_fields(*, require_ml: bool, require_sto: bool) -> set[str]:
    required: set[str] = set()
    if require_ml:
        required.update(ML_REQUIRED_FIELDS)
    if require_sto:
        required.update(STO_REQUIRED_FIELDS)
    return required


def suggest_mapping(
    columns: list[str],
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, str]:
    aliases = aliases or DEFAULT_FIELD_ALIASES
    low_cols = {name.lower(): name for name in columns}
    mapping: dict[str, str] = {}
    for target, names in aliases.items():
        selected = "(brak)"
        for alias in names:
            if alias.lower() in low_cols:
                selected = low_cols[alias.lower()]
                break
        mapping[target] = selected
    return mapping


def apply_data_mapping(
    df_raw: pd.DataFrame,
    mapping: dict[str, str],
    *,
    require_ml: bool,
    require_sto: bool,
) -> dict:
    out = df_raw.copy()
    req = required_fields(require_ml=require_ml, require_sto=require_sto)
    messages = [f"Wczytano dane: {len(out)} rekordów, {len(out.columns)} kolumn"]

    for target, source in mapping.items():
        if not source or source == "(brak)":
            continue
        out[target] = df_raw[source]
        messages.append(f"Mapowanie: {target} <- {source}")

    for field, default_value in DEFAULT_VALUES.items():
        if field not in out.columns:
            out[field] = default_value
            messages.append(f"Pole {field} niepodane, ustawiono domyślne: {default_value}")

    for field in NUMERIC_FIELDS:
        if field not in out.columns:
            continue
        out[field] = pd.to_numeric(out[field], errors="coerce")
        if field in req and out[field].isna().any():
            bad_count = int(out[field].isna().sum())
            raise ValueError(
                f"Kolumna '{field}' zawiera {bad_count} wartości nienumerycznych lub pustych."
            )

    if "ksztalt" in out.columns:
        out["ksztalt"] = out["ksztalt"].astype(str).str.strip().str.lower()
    if "material" in out.columns:
        out["material"] = out["material"].astype(str).str.strip().str.lower()
    if "sto_job_id" in out.columns:
        out["sto_job_id"] = out["sto_job_id"].astype(str).str.strip()

    return {"full_df": out, "messages": messages}
