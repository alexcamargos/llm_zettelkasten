"""Automation utility for configuring LLM Zettelkasten for Gemini CLI or Cursor IDE.

Allows switching configuration profiles seamlessly by managing .cursorrules and client settings
for Model Context Protocol (MCP) servers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Resolve the repository root directory.

    Returns:
        Path: The absolute path of the repository root.
    """
    return Path(__file__).resolve().parents[1]


def configure_gemini(repo_root: Path) -> int:
    """Configure settings for the Gemini CLI client.

    Creates the .gemini directory and settings.json if missing, and deactivates
    Cursor rules (.cursorrules) to avoid configuration conflicts.

    Args:
        repo_root: The root path of the repository.

    Returns:
        int: The exit code (0 for success).
    """
    print("[-] Configurando o ambiente para o Gemini CLI...")

    try:
        # Ensure .gemini/settings.json exists
        gemini_dir = repo_root / ".gemini"
        gemini_dir.mkdir(parents=True, exist_ok=True)
        settings_file = gemini_dir / "settings.json"

        default_settings = {
            "mcpServers": {
                "ZettelkastenBrain": {
                    "command": "uv",
                    "args": ["run", "zettel-mcp"],
                    "timeout": 600000,
                },
                "pageindex": {
                    "command": "npx",
                    "args": ["-y", "@pageindex/mcp"],
                    "timeout": 600000,
                },
            }
        }

        if not settings_file.exists():
            settings_file.write_text(
                json.dumps(default_settings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(
                "[+] Arquivo de configuracao criado em: "
                f"{settings_file.relative_to(repo_root)}"
            )
        else:
            print(
                "[~] Arquivo de configuracao ja existente em: "
                f"{settings_file.relative_to(repo_root)}"
            )

        # Deactivate .cursorrules to prevent agent confusion in Gemini CLI
        cursorrules = repo_root / ".cursorrules"
        if cursorrules.exists():
            cursorrules_bak = repo_root / ".cursorrules.bak"
            if cursorrules_bak.exists():
                cursorrules_bak.unlink()
            cursorrules.rename(cursorrules_bak)
            print(
                "[+] Regras do Cursor desativadas: "
                f"{cursorrules.name} -> {cursorrules_bak.name}"
            )

        print("\n[OK] Ambiente do Gemini CLI configurado com sucesso!")
        print("    -> Execute o seu agente Gemini CLI normalmente.")
        return 0

    except OSError as exc:
        print(f"[ERRO] Erro ao configurar o ambiente Gemini CLI: {exc}", file=sys.stderr)
        return 1


def configure_cursor(repo_root: Path) -> int:
    """Configure settings for the Cursor IDE client.

    Creates the .cursor directory and mcp.json if missing, and copies GEMINI.md
    to .cursorrules to make rules visible to Cursor's AI models.

    Args:
        repo_root: The root path of the repository.

    Returns:
        int: The exit code (0 for success).
    """
    print("[-] Configurando o ambiente para o Cursor IDE...")

    try:
        # Ensure .cursor/mcp.json exists
        cursor_dir = repo_root / ".cursor"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        mcp_file = cursor_dir / "mcp.json"

        default_mcp = {
            "mcpServers": {
                "ZettelkastenBrain": {
                    "command": "uv",
                    "args": ["run", "zettel-mcp"],
                },
                "pageindex": {
                    "command": "npx",
                    "args": ["-y", "@pageindex/mcp"],
                },
            }
        }

        if not mcp_file.exists():
            mcp_file.write_text(
                json.dumps(default_mcp, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(
                "[+] Arquivo MCP do Cursor criado em: "
                f"{mcp_file.relative_to(repo_root)}"
            )
        else:
            print(
                "[~] Arquivo MCP do Cursor ja existente em: "
                f"{mcp_file.relative_to(repo_root)}"
            )

        # Copy GEMINI.md to .cursorrules
        master_rules = repo_root / "GEMINI.md"
        cursorrules = repo_root / ".cursorrules"
        cursorrules_bak = repo_root / ".cursorrules.bak"

        # If backup exists, we can delete it since we are creating a new .cursorrules
        if cursorrules_bak.exists():
            cursorrules_bak.unlink()

        if master_rules.exists():
            rules_content = master_rules.read_text(encoding="utf-8")
            cursorrules.write_text(rules_content, encoding="utf-8")
            print(
                "[+] Regras sincronizadas: "
                f"{master_rules.name} -> {cursorrules.name}"
            )
        else:
            print(
                "[!] Aviso: GEMINI.md nao encontrado na raiz do projeto. "
                "Nao foi possivel gerar as regras do Cursor."
            )

        print("\n[OK] Ambiente do Cursor IDE configurado com sucesso!")
        print("    -> Abra o Cursor e configure o MCP em Cursor Settings > Features > MCP.")
        print(f"       Use o arquivo {mcp_file.relative_to(repo_root)} como referencia.")
        return 0

    except OSError as exc:
        print(f"[ERRO] Erro ao configurar o ambiente Cursor: {exc}", file=sys.stderr)
        return 1





def main() -> None:
    """Entry point for the setup utility.

    Parses command line arguments and triggers corresponding client configurations.

    Returns:
        None
    """
    repo_root = get_repo_root()
    args = sys.argv[1:]

    if not args:
        print("Erro: Nenhum provedor especificado.", file=sys.stderr)
        print("Uso: uv run install [gemini|cursor]", file=sys.stderr)
        sys.exit(1)

    provider = args[0].lower().strip()
    if provider == "gemini":
        sys.exit(configure_gemini(repo_root))
    elif provider == "cursor":
        sys.exit(configure_cursor(repo_root))
    else:
        print(f"Erro: Provedor '{provider}' desconhecido.", file=sys.stderr)
        print("Uso: uv run install [gemini|cursor]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
