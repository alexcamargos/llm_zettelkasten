from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when project configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    vault_path: Path
    ingestion_history_path: Path
    raw_articles_path: Path
    raw_papers_path: Path
    zettelkasten_path: Path
    logs_path: Path
    youtube_playlist_id: str | None
    llm_model_name: str
    embedding_model_name: str


def load_settings(
    env_path: Path | str | None = None, *, require_youtube: bool = False
) -> Settings:
    """Load project settings from .env and environment variables."""
    repo_root = Path(__file__).resolve().parents[1]
    dotenv_path = Path(env_path) if env_path else repo_root / ".env"
    _load_dotenv(dotenv_path)

    vault_path = _resolve_path(os.getenv("OBSIDIAN_VAULT_PATH", "."), repo_root)
    settings = Settings(
        vault_path=vault_path,
        ingestion_history_path=_resolve_path(
            os.getenv("HISTORICO_INGESTAO_PATH", ".state/historico_ingestao.txt"),
            vault_path,
        ),
        raw_articles_path=_resolve_path(
            os.getenv("RAW_ARTICLES_PATH", "raw/articles"), vault_path
        ),
        raw_papers_path=_resolve_path(
            os.getenv("RAW_PAPERS_PATH", "raw/papers"), vault_path
        ),
        zettelkasten_path=_resolve_path(
            os.getenv("ZETTELKASTEN_PATH", "zettelkasten"), vault_path
        ),
        logs_path=_resolve_path(os.getenv("LOGS_PATH", "logs"), vault_path),
        youtube_playlist_id=_empty_to_none(os.getenv("YOUTUBE_PLAYLIST_ID")),
        llm_model_name=os.getenv("LLM_MODEL_NAME", "gemini-2.5-pro"),
        embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "nomic-embed-text"),
    )
    _validate_settings(settings, require_youtube=require_youtube)
    return settings


def _load_dotenv(dotenv_path: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_dotenv_fallback(dotenv_path)
        return

    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)


def _load_dotenv_fallback(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _resolve_path(value: str, base_path: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_path / path
    return path.resolve()


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _validate_settings(settings: Settings, *, require_youtube: bool) -> None:
    required_dirs = {
        "OBSIDIAN_VAULT_PATH": settings.vault_path,
        "RAW_ARTICLES_PATH": settings.raw_articles_path,
        "RAW_PAPERS_PATH": settings.raw_papers_path,
        "ZETTELKASTEN_PATH": settings.zettelkasten_path,
    }

    missing = [name for name, path in required_dirs.items() if not path.exists()]
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(f"Diretorios obrigatorios ausentes ou invalidos: {joined}")

    if require_youtube and not settings.youtube_playlist_id:
        raise ConfigError("YOUTUBE_PLAYLIST_ID e obrigatorio para o ETL do YouTube.")
