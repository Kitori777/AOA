from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib import error, request
from urllib.parse import quote_plus

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from AOA.core.mh_models import get_mh_model_specs
from AOA.core.ml_models import get_ml_model_specs
from AOA.core.release_segments import (
    data_contract_summary,
    report_template_summary,
    segment_summary,
)


def _has_word(text: str, words: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"(?<![a-zA-Z0-9_]){re.escape(word)}(?![a-zA-Z0-9_])", text) for word in words
    )


@dataclass
class RetrievedChunk:
    source: str
    text: str
    score: float


@dataclass(frozen=True)
class BrainEntry:
    id: str
    aliases: tuple[str, ...]
    answer: str
    steps: tuple[str, ...]


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _load_brain_entries() -> tuple[BrainEntry, ...]:
    path = _workspace_root() / "docs" / "alice_brain.json"
    if not path.exists():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ()
    entries: list[BrainEntry] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        aliases = tuple(
            str(alias).lower().strip() for alias in item.get("aliases", []) if str(alias).strip()
        )
        answer = str(item.get("answer", "")).strip()
        steps = tuple(str(step).strip() for step in item.get("steps", []) if str(step).strip())
        entry_id = str(item.get("id", "")).strip()
        if entry_id and aliases and answer:
            entries.append(BrainEntry(entry_id, aliases, answer, steps))
    return tuple(entries)


def _collect_docs() -> list[tuple[str, str]]:
    root = _workspace_root()
    files: list[Path] = []
    docs_dir = root / "docs"
    if docs_dir.exists():
        files.extend(sorted(docs_dir.glob("*.md")))
    alice_sources = docs_dir / "alice_sources"
    if alice_sources.exists():
        files.extend(sorted(alice_sources.glob("*.md")))
        files.extend(sorted(alice_sources.glob("*.txt")))
        files.extend(sorted(alice_sources.glob("*.html")))

    records: list[tuple[str, str]] = []
    for path in files:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for idx, chunk in enumerate(_split_text(text), start=1):
            records.append((f"{path.name}#{idx}", chunk))
    records.extend(_model_catalog_chunks())
    records.extend(_brain_chunks())
    records.extend(_collect_code_knowledge(root))
    return records


def _brain_chunks() -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    for entry in _load_brain_entries():
        steps = " ".join(f"Krok: {step}" for step in entry.steps)
        aliases = ", ".join(entry.aliases)
        chunks.append((f"alice_brain:{entry.id}", f"Hasla: {aliases}. {entry.answer} {steps}"))
    return chunks


def _collect_code_knowledge(root: Path) -> list[tuple[str, str]]:
    targets = [
        root / "src" / "AOA" / "gui" / "main_window.py",
        root / "src" / "AOA" / "gui" / "assistant_panel.py",
        root / "src" / "AOA" / "gui" / "pages" / "visual_page.py",
        root / "src" / "AOA" / "gui" / "pages" / "results_page.py",
        root / "src" / "AOA" / "gui" / "pages" / "analytics_page.py",
        root / "src" / "AOA" / "gui" / "pages" / "drawio_page.py",
        root / "src" / "AOA" / "core" / "services" / "training.py",
        root / "src" / "AOA" / "core" / "self_learning.py",
        root / "src" / "AOA" / "core" / "mlstack" / "pipelines" / "workflow.py",
    ]
    out: list[tuple[str, str]] = []
    for path in targets:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        defs = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", text)
        classes = re.findall(r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]", text)
        signature = []
        if classes:
            signature.append(f"klasy: {', '.join(classes[:8])}")
        if defs:
            signature.append(f"metody: {', '.join(defs[:16])}")
        if signature:
            out.append((f"code:{path.name}", "; ".join(signature)))
    return out


def _model_catalog_chunks() -> list[tuple[str, str]]:
    ml_rows = [
        f"{spec.name}: {spec.label}. Skupia sie na: {spec.focus}. {spec.description}"
        for spec in get_ml_model_specs()
    ]
    mh_rows = [
        f"{spec.name}: {spec.label}. Skupia sie na: {spec.focus}. {spec.description}"
        for spec in get_mh_model_specs()
    ]
    return [
        ("ml_models", "\n".join(ml_rows)),
        ("sto_models", "\n".join(mh_rows)),
        (
            "architecture",
            (
                "Architektura aplikacji: GUI (CustomTkinter) + Core (modele, wizualizacje, uslugi) + Assets. "
                "MainPage odpowiada za konfiguracje i trening. VisualPage za wykresy Matplotlib/D3. "
                "ResultsPage za filtrowanie tabel, SQL i eksport CSV. Report/AnalyticsPage za raporty, KPI, PDF-like preview, notebook, ML/STO analytics i biblioteke plikow do raportow. "
                "Diagrams Studio za interaktywne schematy, UML, ERD, BPMN i eksport .drawio/SVG/Mermaid/HTML. "
                "TheoryPage za przewodnik krokowy dla classic ML, heurystyk STO oraz TabPFN/nowoczesnych modeli tabelarycznych. "
                "AssistantService laczy RAG (README/docs/specy modeli) z endpointem LLM."
            ),
        ),
        (
            "workflow",
            (
                "Workflow aplikacji: Readme -> Main (dane, classic ML, TabPFN, STO i modele wlasne) -> "
                "Visual (wykresy) -> Diagrams (procesy, UML, ERD, BPMN, produkcja) -> "
                "Report (raporty, PDF, notebook, KPI, ML/STO analytics) -> Results (SQL, tabele, eksport) -> Theory (wyjasnienie modeli)."
            ),
        ),
    ]


def _split_text(text: str, chunk_size: int = 900) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end])
        start = end
    return chunks


class AssistantKnowledgeBase:
    def __init__(self) -> None:
        self.records = _collect_docs()
        corpus = [text for _, text in self.records] or ["brak danych"]
        self.vectorizer = TfidfVectorizer(max_features=3500, ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, k: int = 4) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix).ravel()
        top_idx = sims.argsort()[::-1][:k]
        out: list[RetrievedChunk] = []
        for idx in top_idx:
            source, text = self.records[idx]
            out.append(RetrievedChunk(source=source, text=text, score=float(sims[idx])))
        return out


