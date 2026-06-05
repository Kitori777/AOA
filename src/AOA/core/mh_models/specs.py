from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MHModelSpec:
    name: str
    label: str
    description: str
    focus: str


MH_MODEL_SPECS: tuple[MHModelSpec, ...] = (
    MHModelSpec("MT", "MT / EDD", "Sortuje zlecenia po terminie rosnaco.", "termin realizacji"),
    MHModelSpec(
        "MO",
        "MO / SPT",
        "Sortuje zlecenia po czasie obrobki rosnaco.",
        "krotkie zlecenia i szybkie odblokowanie kolejki",
    ),
    MHModelSpec(
        "MZO",
        "MZO / LPT",
        "Sortuje zlecenia po czasie obrobki malejaco.",
        "dlugie zlecenia i obciazenie startu",
    ),
    MHModelSpec(
        "MOPT",
        "MOpt",
        "Przeglada mozliwe kolejnosci i wybiera najnizsza sume dodatnich opoznien.",
        "dokladny wybor kolejnosci zlecen",
    ),
    MHModelSpec(
        "GENETIC",
        "GENETIC",
        "Ulepsza populacje kolejnosci przez selekcje, krzyzowanie i mutacje.",
        "najlepsze STO w wiekszej przestrzeni wariantow",
    ),
    MHModelSpec(
        "SLACK",
        "Slack",
        "Najpierw wybiera zlecenia z najmniejszym zapasem czasu.",
        "zlecenia z malym buforem",
    ),
    MHModelSpec(
        "CR",
        "Critical Ratio",
        "Sortuje wedlug relacji czasu do terminu, zeby pokazac krytycznosc.",
        "krytycznosc terminu wzgledem dlugosci",
    ),
    MHModelSpec(
        "EDD_SPT",
        "EDD + SPT",
        "Termin jest glownym kryterium, a krotki czas rozstrzyga remisy.",
        "termin z rozstrzyganiem krotszym czasem",
    ),
    MHModelSpec(
        "SPT_EDD",
        "SPT + EDD",
        "Czas obrobki jest glownym kryterium, a termin rozstrzyga remisy.",
        "krotki czas z kontrola terminu",
    ),
    MHModelSpec(
        "LPT_EDD",
        "LPT + EDD",
        "Dlugie zlecenia ida najpierw, potem decyduje termin.",
        "duze operacje i termin",
    ),
    MHModelSpec(
        "NEH",
        "NEH-like",
        "Buduje sekwencje przez wstawianie kolejnych zlecen w najlepsze miejsce.",
        "iteracyjne zmniejszanie STO",
    ),
    MHModelSpec(
        "LOCAL_SEARCH",
        "Local Search",
        "Startuje od kolejki terminowej i sprawdza lokalne zamiany sasiadow.",
        "poprawki po metodzie terminowej",
    ),
    MHModelSpec(
        "RANDOM_RESTART",
        "Random Restart",
        "Sprawdza wiele losowych startow i wybiera najlepszy wynik STO.",
        "przeglad roznych wariantow kolejnosci",
    ),
)

MH_MODEL_NAMES = {spec.name for spec in MH_MODEL_SPECS}
MH_MODEL_LABELS = {spec.name: spec.label for spec in MH_MODEL_SPECS}
MH_MODEL_FOCUS = {spec.name: spec.focus for spec in MH_MODEL_SPECS}


def get_mh_model_specs() -> tuple[MHModelSpec, ...]:
    return MH_MODEL_SPECS
