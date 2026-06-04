"""Unit tests for the local embedding index utilities."""

from __future__ import annotations

from pathlib import Path

from tools_embeddings import (
    build_embedding_index,
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
        dimensions=64,
        model_name="nomic-embed-text",
    )
    results = semantic_search(
        zettelkasten,
        index_path,
        "risco de credito",
        limit=2,
        dimensions=64,
        model_name="nomic-embed-text",
    )

    assert index_path.exists()
    assert len(index["documents"]) == 2
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
        dimensions=16,
        model_name="nomic-embed-text",
    )

    status = embedding_status(
        index_path,
        model_name="nomic-embed-text",
        dimensions=16,
    )

    assert status.index_exists is True
    assert status.document_count == 1
    assert status.provider == "hashing"
