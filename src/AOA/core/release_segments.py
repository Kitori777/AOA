from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DevelopmentSegment:
    name: str
    goal: str
    user_value: str
    commands: tuple[str, ...]
    checks: tuple[str, ...]


DEVELOPMENT_SEGMENTS: tuple[DevelopmentSegment, ...] = (
    DevelopmentSegment(
        name="ALICE Reviewer",
        goal="Ocena diagramu, raportu, wykresu, modelu i calego workflow.",
        user_value="Uzytkownik dostaje konkretna liste brakow przed eksportem albo decyzja.",
        commands=("ocen diagram", "ocen raport", "ocen wykres", "ocen model", "audyt workflow"),
        checks=("cel", "dane", "czytelnosc", "metryki", "ryzyka", "nastepny krok"),
    ),
    DevelopmentSegment(
        name="Scenario Lab",
        goal="Zapisywanie kilku scenariuszy parametrow i porownywanie wynikow.",
        user_value="Mozna testowac warianty bez gubienia ustawien.",
        commands=("scenariusze", "porownaj scenariusze", "zapisz scenariusz"),
        checks=("parametry", "metryki", "roznice", "najlepszy wariant"),
    ),
    DevelopmentSegment(
        name="Model Registry UI",
        goal="Karta modelu z metrykami, parametrami, plikiem .pkl i notatka.",
        user_value="Uzytkownik wie, ktory model wybral, kiedy byl trenowany i jak dzialal.",
        commands=("rejestr modeli", "karta modelu", "porownaj modele"),
        checks=("metryki", "data", "parametry", "plik", "notatka"),
    ),
    DevelopmentSegment(
        name="Workflow History",
        goal="Os czasu od danych do eksportu z mozliwoscia powtorzenia workflow.",
        user_value="Latwiej wrocic do poprzedniej pracy i odtworzyc wynik.",
        commands=("historia workflowow", "pokaz historie", "powtorz workflow"),
        checks=("dane", "modele", "wykresy", "raporty", "eksporty"),
    ),
    DevelopmentSegment(
        name="Dataset Library",
        goal="Biblioteka gotowych datasetow testowych dla wielu domen.",
        user_value="Osoba bez wlasnych danych moze od razu testowac aplikacje.",
        commands=("sample dane", "biblioteka danych", "wczytaj sample"),
        checks=("produkcja", "logistyka", "magazyn", "jakosc", "harmonogram", "serwis"),
    ),
    DevelopmentSegment(
        name="Report Templates",
        goal="Gotowe formaty raportow dla typowych potrzeb decyzyjnych.",
        user_value="Raport mozna zlozyc bez znajomosci LaTeX albo struktury analizy.",
        commands=("szablony raportow", "raport ml", "raport sto", "release report"),
        checks=("cel", "dane", "wyniki", "ryzyka", "rekomendacje"),
    ),
    DevelopmentSegment(
        name="Diagram QA",
        goal="Automatyczna kontrola jakosci diagramu.",
        user_value="Diagram nie wychodzi jako losowa plansza bez startu, konca albo legendy.",
        commands=("qa diagram", "sprawdz diagram", "ocen diagram"),
        checks=("start", "koniec", "decyzje", "samotne elementy", "polaczenia", "legenda"),
    ),
    DevelopmentSegment(
        name="Chart QA",
        goal="Kontrola osi, legendy, outlierow, HTML i czytelnosci wykresu.",
        user_value="Wykres mozna pokazac komus innemu bez tlumaczenia, co sie rozsypalo.",
        commands=("qa wykres", "ocen wykres", "sprawdz html"),
        checks=("osie", "jednostki", "legenda", "outliery", "tooltip", "eksport", "reset"),
    ),
    DevelopmentSegment(
        name="Data Contract",
        goal="Opis wymaganych kolumn, typow, zakresow i walidacji przed treningiem.",
        user_value="Uzytkownik wie, czemu dane nie przechodza treningu i co poprawic.",
        commands=("kontrakt danych", "walidacja danych", "sprawdz dane"),
        checks=("kolumny", "typy", "zakresy", "braki", "NaN", "inf"),
    ),
    DevelopmentSegment(
        name="Assistant Playbooks",
        goal="Tryby pracy ALICE: nauczyciel, operator, recenzent, analityk i kontroler release.",
        user_value="ALICE odpowiada odpowiednim stylem do zadania, a nie jednym szablonem.",
        commands=("tryby alice", "playbook alice", "co umiesz"),
        checks=("nauczyciel", "operator", "recenzent", "analityk", "release"),
    ),
)


