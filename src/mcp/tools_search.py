from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: int
    excerpt: str


def lexical_search(root: Path, query: str, *, limit: int = 8) -> list[SearchResult]:
    terms = [term.lower() for term in re.findall(r"\w+", query) if len(term) >= 2]
    if not terms:
        return []

    results: list[SearchResult] = []
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        score = sum(lowered.count(term) for term in terms)
        if score <= 0:
            continue
        results.append(
            SearchResult(
                path=str(path.relative_to(root)).replace("\\", "/"),
                score=score,
                excerpt=_excerpt(text, terms),
            )
        )
    return sorted(results, key=lambda result: (-result.score, result.path))[:limit]


def _excerpt(text: str, terms: list[str], *, radius: int = 180) -> str:
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return text[: radius * 2].strip()
    start = max(min(positions) - radius, 0)
    end = min(min(positions) + radius, len(text))
    return re.sub(r"\s+", " ", text[start:end]).strip()
