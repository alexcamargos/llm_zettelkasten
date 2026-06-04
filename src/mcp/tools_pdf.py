"""PageIndex layout cache and PDF indexing utilities.

Provides layout caching services for PDF documents under the Obsidian vault.
Manages metadata manifests, layout trees, page extraction, and cryptographic
SHA-256 integrity verification.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Compute the SHA-256 hexadecimal hash of a file's entire binary content.

    Args:
        path: Path to the target file.

    Returns:
        str: The 64-character lowercase hexadecimal hash.
    """
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_pageindex_manifest(pageindex_root: Path, source_path: str) -> dict[str, Any] | None:
    """Find a PageIndex manifest for a given PDF source path in the cache.

    Args:
        pageindex_root: Base Path to the .pageindex folder.
        source_path: The relative path of the PDF document.

    Returns:
        dict[str, Any] | None: The loaded manifest data dictionary, or None if
            no matching manifest exists.
    """
    normalized_source = _normalize_relative_path(source_path)
    for manifest_path in pageindex_root.glob("*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if _normalize_relative_path(str(manifest.get("source_path", ""))) == normalized_source:
            return manifest
    return None


def resolve_pdf_cache(
    vault_path: Path,
    raw_papers_path: Path,
    pageindex_root: Path,
    relative_path: str,
) -> dict[str, Any]:
    """Resolve a PDF's document ID and check if its manifest exists.

    Args:
        vault_path: Root Path of the vault.
        raw_papers_path: Root Path of the raw papers folder.
        pageindex_root: Base Path to the .pageindex directory.
        relative_path: The relative path of the PDF.

    Returns:
        dict[str, Any]: Resolution status map containing source path, document ID,
            cache presence, and loaded manifest (if available).
    """
    pdf_path = _safe_pdf_path(vault_path, raw_papers_path, relative_path)
    document_id = sha256_file(pdf_path)
    source_path = _normalize_relative_path(str(pdf_path.relative_to(vault_path.resolve())))
    manifest = _read_manifest_for_document_id(pageindex_root, document_id)
    if manifest is None:
        manifest = find_pageindex_manifest(pageindex_root, source_path)

    return {
        "source_path": source_path,
        "document_id": document_id,
        "cache_found": manifest is not None,
        "manifest": manifest,
    }


def index_pdf_with_command(
    vault_path: Path,
    raw_papers_path: Path,
    pageindex_root: Path,
    relative_path: str,
    *,
    pageindex_command: str | None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Index a PDF using an external command that emits PageIndex tree JSON.

    The command is configured without the target PDF path; this function appends
    the validated absolute PDF path as the final argument and expects stdout to
    be a JSON object/list compatible with `persist_pageindex_cache`.
    """
    pdf_path = _safe_pdf_path(vault_path, raw_papers_path, relative_path)
    if not pageindex_command:
        return {
            "indexed": False,
            "reason": "PAGEINDEX_COMMAND nao configurado.",
            "source_path": _normalize_relative_path(str(pdf_path.relative_to(vault_path))),
            "document_id": sha256_file(pdf_path),
        }

    executable = shlex.split(pageindex_command)[0]
    if shutil.which(executable) is None:
        return {
            "indexed": False,
            "reason": f"Comando PageIndex indisponivel: {executable}",
            "source_path": _normalize_relative_path(str(pdf_path.relative_to(vault_path))),
            "document_id": sha256_file(pdf_path),
        }

    command = [*shlex.split(pageindex_command), str(pdf_path)]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            cwd=vault_path,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "indexed": False,
            "reason": f"Falha ao executar PageIndex: {exc}",
            "source_path": _normalize_relative_path(str(pdf_path.relative_to(vault_path))),
            "document_id": sha256_file(pdf_path),
        }

    if completed.returncode != 0:
        return {
            "indexed": False,
            "reason": completed.stderr.strip() or "PageIndex retornou codigo diferente de zero.",
            "source_path": _normalize_relative_path(str(pdf_path.relative_to(vault_path))),
            "document_id": sha256_file(pdf_path),
        }

    persisted = persist_pageindex_cache(
        vault_path,
        raw_papers_path,
        pageindex_root,
        relative_path,
        completed.stdout,
        index_source="pageindex_external_command",
        mcp_transport=pageindex_command,
    )
    return {"indexed": True, **persisted}


def persist_pageindex_cache(
    vault_path: Path,
    raw_papers_path: Path,
    pageindex_root: Path,
    relative_path: str,
    tree: dict[str, Any] | list[Any] | str,
    *,
    hash_tool: str = "python_hashlib_sha256",
    index_source: str = "pageindex_mcp_local",
    mcp_transport: str = "npx -y @pageindex/mcp",
) -> dict[str, Any]:
    """Write the layout tree and a metadata manifest to the PageIndex cache.

    Args:
        vault_path: Root Path of the vault.
        raw_papers_path: Root Path of the raw papers folder.
        pageindex_root: Base Path of the .pageindex folder.
        relative_path: The relative path of the PDF file.
        tree: Parsed tree data structure or raw JSON representation of it.
        hash_tool: Name of the hashing mechanism. Defaults to "python_hashlib_sha256".
        index_source: String tag identifying the index client. Defaults to
            "pageindex_mcp_local".
        mcp_transport: String tag describing the MCP invocation script. Defaults to
            "npx -y @pageindex/mcp".

    Returns:
        dict[str, Any]: Information mapping of the written paths and metadata.
    """
    pdf_path = _safe_pdf_path(vault_path, raw_papers_path, relative_path)
    document_id = sha256_file(pdf_path)
    source_path = _normalize_relative_path(str(pdf_path.relative_to(vault_path.resolve())))
    parsed_tree = _parse_tree_payload(tree)

    document_root = pageindex_root / document_id
    document_root.mkdir(parents=True, exist_ok=True)
    tree_path = document_root / "tree.json"
    manifest_path = document_root / "manifest.json"

    tree_path.write_text(
        json.dumps(parsed_tree, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "schema_version": "1",
        "document_id": document_id,
        "hash_tool": hash_tool,
        "source_path": source_path,
        "source_filename": pdf_path.name,
        "byte_size": pdf_path.stat().st_size,
        "indexed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "index_source": index_source,
        "mcp_transport": mcp_transport,
        **_infer_tree_metadata(parsed_tree),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "document_id": document_id,
        "source_path": source_path,
        "tree_path": _normalize_relative_path(str(tree_path.relative_to(vault_path.resolve()))),
        "manifest_path": _normalize_relative_path(
            str(manifest_path.relative_to(vault_path.resolve()))
        ),
        "manifest": manifest,
    }


def list_pageindex_manifests(pageindex_root: Path) -> list[dict[str, Any]]:
    """List summary metadata for all PageIndex cache entries.

    Args:
        pageindex_root: Base Path of the .pageindex folder.

    Returns:
        list[dict[str, Any]]: List of metadata maps containing document IDs and source paths.
    """
    manifests: list[dict[str, Any]] = []
    for manifest_path in sorted(pageindex_root.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        manifests.append(
            {
                "document_id": manifest_path.parent.name,
                "source_path": manifest.get("source_path"),
                "source_filename": manifest.get("source_filename"),
                "indexed_at": manifest.get("indexed_at"),
                "page_count": manifest.get("page_count") or manifest.get("page_count_estimate"),
            }
        )
    return manifests


def read_pageindex_cache(
    pageindex_root: Path,
    document_id: str,
    *,
    query: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Read cached tree/manifest files and optionally search for terms in the tree.

    Args:
        pageindex_root: Base Path of the .pageindex folder.
        document_id: Hexadecimal SHA-256 document identifier.
        query: Optional whitespace-separated search term(s) to query.
        limit: Maximum number of search results to return. Defaults to 5.

    Returns:
        dict[str, Any]: Dict containing resolution status, manifest info, and match list.

    Raises:
        ValueError: If document_id is not a valid SHA-256 identifier or escapes boundaries.
    """
    if not _is_document_id(document_id):
        raise ValueError("document_id deve ser um SHA-256 hexadecimal em minusculas.")

    resolved_root = pageindex_root.resolve()
    document_root = (resolved_root / document_id).resolve()
    if resolved_root not in document_root.parents:
        raise ValueError("document_id invalido.")

    manifest_path = document_root / "manifest.json"
    tree_path = document_root / "tree.json"
    if not manifest_path.exists() or not tree_path.exists():
        return {"found": False, "document_id": document_id}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    matches = _find_tree_matches(tree, query=query, limit=limit) if query else []
    return {
        "found": True,
        "document_id": document_id,
        "manifest": manifest,
        "matches": matches,
    }


def read_pageindex_page(pageindex_root: Path, document_id: str, page: int) -> dict[str, Any]:
    """Retrieve layout text content for a single page from cached tree.

    Args:
        pageindex_root: Base Path of the .pageindex folder.
        document_id: Hexadecimal SHA-256 document identifier.
        page: 1-indexed page number to look up.

    Returns:
        dict[str, Any]: Status dictionary containing matching page text and metadata.

    Raises:
        ValueError: If page is less than 1 or if document_id is invalid.
    """
    if page < 1:
        raise ValueError("page deve ser maior ou igual a 1.")
    if not _is_document_id(document_id):
        raise ValueError("document_id deve ser um SHA-256 hexadecimal em minusculas.")

    resolved_root = pageindex_root.resolve()
    document_root = (resolved_root / document_id).resolve()
    if resolved_root not in document_root.parents:
        raise ValueError("document_id invalido.")

    manifest_path = document_root / "manifest.json"
    tree_path = document_root / "tree.json"
    if not manifest_path.exists() or not tree_path.exists():
        return {"found": False, "document_id": document_id, "page": page}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    nodes = _find_page_nodes(tree, page=page)
    return {
        "found": True,
        "document_id": document_id,
        "page": page,
        "manifest": manifest,
        "text": "\n\n".join(_node_text(node) for node in nodes if _node_text(node)),
        "node_count": len(nodes),
    }


def _find_tree_matches(value: Any, *, query: str | None, limit: int) -> list[dict[str, Any]]:
    """Scan the layout tree for nodes containing search terms.

    Args:
        value: Root node or sub-tree layout list/dictionary.
        query: Search query containing space-separated terms.
        limit: Maximum results to return.

    Returns:
        list[dict[str, Any]]: List of dictionary mappings representing matches.
    """
    terms = [term.lower() for term in (query or "").split() if len(term) >= 2]
    if not terms:
        return []

    matches: list[dict[str, Any]] = []
    for node in _walk_json(value):
        text = _node_text(node)
        lowered = text.lower()
        score = sum(lowered.count(term) for term in terms)
        if score <= 0:
            continue
        matches.append(
            {
                "score": score,
                "page": _node_page(node),
                "excerpt": text[:600],
            }
        )
    return sorted(matches, key=lambda item: -int(item["score"]))[:limit]


def _walk_json(value: Any) -> list[Any]:
    """Recursively traverse a JSON object hierarchy to collect nested nodes.

    Args:
        value: JSON-like structure (dict, list, string, etc.).

    Returns:
        list[Any]: Flat list of all child nodes and structures found.
    """
    nodes = [value]
    if isinstance(value, dict):
        for child in value.values():
            nodes.extend(_walk_json(child))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(_walk_json(child))
    return nodes


def _node_text(node: Any) -> str:
    """Extract string content out of a layout tree node.

    Args:
        node: A node from the layout tree.

    Returns:
        str: Textual description/content of the node.
    """
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        parts = [
            str(value)
            for key, value in node.items()
            if key.lower() in {"text", "content", "title", "heading", "summary"}
            and isinstance(value, str)
        ]
        return " ".join(parts)
    return ""


def _node_page(node: Any) -> int | None:
    """Extract page number from a node if it represents one.

    Args:
        node: A node from the layout tree.

    Returns:
        int | None: Page number if found, otherwise None.
    """
    if not isinstance(node, dict):
        return None
    for key in ("page", "page_number", "pageIndex", "page_index"):
        value = node.get(key)
        if isinstance(value, int):
            return value
    return None


def _is_document_id(value: str) -> bool:
    """Validate if string conforms to lowercase hexadecimal SHA-256 pattern.

    Args:
        value: Input string.

    Returns:
        bool: True if it is a valid format, otherwise False.
    """
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _find_page_nodes(value: Any, *, page: int) -> list[Any]:
    """Filter layout nodes that belong to a specific page index.

    Args:
        value: The parent tree node or list.
        page: The page number to match.

    Returns:
        list[Any]: Matching nodes in the sub-tree.
    """
    return [node for node in _walk_json(value) if _node_page(node) == page]


def _read_manifest_for_document_id(
    pageindex_root: Path,
    document_id: str,
) -> dict[str, Any] | None:
    """Read PageIndex manifest file by document ID folder path.

    Args:
        pageindex_root: Base Path of .pageindex folder.
        document_id: Hexadecimal SHA-256 document identifier.

    Returns:
        dict[str, Any] | None: Loaded manifest dictionary or None if missing/invalid.
    """
    manifest_path = pageindex_root / document_id / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _safe_pdf_path(vault_path: Path, raw_papers_path: Path, relative_path: str) -> Path:
    """Verify that a path is a PDF, exists, and resides within raw/papers directory.

    Args:
        vault_path: Obsidian vault root Path.
        raw_papers_path: Papers folder Path.
        relative_path: The relative path to resolve.

    Returns:
        Path: Resolved absolute PDF Path.

    Raises:
        ValueError: If path escapes raw/papers directory or is not a PDF.
        FileNotFoundError: If the target file does not exist.
    """
    resolved_vault = vault_path.resolve()
    resolved_raw_papers = raw_papers_path.resolve()
    pdf_path = (resolved_vault / relative_path).resolve()
    if resolved_raw_papers != pdf_path.parent and resolved_raw_papers not in pdf_path.parents:
        raise ValueError("Apenas PDFs dentro de raw/papers podem ser acessados.")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("O arquivo informado nao e PDF.")
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(relative_path)
    return pdf_path


def _normalize_relative_path(value: str) -> str:
    """Convert backslashes and strip prefix indicators from a path string.

    Args:
        value: Input path string.

    Returns:
        str: Normalized relative path string.
    """
    normalized = value.replace("\\", "/").strip()
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _parse_tree_payload(tree: dict[str, Any] | list[Any] | str) -> dict[str, Any] | list[Any]:
    """Parse layout tree from tree data payload.

    Args:
        tree: Pre-parsed dictionary/list, or raw JSON string.

    Returns:
        dict[str, Any] | list[Any]: Validated tree representation.

    Raises:
        ValueError: If serialization is not a valid JSON object or list.
    """
    if isinstance(tree, dict | list):
        return tree
    try:
        parsed = json.loads(tree)
    except json.JSONDecodeError as exc:
        raise ValueError("tree_json deve ser JSON valido.") from exc
    if not isinstance(parsed, dict | list):
        raise ValueError("tree_json deve representar um objeto ou lista JSON.")
    return parsed


def _infer_tree_metadata(tree: dict[str, Any] | list[Any]) -> dict[str, Any]:
    """Infer the total page count for a tree structure.

    Args:
        tree: The layout tree payload.

    Returns:
        dict[str, Any]: Metdata dict containing page count estimate if found.
    """
    pages = sorted({page for node in _walk_json(tree) if (page := _node_page(node)) is not None})
    if not pages:
        return {}
    return {"page_count_estimate": max(pages)}