REPORT_TEMPLATES: dict[str, tuple[str, ...]] = {
    "executive_summary": ("Cel decyzji", "Najwazniejszy wynik", "Ryzyko", "Rekomendowana akcja"),
    "ml_validation": ("Dane", "Model", "Metryki", "Baseline", "Interpretacja", "Ryzyka"),
    "sto_comparison": ("Metody STO", "Kolejka", "Opoznienia", "Bufor", "Najlepsza metoda"),
    "data_quality": ("Zakres danych", "Braki", "Duplikaty", "Outliery", "Kontrakt danych"),
    "release_check": ("Testy", "QA HTML", "ALICE", "README", "Changelog", "Tag"),
    "incident_review": ("Co sie stalo", "Wplyw", "Przyczyna", "Naprawa", "Zapobieganie"),
}


DATA_CONTRACT_FIELDS: dict[str, str] = {
    "czas_h": "liczba dodatnia; czas wykonania albo pracy",
    "termin_h": "liczba dodatnia; deadline lub oczekiwany termin",
    "koszt": "liczba nieujemna; koszt, cena albo wartosc operacji",
    "material": "kategoria lub liczba; material, typ produktu albo segment",
    "jakosc": "liczba lub etykieta; cel dla modeli Quality",
    "opoznienie": "liczba; cel dla modeli Delay",
    "schedule": "etykieta; cel klasyfikacji harmonogramu",
}


REQUIRED_HTML_CONTROLS = {
    "interactive_chart": (
        "ctl-chart",
        "ctl-library",
        "ctl-x",
        "ctl-y",
        "ctl-z",
        "ctl-redraw",
        "ctl-full",
        "ctl-png",
        "ctl-export-json",
        "ctl-reset",
        "tooltip",
    ),
    "dashboard": (
        "ctl-full",
        "ctl-export-csv",
        "ctl-export-json",
        "ctl-zoom-in",
        "ctl-zoom-out",
        "ctl-reset",
        "tooltip",
    ),
    "solution_tree": (
        "ctl-tree-zoom-in",
        "ctl-tree-zoom-out",
        "ctl-tree-zoom-reset",
        "ctl-delete-tree",
        "ctl-restore-tree",
        "tree-stats",
        "tree-hidden-list",
    ),
}


def list_development_segments() -> tuple[DevelopmentSegment, ...]:
    return DEVELOPMENT_SEGMENTS


def segment_summary() -> str:
    lines = ["Segmenty rozwoju AOA:"]
    for segment in DEVELOPMENT_SEGMENTS:
        commands = ", ".join(segment.commands)
        lines.append(f"- {segment.name}: {segment.goal} Komendy: {commands}.")
    return "\n".join(lines)


def report_template_summary() -> str:
    lines = ["Szablony raportow AOA:"]
    for name, sections in REPORT_TEMPLATES.items():
        lines.append(f"- {name}: {', '.join(sections)}")
    return "\n".join(lines)


def data_contract_summary() -> str:
    lines = ["Kontrakt danych AOA:"]
    for field, rule in DATA_CONTRACT_FIELDS.items():
        lines.append(f"- {field}: {rule}")
    lines.append("- zasady globalne: brak NaN/inf w cechach, zgodna liczba X/y, minimum 3 rekordy.")
    return "\n".join(lines)


def audit_html_controls(html_text: str, *, profile: str = "interactive_chart") -> dict[str, list[str]]:
    required = REQUIRED_HTML_CONTROLS.get(profile, REQUIRED_HTML_CONTROLS["interactive_chart"])
    missing = [control for control in required if control not in html_text]
    present = [control for control in required if control in html_text]
    return {"present": present, "missing": missing}


def audit_html_file(path: str | Path, *, profile: str = "interactive_chart") -> dict[str, list[str]]:
    html_text = Path(path).read_text(encoding="utf-8")
    return audit_html_controls(html_text, profile=profile)