class AIRIAdapter:
    def __init__(self) -> None:
        self.endpoint = (
            os.getenv("AOA_ALICE_ENDPOINT", "").strip()
            or os.getenv("AOA_AIRI_ENDPOINT", "").strip()
        )
        self.model = (
            os.getenv("AOA_ALICE_MODEL", "").strip()
            or os.getenv("AOA_AIRI_MODEL", "").strip()
            or "default"
        )

    def available(self) -> bool:
        return bool(self.endpoint)

    def ask(self, prompt: str, context: str, style_hint: str = "normal") -> str | None:
        if not self.available():
            return None
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Jestes ALICE, asystentka aplikacji AOA. Odpowiadasz po polsku, konkretnie i praktycznie. "
                        "Dawaj sedno odpowiedzi i na koncu 2-3 konkretne nastepne kroki. "
                        f"Styl odpowiedzi: {style_hint}."
                    ),
                },
                {"role": "user", "content": f"Pytanie: {prompt}\n\nKontekst:\n{context}"},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
            parsed = json.loads(raw)
        except (error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return None
        for key in ("answer", "content", "text"):
            if key in parsed and isinstance(parsed[key], str):
                return parsed[key]
        try:
            return parsed["choices"][0]["message"]["content"]
        except Exception:
            return None

    def ping(self) -> bool:
        if not self.available():
            return False
        req = request.Request(self.endpoint, method="OPTIONS")
        try:
            with request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False


class AssistantService:
    def __init__(self) -> None:
        self.kb = AssistantKnowledgeBase()
        self.airi = AIRIAdapter()

    def answer(
        self, question: str, profile: str = "normal"
    ) -> tuple[str, list[RetrievedChunk], bool]:
        q = question.lower().strip()
        casual_answer = self._casual_playbook(q)
        if casual_answer is not None:
            return self._finalize_answer(casual_answer, q, profile), [], False

        theory_answer = self._theory_playbook(q)
        if theory_answer is not None:
            return self._finalize_answer(theory_answer, q, profile), [], False

        model_answer = self._model_playbook(q)
        if model_answer is not None:
            return self._finalize_answer(model_answer, q, profile), [], False

        process_answer = self._process_playbook(q)
        if process_answer is not None:
            return self._finalize_answer(process_answer, q, profile), [], False

        brain_answer = self._brain_playbook(q)
        if brain_answer is not None:
            return self._finalize_answer(brain_answer, q, profile), [], False

        hits = self.kb.retrieve(question, k=4)
        context = "\n\n".join(f"[{h.source}] {h.text}" for h in hits)

        if self.airi.available():
            generated = self.airi.ask(question, context, style_hint=profile)
            if generated:
                return self._finalize_answer(generated, q, profile), hits, True

        useful_hits = [
            hit for hit in hits if hit.score >= 0.08 and not self._is_code_signature_chunk(hit)
        ]
        if not useful_hits:
            web_note = self._web_lookup(question)
            msg = (
                "Nie mam do tego wystarczajaco pewnego kontekstu w aplikacji.\n"
                "Moge za to pomoc praktycznie: opisac Main, Visual, Results, Report, Diagrams, Theory albo ALICE."
            )
            if web_note:
                msg = f"{msg}\n\nDodatkowo sprawdzilam siec: {web_note}"
            return self._finalize_answer(msg, q, profile), [], False

        best = useful_hits[0]
        if best.source.startswith("alice_brain:"):
            entry_id = best.source.split(":", 1)[1]
            entry = next((item for item in _load_brain_entries() if item.id == entry_id), None)
            if entry is not None:
                steps = "\n".join(f"{idx}. {step}" for idx, step in enumerate(entry.steps, start=1))
                msg = (
                    f"{entry.answer}\n\nJak to zrobic w aplikacji:\n{steps}"
                    if steps
                    else entry.answer
                )
                return self._finalize_answer(msg, q, profile), useful_hits, False
        short = best.text[:260] + ("..." if len(best.text) > 260 else "")
        msg = f"Jasne, juz tlumacze prosto.\n{short}"
        return self._finalize_answer(msg, q, profile), useful_hits, False

    @staticmethod
    def _is_code_signature_chunk(hit: RetrievedChunk) -> bool:
        text = hit.text.lower()
        return hit.source.startswith("code:") or ("klasy:" in text and "metody:" in text)

    @staticmethod
    def _brain_playbook(question: str) -> str | None:
        best_entry: BrainEntry | None = None
        best_score = 0
        tokens = set(re.findall(r"[a-zA-Z0-9_]+", question.lower()))
        for entry in _load_brain_entries():
            score = 0
            for alias in entry.aliases:
                alias_tokens = set(re.findall(r"[a-zA-Z0-9_]+", alias))
                if not alias_tokens:
                    continue
                if alias in question:
                    score += 8 + len(alias_tokens)
                elif alias_tokens <= tokens:
                    score += 5 + len(alias_tokens)
                else:
                    overlap = len(alias_tokens & tokens)
                    if overlap:
                        score += overlap
            if score > best_score:
                best_score = score
                best_entry = entry
        if best_entry is None or best_score < 5:
            return None
        steps = "\n".join(f"{idx}. {step}" for idx, step in enumerate(best_entry.steps, start=1))
        if steps:
            return f"{best_entry.answer}\n\nJak to zrobic w aplikacji:\n{steps}"
        return best_entry.answer

    @staticmethod
    def _finalize_answer(answer: str, question: str, profile: str = "normal") -> str:
        answer = (answer or "").strip()
        if not answer:
            answer = "Brak odpowiedzi."

        next_steps: list[str] = []
        if AssistantService._category_help(question):
            next_steps = [
                "Wybierz jedna komende z tej kategorii i wpisz ja normalnym zdaniem.",
                "Mozesz dopisac szczegol, np. 'dla sample', 'z SQL', 'do raportu' albo 'z opisu'.",
                "Jesli chcesz tylko nauke, napisz 'wytlumacz krok po kroku'.",
            ]
        elif any(
            k in question
            for k in ["theory", "teoria", "animac", "random forest", "boost", "extra", "softmax", "tabpfn"]
        ) or ("sto" in question and ("machine learning" in question or " ml" in question)):
            next_steps = [
                "Przejdz do Theory i wybierz grupe ML, Heurystyki albo TabPFN.",
                "Porownaj classic ML, TabPFN i STO na tych samych danych.",
                "Sprawdz dolny blok z logika, wzorami i oznaczeniami.",
            ]
        elif AssistantService._is_function_list_question(question):
            next_steps = [
                "Wpisz jedna komende, np. 'zrob mi wykres' albo 'stworz raport ML'.",
                "Mozesz laczyc polecenia w jednym zdaniu, np. 'stworz raport i pokaz PDF'.",
                "Do nauki wpisz 'lekcja ML', 'lekcja raportow' albo 'lekcja diagramow'.",
            ]
        elif any(k in question for k in ["tren", "model", "main"]):
            next_steps = [
                "Przejdz do Main i zaznacz modele.",
                "Wczytaj dane i uruchom trening.",
                "Sprawdz metryki i zapisz najlepszy model.",
            ]
        elif any(k in question for k in ["heuryst", "sto", "mopt", "mt", "mo", "mzo", "genetic"]):
            next_steps = [
                "Przejdz do Main i wybierz metody STO.",
                "Podaj zlecenia, czasy wykonania i terminy.",
                "Porownaj STO w Results albo otworz SolutionTree w Visual.",
            ]
        elif any(
            k in question
            for k in ["diagram", "diagrams", "drawio", "draw.io", "uml", "erd", "bpmn"]
        ):
            next_steps = [
                "Przejdz do Diagrams.",
                "Wybierz szablon albo dodaj ksztalt.",
                "Przeciagnij elementy myszka i wyeksportuj .drawio, SVG, Mermaid albo HTML.",
            ]
        elif any(k in question for k in ["visual", "wykres", "drzew", "gantt", "html"]):
            next_steps = [
                "Przejdz do Visual i ustaw X/Y/Z.",
                "Kliknij Aktualizuj wykres.",
                "Otworz D3 HTML do analizy interaktywnej.",
            ]
        elif any(k in question for k in ["analytics", "kpi", "notebook", "raport"]):
            next_steps = [
                "Przejdz do Report.",
                "Wczytaj dane albo otworz Report Builder.",
                "Dodaj wynik, Pipeline, ML/STO analize albo plik z Visual/Diagrams.",
                "Sprawdz podglad PDF-like i dopiero eksportuj HTML/PDF.",
            ]
        elif any(k in question for k in ["sql", "result", "csv", "tabela"]):
            next_steps = [
                "Przejdz do Results i wlacz tryb SQL.",
                "Uruchom SELECT i sprawdz osobna tabele wynikow.",
                "Wyeksportuj wynik do CSV.",
            ]
        else:
            next_steps = [
                "Napisz, czy chcesz pomoc z Main, Visual czy Results.",
                "Moge od razu podac liste klikniec krok po kroku.",
            ]

        if profile == "krotko":
            answer = answer.split("\n")[0].strip() or answer
            next_steps = next_steps[:2]
        elif profile == "ekspercko":
            answer = f"{answer}\n\nWniosek praktyczny: skup sie na przewidywalnosci metryk i porownaniu wariantow."

        formatted_steps = "\n".join(f"- {step}" for step in next_steps)
        clean = answer.replace("[RAG]", "").replace("zrodla:", "").strip()
        lead = AssistantService._human_lead(clean, question)
        if lead and not clean.lower().startswith(lead.lower()):
            clean = f"{lead}\n\n{clean}"
        clean = AssistantService._add_plain_explanation(clean, question, profile)
        return f"{clean}\n\nCo dalej:\n{formatted_steps}"

    @staticmethod
    def _add_plain_explanation(answer: str, question: str, profile: str = "normal") -> str:
        if profile == "krotko":
            return answer
        if AssistantService._is_function_list_question(question) or AssistantService._category_help(question):
            return answer
        lowered = answer.lower()
        if "jak to czytac:" in lowered or "jak to czytać:" in lowered:
            return answer

        blocks: list[str] = []
        if any(k in question for k in ["diagram", "diagrams", "drawio", "uml", "erd", "bpmn"]):
            blocks.append(
                "Jak to czytac:\n"
                "- Traktuj diagram jak mape procesu: ksztalt to krok, strzalka to zaleznosc albo przeplyw.\n"
                "- Najpierw ustaw glowna sciezke od startu do konca, dopiero potem dodawaj warunki i odgalezienia.\n"
                "- Do dokumentacji eksportuj HTML albo SVG, a do dalszej edycji .drawio."
            )
        elif any(k in question for k in ["wykres", "visual", "html", "dashboard", "chart"]):
            blocks.append(
                "Jak to czytac:\n"
                "- Najpierw patrz na osie: X mowi, co porownujesz, Y pokazuje wartosc albo wynik.\n"
                "- Kolor, rozmiar albo linia zwykle oznacza dodatkowy wymiar, np. termin, grupe albo jakosc.\n"
                "- Jesli punkt lub galaz mocno odstaje, nie traktuj tego od razu jako blad; sprawdz rekord w Results."
            )
        elif any(k in question for k in ["analytics", "kpi", "raport", "notebook", "analiza"]):
            blocks.append(
                "Jak to czytac:\n"
                "- Najpierw sprawdz liczbe wierszy, braki i duplikaty, bo one decyduja, czy wynik jest wiarygodny.\n"
                "- Potem porownaj metryke glowna z wymiarem, np. cena wzgledem materialu albo odpad wzgledem terminu.\n"
                "- Na koncu wybierz jedna akcje: popraw dane, zrob wykres w Visual albo zapisz raport HTML."
            )
        elif any(k in question for k in ["drzew", "solutiontree", "decisiontree"]):
            blocks.append(
                "Jak to czytac:\n"
                "- Zielona sciezka pokazuje wariant aktualnie najlepszy albo wybrany przez algorytm.\n"
                "- Zolty element oznacza przejscie, ktore bylo sprawdzone i po porownaniu algorytm wrocil dalej.\n"
                "- Klikaj wezly w HTML, zeby chowac galazie i zostawic tylko fragment, ktory teraz analizujesz."
            )
        elif any(k in question for k in ["model", "algorytm", "trening", "metryk"]):
            blocks.append(
                "Jak to czytac:\n"
                "- Wynik treningowy pokazuje, czego model nauczyl sie na znanych danych.\n"
                "- Wynik testowy pokazuje, czy model radzi sobie na nowych danych.\n"
                "- Duza roznica miedzy nimi oznacza ryzyko przeuczenia i warto wtedy uproscic model albo poprawic dane."
            )

        if profile == "ekspercko":
            blocks.append(
                "Kontrola jakosci odpowiedzi:\n"
                "- Nie opieraj decyzji na jednym wykresie; porownaj go z tabela i raportem brakow.\n"
                "- Jezeli dane sa male, traktuj rekomendacje jako hipoteze do sprawdzenia, nie jako pewnik."
            )
        if not blocks:
            return answer
        return f"{answer}\n\n" + "\n\n".join(blocks)

    @staticmethod
    def _human_lead(answer: str, question: str) -> str:
        if any(k in question for k in ["jak sie masz", "jak się masz", "co u ciebie"]):
            return ""
        if AssistantService._is_function_list_question(question) or AssistantService._category_help(question):
            return ""
        if "raport" in question or "podsumowanie" in question:
            return "Jasne. Najpierw dam Ci sedno, a szczegoly zostawiam ponizej."
        if any(k in question for k in ["jak", "dlaczego", "czemu"]):
            return "Jasne, tlumacze po ludzku."
        if any(k in question for k in ["otworz", "przejdz", "uruchom", "zrob"]):
            return "Okej, przechodze do konkretnej akcji."
        if len(answer) > 900:
            return "Mam dluzsza odpowiedz, wiec zaczynam od najwazniejszego."
        return ""

    @staticmethod
    def _web_lookup(question: str) -> str:
        query = quote_plus(question.strip())
        if not query:
            return ""
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
        req = request.Request(url, headers={"User-Agent": "AOA-ALICE/1.0"}, method="GET")
        try:
            with request.urlopen(req, timeout=6) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
            payload = json.loads(raw)
        except Exception:
            return ""
        abstract = (payload.get("AbstractText") or "").strip()
        heading = (payload.get("Heading") or "").strip()
        if abstract:
            return f"{heading}: {abstract}" if heading else abstract
        related = payload.get("RelatedTopics") or []
        for item in related[:3]:
            if isinstance(item, dict):
                text = (item.get("Text") or "").strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _casual_playbook(question: str) -> str | None:
        compact = question.strip().lower()
        category_help = AssistantService._category_help(compact)
        if category_help:
            return category_help
        if AssistantService._is_function_list_question(compact):
            return AssistantService._terminal_help()
        if any(
            k in compact
            for k in [
                "opowiedz cos o projekcie",
                "opowiedz o projekcie",
                "co to za projekt",
                "co robi projekt",
                "co robi aplikacja",
                "o projekcie",
                "production optimization",
                "aoa",
                "aplikacja optymalnego algorytmowania",
            ]
        ):
            return (
                "To jest AOA - Aplikacja Optymalnego Algorytmowania, czyli aplikacja do przejscia calej pracy od danych do decyzji.\n\n"
                "Najprosciej:\n"
                "- Main przygotowuje dane, uruchamia classic ML, TabPFN, XGBoost/nowoczesne ML, STO i modele wlasne.\n"
                "- Visual pokazuje wykresy, dashboardy, drzewa decyzyjne i interaktywne HTML.\n"
                "- Results pozwala sprawdzac tabele, filtrowac, uzywac SQL i eksportowac CSV.\n"
                "- Report sklada raporty: gotowe formaty, KPI, ML/STO, pipeline, pliki z wykresow i PDF/HTML.\n"
                "- Diagrams sluzy do flowchartow, BPMN, UML, ERD, VSM, procesow produkcyjnych i eksportu.\n"
                "- Theory tlumaczy algorytmy jedna animacja krok po kroku, z logika i wzorami.\n\n"
                "Moja rola jako ALICE: tlumaczyc te ekrany po ludzku, prowadzic krok po kroku, podpowiadac co kliknac i wyjasniac, co znacza metryki, modele, pliki oraz raporty."
            )
        if any(k in compact for k in ["kolejne segmenty", "segmenty rozwoju", "roadmap", "co dalej rozwijac"]):
            return (
                f"{segment_summary()}\n\n"
                "Te segmenty sa w aplikacji opisane i podlaczone do ALICE jako playbooki: recenzent, operator, "
                "kontroler release, analityk raportu i przewodnik po modelach."
            )
        if any(k in compact for k in ["szablony raportow", "report templates", "gotowe raporty"]):
            return (
                f"{report_template_summary()}\n\n"
                "Najprosciej: napisz 'stworz raport ML', 'stworz raport STO' albo 'release report', "
                "a ALICE poprowadzi Cie przez potrzebne sekcje."
            )
        if any(k in compact for k in ["kontrakt danych", "data contract", "wymagane kolumny", "walidacja danych"]):
            return (
                f"{data_contract_summary()}\n\n"
                "Jesli dane nie przechodza treningu, najpierw sprawdz typy kolumn, braki, NaN/inf i czy cel y istnieje."
            )
        if any(
            k in compact
            for k in [
                "ocen",
                "oceń",
                "sprawdz czy",
                "sprawdz moj",
                "sprawdz diagram",
                "sprawdz raport",
                "sprawdz wykres",
                "sprawdz model",
                "audyt",
                "czy jest git",
            ]
        ):
            if any(k in compact for k in ["diagram", "bpmn", "uml", "erd", "flow", "proces"]):
                return (
                    "Moge ocenic diagram jak checklist QA, niezaleznie od tego, w ktorym module jestes.\n\n"
                    "Sprawdzam po kolei:\n"
                    "1. Cel: czy tytul mowi, jaki proces/relacje pokazuje diagram.\n"
                    "2. Start i koniec: czy wiadomo, gdzie zaczyna sie przeplyw i co jest wynikiem.\n"
                    "3. Elementy: czy kazdy blok ma krotka, konkretna etykiete.\n"
                    "4. Polaczenia: czy strzalki ida w jedna logiczna strone i nie krzyzuja sie bez potrzeby.\n"
                    "5. Decyzje: czy bramki maja opisane wyjscia, np. tak/nie, OK/NOK.\n"
                    "6. Kolory: czy kolor oznacza znaczenie, a nie losowa dekoracje.\n"
                    "7. Czytelnosc: czy po eksporcie SVG/HTML tekst nie nachodzi na linie.\n"
                    "8. Kontekst: czy diagram ma note, co oznaczaja skroty i kto ma z niego korzystac.\n\n"
                    "Jesli chcesz, napisz 'ocen diagram z opisu: ...', a podam brakujace elementy przed zbudowaniem go w Diagrams."
                )
            if any(k in compact for k in ["raport", "report", "pdf", "latex"]):
                return (
                    "Moge ocenic raport jak redaktor i analityk.\n\n"
                    "Minimalny dobry raport AOA powinien miec:\n"
                    "1. Cel decyzji: po co raport powstal i jaka decyzje wspiera.\n"
                    "2. Dane: zrodlo, zakres, liczba rekordow, braki i ograniczenia.\n"
                    "3. Pipeline: dane -> walidacja -> ML/STO/TabPFN -> Visual/Results -> wnioski.\n"
                    "4. Wyniki: metryki, wykresy, tabele i porownanie modeli/metod.\n"
                    "5. Interpretacje: co oznacza wynik po ludzku, nie tylko liczby.\n"
                    "6. Ryzyka: czego nie wiemy, co moze zaburzyc wynik.\n"
                    "7. Rekomendacje: konkretne nastepne dzialania.\n"
                    "8. Podglad PDF/HTML: czy strona ma marginesy, nie ucina tabel i ma czytelne naglowki.\n\n"
                    "Komendy: 'stworz raport ML', 'dodaj ryzyka', 'podglad PDF', 'dodaj plik do raportu'."
                )
            if any(k in compact for k in ["wykres", "visual", "dashboard", "html"]):
                return (
                    "Moge ocenic wykres albo dashboard pod decyzje, nie tylko wyglad.\n\n"
                    "Patrze na:\n"
                    "1. Pytanie: czy wykres odpowiada na konkretne pytanie.\n"
                    "2. Osie: czy X/Y maja nazwy, jednostki i sensowny zakres.\n"
                    "3. Typ: scatter do relacji, histogram do rozkladu, bar do porownan, linia do czasu, heatmap do macierzy.\n"
                    "4. Kolor i rozmiar: czy koduja konkretna zmienna.\n"
                    "5. Outliery: czy widac rekordy odstajace i czy sa opisane.\n"
                    "6. Interakcja HTML: tooltip, zoom/fullscreen, eksport i reset.\n"
                    "7. Czytelnosc: czy etykiety nie nachodza i legenda nie przykrywa danych.\n\n"
                    "Po wykresie warto przejsc do Results i sprawdzic rekordy, ktore wygladaja podejrzanie."
                )
            if any(k in compact for k in ["model", "ml", "tabpfn", "xgboost", "metryk", "trening"]):
                return (
                    "Moge ocenic model ML/TabPFN/XGBoost jako kontrola przed zaufaniem wynikowi.\n\n"
                    "Sprawdzam:\n"
                    "1. Typ zadania: Quality/Delay = regresja, Schedule = klasyfikacja.\n"
                    "2. Dane: brak NaN/inf, sensowne typy kolumn, brak przecieku celu do cech.\n"
                    "3. Podzial: train/test jest staly i taki sam dla porownywanych modeli.\n"
                    "4. Metryki: regresja RMSE/MAE/R2, klasyfikacja accuracy/F1/confusion matrix.\n"
                    "5. Baseline: porownanie z prostym modelem albo heurystyka.\n"
                    "6. Stabilnosc: random_state, kilka modeli, historia treningow.\n"
                    "7. Interpretacja: wazne cechy, drzewo decyzyjne albo Theory.\n"
                    "8. Decyzja: co wynik zmienia w praktyce, a czego jeszcze nie wolno wnioskowac.\n\n"
                    "Komendy: 'porownaj modele', 'pokaz historie', 'lekcja XGBoost', 'trenuj Quality'."
                )
            return (
                "Moge zrobic uniwersalny audyt AOA dla kazdego trybu: Main, Visual, Results, Report, Diagrams i Theory.\n\n"
                "Moja checklista:\n"
                "1. Czy wiadomo, jaki jest cel pracy.\n"
                "2. Czy dane albo wejscie sa poprawne i opisane.\n"
                "3. Czy wybrany model/wykres/diagram pasuje do celu.\n"
                "4. Czy wynik ma metryki, opis i ryzyka.\n"
                "5. Czy uzytkownik ma nastepny krok: Results, Visual, Report, eksport albo poprawka danych.\n"
                "6. Czy artefakt da sie odtworzyc pozniej z plikow, historii albo raportu.\n\n"
                "Mozesz napisac: 'ocen diagram', 'ocen raport', 'ocen wykres', 'ocen model' albo 'audyt workflow'."
            )
        if any(
            k in compact
            for k in [
                "co mozesz przetestowac",
                "co mozesz pokazac",
                "co mozesz stworzyc",
                "co mozesz utworzyc",
                "co mozesz zrobic w aplikacji",
                "jak mozesz sterowac",
                "jakie akcje alice",
                "tryb operatora",
            ]
        ):
            return (
                "Moge dzialac w trybie operatora, czyli nie tylko odpowiadac, ale tez wykonac ruch w aplikacji.\n\n"
                "Przyklady polecen:\n"
                "- 'przetestuj raport' -> uruchomie Report Studio, wczytam gotowy format i otworze edytor.\n"
                "- 'stworz raport' -> zloze szkic raportu z sekcjami ML, STO, pipeline i rekomendacjami.\n"
                "- 'stworz raport ML' albo 'stworz raport STO' -> przygotuje raport pod konkretny typ decyzji.\n"
                "- 'dodaj wykres/plik/KPI do raportu' -> rozbuduje aktualny raport o gotowy blok.\n"
                "- 'eksportuj notebook' albo 'csv akcji' -> wygeneruje material do dalszej analizy.\n"
                "- 'pokaz XGBoost' -> przejde do Theory i ustawie animacje XGBoost.\n"
                "- 'pokaz MLP/Stacking/Schedule' -> ustawie odpowiednia animacje nowoczesnego ML.\n"
                "- 'przetestuj diagram' -> zbuduje diagram z opisu w Diagrams.\n"
                "- 'wczytaj dane do Visual' -> otworze plik w Visual, a potem moge dobrac wykres.\n"
                "- 'dobierz wykres' -> wezme aktualne dane albo sample i wybiore sensowny wykres startowy.\n"
                "- 'wczytaj sample do Results' -> pokaze tabele w Results bez szukania pliku.\n"
                "- 'pokaz SQL przyklad/statystyki/braki/top' -> przelacze Results w SQL i odpale gotowe zapytanie.\n"
                "- 'stworz diagram produkcji/logistyczny/systemu' -> sama wybiore typ diagramu i uloze elementy.\n"
                "- 'stworz diagram danych' -> uloze pipeline CSV -> walidacja -> model -> metryki -> raport.\n"
                "- 'diagram BPMN/UML/ERD/sieci/swimlane/kanban/QC/MLOps/VSM' -> zbuduje konkretny typ diagramu na planszy.\n"
                "- 'otworz kreator diagramu' -> pokaze formularz do opisania diagramu slowami.\n"
                "- 'dodaj maszyne/model ML/notatke/kontener' -> dodam gotowy blok do aktualnego diagramu.\n"
                "- 'sample dashboard' -> przejde do Visual i narysuje przykladowy dashboard.\n"
                "- 'otworz raport D3' albo 'pokaz wybor wykresu' -> pomoge w Visual.\n"
                "- 'przejdz do Results' albo 'uruchom SQL' -> otworze Results i wykonam odpowiednia akcje.\n"
                "- 'pokaz braki danych', 'eksportuj widoczne wyniki' albo 'eksportuj wynik SQL' -> pomoge w Results.\n"
                "- 'przetestuj Main' -> przygotuje dane testowe i pokaze panel modeli.\n"
                "- 'wczytaj sample do Main' -> wygeneruje dane treningowe z aktualnych parametrow.\n"
                "- 'zaznacz Quality/Delay/Schedule' -> ustawie odpowiednie modele w Main.\n"
                "- 'ustaw TabPFN' albo 'ustaw classic' -> zmienie backend treningu.\n"
                "- 'naucz modele', 'trenuj Quality' albo 'trenuj TabPFN Quality' -> przygotuje dane, zaznacze cel i uruchomie trening po potwierdzeniu.\n\n"
                "Moge tez prowadzic sciezkami: 'lekcja ML', 'lekcja raportow', 'lekcja diagramow' albo 'co powinienem kliknac'.\n\n"
                "Ciezsze akcje, np. trening modeli albo samonauka, wymagaja potwierdzenia, jesli nie wlaczysz auto-potwierdzania."
            )
        if any(
            k in compact
            for k in [
                "opowiedz o sobie",
                "powiedz o sobie",
                "kim jestes",
                "kim jesteś",
                "co umiesz",
            ]
        ):
            return (
                "Jestem ALICE, czyli przewodniczka po AOA - Aplikacji Optymalnego Algorytmowania.\n"
                "Moim zadaniem nie jest tylko odpowiadac jednym zdaniem, ale prowadzic uzytkownika krok po kroku: "
                "co kliknac, co oznacza wynik i gdzie sprawdzic szczegoly.\n\n"
                "Znam glowne miejsca aplikacji:\n"
                "- Main: wczytanie danych, wybor classic ML/TabPFN/STO, modele wlasne i zapis wynikow.\n"
                "- Visual: wykresy, dashboardy, ML Decision Tree, SolutionTree i eksport HTML.\n"
                "- Results: tabela wynikow, filtrowanie, SQL, eksport CSV.\n"
                "- Report: raporty, pelny Report Builder, KPI, diagnostyka danych, notebook i workflow analityczne.\n"
                "- Diagrams: schematy procesow, UML, ERD, BPMN, VSM, supply chain, produkcja, edycja i eksport.\n"
                "- Theory: animacje, ktore tlumacza ML, heurystyki/STO, TabPFN, XGBoost, MLP i Stacking.\n\n"
                "Wiem tez, czym sa zadania regresji i klasyfikacji: Quality/Delay przewiduja liczby, a Schedule wybiera klase/strategie.\n\n"
                "Najlepiej pytaj mnie normalnie, np. 'co zrobic w Main?', 'czemu drzewo jest zolte?', "
                "'jak czytac raport?', 'jaki model wybrac?' albo 'przeprowadz mnie przez workflow'."
            )
        if "main" in compact and any(
            k in compact
            for k in ["co robi", "co sie robi", "co robi sie", "powiedz", "wytlumacz", "opowiedz"]
        ):
            return (
                "Main to miejsce startowe do pracy z danymi i modelami.\n"
                "Tam uzytkownik przygotowuje dane, wybiera modele, uruchamia trening albo heurystyki STO i zapisuje wyniki.\n\n"
                "Jak to przejsc:\n"
                "1. Wczytaj plik z danymi albo uzyj danych przykladowych.\n"
                "2. Sprawdz, czy kolumny typu cena, odpad, czas, termin i material sa poprawnie rozpoznane.\n"
                "3. Wybierz modele ML, jesli chcesz predykcje jakosci/opoznienia/strategii.\n"
                "4. Wybierz heurystyki STO, jesli chcesz ulozyc kolejke zlecen i policzyc opoznienia.\n"
                "5. Uruchom obliczenia, potem przejdz do Visual albo Results, zeby zobaczyc wynik.\n\n"
                "Najprosciej: Main robi obliczenia, Visual pokazuje je na wykresach, Results pozwala sprawdzic tabele."
            )
        if any(
            k in compact
            for k in [
                "zbudowac agenta",
                "zbudować agenta",
                "llm agenta",
                "dobrego agenta",
                "agent llm",
            ]
        ):
            return (
                "Dobry agent LLM w tej aplikacji powinien miec trzy warstwy.\n"
                "1. Wiedza stala: opis zakladek, modeli, workflow, wykresow i typowych problemow uzytkownika.\n"
                "2. Wiedza z aplikacji: aktualnie wybrany ekran, wczytane kolumny, typ wykresu, wynik raportu i bledy.\n"
                "3. Akcje: przejscie do zakladki, ustawienie wykresu, otwarcie HTML, wygenerowanie raportu albo wyjasnienie wyniku.\n\n"
                "W praktyce ALICE powinna odpowiadac tak: najpierw sedno, potem proste wyjasnienie, na koncu konkretne kroki. "
                "Jesli nie zna odpowiedzi, nie powinna udawac; ma powiedziec, czego brakuje i zaproponowac najblizsza akcje."
            )
        if any(k in compact for k in ["jak sie masz", "jak się masz", "co u ciebie"]):
            return (
                "Mam sie dobrze i jestem gotowa do pracy w aplikacji.\n"
                "Mozesz traktowac mnie jak terminal z jezykiem naturalnym: piszesz, co chcesz zrobic, "
                "a ja wykonuje akcje albo pokazuje, gdzie kliknac.\n\n"
                "Przyklady: 'zrob mi wykres', 'stworz raport ML', 'pokaz braki danych', "
                "'lekcja ML', 'stworz diagram produkcji', 'wypisz funkcje'."
            )
        casual_prompts = {
            "powiedz cos",
            "powiedz coś",
            "hej",
            "czesc",
            "cześć",
            "siema",
            "test",
            "halo",
        }
        if (
            compact in casual_prompts
            or len(compact.split()) <= 2
            and any(k in compact for k in ["powiedz", "test", "hej"])
        ):
            return (
                "Jestem ALICE i moge pomoc Ci przejsc przez aplikacje bez zgadywania.\n"
                "Najlepiej dzialam, gdy pytasz konkretnie, np.:\n"
                "- co pokazuje ten wykres,\n"
                "- jak uruchomic workflow w Report,\n"
                "- czym rozni sie ML od STO,\n"
                "- jak zrobic raport albo diagram,\n"
                "- czym rozni sie classic ML, TabPFN, custom ML i STO.\n"
                "Jesli chcesz szybki start: wczytaj dane, wejdz w Report albo Visual, a ja wytlumacze wynik krok po kroku."
            )
        if "workflow" in compact and any(
            k in compact for k in ["powiedz", "wymow", "czytaj", "glos", "akcent"]
        ):
            return (
                "Workflow czytam jako 'łork-floł', czyli przeplyw pracy.\n"
                "W aplikacji workflow oznacza gotowy zestaw krokow, np. kontrola danych, analiza metryki, wykres, raport i rekomendacje."
        )
        return None

    @staticmethod
    def _is_function_list_question(compact: str) -> bool:
        phrases = [
            "wypisz funkcje",
            "wypisz komendy",
            "lista funkcji",
            "lista komend",
            "jakie masz funkcje",
            "jakie funkcje masz",
            "co potrafisz",
            "co umiesz",
            "co umiesz zrobic",
            "co mozesz zrobic",
            "komendy alice",
            "help alice",
            "terminal alice",
        ]
        return any(phrase in compact for phrase in phrases)

    @staticmethod
    def _terminal_help() -> str:
        return (
            "Tryb terminalowy ALICE: piszesz normalnym jezykiem, a ja odpowiadam, przenosze do modulu albo wykonuje dostepna akcje.\n\n"
            "Kategorie komend:\n"
            "1. Dane i modele - Main, dane treningowe, zaznaczanie modeli, backend classic/TabPFN, trening, XGBoost, custom ML, custom STO.\n"
            "2. Wykresy i Visual - dashboardy, HTML, drzewa, wykresy i interpretacja.\n"
            "3. Results i SQL - tabele, filtry, braki danych, sample, eksport CSV i zapytania.\n"
            "4. Raporty - Report Builder, PDF/HTML, KPI, ML/STO analytics, pliki i szablony.\n"
            "5. Diagramy - flowchart, BPMN, UML, ERD, VSM, MLOps i diagramy z opisu.\n"
            "6. Theory i lekcje - animacje ML/STO/nowoczesne ML, wzory i nauka krok po kroku.\n"
            "7. Sterowanie aplikacja - przechodzenie po ekranach, podswietlanie paneli i testy.\n"
            "8. Pliki i porzadek - podglad wygenerowanych CSV/HTML/PDF/modeli oraz bezpieczne usuwanie po potwierdzeniu.\n"
            "9. Release i QA - check przed GitHubem, kontrola HTML i historia workflowow.\n"
            "10. Historia, sample i porownania - ostatnie pliki, zapisane workflowy, sample do Main/Visual/Results i porownywarka modeli.\n"
            "11. Ocena i audyt - sprawdzenie diagramu, raportu, wykresu, modelu, wynikow albo calego workflow.\n"
            "12. ALICE i samonauka - status, baza wiedzy, co wiem o aplikacji i potwierdzanie akcji.\n\n"
            "Zapytaj o kategorie, np. 'co mozesz w diagramach?', 'co umiesz w raportach?', "
            "'jakie komendy do Results?' albo od razu wydaj polecenie: 'wczytaj sample do Main', "
            "'zaznacz Quality i ustaw TabPFN', 'naucz modele', 'stworz diagram BPMN', "
            "'zrob raport ML', 'pokaz braki danych', 'otworz pliki', 'release check', "
            "'pokaz historie', 'porownaj modele', 'pokaz tutoriale', 'ocen diagram', 'lekcja XGBoost'."
        )

    @staticmethod
    def _category_help(compact: str) -> str | None:
        if not AssistantService._has_help_intent(compact):
            return None
        if "operatora" in compact or "tryb operator" in compact:
            return None
        if _has_word(compact, ("plik", "pliki", "plikami", "usun", "usuwanie", "porzadek")) and not any(
            k in compact for k in ["visual", "report", "results", "main", "diagram"]
        ):
            return (
                "Pliki i porzadek - co moge zrobic:\n"
                "1. Otworzyc menedzer plikow AOA.\n"
                "2. Pokazac wygenerowane dane, raporty HTML, PDF, Markdown, JSON, modele .pkl i obrazy.\n"
                "3. Zrobic tekstowy podglad pliku przed decyzja.\n"
                "4. Otworzyc plik w domyslnej aplikacji albo przegladarce.\n"
                "5. Usunac wybrany plik dopiero po potwierdzeniu.\n\n"
                "Polecenia: 'otworz pliki', 'menedzer plikow', 'pokaz pliki', 'usun pliki', 'posprzataj pliki'."
            )
        if any(k in compact for k in ["release", "github", "qa", "kontrola", "publikacja"]):
            return (
                "Release i QA - co moge zrobic:\n"
                "1. Podac checklist przed publikacja na GitHubie.\n"
                "2. Przejsc przez Main, Visual, Results, Report, Diagrams i Theory.\n"
                "3. Otworzyc kontrolny HTML z Visual i sprawdzic fullscreen, eksport, tooltipy oraz czy wykres nie wychodzi poza ekran.\n"
                "4. Przypomniec o testach, historii treningow, historii workflowow i porownaniu modeli.\n\n"
                "Polecenia: 'release check', 'sprawdz release', 'qa html', 'sprawdz wykresy html'."
            )
        if any(
            k in compact
            for k in [
                "historia",
                "workflow",
                "workflowow",
                "porown",
                "porownaj",
                "porownywarka",
                "sample",
                "przykladowe",
                "tutorial",
                "tutoriale",
                "instrukcja",
            ]
        ):
            return (
                "Historia, sample, porownania i tutoriale - co moge zrobic:\n"
                "1. Otworzyc historie artefaktow AOA: wyniki, modele, raporty, wykresy HTML, diagramy, JSON i notebooki.\n"
                "2. Pokazac menedzer plikow jako historie treningow i workflowow zapisanych lokalnie.\n"
                "3. Przygotowac sample do Main, Visual albo Results, zeby testowac bez szukania pliku.\n"
                "4. Przeniesc do porownywania modeli w Results/Visual/Report i przypomniec metryki: RMSE, MAE, R2, accuracy, F1, opoznienia i bufor.\n"
                "5. Otworzyc tutoriale krok po kroku w Readme, docs i Theory.\n"
                "6. Podpowiedziec nastepny krok po wykonanym workflow: trening -> Results -> Visual -> Report -> pliki.\n\n"
                "Polecenia: 'pokaz historie', 'historia treningow', 'ostatnie pliki', "
                "'porownaj modele', 'pokaz sample', 'wczytaj sample do Main', "
                "'pokaz tutoriale', 'instrukcja krok po kroku'."
            )
        if any(k in compact for k in ["diagram", "drawio", "draw.io", "uml", "erd", "bpmn"]):
            return (
                "Diagramy - co moge zrobic:\n"
                "1. Stworzyc diagram z opisu: 'zrob diagram z opisu: dostawca -> magazyn -> QC -> produkcja'.\n"
                "2. Otworzyc kreator: 'otworz kreator diagramu'.\n"
                "3. Zbudowac praktyczne typy: proces, BPMN, UML, ERD, siec, swimlane, sekwencja, org chart, mind map, decyzje.\n"
                "4. Zbudowac diagramy operacyjne: kanban, magazyn, QC, MLOps, utrzymanie ruchu, VSM, supply chain, layout hali, ANDON, zapasy i energia.\n"
                "5. Dodac elementy: maszyna, magazyn, model ML, notatka, kontener, bramka decyzyjna albo polaczenie.\n"
                "6. Uporzadkowac plansze: auto layout, zastosuj styl, wyczysc, duplikuj, usun zaznaczony.\n"
                "7. Wyeksportowac: .drawio, SVG, Mermaid albo HTML.\n\n"
                "Najlepsze polecenia startowe:\n"
                "- 'stworz diagram BPMN procesu reklamacji'\n"
                "- 'stworz ERD dla zamowien, produktow i klientow'\n"
                "- 'zrob diagram MLOps od danych do monitoringu'\n"
                "- 'diagram magazynu z kontrola jakosci i wysylka'"
            )
        if any(k in compact for k in ["raport", "report", "pdf", "kpi", "notebook", "analytics"]):
            return (
                "Raporty - co moge zrobic:\n"
                "1. Otworzyc pelny Report Builder jak edytor Overleaf/LaTeX.\n"
                "2. Wstawic gotowy format: cel raportu, pipeline pracy, dane i wyniki, ML analiza, STO analiza, wnioski.\n"
                "3. Dodac bloki: KPI, wykres, rekomendacje, ryzyka, plan predykcji, pipeline, obraz/HTML z Visual albo diagram.\n"
                "4. Wczytac pliki z projektu i wstawic je do raportu jako zalacznik, obraz albo link.\n"
                "5. Pokazac podglad strony/PDF i eksportowac HTML, MD, TeX albo PDF.\n"
                "6. Wykonac workflow Report Studio: data quality, dashboard, KPI, diagnostyka, korelacje, outliery, notebook.\n\n"
                "Polecenia:\n"
                "- 'stworz raport ML'\n"
                "- 'stworz raport STO'\n"
                "- 'otworz pelny edytor raportu'\n"
                "- 'dodaj KPI do raportu'\n"
                "- 'podglad PDF'\n"
                "- 'eksportuj notebook'"
            )
        if any(k in compact for k in ["visual", "wykres", "dashboard", "html", "drzewo"]):
            return (
                "Visual - co moge zrobic:\n"
                "1. Przejsc do Visual i ustawic panel wykresu.\n"
                "2. Wczytac plik do Visual albo sample bez szukania danych.\n"
                "3. Dobierac wykres startowy do kolumn: scatter, histogram albo dashboard.\n"
                "4. Rysowac z opisu: scatter, histogram, dashboard i potem odswiezyc raport.\n"
                "5. Otworzyc interaktywny raport D3/HTML.\n"
                "6. Wyjasnic osie, kolory, rozmiar punktow, outliery i relacje.\n"
                "7. Rozroznic ML Decision Tree od SolutionTree.\n"
                "8. Pomoc dobrac biblioteke: Matplotlib, Seaborn, Plotly, Altair, NetworkX.\n\n"
                "Polecenia: 'wczytaj dane do Visual', 'wczytaj sample do Visual', 'dobierz wykres', "
                "'scatter z opisu', 'histogram z opisu', 'dashboard z opisu', 'otworz raport D3'."
            )
        if any(k in compact for k in ["results", "wynik", "wyniki", "sql", "csv", "tabela", "filtr"]):
            return (
                "Results i SQL - co moge zrobic:\n"
                "1. Przeniesc do Results i pokazac tabele wynikow.\n"
                "2. Wczytac plik do Results albo sample do testow.\n"
                "3. Pokazac braki danych, duplikaty albo rekordy odstajace.\n"
                "4. Pomoc z filtrowaniem i sortowaniem kolumn.\n"
                "5. Uruchomic gotowe SQL: pierwsze wiersze, statystyki, braki albo top rekordy.\n"
                "6. Uruchomic albo wyjasnic wlasne zapytanie SQL.\n"
                "7. Eksportowac widoczne wyniki albo wynik SQL do CSV.\n\n"
                "Polecenia: 'wczytaj dane do Results', 'wczytaj sample do Results', 'pokaz SQL przyklad', "
                "'SQL statystyki', 'SQL braki', 'SQL top', 'eksportuj wynik SQL'."
            )
        if any(
            k in compact
            for k in ["main", "dane", "model", "modele", "trening", "tabpfn", "xgboost", "custom"]
        ) or _has_word(compact, ("sto",)):
            return (
                "Dane i modele - co moge zrobic:\n"
                "1. Otworzyc Main, wczytac plik albo wygenerowac dane testowe.\n"
                "2. Wczytac sample do Main, czyli przygotowac dane treningowe bez szukania pliku.\n"
                "3. Zaznaczyc modele za uzytkownika: Quality, Delay, Schedule, wszystkie ML, podstawowe ML, wszystkie STO albo podstawowe STO.\n"
                "4. Ustawic backend classic albo TabPFN.\n"
                "5. Wyjasnic typ zadania: Quality/Delay to regresja, Schedule to klasyfikacja.\n"
                "6. Pomoc wybrac model: RandomForest, ExtraTrees, GradientBoosting, HistGradient, SVR, KNN, Ridge, LogisticRegression, XGBoost, MLP, Stacking, TabPFN.\n"
                "7. Utworzyc wlasny model sklearn albo wlasna heurystyke STO z opisem/wzorem.\n"
                "8. Uruchomic trening po potwierdzeniu: aktualnie zaznaczone modele, Quality, Delay, Schedule albo TabPFN Quality.\n"
                "9. Uruchomic STO i pokazac, co dalej sprawdzic w Results/Visual.\n\n"
                "Polecenia: 'wczytaj dane z pliku', 'wczytaj sample do Main', 'zaznacz Quality', "
                "'zaznacz wszystkie ML', 'zaznacz podstawowe STO', 'ustaw TabPFN', "
                "'naucz modele', 'trenuj Quality', 'trenuj TabPFN Quality', "
                "'dodaj wlasny model ML', 'dodaj heurystyke', 'uruchom STO'."
            )
        if any(k in compact for k in ["theory", "teoria", "lekcja", "nauka", "algorytm", "wzor", "wzory"]):
            return (
                "Theory i lekcje - co moge zrobic:\n"
                "1. Pokazac animacje classic ML: Random Forest, ExtraTrees, GradientBoosting, HistGradient, Logistic/Schedule.\n"
                "2. Pokazac heurystyki STO: MT/EDD, MO/SPT, MZO/LPT, MOpt, Genetic, Slack, Critical Ratio.\n"
                "3. Pokazac nowoczesne ML: TabPFN, XGBoost, MLP, Stacking.\n"
                "4. Wyjasnic kazdy krok: dane, cechy, braki, trening, walidacja, predykcja, metryki.\n"
                "5. Podac wzory i oznaczenia po ludzku.\n\n"
                "Polecenia: 'lekcja ML', 'lekcja raportow', 'lekcja diagramow', "
                "'pokaz XGBoost', 'pokaz TabPFN', 'pokaz Stacking', 'daj liste krok po kroku'."
            )
        if any(
            k in compact
            for k in ["sterowanie", "sterowania", "nawigacja", "przejdz", "klik", "test"]
        ):
            return (
                "Sterowanie aplikacja - co moge zrobic:\n"
                "1. Przejsc do modulu: Main, Visual, Results, Report, Diagrams albo Theory.\n"
                "2. Podswietlic panel, ktory warto kliknac.\n"
                "3. Uruchomic bezpieczne akcje: sample dashboard, diagram z opisu, szkic raportu, podglad HTML/PDF.\n"
                "4. Przetestowac sciezke: Main -> Visual -> Results -> Report -> Theory.\n"
                "5. Dla ciezkich akcji, jak trening lub samonauka, poprosic o potwierdzenie.\n\n"
                "Polecenia: 'przejdz do Report', 'co powinienem kliknac?', 'przetestuj raport', "
                "'przetestuj diagram', 'przetestuj Main'."
            )
        if any(k in compact for k in ["alice", "samonauka", "self learning", "baza wiedzy", "status"]):
            return (
                "ALICE i samonauka - co moge zrobic:\n"
                "1. Przedstawic siebie i wyjasnic, co wiem o aplikacji.\n"
                "2. Korzystac z bazy wiedzy: README, docs, specy modeli, akcje GUI i alice_brain.json.\n"
                "3. Odpowiadac na pytania o Main, Visual, Results, Report, Diagrams, Theory i modele.\n"
                "4. Pokazywac kategorie komend zamiast zalewac sciana tekstu.\n"
                "5. Wlaczyc/wyjasnic samonauke i raport z uczenia, gdy uzytkownik to potwierdzi.\n\n"
                "Polecenia: 'opowiedz o sobie', 'co wiesz o aplikacji?', 'status samonauki', "
                "'czego sie nauczyla ALICE?', 'wypisz funkcje'."
            )
        return None

    @staticmethod
    def _has_help_intent(compact: str) -> bool:
        phrases = [
            "co mozesz",
            "co umiesz",
            "co potrafisz",
            "jakie komendy",
            "jakie masz komendy",
            "jakie funkcje",
            "jakie masz funkcje",
            "lista",
            "wypisz",
            "pomoc",
            "help",
            "jak mozesz",
            "czym mozesz",
            "co da rade",
            "kategorie",
            "kategoria",
        ]
        return any(phrase in compact for phrase in phrases)

    @staticmethod
    def _process_playbook(question: str) -> str | None:
        if any(
            k in question
            for k in [
                "svm",
                "svr",
                "knn",
                "ridge",
                "histgradient",
                "randomforest",
                "extratrees",
                "gradientboosting",
                "logisticregression",
                "n_estimators",
                "learning_rate",
                "max_depth",
                "estymator",
                "parametry json",
            ]
        ):
            return (
                "Nazwy w kreatorze własnego modelu to klasy sklearn i ich parametry.\n\n"
                "Najważniejsze algorytmy:\n"
                "- RandomForest: wiele drzew decyzyjnych; wynik regresji to średnia, a klasyfikacji głosowanie.\n"
                "- ExtraTrees: podobne do RandomForest, ale mocniej losuje progi podziału, więc często jest szybkie i odporne na szum.\n"
                "- GradientBoosting: buduje kolejne małe modele, które poprawiają błędy poprzednich: F_m(x)=F_{m-1}(x)+η·h_m(x).\n"
                "- HistGradientBoosting: boosting na koszykach/histogramach wartości, dobry dla większych danych.\n"
                "- SVR/SVM: szuka granicy z marginesem; w regresji toleruje błąd epsilon i ma karę C. Wymaga skalowania.\n"
                "- KNN: patrzy na najbliższe podobne rekordy; n_neighbors mówi ilu sąsiadów użyć. Wymaga skalowania.\n"
                "- Ridge: prosta regresja liniowa z karą alpha: min ||y-Xw||² + alpha·||w||².\n"
                "- LogisticRegression: klasyfikacja; liczy P(klasa|X), a wygrywa największe prawdopodobieństwo.\n\n"
                "Co znaczą parametry:\n"
                "- n_estimators: liczba drzew/modeli.\n"
                "- max_depth: maksymalna głębokość drzewa.\n"
                "- min_samples_leaf: minimalna liczba rekordów w liściu, chroni przed przeuczeniem.\n"
                "- learning_rate: tempo poprawiania błędu w boostingu.\n"
                "- C: kara w SVM; większe C mocniej dopasowuje model.\n"
                "- epsilon: tolerowany błąd w SVR.\n"
                "- alpha: siła regularyzacji Ridge.\n"
                "- random_state: powtarzalny wynik.\n"
                "- n_jobs: liczba równoległych wątków, -1 oznacza użyj dostępnych rdzeni.\n\n"
                "Ścieżka typu sklearn.svm.SVR to po prostu pełna nazwa klasy w bibliotece sklearn, którą aplikacja tworzy i trenuje."
            )
        if any(
            k in question
            for k in [
                "wlasny model",
                "własny model",
                "custom model",
                "sklearn",
                "dodac model",
                "dodać model",
            ]
        ):
            return (
                "Własny model sklearn dodajesz w Main przez przycisk '+ Własny model sklearn'.\n\n"
                "Krok po kroku:\n"
                "1. Wybierz gotowy preset, np. RandomForest, ExtraTrees, GradientBoosting, SVR, KNN, Ridge albo LogisticRegression.\n"
                "2. Wybierz zadanie aplikacji: jakość, opóźnienie albo harmonogram. To jest cel y, który model ma przewidywać.\n"
                "3. Zostaw nazwę na ekranie jako 'Mój model ML' albo wpisz własną etykietę.\n"
                "4. Sprawdź estymator sklearn. Regresory są do jakości/opóźnienia, klasyfikatory do harmonogramu.\n"
                "5. Jeśli model to SVR, KNN albo LogisticRegression, użyj skalowania standard/robust. Dla drzew zwykle wystarczy none.\n"
                "6. Zostaw JSON bez zmian, jeśli nie wiesz co ustawić. Parametry trafiają bezpośrednio do sklearn.\n"
                "7. Kliknij 'Zapisz model', zaznacz nowy model na liście i uruchom trening.\n\n"
                "Logika pod spodem: dane produkcji -> cechy X -> brakujące dane medianą -> opcjonalne skalowanie -> estimator.fit(X, y) -> predykcja i metryki."
            )
        if (
            "sto" in question
            and ("machine learning" in question or " ml" in question or "model ml" in question)
        ) or (
            "mt" in question and "mo" in question and ("theory" in question or "animac" in question)
        ):
            return (
                "Tu sa dwa rozne swiaty i nie wolno ich mieszac.\n"
                "- ML uczy zaleznosci z danych: Random Forest usrednia wiele drzew, ExtraTrees losuje progi, boosting poprawia bledy, a regresja logistyczna uczy liniowa granice klas.\n"
                "- STO nie uczy modelu ML. STO uklada kolejke zlecen i liczy opoznienia: Tj = max(0, Cj - dj), a wynik to suma Tj.\n"
                "- MT, MO i MZO to metody/reguly STO, wiec w animacji ML nie powinny byc pokazywane jako sposob dzialania machine learning.\n"
                "Poprawny podglad: w Theory ML pokazuje cechy danych, drzewa/boosting/softmax, a zakladka heurystyk pokazuje MT/MO/MZO i ranking STO."
            )
        if any(
            k in question
            for k in ["proces", "workflow", "krok po kroku", "jak dziala cala aplikacja"]
        ):
            return (
                "Pelny proces pracy w aplikacji:\n"
                "1) Readme: szybki start i co oznaczaja moduly.\n"
                "2) Main: wczytaj dane, wybierz classic ML, TabPFN, STO albo wlasny model.\n"
                "3) Trening/predykcja: uruchom pipeline, sprawdz metryki, zapisz model i wyniki.\n"
                "4) Visual: porownaj wykresy, drzewa decyzji/rozwiazan i dashboardy.\n"
                "5) Diagrams: opisz proces, przeplyw produkcji, BPMN/UML/ERD albo pipeline operacyjny.\n"
                "6) Report: zloz raport jak w Overleaf, dodaj PDF preview, pliki, ML/STO analytics i KPI.\n"
                "7) Results: filtruj tabele, SQL, eksportuj CSV/raport.\n"
                "8) Theory: przejdz przez animacje classic ML, STO i TabPFN, z logika i wzorami.\n"
                "Jesli chcesz, przeprowadze Cie teraz przez wybrany punkt (np. 'krok 3')."
            )
        if any(
            k in question
            for k in ["jak zbudowane", "architektura", "jak to jest zrobione", "struktura projektu"]
        ):
            return (
                "Jak to jest zbudowane:\n"
                "1) Warstwa GUI (src/AOA/gui): strony Readme/Main/Visual/Results/Theory + ALICE.\n"
                "2) Warstwa Core (src/AOA/core): modele ML i STO, serwisy danych, RAG asystenta, generator wykresow.\n"
                "3) Wizualizacje: Matplotlib w aplikacji + D3 HTML do analizy interaktywnej.\n"
                "4) Dane i assety: data/ oraz src/AOA/assets/assistant.\n"
                "5) Przeplyw pracy: dane -> trening/heurystyki -> wizualizacja -> wyniki/SQL -> eksport."
            )
        if any(k in question for k in ["sql", "results", "result lab", "zapytania"]):
            return (
                "Tryb Results/SQL:\n"
                "- wczytaj dane,\n"
                "- przejdz do zakladki SQL,\n"
                "- wpisz zapytanie (SELECT ...),\n"
                "- uruchom i sprawdz osobna tabele wynikow,\n"
                "- wyeksportuj wynik SQL do CSV."
            )
        if any(k in question for k in ["heuryst", "metaheuryst"]) or _has_word(
            question, ("sto", "mopt", "mt", "mo", "mzo")
        ):
            return (
                "Modele STO/heurystyczne:\n"
                "- uruchamiasz je z Main po przygotowaniu danych,\n"
                "- zapisujesz model/konfiguracje,\n"
                "- w Visual mozesz obejrzec SolutionTree i wskazana najlepsza sciezke,\n"
                "- w Results porownujesz wyniki i eksportujesz raport."
            )
        if any(k in question for k in ["llm", "rag", "asystent", "alice"]):
            return (
                "ALICE dziala hybrydowo:\n"
                "- najpierw RAG po README/docs/specach modeli,\n"
                "- opcjonalnie dopytuje endpoint LLM,\n"
                "- zwraca odpowiedz krokowa i moze nawigowac po sekcjach aplikacji."
            )
        if any(k in question for k in ["analytics", "kpi", "notebook", "data analytics"]):
            return (
                "Report Studio to panel do pracy raportowej i analitycznej, a nie tylko opis.\n"
                "- Wczytujesz CSV/TXT/TSV.\n"
                "- Wybierasz workflow: jakosc danych, dashboard, raport, KPI, diagnostyka, market sizing albo notebook.\n"
                "- Report Builder dziala jak prosty Overleaf: po lewej zrodlo, po prawej podglad strony PDF, obok guide komend.\n"
                "- Do raportu mozesz wstawic pliki z Visual, Diagrams, Report i Reports: obrazy, SVG, HTML, CSV albo tekst.\n"
                "- Klikasz Uruchom analize, Otworz HTML, Wykonaj wszystko, Notebook .ipynb, CSV akcji albo eksport PDF.\n"
                "- Wyniki z Report mozna potem odtworzyc wykresem w Visual i opisac diagramem w Diagrams."
            )
        if any(k in question for k in ["diagram z opisu", "smart diagram", "madry diagram", "zrob diagram"]):
            return (
                "W Diagrams mozesz zaczac od opisu slownego.\n"
                "- Kliknij Z opisu.\n"
                "- Wpisz proces strzalkami albo normalnym zdaniem, np. CSV -> walidacja -> model ML -> raport.\n"
                "- Aplikacja dobierze szablon, ksztalty, kolory i etykiety polaczen.\n"
                "- Jesli elementy sa zbyt ciasno, kliknij Auto layout i dopiero potem popraw detale recznie.\n"
                "- Potem poprawiasz diagram recznie: przesuwasz elementy, zmieniasz kolor, dodajesz kontenery i eksportujesz.\n"
                "To jest dobry start, gdy osoba nie wie jeszcze, czy potrzebuje Flowchart, Data Pipeline, Supply Chain czy System Architecture."
            )
        if any(
            k in question
            for k in ["diagram", "diagrams", "drawio", "draw.io", "uml", "erd", "bpmn"]
        ):
            return (
                "Diagrams to interaktywny panel schematow.\n"
                "- Wybierasz szablon: Flowchart, UML, ERD, BPMN, Network, Mind Map, Production Line, Value Stream Map, Supply Chain, Plant Layout, Andon, Energy Flow i inne.\n"
                "- Dodajesz ksztalty albo gotowce: maszyna, magazyn, transport, QC, bufor WIP, sensor, PLC, Andon, energia, KPI, model ML.\n"
                "- Przeciagasz elementy myszka, dwuklik zmienia tekst, prawy klik usuwa blok.\n"
                "- Mozesz duplikowac zaznaczony element, usunac zaznaczony blok i uzyc Auto layout.\n"
                "- Eksportujesz do .drawio, SVG, Mermaid albo HTML.\n"
                "- Eksport HTML ma interaktywny podglad: przewijanie/przesuwanie widoku, chowanie etykiet i reset."
            )
        if any(k in question for k in ["tabpfn", "tabular prior", "nowoczesne"]):
            return (
                "TabPFN w tej aplikacji jest trzecia sciezka obok classic ML i heurystyk STO.\n"
                "- Classic ML trenuje estimator, np. RandomForest, SVM albo XGBoost.\n"
                "- TabPFN traktuje mala lub srednia tabele jako kontekst i korzysta z pretrenowanego priora tabelarycznego.\n"
                "- Przed treningiem aplikacja waliduje X/y: rozmiar tabeli, braki, inf, zgodna liczba rekordow i minimum 2 klasy dla schedule.\n"
                "- W praktyce porownujesz go na tym samym train/test: jakosc, opoznienie albo harmonogram.\n"
                "- Najlepiej uzywac go jako szybki nowoczesny baseline, szczegolnie gdy nie chcesz stroic wielu parametrow.\n"
                "- W Theory ta grupa pokazuje tez inne nowoczesne segmenty: XGBoost, MLP i Stacking.\n"
                "- W raporcie opisuj go jako: y_hat = f_PFN(X_train, y_train, x_new)."
            )
        if any(k in question for k in ["pdf", "overleaf", "includegraphics", "includehtml", "report builder"]):
            return (
                "Report Builder sklada raport podobnie do Overleaf, tylko prosciej.\n"
                "- Po lewej wpisujesz zrodlo: sekcje, wzory, listy i odwolania do plikow.\n"
                "- W srodku widzisz jasny podglad strony A4, czyli symulacje ukladu PDF.\n"
                "- Faktyczny PDF sprawdzisz przyciskiem Podglad PDF albo Eksport PDF.\n"
                "- Pliki z Visual/Diagrams dodawaj przez biblioteke plikow albo komendy \\includegraphics{} i \\includehtml{}.\n"
                "- Obrazy i SVG ida jako grafiki, HTML jako interaktywny iframe w raporcie HTML, CSV jako tabela podgladowa.\n"
                "- Dobry raport ma pipeline: dane -> jakosc -> model/STO -> wykres/diagram -> decyzja -> ryzyka."
            )
        if any(k in question for k in ["decision tree", "solution tree", "drzewo"]):
            return (
                "Roznica jest praktyczna:\n"
                "- ML Decision Tree: pokazuje logike podzialu/decyzji modelu.\n"
                "- SolutionTree: pokazuje drzewo wariantow rozwiazania STO i najlepsza sciezke.\n"
                "Do analizy decyzji modelu wybieraj ML Decision Tree, a do harmonogramowania i wyboru wariantu STO wybieraj SolutionTree."
            )
        if any(k in question for k in ["gantt", "maszyn", "machine"]):
            return (
                "Wykres Gantt pokazuje plan realizacji zadan w czasie.\n"
                "Najlepiej dziala, gdy masz kolumny czasu startu/konca albo czas trwania i termin.\n"
                "Dla wielu maszyn porownuj obciazenie i opoznienia miedzy lane'ami."
            )
        if any(k in question for k in ["dbscan", "anomali"]):
            return (
                "DBSCAN wykrywa skupiska i punkty odstajace bez z gory ustalonej liczby klastrow.\n"
                "W Waszym flow: najpierw normalizacja, potem DBSCAN, a wynik najlepiej czytac razem z PCA."
            )
        if any(k in question for k in ["pca", "lda", "t-sne", "tsne", "kmeans", "gmm"]):
            return (
                "Szybkie porownanie metod:\n"
                "- PCA: redukcja wymiaru i czytelna mapa trendu.\n"
                "- LDA: separacja klas, gdy masz etykiety.\n"
                "- t-SNE: nieliniowa mapa struktur lokalnych.\n"
                "- KMeans: szybkie grupowanie o centroidach.\n"
                "- GMM: miekkie grupowanie probabilistyczne.\n"
                "Najlepiej uruchamiac je parami: LDA vs t-SNE oraz KMeans vs GMM."
            )
        if "krok 3" in question or "trening" in question:
            return (
                "Krok 3 (trening):\n"
                "- Wejdz w Main,\n"
                "- zaznacz modele,\n"
                "- ustaw parametry,\n"
                "- kliknij uruchom,\n"
                "- porownaj RMSE/MAE/R2 i zapisz najlepszy model."
            )
        if "krok 4" in question or "visual" in question:
            return (
                "Krok 4 (Visual):\n"
                "- ustaw X/Y/Z,\n"
                "- wybierz typ wykresu,\n"
                "- dla drzew sprawdz podswietlona najlepsza sciezke,\n"
                "- otworz D3 HTML do analizy interaktywnej."
            )
        if "krok 5" in question or "results" in question or "sql" in question:
            return (
                "Krok 5 (Results):\n"
                "- filtruj kolumny i rekordy,\n"
                "- uzyj trybu SQL do zapytan,\n"
                "- wyeksportuj wynik SQL albo cala tabele do CSV."
            )
        return None

    @staticmethod
    def _theory_playbook(question: str) -> str | None:
        if (
            "sto" in question
            and ("machine learning" in question or " ml" in question or "model ml" in question)
        ) or (
            "mt" in question and "mo" in question and ("theory" in question or "animac" in question)
        ):
            return (
                "Tu sa dwa rozne swiaty i nie wolno ich mieszac.\n"
                "- ML uczy zaleznosci z danych: Random Forest usrednia wiele drzew, ExtraTrees losuje progi, boosting poprawia bledy, a regresja logistyczna uczy liniowa granice klas.\n"
                "- TabPFN to osobny backend tabelaryczny: bierze tabele jako kontekst i porownujemy go z classic ML na tych samych metrykach.\n"
                "- STO nie uczy modelu ML. STO uklada kolejke zlecen i liczy opoznienia: Tj = max(0, Cj - dj), a wynik to suma Tj.\n"
                "- MT, MO i MZO to metody/reguly STO, wiec w animacji ML nie powinny byc pokazywane jako sposob dzialania machine learning.\n"
                "Poprawny podglad: w Theory ML pokazuje cechy danych, drzewa/boosting/softmax, TabPFN pokazuje kontekst tabelaryczny, a zakladka heurystyk pokazuje MT/MO/MZO i ranking STO."
            )
        if "random forest" in question or "quality rf" in question:
            return (
                "Random Forest w AOA to ensemble wielu drzew.\n"
                "1. Dane sa imputowane mediana, ale drzewa nie wymagaja skalowania cech.\n"
                "2. Kazde drzewo dostaje losowa probke danych i wybiera podzialy w wezlach.\n"
                "3. W regresji, np. Quality albo Delay_RF, wynik to srednia predykcji drzew.\n"
                "4. W klasyfikacji, np. Schedule, wynik to glosowanie albo srednia prawdopodobienstw klas.\n"
                "5. OOB i test train/test pomagaja sprawdzic, czy model nie uczy sie tylko na pamiec."
            )
        if "extra" in question and "tree" in question:
            return (
                "ExtraTrees jest podobne do Random Forest, ale mocniej losuje progi podzialu.\n"
                "To daje szybkie, roznorodne drzewa. Model dalej laczy wiele drzew, ale pojedyncze podzialy sa mniej 'optymalne' i bardziej losowe."
            )
        if "boost" in question or "gradient" in question:
            return (
                "Boosting dziala sekwencyjnie, nie jak losowy las.\n"
                "Najpierw powstaje prosta predykcja, potem model liczy blad i dodaje kolejne male drzewa jako poprawki. Wynik koncowy to suma tych poprawek."
            )
        if "logist" in question or "softmax" in question:
            return (
                "Regresja logistyczna w Schedule_LOG jest liniowym klasyfikatorem.\n"
                "Skaluje cechy, uczy wagi klas, liczy wyniki liniowe i przez softmax zamienia je na prawdopodobienstwa strategii."
            )
        return None

    @staticmethod
    def _model_playbook(question: str) -> str | None:
        mh_terms = (
            "mt",
            "mo",
            "mzo",
            "mopt",
            "genetic",
            "slack",
            "neh",
            "local_search",
            "random_restart",
        )
        mentioned_mh_terms = [term for term in mh_terms if _has_word(question, (term,))]
        if "sto" in question and len(mentioned_mh_terms) >= 2:
            return (
                "STO to suma dodatnich opoznien dla calej kolejki zlecen.\n"
                "Dla kazdego zlecenia liczymy czas zakonczenia Cj, termin dj i opoznienie Tj = max(0, Cj - dj). "
                "Wynik metody to suma Tj; im mniejszy wynik, tym lepsza kolejnosc.\n\n"
                "Najwazniejsze metody:\n"
                "- MT / EDD: sortuje po najblizszym terminie.\n"
                "- MO / SPT: sortuje po najkrotszym czasie obrobki.\n"
                "- MZO / LPT: zaczyna od najdluzszych zlecen.\n"
                "- MOPT: sprawdza warianty i szuka najmniejszego STO.\n"
                "- GENETIC: ulepsza populacje kolejek przez selekcje, krzyzowanie i mutacje.\n"
                "- LOCAL_SEARCH: poprawia kolejke lokalnymi zamianami.\n\n"
                "W aplikacji wynik najlepiej czytac w Results i jako SolutionTree w Visual."
            )
        ml_specs = {spec.name.lower(): spec for spec in get_ml_model_specs()}
        mh_specs = {spec.name.lower(): spec for spec in get_mh_model_specs()}
        mentioned_ml = next(
            (spec for name, spec in ml_specs.items() if _has_word(question, (name,))), None
        )
        mentioned_mh = next(
            (spec for name, spec in mh_specs.items() if _has_word(question, (name,))), None
        )

        if mentioned_ml is not None:
            if mentioned_ml.task == "quality":
                behavior = (
                    "To model regresyjny od jakosci produkcji. Patrzy na cechy zlecenia/materialu/czasu "
                    "i przewiduje wartosc jakosci albo wskaznik podobny do jakosci."
                )
            elif mentioned_ml.task == "delay":
                behavior = (
                    "To model regresyjny od opoznien. Uczy sie relacji miedzy czasem produkcji, terminem, "
                    "kosztem i innymi cechami, a potem przewiduje ryzyko opoznienia."
                )
            else:
                behavior = (
                    "To model klasyfikacyjny harmonogramowania. Szuka najbardziej prawdopodobnej strategii "
                    "lub klasy decyzji dla danego zestawu cech."
                )
            return (
                f"Model {mentioned_ml.name} ({mentioned_ml.label})\n"
                f"- Zadanie: {mentioned_ml.task}.\n"
                f"- Jak dziala: {behavior}\n"
                f"- Technicznie: {mentioned_ml.description}\n"
                f"- Na co zwraca uwage: {mentioned_ml.focus}.\n"
                "- Jak czytac wynik: porownaj metryki train/test, sprawdz blad i gap; jesli gap jest duzy, model moze przeuczac dane.\n"
                "- Najlepszy podglad w aplikacji: Main do treningu, Results do metryk, Visual do relacji i raportu HTML."
            )

        if mentioned_mh is not None:
            return (
                f"Metoda {mentioned_mh.name} ({mentioned_mh.label})\n"
                f"- Jak dziala: {mentioned_mh.description}\n"
                f"- Cel: {mentioned_mh.focus}.\n"
                "- To metoda STO/harmonogramowania, czyli uklada kolejnosc zadan tak, aby poprawic wynik procesu.\n"
                "- Najlepszy podglad w aplikacji: SolutionTree w Visual oraz tabela wynikow w Results."
            )

        if any(
            k in question
            for k in ["jak sam algorytm dziala", "jak algorytm dziala", "jak dziala algorytm"]
        ):
            return (
                "Jesli pytasz o algorytm ML w tej aplikacji, logika jest taka:\n"
                "1) Dane sa czyszczone i zamieniane na cechy liczbowe.\n"
                "2) Model uczy sie zaleznosci miedzy cechami a celem, np. jakoscia, opoznieniem albo strategia.\n"
                "3) Random Forest/ExtraTrees lacza wiele drzew i usredniaja wynik, dzieki czemu sa stabilniejsze.\n"
                "4) Gradient Boosting buduje drzewa po kolei, a kazde nastepne poprawia bledy poprzednich.\n"
                "5) Wynik oceniasz po metrykach train/test i po tym, czy blad nie rosnie na danych testowych."
            )
        return None
