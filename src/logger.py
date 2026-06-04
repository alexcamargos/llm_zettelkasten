from __future__ import annotations

import functools
import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

try:
    from loguru import logger as _logger
except ImportError:  # pragma: no cover - exercised only without optional dependency
    _logger = None

F = TypeVar("F", bound=Callable[..., Any])


def configure_logging(logs_path: Path) -> Any:
    """Configure structured logs with loguru when available, otherwise stdlib logging."""
    logs_path.mkdir(parents=True, exist_ok=True)
    log_file = logs_path / "zettelkasten.log"

    if _logger is not None:
        _logger.remove()
        _logger.add(
            sink=sys.stderr,
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
        )
        _logger.add(
            log_file,
            rotation="10 MB",
            retention="14 days",
            encoding="utf-8",
            enqueue=True,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        )
        return _logger

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("llm_zettelkasten")


def get_logger() -> Any:
    if _logger is not None:
        return _logger
    return logging.getLogger("llm_zettelkasten")


def log_skill_execution(func: F) -> F:
    """Log function name, elapsed time and failures for MCP tool handlers."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger()
        started = time.perf_counter()
        tool_name = func.__name__
        logger.info("skill_start name={} args={} kwargs={}", tool_name, args, kwargs)
        try:
            result = func(*args, **kwargs)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "skill_error name={} elapsed_ms={:.2f}", tool_name, elapsed_ms
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info("skill_end name={} elapsed_ms={:.2f}", tool_name, elapsed_ms)
        return result

    return wrapper  # type: ignore[return-value]
