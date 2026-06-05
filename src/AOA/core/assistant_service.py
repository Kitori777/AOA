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
                "ResultsPage za filtrowanie tabel, SQL i eksport CSV. AnalyticsPage za raporty, KPI i notebook. "
                "Diagrams Studio za interaktywne schematy, UML, ERD, BPMN i eksport .drawio/SVG/Mermaid/HTML. "
                "TheoryPage za przewodnik krokowy. "
                "AssistantService laczy RAG (README/docs/specy modeli) z endpointem LLM."
            ),
        ),
        (
            "workflow",
            (
                "Workflow aplikacji: Readme -> Main (dane i modele) -> Visual (wykresy) -> "
                "Results (filtrowanie i eksport) -> Theory (wyjasnienie modeli)."
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
                "Moge za to pomoc praktycznie: opisac Main, Visual, Results, Analytics, Diagrams, Theory albo ALICE."
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
        if any(
            k in question
            for k in ["theory", "teoria", "animac", "random forest", "boost", "extra", "softmax"]
        ) or ("sto" in question and ("machine learning" in question or " ml" in question)):
            next_steps = [
                "Przejdz do Theory i wybierz najpierw grupe ML.",
                "Porownaj animacje Random Forest, ExtraTrees, Boosting i Logistic.",
                "Potem przelacz na Heurystyki, zeby osobno zobaczyc MT, MO, MZO i STO.",
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
                "Przejdz do Analytics.",
                "Wczytaj dane, wybierz workflow i kliknij Uruchom analize.",
                "Uzyj Otworz HTML albo Wykonaj wszystko, jesli chcesz pelny pakiet.",
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
                "Jestem ALICE, czyli przewodniczka po aplikacji Production Optimization.\n"
                "Moim zadaniem nie jest tylko odpowiadac jednym zdaniem, ale prowadzic uzytkownika krok po kroku: "
                "co kliknac, co oznacza wynik i gdzie sprawdzic szczegoly.\n\n"
                "Znam glowne miejsca aplikacji:\n"
                "- Main: wczytanie danych, wybor modeli, trening i zapis wynikow.\n"
                "- Visual: wykresy, dashboardy, ML Decision Tree, SolutionTree i eksport HTML.\n"
                "- Results: tabela wynikow, filtrowanie, SQL, eksport CSV.\n"
                "- Analytics: raporty, KPI, diagnostyka danych, notebook i workflow analityczne.\n"
                "- Diagrams: schematy procesow, UML, ERD, BPMN, edycja i eksport.\n"
                "- Theory: animacje, ktore tlumacza osobno ML oraz heurystyki/STO.\n\n"
                "Najlepiej pytaj mnie normalnie, np. 'co zrobic w Main?', 'czemu drzewo jest zolte?', "
                "'jak czytac raport?' albo 'przeprowadz mnie przez workflow'."
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
                "- jak uruchomic workflow w Analytics,\n"
                "- czym rozni sie ML od STO,\n"
                "- jak zrobic raport albo diagram.\n"
                "Jesli chcesz szybki start: wczytaj dane, wejdz w Analytics albo Visual, a ja wytlumacze wynik krok po kroku."
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
    def _process_playbook(question: str) -> str | None:
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
                "2) Main: wybierz modele ML/STO i przygotuj lub wczytaj dane.\n"
                "3) Trening: uruchom modele, sprawdz metryki i zapisz najlepszy wariant.\n"
                "4) Visual: porownaj wykresy, drzewa decyzji/rozwiazan i dashboardy.\n"
                "5) Analytics: generuj raporty, KPI, HTML, notebook i akcje.\n"
                "6) Diagrams: buduj interaktywne schematy i eksportuj .drawio/SVG/Mermaid/HTML.\n"
                "7) Results: filtruj tabele, SQL, eksportuj CSV/raport.\n"
                "8) Theory: przejdz przez instrukcje krokowe i autopokaz.\n"
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
                "Analytics to panel do pracy analitycznej, a nie tylko opis.\n"
                "- Wczytujesz CSV/TXT/TSV.\n"
                "- Wybierasz workflow: jakosc danych, dashboard, raport, KPI, diagnostyka, market sizing albo notebook.\n"
                "- Klikasz Uruchom analize, Otworz HTML, Wykonaj wszystko, Notebook .ipynb albo CSV akcji.\n"
                "- Wyniki z Analytics mozna potem odtworzyc wykresem w Visual."
            )
        if any(
            k in question
            for k in ["diagram", "diagrams", "drawio", "draw.io", "uml", "erd", "bpmn"]
        ):
            return (
                "Diagrams to interaktywny panel schematow.\n"
                "- Wybierasz szablon: Flowchart, UML, ERD, BPMN, Network, Mind Map, Org Chart i inne.\n"
                "- Dodajesz ksztalty i polaczenia.\n"
                "- Przeciagasz elementy myszka, dwuklik zmienia tekst, prawy klik usuwa blok.\n"
                "- Mozesz duplikowac zaznaczony element, usunac zaznaczony blok i uzyc Auto layout.\n"
                "- Eksportujesz do .drawio, SVG, Mermaid albo HTML.\n"
                "- Eksport HTML ma interaktywny podglad: przewijanie/przesuwanie widoku, chowanie etykiet i reset."
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
                "- STO nie uczy modelu ML. STO uklada kolejke zlecen i liczy opoznienia: Tj = max(0, Cj - dj), a wynik to suma Tj.\n"
                "- MT, MO i MZO to metody/reguly STO, wiec w animacji ML nie powinny byc pokazywane jako sposob dzialania machine learning.\n"
                "Poprawny podglad: w Theory ML pokazuje cechy danych, drzewa/boosting/softmax, a zakladka heurystyk pokazuje MT/MO/MZO i ranking STO."
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
