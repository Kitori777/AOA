from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from AOA.config import DATA_DIR, DOCS_DIR, MODELS_DIR

ALLOWED_SUFFIXES = {
    ".csv",
    ".tsv",
    ".txt",
    ".html",
    ".htm",
    ".json",
    ".pkl",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".md",
    ".tex",
    ".pdf",
    ".ipynb",
}

MANAGED_ROOTS: dict[str, Path] = {
    "data": DATA_DIR,
    "models": MODELS_DIR,
    "docs": DOCS_DIR,
}


@dataclass(frozen=True)
class ManagedFile:
    category: str
    path: Path
    suffix: str
    size_bytes: int
    modified: float

    @property
    def label(self) -> str:
        size_kb = max(1, round(self.size_bytes / 1024))
        return f"{self.category} | {self.path.name} | {size_kb} KB"


def _safe_resolve(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    roots = [root.resolve() for root in MANAGED_ROOTS.values()]
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise ValueError("Plik jest poza bezpiecznymi katalogami AOA.")
    return resolved


def list_managed_files(max_files: int = 300) -> list[ManagedFile]:
    files: list[ManagedFile] = []
    for category, root in MANAGED_ROOTS.items():
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            files.append(
                ManagedFile(
                    category=category,
                    path=path,
                    suffix=path.suffix.lower(),
                    size_bytes=stat.st_size,
                    modified=stat.st_mtime,
                )
            )
    files.sort(key=lambda item: item.modified, reverse=True)
    return files[:max_files]


def preview_managed_file(path: str | Path, max_chars: int = 6000) -> str:
    resolved = _safe_resolve(path)
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError("Nie znaleziono pliku do podgladu.")

    suffix = resolved.suffix.lower()
    header = (
        f"Plik: {resolved.name}\n"
        f"Sciezka: {resolved}\n"
        f"Rozmiar: {resolved.stat().st_size} bajtow\n"
        f"Typ: {suffix or 'brak'}\n\n"
    )

    if suffix in {".csv", ".tsv", ".txt"}:
        sep = "\t" if suffix == ".tsv" else None
        try:
            df = pd.read_csv(resolved, sep=sep, engine="python", nrows=20)
            return header + "Podglad tabeli (pierwsze 20 wierszy):\n" + df.to_string(index=False)
        except Exception:
            return header + resolved.read_text(encoding="utf-8", errors="ignore")[:max_chars]

    if suffix in {".html", ".htm"}:
        raw = resolved.read_text(encoding="utf-8", errors="ignore")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.I | re.S)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else resolved.name
        plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.I | re.S)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        return header + f"Tytul HTML: {title}\n\nTekstowy podglad:\n{plain[:max_chars]}"

    if suffix in {".json", ".md", ".tex", ".ipynb"}:
        return header + resolved.read_text(encoding="utf-8", errors="ignore")[:max_chars]

    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".pkl"}:
        return (
            header
            + "To jest plik binarny albo wizualny. Uzyj przycisku Otworz, zeby zobaczyc go w domyslnej aplikacji.\n"
            + "Usuwaj dopiero po sprawdzeniu, czy nie jest potrzebny w raporcie."
        )

    return header + "Brak specjalnego podgladu dla tego typu pliku."


def delete_managed_file(path: str | Path) -> Path:
    resolved = _safe_resolve(path)
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError("Nie znaleziono pliku do usuniecia.")
    resolved.unlink()
    return resolved
