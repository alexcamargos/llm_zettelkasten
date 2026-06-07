# Auditoria de Alinhamento da Documentacao

Data da auditoria: 2026-06-07.

## Escopo

Foram comparados os documentos existentes na raiz com:

- `pyproject.toml`
- `src/config.py`
- `src/setup.py`
- `src/mcp/server.py`
- `src/mcp/tools_*.py`
- `src/ingestion/*.py`
- `src/zettelbrain_lint.py`
- `tests/`
- estrutura real de diretorios

## Pontos desalinhados encontrados

| Item | Estado anterior | Estado implementado | Correcao aplicada |
| --- | --- | --- | --- |
| Local canonico das skills | Documentos citavam `.gemini/skills/` como fonte primaria. | Fonte versionada e `skills/`; `.gemini/skills/` e gerado por setup. | README, schema e manual agora apontam `skills/`; setup segue sincronizando para clientes. |
| Configuracoes de cliente | Documentos diziam que `.cursor/mcp.json` e `.gemini/settings.json` eram versionados. | Eles nao existem na arvore atual e sao gerados por `src/setup.py`. | Documentacao passou a trata-los como artefatos locais gerados. |
| Local do schema mestre | `ZETTELBRAIN.md` estava na raiz. | O arquivo e implementacao operacional base, nao documentacao auxiliar. | Mantido na raiz e referenciado pelo README e pelo setup. |
| Manual com links quebraveis | Links relativos apontavam para `.gemini/skills/*.md`. | A origem versionada e `skills/*.md`. | Manual reescrito com links `../skills/*.md`. |
| Estrutura de diretorios | README trazia arvore antiga com `.gemini/`, `.cursor/` e sem `src/`, `tests/`, `docs/`. | Arvore atual contem `src/`, `tests/`, `skills/`, `docs/`, `raw/`, `zettelbrain/`. | README e arquitetura documentam a estrutura atual. |
| ETL de YouTube | Havia confusao textual entre `raw/articles/` e `raw/youtube/`. | `src/ingestion/youtube_etl.py` usa `settings.raw_youtube_path`. | Manual e configuracao documentam `raw/youtube/` como saida correta. |
| Ferramentas MCP | README mencionava poucas ferramentas. | `server.py` registra 20 ferramentas MCP. | Criado `docs/mcp-tools.md` com lista completa. |
| Embeddings | Documentos citavam hashing e Ollama, mas sem contrato de indexacao. | `tools_embeddings.py` indexa apenas `literature/` e `permanent/`. | Arquitetura e MCP docs registram essa regra. |
| Setup local | README nao descrevia `uv run install gemini|cursor|clean` como fluxo principal. | `pyproject.toml` registra script `install = setup:main`. | README e configuracao incluem comandos. |
| Testes | Documentacao nao indicava suite de testes. | `tests/` cobre ETL, MCP tools, linter, setup e config. | README e arquitetura incluem `uv run pytest`. |

## Documentos reorganizados

- `ZETTELBRAIN.md` permaneceu na raiz por ser schema operacional do projeto.
- `Manual_Funcionalidades_Agente.md` foi movido para `docs/manual-funcionalidades-agente.md`.
- `README.md` permaneceu na raiz como ponto de entrada do GitHub.
- Foram criados `docs/arquitetura.md`, `docs/configuracao.md`, `docs/mcp-tools.md` e este relatorio.

## Residuos conhecidos

- `raw/`, `zettelbrain/` e `logs/` sao ignorados pelo Git; clones novos devem executar `uv run install bootstrap` para recriar a estrutura local.
- `raw/articles/web-quickstart.md` esta nao rastreado e parece artefato de ingestao, nao documentacao do projeto.
- `.env` existe localmente e e ignorado pelo Git; terceiros devem usar `.env.example`.
- `.pageindex/`, `.state/` e `logs/` podem conter estado local gerado, conforme `.gitignore`.
