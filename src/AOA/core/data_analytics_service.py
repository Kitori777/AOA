from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

ANALYTICS_WORKFLOWS = [
    "Index",
    "Analyze Data Quality",
    "Executive Summary",
    "Build Dashboard",
    "Build Report",
    "ML Analytics",
    "STO Analytics",
    "Prediction Plan",
    "Design KPIs",
    "KPI Reporting",
    "Metric Diagnostics",
    "Product Business Analysis",
    "Opportunity Sizing",
    "Market Sizing",
    "Visualize Data",
    "Statistical Summary",
    "Segment Explorer",
    "Correlation Explorer",
    "Outlier Analysis",
    "Pivot Summary",
    "Data Dictionary",
    "Time Trend",
    "Chart QA",
    "Risk & Caveats",
    "Action Plan",
    "Gather Business Context",
    "Jupyter Notebook Plan",
]


@dataclass(frozen=True)
class AnalyticsResult:
    title: str
    body: str
    recommended_chart: str


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=[np.number]).columns.tolist()


def _categorical_columns(df: pd.DataFrame) -> list[str]:
    numeric = set(_numeric_columns(df))
    return [column for column in df.columns if column not in numeric]


def _safe_metric(df: pd.DataFrame, metric: str | None) -> str | None:
    numeric = _numeric_columns(df)
    if metric in numeric:
        return metric
    return numeric[0] if numeric else None


def _safe_dimension(df: pd.DataFrame, dimension: str | None) -> str | None:
    if dimension in df.columns:
        return dimension
    categorical = _categorical_columns(df)
    return categorical[0] if categorical else (df.columns[0] if len(df.columns) else None)


def _safe_dimension_for_metric(
    df: pd.DataFrame, metric: str | None, dimension: str | None
) -> str | None:
    dimension = _safe_dimension(df, dimension)
    if dimension and dimension != metric:
        return dimension
    categorical = [column for column in _categorical_columns(df) if column != metric]
    if categorical:
        return categorical[0]
    alternatives = [column for column in df.columns if column != metric]
    return alternatives[0] if alternatives else None


def _column_series(df: pd.DataFrame, column: str | None) -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series(dtype=object)
    selected = df[column]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


def _quality_score(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    total_cells = max(1, int(df.shape[0] * df.shape[1]))
    missing_rate = float(df.isna().sum().sum()) / total_cells
    duplicate_rate = float(df.duplicated().sum()) / max(1, len(df))
    return max(0.0, min(100.0, 100.0 * (1.0 - missing_rate * 0.7 - duplicate_rate * 0.3)))


def _basic_profile(df: pd.DataFrame) -> list[str]:
    numeric = _numeric_columns(df)
    categorical = _categorical_columns(df)
    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())
    return [
        f"- Wiersze: {len(df):,}",
        f"- Kolumny: {len(df.columns):,}",
        f"- Kolumny liczbowe: {len(numeric):,}",
        f"- Kolumny opisowe/kategorie: {len(categorical):,}",
        f"- Braki danych: {missing:,}",
        f"- Duplikaty: {duplicates:,}",
        f"- Ocena jakosci danych: {_quality_score(df):.1f}/100",
    ]


