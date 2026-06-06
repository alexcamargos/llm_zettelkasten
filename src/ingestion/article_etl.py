"""Web article ETL pipeline.

This module automates the fetching and cleaning of web articles from HTTP/HTTPS URLs
using the trafilatura library. It extracts main text as Markdown, pulls structural
metadata, and writes the output with YAML front matter into the raw articles directory.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import trafilatura

from config import load_settings
from logger import configure_logging, get_logger


def fetch_and_clean_article(url: str) -> dict[str, Any] | None:
    """Downloads a webpage and extracts its main body content and metadata.

    Args:
        url: The absolute HTTP/HTTPS URL of the web article.

    Returns:
        A dictionary containing extracted metadata and Markdown content, or
        None if the download or extraction fails. The returned dictionary has
        the following keys: 'title', 'author', 'date', 'url', 'content'.

    Raises:
        ValueError: If the provided URL is empty or invalid.
    """
    if not url.strip():
        raise ValueError("Article URL cannot be empty.")

    get_logger().info("Downloading article from URL: {}", url)
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        get_logger().error("Failed to download content from URL: {}", url)
        return None

    # Extract document metadata.
    metadata = trafilatura.extract_metadata(downloaded)

    # Extract the main article body formatted as Markdown.
    markdown_content = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
    )

    if not markdown_content:
        get_logger().error("Failed to extract useful text content from URL: {}", url)
        return None

    title = metadata.title if metadata and metadata.title else "Untitled"
    author = metadata.author if metadata and metadata.author else "Unknown author"
    date = metadata.date if metadata and metadata.date else "Unknown date"

    return {
        "title": title,
        "author": author,
        "date": date,
        "url": url,
        "content": markdown_content,
    }


def slugify(value: str) -> str:
    """Converts a string to a filesystem-safe slug representation.

    Args:
        value: Input string to slugify.

    Returns:
        A slugified string containing only lowercase letters, numbers, and hyphens.
    """
    # Decompose accented characters and strip accent marks.
    normalized = unicodedata.normalize("NFKD", value)
    ascii_encoded = normalized.encode("ascii", "ignore").decode("ascii")

    slug = ascii_encoded.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:80] or "article"


def save_raw_article(
    url: str,
    raw_articles_path: Path,
    filename: str | None = None,
) -> Path | None:
    """Fetches web article content and saves it as a Markdown file with YAML metadata.

    Args:
        url: The absolute HTTP/HTTPS URL of the web article.
        raw_articles_path: Target directory path for storing raw articles.
        filename: Optional output filename (e.g., 'article.md'). If omitted, a
            filename is generated automatically based on the article's title.

    Returns:
        The Path to the saved Markdown file, or None if extraction fails.
    """
    data = fetch_and_clean_article(url)
    if not data:
        return None

    raw_articles_path.mkdir(parents=True, exist_ok=True)

    if not filename:
        slug = slugify(data["title"])
        filename = f"web-{slug}.md"
    elif not filename.endswith(".md"):
        filename = f"{filename}.md"

    output_path = raw_articles_path / filename
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")

    # Escape quotes and backslashes for YAML front matter.
    escaped_title = data["title"].replace("\\", "\\\\").replace('"', '\\"')
    escaped_author = data["author"].replace("\\", "\\\\").replace('"', '\\"')

    lines = [
        "---",
        f'title: "{escaped_title}"',
        f'author: "{escaped_author}"',
        f'published_at: "{data["date"]}"',
        f'url: "{url}"',
        f'retrieved_at: "{retrieved_at}"',
        "source_kind: web_article",
        "---",
        "",
        f"# {data['title']}",
        "",
        "Content automatically extracted from the web. This file must be processed "
        "by the `/ingest-article` workflow before entering the ZettelBrain vault.",
        "",
        data["content"],
    ]

    content_to_write = "\n".join(lines).rstrip() + "\n"
    output_path.write_text(content_to_write, encoding="utf-8", newline="\n")

    get_logger().info("Article saved successfully at: {}", output_path)
    return output_path


def main() -> None:
    """CLI entry point for the Web Article ETL pipeline.

    Parses CLI arguments, loads settings, and runs the extraction and saving processes.
    """
    parser = argparse.ArgumentParser(
        description="Ingest a web article and save it as clean Markdown."
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="The web article URL to process.",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        help="Custom filename to save (for example, my-article.md).",
    )
    args = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.logs_path)

    saved_path = save_raw_article(
        url=args.url,
        raw_articles_path=settings.raw_articles_path,
        filename=args.filename,
    )

    if saved_path:
        get_logger().info("Article ETL completed successfully.")
    else:
        get_logger().error("Article ETL failed.")


if __name__ == "__main__":
    main()
