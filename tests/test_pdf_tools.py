from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools_pdf import list_pageindex_manifests, read_pageindex_cache, sha256_file


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


def test_read_pageindex_cache_rejects_invalid_document_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="document_id"):
        read_pageindex_cache(tmp_path, "../invalid")