def _metric_stats(df: pd.DataFrame, metric: str | None) -> dict[str, float]:
    metric = _safe_metric(df, metric)
    if not metric:
        return {}
    series = pd.to_numeric(_column_series(df, metric), errors="coerce").dropna()
    if series.empty:
        return {}
    return {
        "count": float(series.count()),
        "sum": float(series.sum()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "min": float(series.min()),
        "max": float(series.max()),
        "std": float(series.std(ddof=0)),
        "q25": float(series.quantile(0.25)),
        "q75": float(series.quantile(0.75)),
    }


def _format_stats(stats: dict[str, float], metric: str | None) -> list[str]:
    if not stats:
        return ["- Brak stabilnej kolumny liczbowej do policzenia statystyk."]
    return [
        f"- Metryka: {metric}",
        f"- Liczba obserwacji: {stats['count']:,.0f}",
        f"- Suma: {stats['sum']:,.3f}",
        f"- Srednia / mediana: {stats['mean']:,.3f} / {stats['median']:,.3f}",
        f"- Min / max: {stats['min']:,.3f} / {stats['max']:,.3f}",
        f"- Q25 / Q75: {stats['q25']:,.3f} / {stats['q75']:,.3f}",
        f"- Odchylenie standardowe: {stats['std']:,.3f}",
    ]


def _opportunity_lines(df: pd.DataFrame, metric: str | None, dimension: str | None) -> list[str]:
    metric = _safe_metric(df, metric)
    dimension = _safe_dimension_for_metric(df, metric, dimension)
    if not metric or not dimension:
        return ["- Brak metryki albo wymiaru do policzenia okazji."]
    work = pd.DataFrame(
        {
            "segment": _column_series(df, dimension).astype(str),
            "metric": pd.to_numeric(_column_series(df, metric), errors="coerce"),
        }
    ).dropna()
    if work.empty:
        return ["- Brak danych po usunieciu pustych wartosci."]
    total = work["metric"].sum()
    grouped = (
        work.groupby("segment", dropna=False)["metric"]
        .agg(["count", "sum", "mean"])
        .sort_values("sum", ascending=False)
        .head(8)
    )
    lines = [f"- Wymiar okazji: {dimension}", f"- Calkowita suma metryki: {total:,.3f}"]
    for segment, row in grouped.iterrows():
        share = (row["sum"] / total * 100.0) if total else 0.0
        lines.append(
            f"- {segment}: suma={row['sum']:,.3f}, udzial={share:.1f}%, srednia={row['mean']:,.3f}, n={int(row['count'])}"
        )
    return lines


def _chart_qa_lines(df: pd.DataFrame, metric: str | None, dimension: str | None) -> list[str]:
    numeric = _numeric_columns(df)
    categorical = _categorical_columns(df)
    rows = len(df)
    lines = [
        "Kontrola doboru wykresow HTML:",
        f"- Obserwacje: {rows}",
        f"- Kolumny liczbowe: {', '.join(numeric[:8]) or 'brak'}",
        f"- Kategorie/wymiary: {', '.join(categorical[:8]) or 'brak'}",
    ]
    if rows < 8:
        lines.append(
            "- Scatter/regresja moga byc za slabe: jest mniej niz 8 punktow. Lepiej pokazac tabele, KPI albo bar."
        )
    elif rows < 20:
        lines.append(
            "- Scatter jest mozliwy, ale traktuj go jako podglad, nie dowod silnego trendu."
        )
    else:
        lines.append(
            "- Scatter, regresja, outlier map i heatmap density maja wystarczajaco punktow na pierwszy podglad."
        )
    if len(numeric) >= 2:
        lines.append(
            "- Dobre HTML: Scatter, Regression Plot, CorrelationMatrix, Model Diagnostics, Bubble Chart."
        )
    if categorical:
        lines.append(
            "- Dobre HTML: Bar Chart, Pie Chart tylko dla kilku kategorii, Column Ranking i Dashboard."
        )
    if metric:
        lines.append(f"- Metryka startowa: {metric}. Do raportu dodaj jednostke i interpretacje.")
    if dimension:
        lines.append(
            f"- Wymiar startowy: {dimension}. Sprawdz, czy segmenty nie sa zbyt drobne albo puste."
        )
    lines += [
        "- Unikaj Pie Chart przy wielu kategoriach: lepszy bedzie Bar Chart/Column Ranking.",
        "- Do drzew uzywaj SolutionTree, gdy dane maja node_id/parent_id albo dane STO.",
        "- Do HTML wybieraj Plotly/Altair dla eksportu i tooltipow; D3 jest najlepszy do drzew i dashboardow.",
    ]
    return lines


def _top_correlations(df: pd.DataFrame, metric: str | None) -> list[str]:
    numeric = _numeric_columns(df)
    metric = _safe_metric(df, metric)
    if not metric or len(numeric) < 2:
        return ["- Za malo kolumn liczbowych, aby policzyc korelacje."]
    corr = df[numeric].corr(numeric_only=True)[metric].drop(labels=[metric], errors="ignore")
    corr = corr.dropna().abs().sort_values(ascending=False).head(5)
    if corr.empty:
        return ["- Brak stabilnych korelacji dla wybranej metryki."]
    return [f"- {column}: korelacja |r| = {value:.3f}" for column, value in corr.items()]


def _group_summary(df: pd.DataFrame, metric: str | None, dimension: str | None) -> list[str]:
    metric = _safe_metric(df, metric)
    dimension = _safe_dimension_for_metric(df, metric, dimension)
    if not metric or not dimension or dimension not in df.columns:
        return ["- Brak metryki albo wymiaru do segmentacji."]
    metric_values = pd.to_numeric(_column_series(df, metric), errors="coerce")
    grouped = (
        pd.DataFrame(
            {"_dimension": _column_series(df, dimension).astype(str), "_metric": metric_values}
        )
        .dropna()
        .groupby("_dimension", dropna=False)["_metric"]
        .agg(["count", "mean", "min", "max"])
        .sort_values("mean", ascending=False)
        .head(8)
    )
    if grouped.empty:
        return ["- Brak segmentow po odfiltrowaniu pustych wartosci."]
    return [
        f"- {idx}: n={int(row['count'])}, srednia={row['mean']:.3f}, min={row['min']:.3f}, max={row['max']:.3f}"
        for idx, row in grouped.iterrows()
    ]


def _workflow_index() -> AnalyticsResult:
    body = "\n".join(
        [
            "Modul Data Analytics w tej aplikacji obejmuje:",
            "- Analyze Data Quality: szybka kontrola brakow, duplikatow i typow kolumn.",
            "- Executive Summary: krotkie podsumowanie decyzyjne do raportu.",
            "- Build Dashboard: lista kart KPI i wykresow do odtworzenia w Visual.",
            "- Build Report: gotowy raport tekstowy do zapisania lub wklejenia do dokumentu.",
            "- ML Analytics: plan predykcji, metryki, walidacja i interpretacja modeli ML.",
            "- STO Analytics: porownanie kolejek, opoznien, buforow i heurystyk STO.",
            "- Prediction Plan: co trzeba przygotowac, zeby predykcja byla uzywalna w decyzji.",
            "- Design KPIs: propozycje metryk, driverow i guardrails.",
            "- KPI Reporting: status wybranej metryki i segmentow.",
            "- Metric Diagnostics: wyjasnienie, co moze pchac metryke w gore lub dol.",
            "- Product Business Analysis: rekomendacje biznesowe z danych.",
            "- Opportunity Sizing: najwieksze segmenty i potencjal dzialania.",
            "- Market Sizing: szablon TAM/SAM/SOM oparty o dostepne dane.",
            "- Visualize Data: podpowiedz najlepszych wykresow dla Visual.",
            "- Statistical Summary: pelne statystyki metryk liczbowych.",
            "- Segment Explorer: ranking segmentow po metryce.",
            "- Correlation Explorer: najsilniejsze zaleznosci liczbowe.",
            "- Outlier Analysis: wykrywanie obserwacji odstajacych IQR.",
            "- Pivot Summary: prosta tabela przestawna metryka x wymiar.",
            "- Data Dictionary: slownik kolumn i typow danych.",
            "- Time Trend: analiza trendu, jesli jest kolumna czasu.",
            "- Chart QA: kontrola, czy wykres HTML dobrze oddaje dane.",
            "- Risk & Caveats: ryzyka, ograniczenia i brakujacy kontekst.",
            "- Action Plan: lista konkretnych krokow po analizie.",
            "- Gather Business Context: checklista kontekstu, ktory warto dopisac do danych.",
            "- Jupyter Notebook Plan: plan notebooka analitycznego krok po kroku.",
        ]
    )
    return AnalyticsResult("Data Analytics - Index", body, "Dashboard")


def run_analytics_workflow(
    df: pd.DataFrame | None,
    workflow: str,
    metric: str | None = None,
    dimension: str | None = None,
) -> AnalyticsResult:
    if workflow == "Index":
        return _workflow_index()
    if df is None or df.empty:
        return AnalyticsResult(
            "Brak danych",
            "Wczytaj plik CSV/TXT/TSV, aby uruchomic analize Data Analytics.",
            "Dashboard",
        )

    workflow = workflow if workflow in ANALYTICS_WORKFLOWS else "Build Report"
    metric = _safe_metric(df, metric)
    dimension = _safe_dimension_for_metric(df, metric, dimension)
    numeric = _numeric_columns(df)
    categorical = _categorical_columns(df)
    stats = _metric_stats(df, metric)

    if workflow == "Analyze Data Quality":
        worst_missing = df.isna().mean().sort_values(ascending=False).head(8)
        lines = [
            "Profil jakosci danych:",
            *_basic_profile(df),
            "",
            "Kolumny z najwiekszym udzialem brakow:",
        ]
        lines += [f"- {col}: {rate:.1%}" for col, rate in worst_missing.items()]
        lines += [
            "",
            "Rekomendacje:",
            "- Uzupelnij lub usun kolumny z wysokim udzialem brakow.",
            "- Sprawdz duplikaty przed trenowaniem i raportowaniem KPI.",
        ]
        return AnalyticsResult("Analyze Data Quality", "\n".join(lines), "Missingness Map")

    if workflow == "Executive Summary":
        lines = [
            "Executive Summary",
            "",
            "Najwazniejsze fakty:",
            *_basic_profile(df),
            "",
            "Metryka glowna:",
            *_format_stats(stats, metric),
            "",
            "Najwazniejsze segmenty:",
            *_group_summary(df, metric, dimension),
            "",
            "Decyzja robocza:",
            "- Najpierw sprawdz jakosc danych i segmenty o najwiekszym udziale.",
            "- Potem w Visual otworz Dashboard, Regression Plot i Column Ranking w HTML.",
            "- W Report Builder wrzuc Executive Summary + wykres + Action Plan.",
        ]
        return AnalyticsResult("Executive Summary", "\n".join(lines), "Dashboard")

    if workflow == "Build Dashboard":
        lines = [
            "Proponowany dashboard:",
            "- Karta 1: liczba rekordow i kolumn.",
            "- Karta 2: jakosc danych i duplikaty.",
            f"- Karta 3: glowna metryka: {metric or 'brak kolumny liczbowej'}.",
            f"- Karta 4: segmentacja po: {dimension or 'brak wymiaru'}.",
            "",
            "Widoki do dodania w Visual:",
            "- Production Dashboard",
            "- Missingness Map",
            "- Column Ranking",
            "- Bar Chart albo Pie Chart dla kategorii",
            "- Regression Plot lub Scatter dla relacji liczbowych",
        ]
        return AnalyticsResult("Build Dashboard", "\n".join(lines), "Production Dashboard")

    if workflow == "Build Report":
        lines = [
            "Raport analityczny",
            "",
            "1. Profil danych",
            *_basic_profile(df),
            "",
            "2. Najwazniejsze zaleznosci",
            *_top_correlations(df, metric),
            "",
            "3. Segmenty",
            *_group_summary(df, metric, dimension),
            "",
            "4. Rekomendacja",
            "- Zacznij od walidacji jakosci danych, potem obejrzyj dashboard i segmenty metryki.",
        ]
        return AnalyticsResult("Build Report", "\n".join(lines), "Dashboard")

    if workflow == "ML Analytics":
        metric = _safe_metric(df, metric)
        correlations = _top_correlations(df, metric)
        lines = [
            "ANALITYKA ML",
            "============",
            "Cel: przygotowac dane i raport tak, aby bylo wiadomo, co model przewiduje, jak to mierzyc i czy wynik nadaje sie do decyzji.",
            "",
            "Profil danych:",
            *_basic_profile(df),
            "",
            "Cel predykcji:",
            f"- Proponowany target y: {metric or 'wybierz kolumne liczbową albo klase'}",
            "- X: pozostale cechy po oczyszczeniu, kodowaniu kategorii i uzupelnieniu brakow.",
            "- Regresja: jakosc, opoznienie, czas, koszt, ryzyko liczbowo.",
            "- Klasyfikacja: harmonogram, decyzja, status, segment albo klasa ryzyka.",
            "",
            "Modele do porownania:",
            "- Baseline: Linear/Ridge albo LogisticRegression.",
            "- Drzewa: RandomForest, ExtraTrees, DecisionTree.",
            "- Boosting: GradientBoosting, HistGradient, XGBoost.",
            "- Modele wrazliwe na skale: SVM/SVR, KNN, MLP.",
            "- TabPFN: eksperymentalny backend dla malych/średnich danych tabularnych.",
            "",
            "Metryki:",
            "- Regresja: RMSE, MAE, R2, blad po segmentach.",
            "- Klasyfikacja: accuracy, precision, recall, F1, macierz pomylek.",
            "- Operacyjnie: ile decyzji zmienia model i jaki jest koszt bledu.",
            "",
            "Najsilniejsze korelacje z metryka:",
            *correlations,
            "",
            "Do raportu dodaj:",
            "- Model Diagnostics, Regression Plot, CorrelationMatrix, Outlier Map.",
            "- Tabele cech, opis targetu, metryki train/test i rekomendacje.",
        ]
        return AnalyticsResult("ML Analytics", "\n".join(lines), "Model Diagnostics")

    if workflow == "STO Analytics":
        duration_col = "czas_produkcji_h" if "czas_produkcji_h" in df.columns else _safe_metric(df, metric)
        deadline_col = "termin_h" if "termin_h" in df.columns else None
        stats = _metric_stats(df, duration_col)
        lines = [
            "ANALITYKA STO / HEURYSTYKI",
            "==========================",
            "Cel: porownac kolejnosci zadan, opoznienia i bufor, a potem opisac, ktora metoda jest najlepsza i dlaczego.",
            "",
            "Wymagane dane:",
            f"- p_j / czas wykonania: {duration_col or 'brak - wskaż kolumne czasu'}",
            f"- d_j / termin: {deadline_col or 'brak - wskaż termin/deadline'}",
            "- opcjonalnie: priorytet, maszyna, klient, material, koszt przestoju.",
            "",
            "Statystyki czasu wykonania:",
            *_format_stats(stats, duration_col),
            "",
            "Wzory:",
            "- C_j = suma czasow p_k dla zadan przed j i zadania j.",
            "- T_j = max(0, C_j - d_j).",
            "- STO = suma T_j; im mniej, tym lepiej.",
            "",
            "Metody do opisania:",
            "- MT/EDD: najblizszy termin pierwszy.",
            "- MO/SPT: najkrotszy czas pierwszy.",
            "- MZO/LPT: najdluzszy czas pierwszy.",
            "- Slack / Critical ratio / wlasne heurystyki: score dla kazdego zadania.",
            "- MOPT/GENETIC: przeszukiwanie wielu wariantow kolejnosci.",
            "",
            "Do raportu dodaj:",
            "- Ranking metod STO, wykres Gantta, SolutionTree i tabele opoznien po zadaniu.",
            "- Wniosek: najlepsza metoda, roznica do najgorszej, ryzyko spoznien i rekomendowana kolejnosc.",
        ]
        return AnalyticsResult("STO Analytics", "\n".join(lines), "SolutionTree")

    if workflow == "Prediction Plan":
        metric = _safe_metric(df, metric)
        dimension = _safe_dimension_for_metric(df, metric, dimension)
        lines = [
            "PLAN PREDYKCJI",
            "==============",
            "Ten workflow opisuje, co trzeba przygotowac, zeby predykcja w aplikacji byla zrozumiala i uzywalna.",
            "",
            "1. Decyzja:",
            "- Co uzytkownik zrobi po wyniku modelu?",
            "- Czy model ma ostrzegac, rekomendowac, czy automatycznie wybierac akcje?",
            "",
            "2. Dane:",
            f"- Proponowany target: {metric or 'wybierz cel'}",
            f"- Proponowany wymiar kontroli: {dimension or 'wybierz segment'}",
            "- Sprawdz braki, duplikaty, jednostki, zakresy i przecieki danych.",
            "",
            "3. Model:",
            "- Zacznij od baseline, potem porownaj las, boosting, SVM/KNN/MLP/XGBoost/TabPFN.",
            "- Zapisz, ktory model wygrywa i na jakiej metryce.",
            "",
            "4. Walidacja:",
            "- Train/test, segmenty, outliery, stabilnosc, drift.",
            "- Dla STO: porownaj ranking metod i koszt opoznien.",
            "",
            "5. Raport:",
            "- Dodaj Analityke ML, Analityke STO, Ryzyka, Plan akcji i wykresy HTML.",
        ]
        return AnalyticsResult("Prediction Plan", "\n".join(lines), "Build Report")

    if workflow == "Design KPIs":
        lines = [
            "Propozycja KPI:",
            f"- North Star / metryka glowna: {metric or 'wybierz kolumne liczbowa'}.",
            f"- Driver 1: segmentacja po {dimension or 'wybranym wymiarze'}.",
            "- Driver 2: trend w czasie, jesli dodasz kolumne daty/czasu.",
            "- Guardrail 1: braki danych i duplikaty.",
            "- Guardrail 2: stabilnosc rozkladu i outliery.",
            "",
            "Definicja pomiaru:",
            "- Raportuj wartosc aktualna, srednia, mediane, min/max i liczbe rekordow.",
            "- Porownuj segmenty oraz zmiany po filtrowaniu.",
        ]
        return AnalyticsResult("Design KPIs", "\n".join(lines), "Column Ranking")

    if workflow == "KPI Reporting":
        metric_series = (
            pd.to_numeric(_column_series(df, metric), errors="coerce").dropna()
            if metric
            else pd.Series(dtype=float)
        )
        lines = [
            f"KPI Reporting dla: {metric or 'brak metryki'}",
            f"- Liczba pomiarow: {len(metric_series):,}",
            f"- Srednia: {metric_series.mean():.3f}"
            if not metric_series.empty
            else "- Srednia: brak",
            f"- Mediana: {metric_series.median():.3f}"
            if not metric_series.empty
            else "- Mediana: brak",
            f"- Min/Max: {metric_series.min():.3f} / {metric_series.max():.3f}"
            if not metric_series.empty
            else "- Min/Max: brak",
            "",
            "Segmenty:",
            *_group_summary(df, metric, dimension),
        ]
        return AnalyticsResult("KPI Reporting", "\n".join(lines), "Bar Chart")

    if workflow == "Metric Diagnostics":
        lines = [
            f"Metric Diagnostics dla: {metric or 'brak metryki'}",
            "",
            "Najbardziej podejrzane drivery liczbowe:",
            *_top_correlations(df, metric),
            "",
            "Segmenty o najwyzszych wartosciach:",
            *_group_summary(df, metric, dimension),
            "",
            "Co sprawdzic dalej:",
            "- Czy segmenty maja podobna liczbe rekordow.",
            "- Czy outliery nie steruja wynikiem.",
            "- Czy definicja metryki jest taka sama w Results, Visual i raporcie.",
        ]
        return AnalyticsResult("Metric Diagnostics", "\n".join(lines), "Regression Plot")

    if workflow == "Product Business Analysis":
        lines = [
            "Product / Business Analysis",
            "",
            "Sygnały z danych:",
            *_basic_profile(df),
            "",
            "Mozliwe okazje:",
            f"- Skup sie na segmentach {dimension or 'wymiaru'}, gdzie {metric or 'metryka'} jest najwyzsza lub najnizsza.",
            "- Uzyj Visual do sprawdzenia relacji, outlierow i dashboardu.",
            "- Jesli dane sa produkcyjne, porownaj koszt/opoznienie/odpad miedzy wariantami.",
        ]
        return AnalyticsResult("Product Business Analysis", "\n".join(lines), "Bubble Chart")

    if workflow == "Market Sizing":
        total = (
            float(pd.to_numeric(_column_series(df, metric), errors="coerce").dropna().sum())
            if metric
            else 0.0
        )
        lines = [
            "Market Sizing / TAM-SAM-SOM",
            "",
            f"- Dostepna suma metryki ({metric or 'brak'}): {total:,.2f}",
            "- TAM: caly potencjal rynku lub procesu.",
            "- SAM: czesc rynku/procesu obslugiwana przez obecny zakres danych.",
            "- SOM: realistyczny udzial do zdobycia/usprawnienia w najblizszym okresie.",
            "",
            "W aplikacji traktuj to jako kalkulator zalozen: dopisz zasieg, wspolczynnik penetracji i ograniczenia.",
        ]
        return AnalyticsResult("Market Sizing", "\n".join(lines), "Area Chart")

    if workflow == "Opportunity Sizing":
        lines = [
            "Opportunity Sizing",
            "",
            "Gdzie jest najwiekszy potencjal:",
            *_opportunity_lines(df, metric, dimension),
            "",
            "Jak to wykorzystac:",
            "- Najwiekszy segment nie zawsze jest najlepsza akcja: porownaj udzial, srednia i liczbe rekordow.",
            "- Segment o wysokiej sredniej i duzym udziale powinien wejsc do dashboardu i raportu.",
            "- Segment o malej liczbie rekordow traktuj jako hipoteze, nie twardy wniosek.",
        ]
        return AnalyticsResult("Opportunity Sizing", "\n".join(lines), "Column Ranking")

    if workflow == "Visualize Data":
        lines = [
            "Rekomendacje wizualizacji:",
            "- Porownanie kategorii: Bar Chart, Pie Chart.",
            "- Relacja dwoch liczb: Scatter, Regression Plot, Bubble Chart.",
            "- Rozklad: Histogram, KDE Plot, ECDF Plot, Boxplot, Violin Plot.",
            "- Jakość danych: Missingness Map.",
            "- Zaleznosci wielu kolumn: Pair Plot, CorrelationMatrix.",
            "- Drzewa/decyzje: SolutionTree, Network Graph.",
        ]
        if numeric:
            lines.append(f"- Kolumny liczbowe do startu: {', '.join(numeric[:6])}.")
        if categorical:
            lines.append(f"- Kategorie do startu: {', '.join(categorical[:6])}.")
        return AnalyticsResult("Visualize Data", "\n".join(lines), "Pair Explorer")

    if workflow == "Statistical Summary":
        lines = ["Statistical Summary", "", "Statystyki kolumn liczbowych:"]
        if numeric:
            summary = df[numeric].describe().T
            for column, row in summary.iterrows():
                lines.append(
                    f"- {column}: n={row['count']:.0f}, mean={row['mean']:.3f}, "
                    f"std={row['std']:.3f}, min={row['min']:.3f}, max={row['max']:.3f}"
                )
        else:
            lines.append("- Brak kolumn liczbowych.")
        lines += [
            "",
            "Do raportu:",
            "- Dodaj jednostki miary i wskaz, czy wieksza wartosc jest dobra czy zla.",
        ]
        return AnalyticsResult("Statistical Summary", "\n".join(lines), "Histogram")

    if workflow == "Segment Explorer":
        lines = [
            "Segment Explorer",
            "",
            f"Metryka: {metric or 'brak'}",
            f"Wymiar: {dimension or 'brak'}",
            "",
            "Ranking segmentow:",
            *_group_summary(df, metric, dimension),
            "",
            "Jak czytac:",
            "- Segment z wysoka srednia i duza liczba rekordow jest dobrym kandydatem do decyzji.",
            "- Segment z mala liczba rekordow wymaga ostroznosci.",
        ]
        return AnalyticsResult("Segment Explorer", "\n".join(lines), "Bar Chart")

    if workflow == "Correlation Explorer":
        lines = [
            "Correlation Explorer",
            "",
            f"Metryka centralna: {metric or 'brak'}",
            "Najsilniejsze relacje:",
            *_top_correlations(df, metric),
            "",
            "Uwaga:",
            "- Korelacja pokazuje wspolruch, nie przyczynowosc.",
            "- Najlepiej potwierdzic wynik wykresem Regression Plot lub Pair Explorer.",
        ]
        return AnalyticsResult("Correlation Explorer", "\n".join(lines), "CorrelationMatrix")

    if workflow == "Outlier Analysis":
        lines = ["Outlier Analysis", ""]
        if metric:
            series = pd.to_numeric(_column_series(df, metric), errors="coerce").dropna()
            if series.empty:
                lines.append("- Brak wartosci liczbowych do analizy outlierow.")
            else:
                q1 = float(series.quantile(0.25))
                q3 = float(series.quantile(0.75))
                iqr = q3 - q1
                low = q1 - 1.5 * iqr
                high = q3 + 1.5 * iqr
                count = int(((series < low) | (series > high)).sum())
                lines += [
                    f"- Metryka: {metric}",
                    f"- Q1/Q3: {q1:.3f} / {q3:.3f}",
                    f"- Granice IQR: {low:.3f} do {high:.3f}",
                    f"- Liczba obserwacji odstajacych: {count}",
                    "- W Visual uzyj Outlier Map albo Boxplot.",
                ]
        else:
            lines.append("- Brak metryki liczbowej.")
        return AnalyticsResult("Outlier Analysis", "\n".join(lines), "Outlier Map")

    if workflow == "Pivot Summary":
        lines = ["Pivot Summary", ""]
        if metric and dimension:
            work = pd.DataFrame(
                {
                    "segment": _column_series(df, dimension).astype(str),
                    "metric": pd.to_numeric(_column_series(df, metric), errors="coerce"),
                }
            ).dropna()
            if work.empty:
                lines.append("- Brak danych do tabeli przestawnej.")
            else:
                pivot = (
                    work.groupby("segment")["metric"]
                    .agg(["count", "mean", "sum"])
                    .sort_values("sum", ascending=False)
                    .head(12)
                )
                lines.append(f"Metryka: {metric} | Wymiar: {dimension}")
                for segment, row in pivot.iterrows():
                    lines.append(
                        f"- {segment}: n={int(row['count'])}, mean={row['mean']:.3f}, sum={row['sum']:.3f}"
                    )
        else:
            lines.append("- Wybierz metryke i wymiar.")
        return AnalyticsResult("Pivot Summary", "\n".join(lines), "Column Ranking")

    if workflow == "Data Dictionary":
        lines = ["Data Dictionary", "", "Kolumny:"]
        for column in df.columns:
            column_data = _column_series(df, column)
            missing = float(column_data.isna().mean())
            unique = int(column_data.nunique(dropna=True))
            dtype = str(column_data.dtype)
            role = "metryka" if column in numeric else "wymiar/opis"
            lines.append(
                f"- {column}: typ={dtype}, rola={role}, unikalne={unique}, braki={missing:.1%}"
            )
        lines += [
            "",
            "Do raportu:",
            "- Przy waznych kolumnach dopisz definicje biznesowa i jednostke.",
        ]
        return AnalyticsResult("Data Dictionary", "\n".join(lines), "Build Report")

    if workflow == "Time Trend":
        date_candidates = [
            column
            for column in df.columns
            if any(
                token in column.lower()
                for token in ["date", "data", "time", "czas", "created", "termin"]
            )
        ]
        lines = ["Time Trend", ""]
        if not metric:
            lines.append("- Brak metryki liczbowej do trendu.")
        elif not date_candidates:
            lines.append(
                "- Nie znaleziono oczywistej kolumny czasu. Dodaj kolumne daty albo wybierz ja jako wymiar."
            )
        else:
            time_col = date_candidates[0]
            parsed = pd.to_datetime(df[time_col], errors="coerce")
            work = pd.DataFrame(
                {
                    "time": parsed,
                    "metric": pd.to_numeric(_column_series(df, metric), errors="coerce"),
                }
            ).dropna()
            if work.empty:
                lines.append(f"- Kolumna {time_col} nie dala stabilnej osi czasu.")
            else:
                trend = (
                    work.set_index("time")
                    .sort_index()["metric"]
                    .resample("D")
                    .mean()
                    .dropna()
                    .tail(12)
                )
                lines.append(f"- Oś czasu: {time_col}")
                lines.append(f"- Metryka: {metric}")
                for ts, value in trend.items():
                    lines.append(f"- {ts.date()}: {value:.3f}")
        return AnalyticsResult("Time Trend", "\n".join(lines), "Line")

    if workflow == "Chart QA":
        return AnalyticsResult(
            "Chart QA", "\n".join(_chart_qa_lines(df, metric, dimension)), "Dashboard"
        )

    if workflow == "Risk & Caveats":
        lines = [
            "Risk & Caveats",
            "",
            "Ryzyka interpretacji:",
            f"- Jakosc danych: {_quality_score(df):.1f}/100.",
            f"- Braki danych: {int(df.isna().sum().sum()):,}.",
            f"- Duplikaty: {int(df.duplicated().sum()):,}.",
            "- Korelacja nie oznacza przyczynowosci: sprawdz proces i definicje kolumn.",
            "- Male segmenty moga dawac przypadkowo wysokie srednie.",
            "- Outliery moga przesuwac srednia; porownaj mediane i wykres Boxplot/Outlier Map.",
            "",
            "Co powinno byc dopisane w raporcie:",
            "- Zrodlo danych, data wygenerowania, filtry i definicja metryki.",
            "- Czy wieksza wartosc metryki jest dobra czy zla.",
            "- Ktore wykresy sa dowodem, a ktore tylko eksploracja.",
        ]
        return AnalyticsResult("Risk & Caveats", "\n".join(lines), "Outlier Map")

    if workflow == "Action Plan":
        lines = [
            "Action Plan",
            "",
            "Kolejnosc pracy:",
            "1. Wczytaj dane i uruchom Analyze Data Quality.",
            "2. Otworz Chart QA, zeby dobrac wykresy HTML do liczby punktow i kolumn.",
            "3. Uruchom Executive Summary i Opportunity Sizing.",
            "4. W Visual wygeneruj HTML dla Dashboard, Regression Plot, Column Ranking i ewentualnie SolutionTree.",
            "5. W Report Builder dodaj wynik analizy, pliki HTML/PNG/SVG oraz wnioski.",
            "6. Eksportuj HTML i .tex/.md.",
            "",
            "Minimalny pakiet do oddania:",
            "- Executive Summary",
            "- Dashboard HTML",
            "- Segmenty/Opportunity Sizing",
            "- Risk & Caveats",
            "- 3 konkretne rekomendacje",
        ]
        return AnalyticsResult("Action Plan", "\n".join(lines), "Build Report")

    if workflow == "Gather Business Context":
        lines = [
            "Kontekst biznesowy do dopisania:",
            "- Jaki jest cel analizy?",
            "- Kto podejmuje decyzje na podstawie raportu?",
            "- Jak definiujemy sukces i porazke?",
            "- Jakie sa filtry czasowe, segmenty i ograniczenia danych?",
            "- Ktore kolumny sa metrykami, a ktore wymiarami?",
            "- Jakie akcje uzytkownik moze podjac po analizie?",
        ]
        return AnalyticsResult("Gather Business Context", "\n".join(lines), "Build Report")

    if workflow == "Jupyter Notebook Plan":
        lines = [
            "Plan notebooka:",
            "1. Import bibliotek i wczytanie danych.",
            "2. Profil danych: typy, braki, duplikaty.",
            "3. EDA: rozklady, segmenty, korelacje.",
            "4. KPI: definicja metryki, agregacje i segmentacja.",
            "5. Diagnostyka: drivery, outliery, stabilnosc.",
            "6. Wykresy: dashboard i najwazniejsze relacje.",
            "7. Wnioski i rekomendacje.",
        ]
        return AnalyticsResult("Jupyter Notebook Plan", "\n".join(lines), "Build Report")

    return _workflow_index()
