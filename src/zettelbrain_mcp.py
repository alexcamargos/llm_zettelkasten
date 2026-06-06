"""Bootstrap script to launch the ZettelBrain Model Context Protocol (MCP) server.

Configures the system paths so that local MCP files can be imported properly,
and runs the server main loop.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Bootstrap execution for the ZettelBrain MCP server."""
    mcp_root = Path(__file__).resolve().parent / "mcp"
    if str(mcp_root) not in sys.path:
        sys.path.insert(0, str(mcp_root))

    from server import main as server_main

    server_main()
