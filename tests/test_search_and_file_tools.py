from __future__ import annotations

from pathlib import Path

import pytest
from tools_file import list_markdown_files, read_markdown_file
from tools_search import lexical_search


def test_lexical_search_returns_ranked_results(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("credito credito risco", encoding="utf-8")
    (tmp_path / "b.md").write_text("risco operacional", encoding="utf-8")

    results = lexical_search(tmp_path, "credito risco")

    assert [result.path for result in results] == ["a.md", "b.md"]
    assert results[0].score > results[1].score


def test_file_tools_are_limited_to_markdown_inside_root(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "note.md").write_text("conteudo", encoding="utf-8")
    (tmp_path / "note.txt").write_text("bloqueado", encoding="utf-8")

    assert list_markdown_files(tmp_path) == ["nested/note.md"]
    assert read_markdown_file(tmp_path, "nested/note.md") == "conteudo"

    with pytest.raises(ValueError):
        read_markdown_file(tmp_path, "note.txt")
