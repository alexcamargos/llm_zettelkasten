"""Unit tests for the local embedding index utilities."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from tools_embeddings import (
    build_embedding_index,
    embed_text,
    embedding_status,
    hashing_embedding,
    semantic_search,
)


def test_hashing_embedding_is_deterministic_and_normalized() -> None:
    """Test that hashing embeddings are stable and normalized for non-empty text."""
    first = hashing_embedding("credito cooperativo risco", dimensions=32)
    second = hashing_embedding("credito cooperativo risco", dimensions=32)

    assert first == second
    assert len(first) == 32
    assert round(sum(value * value for value in first), 6) == 1.0


def test_build_embedding_index_and_semantic_search_rank_relevant_doc(tmp_path: Path) -> None:
    """Test persisted embedding index creation and semantic ranking."""
    zettelkasten = tmp_path / "zettelkasten"
    zettelkasten.mkdir()
    (zettelkasten / "credito.md").write_text(
        "credito cooperativo risco insolvencia capital",
        encoding="utf-8",
    )
    (zettelkasten / "gan.md").write_text(
        "redes generativas adversariais imagem sintetica",
        encoding="utf-8",
    )
    index_path = tmp_path / ".state" / "embeddings_index.json"

    index = build_embedding_index(
        zettelkasten,
        index_path,
        provider="hashing",
        dimensions=64,
        model_name="nomic-embed-text",
        endpoint=None,
    )
    results = semantic_search(
        zettelkasten,
        index_path,
        "risco de credito",
        limit=2,
        provider="hashing",
        dimensions=64,
        model_name="nomic-embed-text",
        endpoint=None,
    )

    assert index_path.exists()
    assert len(index["documents"]) == 2
    assert index["provider"] == "hashing"
    assert results[0].path == "credito.md"
    assert results[0].engine == "hash-embedding"


def test_embedding_status_reports_existing_index(tmp_path: Path) -> None:
    """Test embedding_status counts indexed documents when cache exists."""
    zettelkasten = tmp_path / "zettelkasten"
    zettelkasten.mkdir()
    (zettelkasten / "note.md").write_text("indicador pearls", encoding="utf-8")
    index_path = tmp_path / ".state" / "embeddings_index.json"
    build_embedding_index(
        zettelkasten,
        index_path,
        provider="hashing",
        dimensions=16,
        model_name="nomic-embed-text",
        endpoint=None,
    )

    status = embedding_status(
        index_path,
        provider="hashing",
        model_name="nomic-embed-text",
        endpoint=None,
        dimensions=16,
    )

    assert status.index_exists is True
    assert status.document_count == 1
    assert status.provider == "hashing"
    assert status.active_provider == "hashing"


def test_ollama_provider_falls_back_to_hashing_when_endpoint_fails(tmp_path: Path) -> None:
    """Test offline fallback if a configured Ollama endpoint is unavailable."""
    zettelkasten = tmp_path / "zettelkasten"
    zettelkasten.mkdir()
    (zettelkasten / "note.md").write_text("credito cooperativo", encoding="utf-8")
    index_path = tmp_path / ".state" / "embeddings_index.json"

    index = build_embedding_index(
        zettelkasten,
        index_path,
        provider="ollama",
        dimensions=16,
        model_name="nomic-embed-text",
        endpoint="http://127.0.0.1:1/api/embeddings",
    )

    assert index["configured_provider"] == "ollama"
    assert index["provider"] == "hashing"
    assert index["fallback_provider"] == "hashing"


def test_embed_text_uses_hashing_provider() -> None:
    """Test public embed_text dispatch for the hashing provider."""
    vector = embed_text(
        "pearls capital",
        provider="hashing",
        model_name="nomic-embed-text",
        endpoint=None,
        dimensions=24,
    )

    assert len(vector) == 24
    assert any(vector)


def test_embed_text_uses_ollama_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test public embed_text dispatch for a successful Ollama-compatible endpoint."""

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"embedding": [3, 4]}'

    captured = SimpleNamespace(request=None)

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        captured.request = request
        assert timeout == 20
        return FakeResponse()

    monkeypatch.setattr("tools_embeddings.urllib.request.urlopen", fake_urlopen)

    vector = embed_text(
        "texto",
        provider="ollama",
        model_name="nomic-embed-text",
        endpoint="http://localhost:11434/api/embeddings",
        dimensions=24,
    )

    assert captured.request is not None
    assert vector == [0.6, 0.8]


def test_semantic_search_labels_ollama_index_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test semantic search labels results with the active index provider."""
    zettelkasten = tmp_path / "zettelkasten"
    zettelkasten.mkdir()
    (zettelkasten / "note.md").write_text("credito cooperativo", encoding="utf-8")
    index_path = tmp_path / ".state" / "embeddings_index.json"

    monkeypatch.setattr(
        "tools_embeddings.ollama_embedding",
        lambda text, **_kwargs: [1.0, 0.0] if "credito" in text else [0.0, 1.0],
    )

    build_embedding_index(
        zettelkasten,
        index_path,
        provider="ollama",
        dimensions=2,
        model_name="nomic-embed-text",
        endpoint="http://localhost:11434/api/embeddings",
    )
    results = semantic_search(
        zettelkasten,
        index_path,
        "credito",
        limit=1,
        provider="ollama",
        dimensions=2,
        model_name="nomic-embed-text",
        endpoint="http://localhost:11434/api/embeddings",
    )

    assert results[0].engine == "ollama-embedding"
