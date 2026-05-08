from __future__ import annotations

from datetime import datetime
from pathlib import Path

from AOA.config import DATA_DIR, MODELS_DIR


def sanitize_filename(text: str) -> str:
    text = str(text).strip().replace(" ", "_")
    keep = []
    for char in text:
        if char.isalnum() or char in {"_", "-", "."}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep)


def build_model_filename(selected_models, metadata, backend="classic"):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    models_part = "-".join(sorted([m.lower() for m in selected_models])) or "unknown"
    backend_part = sanitize_filename(backend.lower()) if backend else "classic"
    n_part = f"{metadata.get('n', 'x')}r"
    mach_part = f"{metadata.get('n_machines', 'x')}m"
    kszt_part = (
        "-".join(metadata.get("ksztalty", [])) if metadata.get("ksztalty", []) else "allshapes"
    )
    mat_part = (
        "-".join(metadata.get("materialy", [])) if metadata.get("materialy", []) else "allmaterials"
    )
    filename = f"model_{backend_part}_{models_part}_{n_part}_{mach_part}_{kszt_part}_{mat_part}_{stamp}.pkl"
    return MODELS_DIR / sanitize_filename(filename)


def build_sto_model_filename(selected_methods):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    methods_part = "-".join(sorted([m.lower() for m in selected_methods])) or "unknown"
    return MODELS_DIR / sanitize_filename(f"model_sto_{methods_part}_{stamp}.pkl")


def build_result_filename(model_name: str, source_name: str, suffix: str = ".csv") -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_part = sanitize_filename(model_name.lower())
    source_part = sanitize_filename(source_name.lower())
    return DATA_DIR / f"wynik_priority_{model_part}_{source_part}_{stamp}{suffix}"
