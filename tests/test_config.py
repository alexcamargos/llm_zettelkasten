"""Unit tests for the project configuration loader.

Tests the environment variable parsing, path resolution, and validation logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import ConfigError, load_settings


def test_load_settings_from_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings are correctly loaded from a valid .env configuration file.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch utility fixture.

    Returns:
        None
    """
    (tmp_path / "raw" / "articles").mkdir(parents=True)
    (tmp_path / "raw" / "papers").mkdir(parents=True)
    (tmp_path / "zettelkasten").mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"OBSIDIAN_VAULT_PATH={tmp_path}",
                "YOUTUBE_PLAYLIST_ID=PL_TESTE",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.delenv("YOUTUBE_PLAYLIST_ID", raising=False)

    settings = load_settings(env_file, require_youtube=True)

    assert settings.vault_path == tmp_path.resolve()
    assert settings.youtube_playlist_id == "PL_TESTE"
    assert settings.raw_articles_path == (tmp_path / "raw" / "articles").resolve()


def test_load_settings_requires_youtube_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that ConfigError is raised if YouTube playlist ID is missing but required.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch utility fixture.

    Returns:
        None
    """
    (tmp_path / "raw" / "articles").mkdir(parents=True)
    (tmp_path / "raw" / "papers").mkdir(parents=True)
    (tmp_path / "zettelkasten").mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text(f"OBSIDIAN_VAULT_PATH={tmp_path}\n", encoding="utf-8")
    monkeypatch.delenv("YOUTUBE_PLAYLIST_ID", raising=False)

    with pytest.raises(ConfigError, match="YOUTUBE_PLAYLIST_ID"):
        load_settings(env_file, require_youtube=True)
