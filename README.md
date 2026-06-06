# Zettelkasten Modular via Gemini CLI

## Visão Geral do Sistema
Este repositório estabelece a arquitetura oficial para o ecossistema de gestão de conhecimento pessoal e pesquisa acadêmica operado via interface de linha de comando. Adotando o paradigma de **Notas Atômicas em Arquitetura Dissertativa**, o projeto foi desenhado especificamente para suportar o rigor metodológico exigido em modelagem preditiva de risco e análise de indicadores financeiros.

A arquitetura divide as responsabilidades de processamento de dados entre um arquivo mestre de configuração e múltiplas habilidades modulares. Cada habilidade executa uma função isolada e altamente especializada dentro do ambiente de terminal. O sistema orquestra desde a extração rigorosa de referências no padrão ABNT a partir de literatura acadêmica densa até a redação de rascunhos consolidados. O diretório raiz atua como o motor principal de indexação, enquanto a pasta de fontes abriga os documentos originais e a base de conhecimento armazena as conexões lógicas em desenvolvimento.

Esta organização metodológica garante o versionamento seguro de todo o escopo de pesquisa. A modularidade permite a manutenção contínua e a escalabilidade do sistema operacional, mantendo a integridade teórica exigida para a produção acadêmica de alto nível e aplicações de **Business Intelligence**.

## Estrutura de Diretórios do Projeto

Para garantir o funcionamento perfeito do agente local acionado pelo terminal, o repositório reflete a exata árvore de arquivos demonstrada abaixo.

```text
llm_zettelkasten/
├── README.md
├── GEMINI.md
├── Manual_Funcionalidades_Agente.md  # Manual de uso e exemplos
├── .gitignore
├── .pageindex/
│   └── .gitkeep
├── .cursor/
│   └── mcp.json
├── .gemini/
│   ├── settings.json
│   └── skills/
│       ├── start.md
│       ├── ingest-paper.md
│       ├── ingest-paper-intro.md
│       ├── ingest-article.md
│       ├── ingest-youtube.md
│       ├── recall.md
│       ├── visual.md
│       ├── lint.md
│       ├── trace.md
│       ├── bridge.md
│       ├── research-deep.md
│       ├── ghost.md
│       └── close.md
├── .state/
│   ├── hot.md
│   ├── log.md
│   └── embeddings_index.json  # gerado localmente, ignorado pelo Git
├── raw/
│   ├── papers/
│   ├── articles/
│   └── assets/
└── zettelkasten/
    ├── index.md
    ├── overview.md
    ├── literature/
    ├── permanent/
    ├── visual/
    ├── assets/
    ├── presentations/
    ├── drafts/
    └── syntheses/
```

Pastas sem notas ainda usam um arquivo **`.gitkeep`** (vazio) para o Git versionar o diretório; pode remover o `.gitkeep` quando existirem outros arquivos estáveis na mesma pasta. A pasta **`.pageindex/`** segue o mesmo padrão: só o **`.gitkeep`** entra no Git; `tree.json` e `manifest.json` gerados por ingestão com PageIndex ficam ignorados pelo `.gitignore` na raiz.

## Instruções de Configuração e Integração

### Princípios Iniciais
A inicialização em um novo ambiente resume-se a clonar o repositório, instalar o Gemini CLI conforme a documentação oficial e passar a operar na raiz do projeto. As pastas necessárias já vêm no clone; o foco segue sendo a mineração de dados acadêmicos com o agente.

### Clonagem e Versionamento
O usuário deve clonar o repositório para o disco local utilizando um cliente de controle de versão. A árvore de pastas versionada (`raw/`, `zettelkasten/`, `.state/`) já vem preparada para uso imediato; adicione PDFs formais em `raw/papers/` (skills `/ingest-paper` e `/ingest-paper-intro`), recortes informais da web em Markdown em `raw/articles/` (skill `/ingest-article`) e transcrições geradas pelo ETL de YouTube em `raw/articles/` (skill `/ingest-youtube`).

### Gemini CLI
Abra o **[Gemini CLI](https://geminicli.com/)** na **raiz deste repositório** (o diretório que contém `GEMINI.md`, `raw/`, `zettelkasten/` e `.state/`). O agente assim carrega o schema e as skills em `.gemini/skills/`. Para a versão instalada, siga o comando indicado na documentação da sua instalação (por exemplo `gemini --version`, se existir).

### Motor Python Local
O repositório agora inclui a camada do motor Python previsto na arquitetura: `pyproject.toml`, configuração centralizada em `src/config.py`, logs em `src/logger.py`, ETL de YouTube em `src/ingestion/youtube_etl.py`, linter de integridade estática em `src/zettel_lint.py` e o servidor MCP em `src/mcp/server.py`. As dependências são gerenciadas por `uv`; para preparar o ambiente, execute `uv sync` na raiz do projeto.

O linter de integridade do cofre pode ser executado diretamente pelo terminal via `uv run zettel-lint` (ou `uv run zettel-lint --json` para saídas estruturadas) para validar a saúde de links mortos, órfãos, ligação mínima ao grafo, referências a deprecados e padrões de conhecimento emergentes no Zettelkasten. Para validar o servidor sem iniciar o transporte MCP, rode `uv run python src/mcp/server.py --health-json`.

### Embeddings Locais
O servidor MCP expõe `embedding_health`, `index_zettelkasten_embeddings` e `semantic_search_zettelkasten`. A implementação aceita `EMBEDDING_PROVIDER=hashing` para fallback offline determinístico ou `EMBEDDING_PROVIDER=ollama` para consultar um endpoint local compatível com Ollama, usando `EMBEDDING_MODEL_NAME=nomic-embed-text`.

### Novas Funcionalidades Agênticas
O projeto agora suporta recursos avançados de atrito semântico, reconciliação e colheita:
- **Ponte Semântica (`/bridge`):** Localiza notas com baixa similaridade no cofre e estimula conexões interdisciplinares.
- **Pesquisa Científica Profunda (`/research-deep`):** Conecta a bases de preprints e publicações (arXiv, OpenAlex) para suprir lacunas teóricas.
- **Colheita de Sessão (Harvesting):** Executado automaticamente no `/close` para transformar insights de chat em rascunhos de notas.
- **Auto-Reconciliação:** Mecanismo obrigatório de checagem contra redundâncias conceituais no cofre (registrado em `GEMINI.md`).

Para uma explicação detalhada e exemplos práticos de uso dessas funcionalidades, consulte o documento:
*   [Manual_Funcionalidades_Agente.md](Manual_Funcionalidades_Agente.md)

---

## Operação Diária e Casos de Uso
O ciclo diário inicia-se com `/start` para briefings e contextualização de metas, passa pela ingestão (`/ingest-paper`, `/ingest-article`, `/ingest-youtube`), validação cruzada (`/recall`), cruzamento interdisciplinar (`/bridge`), pesquisa de lacunas (`/research-deep`) e redação de sínteses (`/ghost`). O encerramento com `/close` realiza a colheita dos rascunhos conceituais e consolida o histórico.
