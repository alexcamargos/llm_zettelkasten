"""Command-line parsing helpers shared by MCP tools."""

from __future__ import annotations

import os
import shlex


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) < 2:
        return value
    if value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def split_command(command: str) -> list[str]:
    """Split a command string while preserving native Windows path separators."""
    args = shlex.split(command, posix=(os.name != "nt"))
    if os.name == "nt":
        return [_strip_wrapping_quotes(arg) for arg in args]
    return args
