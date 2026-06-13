from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelTask = Literal["quality", "delay", "schedule"]


@dataclass(frozen=True)
class MLModelSpec:
    name: str
    task: ModelTask
    label: str
    description: str
    focus: str


ML_MODEL_SPECS: tuple[MLModelSpec, ...] = (
    MLModelSpec(
        "Quality",
        "quality",
        "Quality RF",
        "Random Forest Regressor dla predykcji jakosci.",
        "stabilnosc, bagging i usrednianie wielu drzew",
    ),
    MLModelSpec(
        "Quality_ET",
        "quality",
        "Quality ExtraTrees",
        "ExtraTrees Regressor z mocniej losowanymi progami podzialu.",
        "szybkie wychwytywanie nieliniowych zaleznosci",
    ),
    MLModelSpec(
        "Quality_GB",
        "quality",
        "Quality GradientBoost",
        "Gradient Boosting Regressor poprawiajacy bledy poprzednich drzew.",
        "bledy resztowe i trudniejsze przypadki",
    ),
    MLModelSpec(
        "Quality_HGB",
        "quality",
        "Quality HistGradient",
        "HistGradient Boosting Regressor dla wiekszych danych.",
        "wydajnosc i zaleznosci nieliniowe",
    ),
    MLModelSpec(
        "Delay",
        "delay",
        "Delay GB",
        "Gradient Boosting Regressor dla przewidywania opoznien.",
        "ryzyko opoznienia i duze bledy",
    ),
    MLModelSpec(
        "Delay_RF",
        "delay",
        "Delay RandomForest",
        "Random Forest Regressor dla stabilnej predykcji opoznien.",
        "stabilnosc predykcji opoznien",
    ),
    MLModelSpec(
        "Delay_ET",
        "delay",
        "Delay ExtraTrees",
        "ExtraTrees Regressor dla opoznien i danych z szumem.",
        "warianty produkcji o podobnych terminach",
    ),
    MLModelSpec(
        "Delay_HGB",
        "delay",
        "Delay HistGradient",
        "HistGradient Boosting Regressor dla opoznien.",
        "silne nieliniowosci i wieksze probki",
    ),
    MLModelSpec(
        "Schedule",
        "schedule",
        "Schedule RF",
        "Random Forest Classifier dla wyboru strategii harmonogramowania.",
        "najbardziej prawdopodobna strategia",
    ),
    MLModelSpec(
        "Schedule_ET",
        "schedule",
        "Schedule ExtraTrees",
        "ExtraTrees Classifier z mocniejsza losowoscia drzew.",
        "stabilnosc decyzji przy szumie",
    ),
    MLModelSpec(
        "Schedule_GB",
        "schedule",
        "Schedule GradientBoost",
        "Gradient Boosting Classifier dla trudniejszych granic klas.",
        "trudniejsze granice miedzy klasami",
    ),
    MLModelSpec(
        "Schedule_LOG",
        "schedule",
        "Schedule Logistic",
        "Regresja logistyczna jako liniowy baseline klasyfikacyjny.",
        "prosty baseline i czytelna decyzja",
    ),
)

ML_MODEL_NAMES = {spec.name for spec in ML_MODEL_SPECS}
ML_MODEL_LABELS = {spec.name: spec.label for spec in ML_MODEL_SPECS}
ML_MODEL_FOCUS = {spec.name: spec.focus for spec in ML_MODEL_SPECS}
ML_MODELS_BY_TASK: dict[ModelTask, tuple[str, ...]] = {
    "quality": tuple(spec.name for spec in ML_MODEL_SPECS if spec.task == "quality"),
    "delay": tuple(spec.name for spec in ML_MODEL_SPECS if spec.task == "delay"),
    "schedule": tuple(spec.name for spec in ML_MODEL_SPECS if spec.task == "schedule"),
}


def get_ml_model_specs() -> tuple[MLModelSpec, ...]:
    from .custom import get_custom_model_specs

    return (*ML_MODEL_SPECS, *get_custom_model_specs())


def get_ml_model_names() -> set[str]:
    return {spec.name for spec in get_ml_model_specs()}


def get_ml_task(model_name: str) -> ModelTask:
    for spec in get_ml_model_specs():
        if spec.name == model_name:
            return spec.task
    raise ValueError(f"Nieznany model ML: {model_name}")
