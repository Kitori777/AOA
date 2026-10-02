from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

SUPPORTED_MATERIALS = frozenset({"bawelna", "mikrofibra", "poliester", "wiskoza"})


@dataclass(frozen=True)
class MachineProfile:
    machine_id: int
    speed_factor: float = 1.0
    waste_factor: float = 1.0
    energy_kwh_per_hour: float = 4.0
    supported_materials: frozenset[str] = SUPPORTED_MATERIALS


def build_machine_profiles(n_machines: int) -> tuple[MachineProfile, ...]:
    if n_machines <= 0 or n_machines > 8:
        raise ValueError("n_machines musi miec wartosc od 1 do 8")
    templates = (
        (1.00, 1.00, 4.0, SUPPORTED_MATERIALS),
        (1.12, 0.92, 4.8, frozenset({"bawelna", "mikrofibra", "poliester"})),
        (0.94, 0.86, 3.7, frozenset({"mikrofibra", "poliester", "wiskoza"})),
        (1.06, 0.96, 4.3, frozenset({"bawelna", "poliester", "wiskoza"})),
    )
    profiles: list[MachineProfile] = []
    for index in range(n_machines):
        speed, waste, energy, materials = templates[index % len(templates)]
        if n_machines == 1:
            materials = SUPPORTED_MATERIALS
        profiles.append(
            MachineProfile(
                machine_id=index + 1,
                speed_factor=speed,
                waste_factor=waste,
                energy_kwh_per_hour=energy,
                supported_materials=materials,
            )
        )
    return tuple(profiles)


def _eligible_machine_ids(value: Any, profiles: tuple[MachineProfile, ...]) -> set[int]:
    available = {profile.machine_id for profile in profiles}
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return available
    if isinstance(value, (list, tuple, set, frozenset)):
        parsed = {int(item) for item in value}
    else:
        normalized = str(value).replace(",", "|").replace(";", "|")
        parsed = {int(item.strip()) for item in normalized.split("|") if item.strip()}
    return parsed & available


def _changeover_values(row: pd.Series, previous: pd.Series | None) -> tuple[float, float]:
    if previous is None:
        return 0.0, 0.0
    material_changed = str(row.get("material", "")) != str(previous.get("material", ""))
    shape_changed = str(row.get("ksztalt", "")) != str(previous.get("ksztalt", ""))
    if not material_changed and not shape_changed:
        return 0.0, 0.0
    base_setup = max(0.0, float(row.get("czas_przezbrojenia_h", 0.0)))
    multiplier = 1.0 if material_changed else 0.45
    if material_changed and shape_changed:
        multiplier = 1.2
    setup = base_setup * multiplier
    base_changeover_waste = max(0.0, float(row.get("odpad_przezbrojenia_kg", 0.0)))
    return setup, base_changeover_waste * multiplier


