from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# ruff: noqa: E402

SRC_ROOT = Path(__file__).resolve().parents[1]
MCP_TOOLS_ROOT = Path(__file__).resolve().parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(MCP_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_TOOLS_ROOT))

from tools_file import list_markdown_files, read_markdown_file
from tools_pdf import (
    find_pageindex_manifest,
    list_pageindex_manifests,
    persist_pageindex_cache,
    read_pageindex_cache,
    read_pageindex_page,
    resolve_pdf_cache,
    sha256_file,
)
from tools_search import hybrid_search

from config import load_settings
from logger import configure_logging, log_skill_execution

settings = load_settings()
configure_logging(settings.logs_path)


@log_skill_execution
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "vault_path": str(settings.vault_path),
        "zettelkasten_path": str(settings.zettelkasten_path),
        "raw_articles_path": str(settings.raw_articles_path),
        "youtube_playlist_configured": bool(settings.youtube_playlist_id),
        "qmd_command": settings.qmd_command,
    }


@log_skill_execution
def search_zettelkasten(query: str, limit: int = 8) -> list[dict[str, Any]]:
    return [
        result.__dict__
        for result in hybrid_search(
            settings.zettelkasten_path,
            query,
            limit=limit,
            qmd_command=settings.qmd_command,
        )
    ]


@log_skill_execution
def list_zettelkasten_markdown() -> list[str]:
    return list_markdown_files(settings.zettelkasten_path)


@log_skill_execution
def read_zettelkasten_markdown(relative_path: str) -> str:
    return read_markdown_file(settings.zettelkasten_path, relative_path)


@log_skill_execution
def inspect_pdf_manifest(source_path: str) -> dict[str, Any]:
    manifest = find_pageindex_manifest(settings.vault_path / ".pageindex", source_path)
    return manifest or {"found": False, "source_path": source_path}


@log_skill_execution
def list_pdf_manifests() -> list[dict[str, Any]]:
    return list_pageindex_manifests(settings.vault_path / ".pageindex")


@log_skill_execution
def read_pdf_cache(
    document_id: str,
    query: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    return read_pageindex_cache(
        settings.vault_path / ".pageindex",
        document_id,
        query=query,
        limit=limit,
    )


@log_skill_execution
def resolve_pdf(relative_path: str) -> dict[str, Any]:
    return resolve_pdf_cache(
        settings.vault_path,
        settings.raw_papers_path,
        settings.vault_path / ".pageindex",
        relative_path,
    )


@log_skill_execution
def read_pdf_page(document_id: str, page: int) -> dict[str, Any]:
    return read_pageindex_page(settings.vault_path / ".pageindex", document_id, page)


@log_skill_execution
def persist_pdf_cache(relative_path: str, tree_json: str) -> dict[str, Any]:
    return persist_pageindex_cache(
        settings.vault_path,
        settings.raw_papers_path,
        settings.vault_path / ".pageindex",
        relative_path,
        tree_json,
    )


@log_skill_execution
def compute_pdf_sha256(relative_path: str) -> dict[str, str]:
    pdf_path = (settings.vault_path / relative_path).resolve()
    if settings.raw_papers_path.resolve() not in pdf_path.parents:
        raise ValueError(
            "Apenas PDFs dentro de raw/papers podem ser hasheados por esta ferramenta."
        )
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("O arquivo informado nao e PDF.")
    return {"source_path": relative_path, "document_id": sha256_file(pdf_path)}


def build_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - depends on runtime dependency
        raise RuntimeError(
            "Instale as dependencias com `uv sync` antes de iniciar o MCP."
        ) from exc

    server = FastMCP("ZettelkastenBrain")
    server.tool()(health)
    server.tool()(search_zettelkasten)
    server.tool()(list_zettelkasten_markdown)
    server.tool()(read_zettelkasten_markdown)
    server.tool()(inspect_pdf_manifest)
    server.tool()(list_pdf_manifests)
    server.tool()(read_pdf_cache)
    server.tool()(resolve_pdf)
    server.tool()(read_pdf_page)
    server.tool()(persist_pdf_cache)
    server.tool()(compute_pdf_sha256)
    return server


def main() -> None:
    if "--health-json" in sys.argv:
        print(json.dumps(health(), ensure_ascii=False))
        return
    build_server().run()


if __name__ == "__main__":
    main()
