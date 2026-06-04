"""Local embedding index utilities for semantic retrieval.

The current implementation uses deterministic hashing embeddings as an offline
fallback. It keeps the MCP retrieval layer functional without requiring a local
model runtime; a model-backed provider can replace `hashing_embedding` later
without changing the persisted index contract.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
DEFAULT_PROVIDER = "hashing"
FALLBACK_PROVIDER = "hashing"
MIN_TOKEN_LENGTH = 2
DEFAULT_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class EmbeddingSearchResult:
    """Represents a semantic search result from the local embedding index."""

    path: str
    score: float
    excerpt: str
    engine: str = "hash-embedding"


@dataclass(frozen=True)
class EmbeddingStatus:
    """Operational status for the local embedding index."""

    provider: str
    active_provider: str
    model_name: str
    endpoint: str | None
    index_path: str
    index_exists: bool
    document_count: int
    dimensions: int
    fallback_provider: str | None


def embedding_status(
    index_path: Path,
    *,
    provider: str,
    model_name: str,
    endpoint: str | None,
    dimensions: int,
) -> EmbeddingStatus:
    """Return availability and size information for the local embedding index."""
    index = _load_index(index_path)
    index_provider = str(index.get("provider", provider)) if index else provider
    fallback_provider = index.get("fallback_provider") if index else None
    return EmbeddingStatus(
        provider=provider,
        active_provider=index_provider,
        model_name=model_name,
        endpoint=endpoint,
        index_path=str(index_path),
        index_exists=index_path.exists(),
        document_count=len(index.get("documents", [])) if index else 0,
        dimensions=int(index.get("dimensions", dimensions)) if index else dimensions,
        fallback_provider=str(fallback_provider) if fallback_provider else None,
    )


def build_embedding_index(
    root: Path,
    index_path: Path,
    *,
    provider: str,
    dimensions: int,
    model_name: str,
    endpoint: str | None,
) -> dict[str, Any]:
    """Build and persist a local embedding index for Markdown files under root."""
    embedder = _resolve_embedder(
        provider=provider,
        model_name=model_name,
        endpoint=endpoint,
        dimensions=dimensions,
    )
    documents: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        embedding = embedder.embed(text)
        if not any(embedding):
            continue
        documents.append(
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "embedding": embedding,
                "text_length": len(text),
            }
        )

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provider": embedder.active_provider,
        "configured_provider": provider,
        "fallback_provider": embedder.fallback_provider,
        "model_name": model_name,
        "dimensions": len(documents[0]["embedding"]) if documents else dimensions,
        "endpoint": endpoint if provider == "ollama" else None,
        "indexed_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "documents": documents,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def semantic_search(
    root: Path,
    index_path: Path,
    query: str,
    *,
    limit: int,
    provider: str,
    dimensions: int,
    model_name: str,
    endpoint: str | None,
    rebuild_if_missing: bool = True,
) -> list[EmbeddingSearchResult]:
    """Search the local embedding index using cosine similarity."""
    index = _load_index(index_path)
    if index is None and rebuild_if_missing:
        index = build_embedding_index(
            root,
            index_path,
            provider=provider,
            dimensions=dimensions,
            model_name=model_name,
            endpoint=endpoint,
        )
    if not index:
        return []

    index_dimensions = int(index.get("dimensions", dimensions))
    active_provider = str(index.get("provider", provider))
    query_embedding = embed_text(
        query,
        provider=active_provider,
        model_name=model_name,
        endpoint=endpoint,
        dimensions=index_dimensions,
    )
    if not any(query_embedding):
        return []

    results: list[EmbeddingSearchResult] = []
    for document in index.get("documents", []):
        path_text = document.get("path")
        embedding = document.get("embedding")
        if not isinstance(path_text, str) or not isinstance(embedding, list):
            continue
        score = cosine_similarity(query_embedding, embedding)
        if score <= 0:
            continue
        markdown_path = (root / path_text).resolve()
        excerpt = ""
        if markdown_path.exists() and root.resolve() in markdown_path.parents:
            excerpt = _excerpt(markdown_path.read_text(encoding="utf-8", errors="ignore"), query)
        results.append(
            EmbeddingSearchResult(
                path=path_text.replace("\\", "/"),
                score=round(score, 6),
                excerpt=excerpt,
                engine=_engine_name(active_provider),
            )
        )

    return sorted(results, key=lambda result: (-result.score, result.path))[:limit]


def hashing_embedding(text: str, *, dimensions: int) -> list[float]:
    """Generate a normalized signed hashing vector for text."""
    if dimensions <= 0:
        raise ValueError("dimensions deve ser maior que zero.")

    vector = [0.0] * dimensions
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def ollama_embedding(
    text: str,
    *,
    endpoint: str,
    model_name: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[float]:
    """Request an embedding vector from a local Ollama-compatible endpoint."""
    payload = json.dumps({"model": model_name, "prompt": text}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError("Nao foi possivel consultar o endpoint local de embeddings.") from exc

    body = json.loads(raw_body)
    embedding = body.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("Resposta de embeddings sem vetor valido.")
    return [float(value) for value in embedding]


def embed_text(
    text: str,
    *,
    provider: str,
    model_name: str,
    endpoint: str | None,
    dimensions: int,
) -> list[float]:
    """Embed text using the configured provider."""
    if provider == "ollama":
        if not endpoint:
            raise RuntimeError("EMBEDDING_ENDPOINT nao configurado para provider ollama.")
        return _normalize(ollama_embedding(text, endpoint=endpoint, model_name=model_name))
    return hashing_embedding(text, dimensions=dimensions)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity between two normalized vectors."""
    if len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


class _Embedder:
    def __init__(
        self,
        *,
        active_provider: str,
        fallback_provider: str | None,
        model_name: str,
        endpoint: str | None,
        dimensions: int,
    ) -> None:
        self.active_provider = active_provider
        self.fallback_provider = fallback_provider
        self.model_name = model_name
        self.endpoint = endpoint
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        return embed_text(
            text,
            provider=self.active_provider,
            model_name=self.model_name,
            endpoint=self.endpoint,
            dimensions=self.dimensions,
        )


def _resolve_embedder(
    *,
    provider: str,
    model_name: str,
    endpoint: str | None,
    dimensions: int,
) -> _Embedder:
    if provider != "ollama":
        return _Embedder(
            active_provider=DEFAULT_PROVIDER,
            fallback_provider=None,
            model_name=model_name,
            endpoint=endpoint,
            dimensions=dimensions,
        )

    try:
        embed_text(
            "healthcheck",
            provider="ollama",
            model_name=model_name,
            endpoint=endpoint,
            dimensions=dimensions,
        )
    except RuntimeError:
        return _Embedder(
            active_provider=FALLBACK_PROVIDER,
            fallback_provider=FALLBACK_PROVIDER,
            model_name=model_name,
            endpoint=endpoint,
            dimensions=dimensions,
        )
    return _Embedder(
        active_provider="ollama",
        fallback_provider=None,
        model_name=model_name,
        endpoint=endpoint,
        dimensions=dimensions,
    )


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def _engine_name(provider: str) -> str:
    if provider == "ollama":
        return "ollama-embedding"
    return "hash-embedding"


def _load_index(index_path: Path) -> dict[str, Any] | None:
    if not index_path.exists():
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _excerpt(text: str, query: str, *, radius: int = 180) -> str:
    terms = _tokenize(query)
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return re.sub(r"\s+", " ", text[: radius * 2]).strip()
    start = max(min(positions) - radius, 0)
    end = min(min(positions) + radius, len(text))
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"\w+", text)
        if len(token) >= MIN_TOKEN_LENGTH
    ]
