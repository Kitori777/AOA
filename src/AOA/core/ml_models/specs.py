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
        "Bazowy Random Forest dla jakości.",
        "stabilność, uśrednianie wielu drzew",
    ),
    MLModelSpec(
        "Quality_ET",
        "quality",
        "Quality ExtraTrees",
        "Losowy las z mocniej losowanymi progami.",
        "szybkie wychwytywanie nieliniowych zależności",
    ),
    MLModelSpec(
        "Quality_GB",
        "quality",
        "Quality GradientBoost",
        "Boosting poprawiający kolejne błędy jakości.",
        "błędy resztowe i trudniejsze przypadki",
    ),
    MLModelSpec(
        "Quality_HGB",
        "quality",
        "Quality HistGradient",
        "Szybszy boosting histogramowy dla większych danych.",
        "wydajność i zależności nieliniowe",
    ),
    MLModelSpec(
        "Delay",
        "delay",
        "Delay GB",
        "Bazowy Gradient Boosting dla opóźnień.",
        "ryzyko opóźnienia i duże błędy",
    ),
    MLModelSpec(
        "Delay_RF",
        "delay",
        "Delay RandomForest",
        "Losowy las przewidujący opóźnienie.",
        "stabilność predykcji opóźnień",
    ),
    MLModelSpec(
        "Delay_ET",
        "delay",
        "Delay ExtraTrees",
        "Szybki model drzew losowych dla opóźnień.",
        "warianty produkcji o podobnych terminach",
    ),
    MLModelSpec(
        "Delay_HGB",
        "delay",
        "Delay HistGradient",
        "Boosting histogramowy dla opóźnień.",
        "silne nieliniowości i większe próbki",
    ),
    MLModelSpec(
        "Schedule",
        "schedule",
        "Schedule RF",
        "Bazowy klasyfikator strategii harmonogramowania.",
        "najbardziej prawdopodobna strategia",
    ),
    MLModelSpec(
        "Schedule_ET",
        "schedule",
        "Schedule ExtraTrees",
        "Klasyfikator z mocniejszą losowością drzew.",
        "stabilność decyzji przy szumie",
    ),
    MLModelSpec(
        "Schedule_GB",
        "schedule",
        "Schedule GradientBoost",
        "Boosting klasyfikacyjny dla strategii.",
        "trudniejsze granice między klasami",
    ),
    MLModelSpec(
        "Schedule_LOG",
        "schedule",
        "Schedule Logistic",
        "Lekki model liniowy jako punkt odniesienia.",
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
    return ML_MODEL_SPECS


def get_ml_task(model_name: str) -> ModelTask:
    for spec in ML_MODEL_SPECS:
        if spec.name == model_name:
            return spec.task
    raise ValueError(f"Nieznany model ML: {model_name}")
