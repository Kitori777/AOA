from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from AOA.config import MODELS_DIR

from .specs import MHModelSpec

CUSTOM_HEURISTIC_CONFIG = MODELS_DIR / "custom_sto_heuristics.json"


@dataclass(frozen=True)
class CustomHeuristicConfig:
    name: str
    label: str
    formula: str
    description: str


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_")
    if not cleaned:
        cleaned = "heuristic"
    if not cleaned.startswith("Custom_STO_"):
        cleaned = f"Custom_STO_{cleaned}"
    return cleaned[:80]


def load_custom_heuristic_configs(path: Path | None = None) -> tuple[CustomHeuristicConfig, ...]:
    path = path or CUSTOM_HEURISTIC_CONFIG
    if not path.exists():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    configs: list[CustomHeuristicConfig] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            configs.append(
                CustomHeuristicConfig(
                    name=_safe_name(str(item["name"])),
                    label=str(item.get("label") or item["name"]),
                    formula=str(item["formula"]),
                    description=str(item.get("description") or "Własna reguła sortowania STO."),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(configs)


def save_custom_heuristic_config(
    *,
    name: str,
    label: str,
    formula: str,
    description: str = "",
    path: Path | None = None,
) -> CustomHeuristicConfig:
    path = path or CUSTOM_HEURISTIC_CONFIG
    config = CustomHeuristicConfig(
        name=_safe_name(name),
        label=label.strip() or _safe_name(name),
        formula=formula.strip() or "d",
        description=description.strip() or "Własna reguła sortowania STO.",
    )
    _validate_formula(config.formula)
    configs = [item for item in load_custom_heuristic_configs(path) if item.name != config.name]
    configs.append(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(item) for item in sorted(configs, key=lambda item: item.name)]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return config


def get_custom_heuristic_specs() -> tuple[MHModelSpec, ...]:
    return tuple(
        MHModelSpec(
            config.name,
            config.label,
            f"Własna heurystyka STO: sortuje po wzorze score = {config.formula}.",
            config.description,
        )
        for config in load_custom_heuristic_configs()
    )


def get_custom_heuristic_config(name: str) -> CustomHeuristicConfig | None:
    return next((item for item in load_custom_heuristic_configs() if item.name == name), None)


def sequence_custom_heuristic(jobs: list[Any], config: CustomHeuristicConfig) -> list[Any]:
    return sorted(
        jobs,
        key=lambda job_index: (
            _evaluate_formula(config.formula, job_index[1], job_index[0], len(jobs)),
            job_index[1].deadline,
            job_index[1].processing_time,
            job_index[1].job_id,
        ),
    ) if jobs and isinstance(jobs[0], tuple) else _sequence_custom_plain(jobs, config)


def _sequence_custom_plain(jobs: list[Any], config: CustomHeuristicConfig) -> list[Any]:
    indexed = list(enumerate(jobs))
    ordered = sequence_custom_heuristic(indexed, config)
    return [job for _index, job in ordered]


def _evaluate_formula(formula: str, job: Any, index: int, n: int) -> float:
    p = float(job.processing_time)
    d = float(job.deadline)
    variables = {
        "p": p,
        "processing": p,
        "czas": p,
        "d": d,
        "deadline": d,
        "termin": d,
        "i": float(index + 1),
        "index": float(index + 1),
        "n": float(n),
        "slack": d - p,
        "cr": d / max(p, 1e-9),
        "urgency": p / max(d, 1e-9),
    }
    tree = ast.parse(formula, mode="eval")
    return float(_eval_node(tree.body, variables))


def _validate_formula(formula: str) -> None:
    try:
        _eval_node(ast.parse(formula, mode="eval").body, {"p": 1, "d": 2, "i": 1, "index": 1, "n": 1, "slack": 1, "cr": 2, "urgency": 0.5, "processing": 1, "deadline": 2, "czas": 1, "termin": 2})
    except Exception as exc:
        raise ValueError(
            "Wzór heurystyki może używać liczb, +, -, *, /, ** oraz zmiennych: p/czas, d/termin, slack, cr, urgency, i, n."
        ) from exc


def _eval_node(node: ast.AST, variables: dict[str, float]) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in variables:
        return float(variables[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, variables)
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / max(right, 1e-9)
        if isinstance(node.op, ast.Pow):
            return left**right
    raise ValueError("Niedozwolony element wzoru heurystyki.")