def simulate_schedule(
    df: pd.DataFrame,
    time_col: str = "czas_produkcji_h",
    *,
    n_machines: int = 1,
    machine_profiles: tuple[MachineProfile, ...] | None = None,
    objective: str = "deadline_then_waste",
    unavailable_machines: tuple[int, ...] = (),
) -> pd.DataFrame:
    """Dispatch jobs to parallel machines and append timing/resource columns."""

    if df is None or df.empty:
        raise ValueError("Brak danych do harmonogramowania.")
    if time_col not in df.columns or "termin_h" not in df.columns:
        raise ValueError("Harmonogram wymaga kolumn czasu produkcji i terminu.")
    profiles = machine_profiles or build_machine_profiles(n_machines)
    if len(profiles) != n_machines:
        raise ValueError("Liczba profili maszyn nie zgadza sie z n_machines.")
    unavailable = set(unavailable_machines)
    invalid_unavailable = sorted(
        machine_id for machine_id in unavailable if machine_id < 1 or machine_id > n_machines
    )
    if invalid_unavailable:
        raise ValueError(
            "Niedostepne maszyny sa poza zakresem 1-n_machines: "
            + ", ".join(map(str, invalid_unavailable))
        )

    availability = {profile.machine_id: 0.0 for profile in profiles}
    previous_rows: dict[int, pd.Series | None] = {profile.machine_id: None for profile in profiles}
    scheduled_rows: list[dict[str, Any]] = []

    for source_order, (_, source_row) in enumerate(df.iterrows(), start=1):
        row = source_row.copy()
        if str(row.get("stock_status", "")).upper() == "UNSCHEDULABLE":
            record = row.to_dict()
            record.update(
                {
                    "setup_start": float("nan"),
                    "setup_h_actual": 0.0,
                    "t_start": float("nan"),
                    "t_end": float("nan"),
                    "lateness_h": 0.0,
                    "waste_kg_actual": 0.0,
                    "changeover_waste_kg": 0.0,
                    "energy_kwh_actual": 0.0,
                    "machine_id": 0,
                    "machine_speed_factor": float("nan"),
                    "machine_waste_factor": float("nan"),
                    "schedule_order": source_order,
                    "scheduled": False,
                    "unscheduled_reason": "Brak kompletu komponentow.",
                }
            )
            scheduled_rows.append(record)
            continue
        material = str(row.get("material", ""))
        declared = _eligible_machine_ids(row.get("dozwolone_maszyny"), profiles)
        supported = [
            profile
            for profile in profiles
            if profile.machine_id in declared
            and (not material or material in profile.supported_materials)
        ]
        eligible = [profile for profile in supported if profile.machine_id not in unavailable]
        if not eligible:
            job_id = row.get("zlecenie_id", row.get("sto_job_id", source_order))
            reason = (
                "Wszystkie dozwolone maszyny sa niedostepne."
                if supported
                else f"Brak maszyny obslugujacej material {material or 'bez ograniczen'}."
            )
            record = row.to_dict()
            record.update(
                {
                    "setup_start": float("nan"),
                    "setup_h_actual": 0.0,
                    "t_start": float("nan"),
                    "t_end": float("nan"),
                    "lateness_h": 0.0,
                    "waste_kg_actual": 0.0,
                    "changeover_waste_kg": 0.0,
                    "energy_kwh_actual": 0.0,
                    "material_wait_h_actual": 0.0,
                    "machine_id": 0,
                    "machine_speed_factor": float("nan"),
                    "machine_waste_factor": float("nan"),
                    "schedule_order": source_order,
                    "scheduled": False,
                    "unscheduled_reason": f"{job_id}: {reason}",
                }
            )
            scheduled_rows.append(record)
            continue

        candidates: list[tuple[tuple[float, ...], MachineProfile, dict[str, float]]] = []
        for profile in eligible:
            setup_h, changeover_waste = _changeover_values(row, previous_rows[profile.machine_id])
            raw_release = row.get("components_ready_h", 0.0)
            release_h = 0.0 if raw_release is None or pd.isna(raw_release) else max(0.0, float(raw_release))
            setup_start = max(availability[profile.machine_id], release_h)
            start = setup_start + setup_h
            processing = max(0.0, float(row[time_col])) / max(profile.speed_factor, 1e-9)
            end = start + processing
            lateness = max(0.0, end - float(row["termin_h"]))
            base_waste = max(0.0, float(row.get("odpad_kg", row.get("odpad", 0.0))))
            waste = base_waste * profile.waste_factor + changeover_waste
            energy_value = row.get("energia_kwh")
            if energy_value is None or pd.isna(energy_value):
                energy = processing * profile.energy_kwh_per_hour
            else:
                base_time = max(float(row[time_col]), 1e-9)
                energy = (
                    max(0.0, float(energy_value))
                    * (processing / base_time)
                    * (profile.energy_kwh_per_hour / 4.0)
                )
            metrics = {
                "setup_start": setup_start,
                "setup_h_actual": setup_h,
                "t_start": start,
                "t_end": end,
                "lateness_h": lateness,
                "waste_kg_actual": waste,
                "changeover_waste_kg": changeover_waste,
                "energy_kwh_actual": energy,
                "material_wait_h_actual": max(
                    0.0, release_h - availability[profile.machine_id]
                ),
            }
            if objective == "waste":
                key = (waste, lateness, end, float(profile.machine_id))
            elif objective == "makespan":
                key = (end, lateness, waste, float(profile.machine_id))
            else:
                key = (lateness, waste, end, float(profile.machine_id))
            candidates.append((key, profile, metrics))

        _, selected_profile, metrics = min(candidates, key=lambda item: item[0])
        machine_id = selected_profile.machine_id
        availability[machine_id] = metrics["t_end"]
        previous_rows[machine_id] = row
        record = row.to_dict()
        record.update(metrics)
        record["machine_id"] = machine_id
        record["machine_speed_factor"] = selected_profile.speed_factor
        record["machine_waste_factor"] = selected_profile.waste_factor
        record["schedule_order"] = source_order
        record["scheduled"] = True
        record["unscheduled_reason"] = ""
        scheduled_rows.append(record)

    out = pd.DataFrame(scheduled_rows).reset_index(drop=True)
    makespan_value = out["t_end"].max()
    makespan = 0.0 if pd.isna(makespan_value) else float(makespan_value)
    total_lateness = float(out["lateness_h"].sum())
    total_waste = float(out["waste_kg_actual"].sum())
    total_energy = float(out["energy_kwh_actual"].sum())
    out["total_time"] = makespan
    out["makespan_h"] = makespan
    out["total_lateness"] = total_lateness
    out["total_waste_kg"] = total_waste
    out["total_energy_kwh"] = total_energy
    return out


