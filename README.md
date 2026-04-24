# Zettelkasten Modular via Gemini CLI

## Visão Geral do Sistema

**Introdução**
Este repositório estabelece a arquitetura oficial para o ecossistema de gestão de conhecimento pessoal e pesquisa acadêmica operado via interface de linha de comando. O projeto foi desenhado especificamente para suportar o rigor metodológico exigido em modelagem preditiva de risco e análise de indicadores financeiros.

**Contexto**
A arquitetura divide as responsabilidades de processamento de dados entre um arquivo mestre de configuração e múltiplas habilidades modulares. Cada habilidade executa uma função isolada e altamente especializada dentro do ambiente de terminal. O sistema orquestra desde a extração rigorosa de referências no padrão ABNT a partir de literatura acadêmica densa até a redação de rascunhos consolidados. O diretório raiz atua como o motor principal de indexação, enquanto a pasta de fontes abriga os documentos originais e a base de conhecimento armazena as conexões lógicas em desenvolvimento.

**Fechamento**
Esta organização metodológica garante o versionamento seguro de todo o escopo de pesquisa. A modularidade permite a manutenção contínua e a escalabilidade do sistema operacional, mantendo a integridade teórica exigida para a produção acadêmica de alto nível e aplicações de **Business Intelligence**.

## Estrutura de Diretórios do Projeto

Para garantir o funcionamento perfeito do agente local acionado pelo terminal, o repositório reflete a exata árvore de arquivos demonstrada abaixo.

```text
llm_zettelkasten/
├── README.md
├── GEMINI.md
├── .gemini/
│   └── skills/
│       ├── start.md
│       ├── ingest-paper.md
│       ├── ingest-paper-intro.md
│       ├── ingest-article.md
│       ├── recall.md
│       ├── visual.md
│       ├── lint.md
│       ├── trace.md
│       ├── ghost.md
│       └── close.md
├── .state/
│       ├── hot.md
│       └── log.md
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

Pastas sem notas ainda usam um arquivo **`.gitkeep`** (vazio) para o Git versionar o diretório; pode remover o `.gitkeep` quando existirem outros arquivos estáveis na mesma pasta.

## Instruções de Configuração e Integração

### Introdução
A inicialização em um novo ambiente resume-se a clonar o repositório, instalar o Gemini CLI conforme a documentação oficial e passar a operar na raiz do projeto. As pastas necessárias já vêm no clone; o foco segue sendo a mineração de dados acadêmicos com o agente.

### Contexto
O usuário deve clonar o repositório para o disco local utilizando um cliente de controle de versão. A árvore de pastas versionada (`raw/`, `zettelkasten/`, `.state/`) já vem preparada para uso imediato; adicione PDFs formais em `raw/papers/` (skills `/ingest-paper` e `/ingest-paper-intro`) e recortes informais da web em Markdown em `raw/articles/` (skill `/ingest-article`).

### Gemini CLI
Abra o **[Gemini CLI](https://geminicli.com/)** na **raiz deste repositório** (o diretório que contém `GEMINI.md`, `raw/`, `zettelkasten/` e `.state/`). O agente assim carrega o schema e as skills em `.gemini/skills/`. Para a versão instalada, siga o comando indicado na documentação da sua instalação (por exemplo `gemini --version`, se existir).

### Fechamento (configuração)
Com o CLI na raiz e o `GEMINI.md` presente, o ambiente está pronto para `/start` e demais comandos descritos no schema.

### Escala do cofre (opcional)
Enquanto o volume for modesto, **`index.md`** mais leitura dirigida costumam bastar. Quando o número de notas crescer (centenas de páginas ou descoberta pelo índice deixar de ser prática), considere ferramentas **externas** ao repositório, sem torná-las obrigatórias:

- **[qmd](https://github.com/tobi/qmd)** — busca local híbrida (BM25 e vetorial) com CLI e servidor MCP, útil para pré-filtrar antes de o agente abrir arquivos.
- **Obsidian CLI** (a partir do Obsidian 1.12) — acesso programático ao cache do vault; exige Obsidian instalado e documentação atual da sua versão. Reduz custo de varreduras puramente por sistema de arquivos em cofres muito grandes.

## Fechamento
Seguindo as etapas de inicialização, o ambiente de pesquisa estará perfeitamente ativo e blindado contra alucinações estruturais. O sistema operará com previsibilidade máxima para processar a literatura metodológica de forma contínua.

## Operação Diária e Casos de Uso
### Introdução
O fluxo de trabalho foi projetado para cobrir o ciclo completo da inteligência de negócios aplicada à pesquisa científica. Cada comando aciona um fluxo isolado e validado, garantindo que a rotina de estudos seja convertida em ativos de conhecimento mensuráveis e estruturados.

### Contexto
O fluxo operacional inicia com o comando de abertura de sessão para recuperar o estado atual do estudo sobre métricas de insolvência. Durante a leitura de um novo estudo formal, use `/ingest-paper` ou `/ingest-paper-intro` em `raw/papers/`; para artigos da web em `raw/articles/`, use `/ingest-article`, sempre com referência e validação humana conforme o `GEMINI.md`. Para cruzar os dados extraídos com indicadores financeiros previamente estudados, o comando de busca é acionado para recuperar a inteligência acumulada no cofre. A etapa de consolidação utiliza o comando de redação acadêmica para criar o rascunho estruturado do texto. O ciclo é finalizado utilizando o comando de encerramento para atualizar o contexto e preparar o ambiente de forma automática para a próxima rotina.

### Fechamento
A cadência operacional descrita transforma a interface de comando em um verdadeiro parceiro analítico. A previsibilidade estrutural elimina o atrito tecnológico e garante a sofisticação intelectual exigida em avaliações acadêmicas rigorosas e no mercado corporativo.
