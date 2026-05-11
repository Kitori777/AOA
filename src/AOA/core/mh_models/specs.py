from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MHModelSpec:
    name: str
    label: str
    description: str
    focus: str


MH_MODEL_SPECS: tuple[MHModelSpec, ...] = (
    MHModelSpec("MT", "MT / EDD", "Sortowanie po wymaganym terminie rosnąco.", "termin realizacji"),
    MHModelSpec(
        "MO",
        "MO / SPT",
        "Sortowanie po czasie obróbki rosnąco.",
        "krótkie zlecenia i szybkie odblokowanie kolejki",
    ),
    MHModelSpec(
        "MZO",
        "MZO / LPT",
        "Sortowanie po czasie obróbki malejąco.",
        "długie zlecenia i obciążenie startu",
    ),
    MHModelSpec(
        "GENETIC",
        "GENETIC",
        "Mutacyjna poprawa populacji kolejności.",
        "najniższe STO w większej przestrzeni wariantów",
    ),
    MHModelSpec(
        "SLACK",
        "Slack",
        "Najpierw najmniejszy zapas: termin minus czas.",
        "zlecenia z małym buforem",
    ),
    MHModelSpec(
        "CR",
        "Critical Ratio",
        "Relacja terminu do czasu obróbki.",
        "krytyczność terminu względem długości",
    ),
    MHModelSpec(
        "EDD_SPT",
        "EDD + SPT",
        "Termin jako główne kryterium, czas jako dogrywka.",
        "termin z rozstrzyganiem krótszym czasem",
    ),
    MHModelSpec(
        "SPT_EDD",
        "SPT + EDD",
        "Czas jako główne kryterium, termin jako dogrywka.",
        "krótki czas z kontrolą terminu",
    ),
    MHModelSpec(
        "LPT_EDD", "LPT + EDD", "Długie zlecenia najpierw, potem termin.", "duże operacje i termin"
    ),
    MHModelSpec(
        "NEH",
        "NEH-like",
        "Budowanie sekwencji przez wstawianie zleceń w najlepsze miejsce.",
        "iteracyjne zmniejszanie STO",
    ),
    MHModelSpec(
        "LOCAL_SEARCH",
        "Local Search",
        "Start od MT i lokalne zamiany sąsiadów.",
        "poprawki po metodzie terminowej",
    ),
    MHModelSpec(
        "RANDOM_RESTART",
        "Random Restart",
        "Wiele losowych startów i wybór najlepszego STO.",
        "przegląd różnych wariantów kolejności",
    ),
)

MH_MODEL_NAMES = {spec.name for spec in MH_MODEL_SPECS}
MH_MODEL_LABELS = {spec.name: spec.label for spec in MH_MODEL_SPECS}
MH_MODEL_FOCUS = {spec.name: spec.focus for spec in MH_MODEL_SPECS}


def get_mh_model_specs() -> tuple[MHModelSpec, ...]:
    return MH_MODEL_SPECS
