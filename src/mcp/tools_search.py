from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: int
    excerpt: str
    engine: str = "lexical"


def hybrid_search(
    root: Path,
    query: str,
    *,
    limit: int = 8,
    qmd_command: str | None = "qmd",
) -> list[SearchResult]:
    """Use qmd when available, with deterministic lexical fallback."""
    if qmd_command:
        qmd_results = qmd_search(root, query, limit=limit, qmd_command=qmd_command)
        if qmd_results:
            return qmd_results
    return lexical_search(root, query, limit=limit)


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


def qmd_search(
    root: Path,
    query: str,
    *,
    limit: int = 8,
    qmd_command: str = "qmd",
) -> list[SearchResult]:
    executable = shlex.split(qmd_command)[0]
    if shutil.which(executable) is None:
        return []

    command = [*shlex.split(qmd_command), "search", query, "--limit", str(limit)]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            cwd=root,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if completed.returncode != 0:
        return []
    return _parse_qmd_output(completed.stdout, root=root, limit=limit)


def _excerpt(text: str, terms: list[str], *, radius: int = 180) -> str:
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return text[: radius * 2].strip()
    start = max(min(positions) - radius, 0)
    end = min(min(positions) + radius, len(text))
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _parse_qmd_output(output: str, *, root: Path, limit: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for line_number, raw_line in enumerate(output.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        path_text, _, excerpt = line.partition(":")
        path = Path(path_text.strip())
        if path.is_absolute():
            try:
                relative_path = path.relative_to(root)
            except ValueError:
                relative_path = Path(path.name)
        else:
            relative_path = path
        results.append(
            SearchResult(
                path=str(relative_path).replace("\\", "/"),
                score=max(limit - line_number + 1, 1),
                excerpt=excerpt.strip() or line,
                engine="qmd",
            )
        )
        if len(results) >= limit:
            break
    return results
