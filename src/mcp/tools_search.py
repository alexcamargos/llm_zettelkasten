"""Search utilities for finding relevant documents inside the Obsidian Zettelkasten.

Provides hybrid search functions merging deterministic lexical word-count matching
with semantic index querying using the external `qmd` tool.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SearchResult:
    """Represents a search hit containing file path, ranking score and excerpt text.

    Attributes:
        path: Relative forward-slash path to the matched markdown file.
        score: Relevance score integer (higher is more relevant).
        excerpt: Snippet of matching text around the keywords.
        engine: The search engine used (e.g., 'lexical' or 'qmd').
    """

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
    """Execute hybrid search using qmd when available, with a lexical fallback.

    Args:
        root: Base Path directory of the Zettelkasten vault.
        query: Space-separated search terms to query.
        limit: Max search hits to return. Defaults to 8.
        qmd_command: Path/name of the qmd executable. Defaults to "qmd".

    Returns:
        list[SearchResult]: Ranked list of SearchResult matches.
    """
    if qmd_command:
        qmd_results = qmd_search(root, query, limit=limit, qmd_command=qmd_command)
        if qmd_results:
            return qmd_results
    return lexical_search(root, query, limit=limit)


def lexical_search(root: Path, query: str, *, limit: int = 8) -> list[SearchResult]:
    """Scan files using regex counting to rank documents by term match density.

    Args:
        root: Base Path directory of the Zettelkasten vault.
        query: Search query text.
        limit: Maximum results to return. Defaults to 8.

    Returns:
        list[SearchResult]: Ranked list of SearchResult matches.
    """
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
    """Invoke the external `qmd` CLI tool for semantic vector-based search.

    Args:
        root: Base Path directory of the Zettelkasten vault.
        query: Search query text.
        limit: Maximum results to return. Defaults to 8.
        qmd_command: Command prefix to execute qmd. Defaults to "qmd".

    Returns:
        list[SearchResult]: Ranked list of SearchResult matches or empty list on error.
    """
    executable = shlex.split(qmd_command)[0]
    if shutil.which(executable) is None:
        return []

    command = [
        *shlex.split(qmd_command),
        "search",
        query,
        "--limit",
        str(limit),
    ]
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
    """Extract snippet context around the first matched search term.

    Args:
        text: Target text to slice.
        terms: List of matching search terms.
        radius: Number of characters to capture before and after the term index.
            Defaults to 180.

    Returns:
        str: Cleaned text snippet containing the match context.
    """
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return text[: radius * 2].strip()
    start = max(min(positions) - radius, 0)
    end = min(min(positions) + radius, len(text))
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _parse_qmd_output(output: str, *, root: Path, limit: int) -> list[SearchResult]:
    """Parse standard stdout lines printed by qmd CLI search into SearchResults.

    Args:
        output: Raw stdout text from qmd executable process.
        root: Zettelkasten root directory Path.
        limit: Maximum results to parse.

    Returns:
        list[SearchResult]: List of parsed SearchResult objects.
    """
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
