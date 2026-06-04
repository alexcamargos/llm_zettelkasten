from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_pageindex_manifest(pageindex_root: Path, source_path: str) -> dict[str, Any] | None:
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


def list_pageindex_manifests(pageindex_root: Path) -> list[dict[str, Any]]:
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
    nodes = [value]
    if isinstance(value, dict):
        for child in value.values():
            nodes.extend(_walk_json(child))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(_walk_json(child))
    return nodes


def _node_text(node: Any) -> str:
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
    if not isinstance(node, dict):
        return None
    for key in ("page", "page_number", "pageIndex", "page_index"):
        value = node.get(key)
        if isinstance(value, int):
            return value
    return None


def _is_document_id(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _find_page_nodes(value: Any, *, page: int) -> list[Any]:
    return [node for node in _walk_json(value) if _node_page(node) == page]


def _read_manifest_for_document_id(
    pageindex_root: Path,
    document_id: str,
) -> dict[str, Any] | None:
    manifest_path = pageindex_root / document_id / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _safe_pdf_path(vault_path: Path, raw_papers_path: Path, relative_path: str) -> Path:
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
    return value.replace("\\", "/").strip().lstrip("./")
