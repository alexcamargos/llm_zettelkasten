from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools_pdf import (
    list_pageindex_manifests,
    persist_pageindex_cache,
    read_pageindex_cache,
    read_pageindex_page,
    resolve_pdf_cache,
    sha256_file,
)


def test_sha256_file(tmp_path: Path) -> None:
    file_path = tmp_path / "paper.pdf"
    file_path.write_bytes(b"abc")

    assert sha256_file(file_path) == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_list_and_read_pageindex_cache(tmp_path: Path) -> None:
    document_id = "a" * 64
    document_root = tmp_path / document_id
    document_root.mkdir()
    (document_root / "manifest.json").write_text(
        json.dumps(
            {
                "document_id": document_id,
                "source_path": "raw/papers/teste.pdf",
                "source_filename": "teste.pdf",
                "page_count": 2,
            }
        ),
        encoding="utf-8",
    )
    (document_root / "tree.json").write_text(
        json.dumps(
            {
                "children": [
                    {"page": 1, "title": "Modelo PEARLS", "text": "credito e liquidez"},
                    {"page": 2, "title": "Outro tema", "text": "governanca"},
                ]
            }
        ),
        encoding="utf-8",
    )

    manifests = list_pageindex_manifests(tmp_path)
    cache = read_pageindex_cache(tmp_path, document_id, query="credito", limit=1)

    assert manifests[0]["source_path"] == "raw/papers/teste.pdf"
    assert cache["found"] is True
    assert cache["matches"][0]["page"] == 1
    assert "credito" in cache["matches"][0]["excerpt"]


def test_resolve_pdf_cache_by_source_path(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    raw_papers = vault / "raw" / "papers"
    pageindex_root = vault / ".pageindex"
    raw_papers.mkdir(parents=True)
    pageindex_root.mkdir()
    pdf_path = raw_papers / "teste.pdf"
    pdf_path.write_bytes(b"abc")
    document_id = sha256_file(pdf_path)
    document_root = pageindex_root / document_id
    document_root.mkdir()
    (document_root / "manifest.json").write_text(
        json.dumps({"source_path": "raw/papers/teste.pdf"}),
        encoding="utf-8",
    )

    resolved = resolve_pdf_cache(vault, raw_papers, pageindex_root, "raw/papers/teste.pdf")

    assert resolved["document_id"] == document_id
    assert resolved["cache_found"] is True
    assert resolved["manifest"]["source_path"] == "raw/papers/teste.pdf"


def test_read_pageindex_page_returns_page_text(tmp_path: Path) -> None:
    document_id = "b" * 64
    document_root = tmp_path / document_id
    document_root.mkdir()
    (document_root / "manifest.json").write_text(
        json.dumps({"document_id": document_id, "source_path": "raw/papers/teste.pdf"}),
        encoding="utf-8",
    )
    (document_root / "tree.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {"page": 1, "text": "conteudo da primeira pagina"},
                    {"page": 2, "heading": "Segunda pagina", "content": "conteudo relevante"},
                ]
            }
        ),
        encoding="utf-8",
    )

    page = read_pageindex_page(tmp_path, document_id, 2)

    assert page["found"] is True
    assert page["page"] == 2
    assert page["node_count"] == 1
    assert "Segunda pagina" in page["text"]
    assert "conteudo relevante" in page["text"]


def test_persist_pageindex_cache_writes_tree_and_manifest(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    raw_papers = vault / "raw" / "papers"
    pageindex_root = vault / ".pageindex"
    raw_papers.mkdir(parents=True)
    pdf_path = raw_papers / "teste.pdf"
    pdf_path.write_bytes(b"abc")

    persisted = persist_pageindex_cache(
        vault,
        raw_papers,
        pageindex_root,
        "raw/papers/teste.pdf",
        {"nodes": [{"page": 3, "text": "conteudo indexado"}]},
    )

    tree_path = vault / persisted["tree_path"]
    manifest_path = vault / persisted["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert tree_path.exists()
    assert manifest_path.exists()
    assert manifest["document_id"] == sha256_file(pdf_path)
    assert manifest["source_path"] == "raw/papers/teste.pdf"
    assert manifest["byte_size"] == 3
    assert manifest["page_count_estimate"] == 3


def test_persist_pageindex_cache_rejects_invalid_tree_json(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    raw_papers = vault / "raw" / "papers"
    pageindex_root = vault / ".pageindex"
    raw_papers.mkdir(parents=True)
    (raw_papers / "teste.pdf").write_bytes(b"abc")

    with pytest.raises(ValueError, match="JSON valido"):
        persist_pageindex_cache(
            vault,
            raw_papers,
            pageindex_root,
            "raw/papers/teste.pdf",
            "{invalid",
        )


def test_read_pageindex_cache_rejects_invalid_document_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="document_id"):
        read_pageindex_cache(tmp_path, "../invalid")
