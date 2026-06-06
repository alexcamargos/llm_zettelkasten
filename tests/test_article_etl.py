"""Unit tests for the web article ETL pipeline.

This module tests web article downloading, content extraction, slugification,
and saving to markdown format with correct metadata and YAML front matter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ingestion.article_etl import fetch_and_clean_article, save_raw_article, slugify


class MockMetaData:
    """Mock class to simulate trafilatura's MetaData object.

    Attributes:
        title: Title of the article.
        author: Author of the article.
        date: Publication date of the article.
    """

    def __init__(self, title: str, author: str, date: str) -> None:
        """Initialize MockMetaData.

        Args:
            title: Title of the article.
            author: Author of the article.
            date: Publication date of the article.
        """
        self.title = title
        self.author = author
        self.date = date


def test_slugify() -> None:
    """Tests that slugify converts arbitrary text to filesystem-safe slugs.

    Returns:
        None
    """
    assert slugify("Meu Artigo Especial! 123") == "meu-artigo-especial-123"
    assert slugify("Python -- Ingestion ETL") == "python-ingestion-etl"
    assert slugify("") == "artigo"


def test_fetch_and_clean_article_success(mocker: Any) -> None:
    """Tests successful retrieval and extraction of article content.

    Args:
        mocker: The pytest-mock fixture.

    Returns:
        None
    """
    mocker.patch("trafilatura.fetch_url", return_value="<html>HTML de Teste</html>")
    mocker.patch(
        "trafilatura.extract_metadata",
        return_value=MockMetaData("Título de Teste", "Autor de Teste", "2026-06-06"),
    )
    mocker.patch("trafilatura.extract", return_value="Corpo de texto do artigo.")

    result = fetch_and_clean_article("https://example.com/artigo")

    assert result is not None
    assert result["title"] == "Título de Teste"
    assert result["author"] == "Autor de Teste"
    assert result["date"] == "2026-06-06"
    assert result["url"] == "https://example.com/artigo"
    assert result["content"] == "Corpo de texto do artigo."


def test_fetch_and_clean_article_fetch_failure(mocker: Any) -> None:
    """Tests fetch_and_clean_article returns None when download fails.

    Args:
        mocker: The pytest-mock fixture.

    Returns:
        None
    """
    mocker.patch("trafilatura.fetch_url", return_value=None)

    result = fetch_and_clean_article("https://example.com/artigo")

    assert result is None


def test_fetch_and_clean_article_extraction_failure(mocker: Any) -> None:
    """Tests fetch_and_clean_article returns None when parsing/extracting fails.

    Args:
        mocker: The pytest-mock fixture.

    Returns:
        None
    """
    mocker.patch("trafilatura.fetch_url", return_value="<html>HTML</html>")
    mocker.patch("trafilatura.extract", return_value=None)

    result = fetch_and_clean_article("https://example.com/artigo")

    assert result is None


def test_fetch_and_clean_article_empty_url_raises_error() -> None:
    """Tests that an empty URL raises ValueError.

    Returns:
        None

    Raises:
        ValueError: When the URL is empty.
    """
    with pytest.raises(ValueError, match="A URL do artigo não pode ser vazia."):
        fetch_and_clean_article("   ")


def test_save_raw_article_success(mocker: Any, tmp_path: Path) -> None:
    """Tests that save_raw_article correctly formats and writes content to disk.

    Args:
        mocker: The pytest-mock fixture.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    mocker.patch(
        "ingestion.article_etl.fetch_and_clean_article",
        return_value={
            "title": "Título Especial",
            "author": "Autor Anônimo",
            "date": "2026-06-06",
            "url": "https://example.com/artigo",
            "content": "Conteúdo limpo do artigo.",
        },
    )

    output = save_raw_article("https://example.com/artigo", tmp_path)

    assert output is not None
    assert output.name == "web-titulo-especial.md"
    assert output.exists()

    content = output.read_text(encoding="utf-8")
    assert 'title: "Título Especial"' in content
    assert 'author: "Autor Anônimo"' in content
    assert 'published_at: "2026-06-06"' in content
    assert 'url: "https://example.com/artigo"' in content
    assert "source_kind: web_article" in content
    assert "Conteúdo limpo do artigo." in content


def test_save_raw_article_custom_filename(mocker: Any, tmp_path: Path) -> None:
    """Tests save_raw_article with custom filename.

    Args:
        mocker: The pytest-mock fixture.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    mocker.patch(
        "ingestion.article_etl.fetch_and_clean_article",
        return_value={
            "title": "Título",
            "author": "Autor",
            "date": "2026",
            "url": "https://example.com/artigo",
            "content": "Conteúdo",
        },
    )

    output = save_raw_article("https://example.com/artigo", tmp_path, filename="custom")

    assert output is not None
    assert output.name == "custom.md"
    assert output.exists()


def test_save_raw_article_failure(mocker: Any, tmp_path: Path) -> None:
    """Tests save_raw_article returns None when fetch_and_clean_article fails.

    Args:
        mocker: The pytest-mock fixture.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    mocker.patch("ingestion.article_etl.fetch_and_clean_article", return_value=None)

    output = save_raw_article("https://example.com/artigo", tmp_path)

    assert output is None
