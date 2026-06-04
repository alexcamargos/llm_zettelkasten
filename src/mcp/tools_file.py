from __future__ import annotations

from pathlib import Path


def list_markdown_files(root: Path) -> list[str]:
    return sorted(str(path.relative_to(root)).replace("\\", "/") for path in root.rglob("*.md"))


def read_markdown_file(root: Path, relative_path: str) -> str:
    target = _safe_child(root, relative_path)
    if target.suffix.lower() != ".md":
        raise ValueError("Apenas arquivos Markdown podem ser lidos por esta ferramenta.")
    return target.read_text(encoding="utf-8")


def _safe_child(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    target = (resolved_root / relative_path).resolve()
    if resolved_root != target and resolved_root not in target.parents:
        raise ValueError("Caminho fora do cofre bloqueado.")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(relative_path)
    return target