def optimize_schedule(
    df: pd.DataFrame,
    time_col: str = "czas_produkcji_h",
    alpha: float = 1.0,
    beta: float = 2.0,
    *,
    n_machines: int = 1,
) -> pd.DataFrame:
    """Choose the best priority strategy for one or more parallel machines."""

    strategies = {
        "EDF": lambda d: d.sort_values("termin_h"),
        "SPT": lambda d: d.sort_values(time_col),
        "LPT": lambda d: d.sort_values(time_col, ascending=False),
        "Slack": lambda d: d.assign(slack=d["termin_h"] - d[time_col]).sort_values("slack"),
    }
    if "material" in df.columns:
        strategies["ECO"] = lambda d: d.sort_values(
            ["material", "ksztalt", "termin_h"], kind="stable"
        )

    best_score = float("inf")
    best_df: pd.DataFrame | None = None
    for name, strategy in strategies.items():
        scheduled = simulate_schedule(strategy(df.copy()), time_col, n_machines=n_machines)
        score = (
            alpha * float(scheduled["makespan_h"].iloc[0])
            + beta * float(scheduled["total_lateness"].iloc[0])
            + 0.15 * float(scheduled["total_waste_kg"].iloc[0])
        )
        if score < best_score:
            best_score = score
            best_df = scheduled
            best_df["strategy"] = name

    assert best_df is not None
    return best_df


def extract_schedule_features(df: pd.DataFrame) -> dict[str, float]:
    """Aggregate a schedule candidate into numeric features for training."""

    return {
        "n_jobs": len(df),
        "mean_time": df["czas_produkcji_h"].mean(),
        "std_time": df["czas_produkcji_h"].std(),
        "max_time": df["czas_produkcji_h"].max(),
        "mean_deadline": df["termin_h"].mean(),
        "load_ratio": df["czas_produkcji_h"].sum() / (df["termin_h"].sum() + 1e-6),
    }


def generate_schedule_label(
    df: pd.DataFrame,
    alpha: float = 1.0,
    beta: float = 2.0,
    *,
    n_machines: int = 1,
) -> str:
    """Return the best strategy label for a schedule candidate."""

    best = optimize_schedule(df, alpha=alpha, beta=beta, n_machines=n_machines)
    return str(best["strategy"].iloc[0])
