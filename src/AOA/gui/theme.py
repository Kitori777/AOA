from __future__ import annotations

COLORS = {
    "app_bg": "#071019",
    "sidebar": "#091722",
    "surface": "#0c1b28",
    "surface_raised": "#102333",
    "surface_hover": "#173247",
    "border": "#20384b",
    "border_soft": "#172d3e",
    "primary": "#1479d1",
    "primary_hover": "#1b8bea",
    "primary_muted": "#113f6b",
    "text": "#edf6ff",
    "text_muted": "#91a7ba",
    "success": "#35c98b",
}

PAGE_META: dict[str, tuple[str, str]] = {
    "EngineeringModePage": (
        "Praca inzynierska",
        "ESM: 7 metod, przyklady 4-10 zlecen, drzewo MOpt i Gantt 1-3 maszyn",
    ),
    "ReadmePage": ("Start", "Przeglad mozliwosci i szybkie kroki"),
    "MainPage": ("Modele i optymalizacja", "Dane, trening, STO i linie produkcyjne"),
    "QueueDashboardPage": (
        "Auto Queue",
        "Stala kolejka CSV, porownanie heurystyk i automatyczne archiwum DONE",
    ),
    "VisualPage": ("Visual Lab", "Wykresy, dashboardy i eksploracja danych"),
    "ResultsPage": ("Results Studio", "Tabele, filtry, SQL i eksport wynikow"),
    "AnalyticsPage": ("Report Studio", "Raporty, KPI i materialy decyzyjne"),
    "DrawIOPage": ("Diagrams", "Procesy, architektura i diagramy produkcyjne"),
    "TheoryPage": ("Theory", "Wyjasnienia modeli i metod optymalizacji"),
}
