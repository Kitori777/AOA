from __future__ import annotations

from AOA.messages import (
    DEADLINE_MIN_GT_MAX,
    MUST_BE_FLOAT,
    MUST_BE_INT,
    MUST_BE_POSITIVE,
    MUST_SELECT_MATERIAL,
    MUST_SELECT_SHAPE,
    PROD_MIN_GT_MAX,
    TEST_SIZE_TOO_LARGE,
)

ML_MODEL_NAMES = {"Quality", "Delay", "Schedule"}
STO_MODEL_NAMES = {"MT", "MO", "MZO", "GENETIC"}


def _parse_positive_int(value, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(MUST_BE_INT.format(field=field_name)) from None

    if number <= 0:
        raise ValueError(MUST_BE_POSITIVE)
    return number


def _parse_positive_float(value, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(MUST_BE_FLOAT.format(field=field_name)) from None

    if number <= 0:
        raise ValueError(MUST_BE_POSITIVE)
    return number


def split_selected_models(selected_models: list[str]) -> tuple[list[str], list[str]]:
    selected_models = selected_models or []
    ml_models = [name for name in selected_models if name in ML_MODEL_NAMES]
    sto_models = [name for name in selected_models if name in STO_MODEL_NAMES]
    return ml_models, sto_models


def parse_generation_config(raw_config: dict) -> dict:
    n = _parse_positive_int(raw_config.get("n", ""), "n")
    n_machines = _parse_positive_int(raw_config.get("n_machines", ""), "n_machines")

    test_size = float(raw_config.get("test_size", ""))
    if test_size <= 0:
        raise ValueError(MUST_BE_POSITIVE)
    if test_size >= 1:
        raise ValueError(TEST_SIZE_TOO_LARGE)

    seed = _parse_positive_int(raw_config.get("seed", ""), "seed")
    prod_min = _parse_positive_float(raw_config.get("prod_min", ""), "prod_min")
    prod_max = _parse_positive_float(raw_config.get("prod_max", ""), "prod_max")
    deadline_min = _parse_positive_float(raw_config.get("deadline_min", ""), "deadline_min")
    deadline_max = _parse_positive_float(raw_config.get("deadline_max", ""), "deadline_max")

    if prod_min > prod_max:
        raise ValueError(PROD_MIN_GT_MAX)
    if deadline_min > deadline_max:
        raise ValueError(DEADLINE_MIN_GT_MAX)

    selected_ksztalty = raw_config.get("selected_ksztalty", [])
    selected_materialy = raw_config.get("selected_materialy", [])

    if not selected_ksztalty:
        raise ValueError(MUST_SELECT_SHAPE)
    if not selected_materialy:
        raise ValueError(MUST_SELECT_MATERIAL)

    return {
        "n": n,
        "n_machines": n_machines,
        "test_size": test_size,
        "seed": seed,
        "prod_min": prod_min,
        "prod_max": prod_max,
        "deadline_min": deadline_min,
        "deadline_max": deadline_max,
        "selected_ksztalty": selected_ksztalty,
        "selected_materialy": selected_materialy,
    }
