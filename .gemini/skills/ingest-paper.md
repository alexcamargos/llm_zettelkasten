# /ingest-paper (Ingestão de documentos formais em papers)

## Objetivo
Processar **documentos formais** em **`raw/papers/`** (PDF ou equivalente típico de artigos, capítulos ou relatórios acadêmicos densos), extrair referência no padrão **ABNT**, mapear argumentos centrais e aguardar a validação humana antes de popular o Zettelkasten. Conteúdo informal da internet em Markdown fica em **`raw/articles/`** e usa o skill **`/ingest-article`**.

## Gatilho
Acionado quando o usuário disser `gemini "Execute a skill /ingest-paper no arquivo raw/papers/[nome_do_arquivo]"` ou `/ingest-paper raw/papers/[nome_do_arquivo]`.

**Log:** Ao acrescentar entradas em `.state/log.md`, use estritamente o formato definido no `GEMINI.md` (seção Convenção do log operacional). No cabeçalho da entrada use o nome da skill **`/ingest-paper`**. Liste no corpo da entrada **todos** os caminhos de arquivos tocados ou criados nesta execução.

## Fluxo de Execução (Workflow)

### PageIndex (MCP local) e cache em `.pageindex/`
Use este ramo quando o documento for **grande** (muitas páginas ou uso intensivo de contexto), quando o usuário pedir explicitamente PageIndex, ou quando a leitura integral do PDF na Etapa 1 for impraticável no ambiente.

**Pré-requisito humano:** o cliente (Gemini CLI, Cursor ou outro compatível com MCP) deve ter o servidor PageIndex em modo **local** conforme o fornecedor: comando `npx`, argumentos `-y` e `@pageindex/mcp` (Node.js ≥ 18). Referência: repositório [VectifyAI/pageindex-mcp](https://github.com/VectifyAI/pageindex-mcp).

**Identificador único (`document_id`):** calcule a impressão digital **SHA-256** do arquivo binário completo em `raw/papers/`, representada como **64 caracteres hexadecimais em minúsculas**. Essa string é o nome da subpasta. Siga **somente** a secção **Instrumentação obrigatória: `document_id` (SHA-256)** no topo do `GEMINI.md` (ferramenta normativa: PowerShell **`Get-FileHash`** no Windows); não derive o hash por leitura parcial do PDF no modelo nem por APIs não determinísticas. No **`manifest.json`**, preencha **`hash_tool`** conforme o método usado (ex.: `powershell_get_file_hash` ou `python_hashlib_sha256`). Se já existir `.pageindex/<document_id>/tree.json` com `manifest.json` cujo `source_path` e `byte_size` coincidam com o PDF atual, **reutilize** o cache, salvo instrução do usuário em contrário.

**Persistência no repositório:** após obter a árvore PageIndex (via ferramentas expostas pelo MCP), grave **exatamente** estes arquivos (crie a pasta se necessário):
1. `.pageindex/<document_id>/tree.json` — saída estrutural PageIndex (JSON).
2. `.pageindex/<document_id>/manifest.json` — metadados conforme o `GEMINI.md` (seção Manifest PageIndex), incluindo `indexed_at` em UTC, `index_source: "pageindex_mcp_local"` e `mcp_transport` descrevendo o `npx` utilizado.

**Leitura na Etapa 1:** em vez de depender só da leitura integral do PDF no contexto, utilize o `tree.json` (e ferramentas MCP adicionais, se disponíveis) para mapear seções, pedir confirmação de cobertura metodológica quando fizer sentido, e ancorar citações. O PDF em `raw/papers/` permanece a fonte de verdade para trechos citados.

**Log e cache quente:** ao criar ou atualizar o cache, a entrada em `.state/log.md` deve listar **obrigatoriamente** o PDF, `tree.json` e `manifest.json`. Ao atualizar `.state/hot.md` na Etapa 4, mencione em prosa o nome do PDF e o `document_id` quando esta ingestão tiver usado PageIndex, conforme o `GEMINI.md`.

### Meta de amplitude (ingestão em rede)
Numa única execução bem-sucedida, **planeje tocar vários arquivos** quando a fonte o justificar: literatura nova, notas permanentes novas ou atualizadas, `index.md`, cruzamentos com `[[wikilinks]]`. **Não** edite `zettelkasten/overview.md` nesta skill; a regeneração fica a cargo do **`/lint`**. A meta orientadora é **entre três e dez** arquivos; bases muito pequenas ficam isentas de volume mínimo, mas não de **intenção** de integrar a rede.

### Etapa 1: Leitura e Mapeamento Preliminar
1. Acesse o documento em `raw/papers/`. Se o fluxo **PageIndex (MCP local)** se aplicar, siga a subseção acima antes de sintetizar; caso contrário, leia integralmente o documento (formato suportado pelo ambiente, em geral PDF).
2. Identifique os metadados acadêmicos (autores, título, ano, publicação) e construa a referência bibliográfica rigorosa no padrão **ABNT**.
3. Formule um resumo geral do documento capturando o problema de pesquisa, a metodologia aplicada e os resultados alcançados.
4. Isole os conceitos-chave, variáveis estatísticas ou constructos teóricos abordados no texto.

### Etapa 2: Interação e Validação (Pausa Obrigatória)
1. Interrompa o processamento e apresente ao usuário na tela:
   a) A referência ABNT gerada.
   b) O resumo geral do documento.
   c) Os conceitos-chave identificados.
2. Pergunte explicitamente: "Quais destes conceitos devemos aprofundar e transformar em Notas Permanentes?"
3. Aguarde a resposta e a aprovação do usuário antes de prosseguir para a Etapa 3.

### Etapa 3: Geração das Notas e Evolução da Base
A partir da resposta do usuário, crie os arquivos aplicando rigorosamente as **Regras Globais de Estilo** (sem uso de listas/bullet points, com título obrigatório no corpo da nota e progressão lógica de Introdução, Contexto e Fechamento em parágrafos, sem rótulos literais desses blocos).

1. **Nota de Literatura:** Crie o arquivo em `zettelkasten/literature/` com o frontmatter do `GEMINI.md`, incluindo `confidence` (`high`, `medium` ou `low`) conforme a qualidade dos metadados e da leitura. No corpo, inclua `# Título da nota` logo após o YAML e redija em prosa contínua.
2. **Notas Permanentes:** Crie notas atômicas em `zettelkasten/permanent/` apenas para os conceitos selecionados pelo usuário. Cada nota deve começar com `# Título da nota` após o YAML. Antes de finalizar o corpo, pesquise no cofre por notas relacionadas por tema, variável, método ou causalidade e conecte com `[[wikilinks]]`. Em cada permanente **nova**, se existirem **duas ou mais** notas claramente relacionadas, o corpo deve conter **pelo menos dois** wikilinks `[[...]]` além de `sources:`. Se não houver candidatos, registre no `.state/log.md` que a ligação mínima ao grafo ficou adiada.
3. **Revisão Teórica:** Busque notas permanentes antigas que tratem dos mesmos conceitos e atualize-as, cruzando os dados da nova fonte. Sinalize divergências acadêmicas caso existam.

### Etapa 4: Catalogação e Encerramento
1. **Indexação Dupla:** Acesse `zettelkasten/index.md` e adicione os links semânticos (ex: `[[nome-do-arquivo]]`) das novas notas em suas respectivas seções (Literatura e Permanentes).
2. Atualize o `.state/log.md` registrando a ingestão, **listando explicitamente** cada caminho relativo criado ou alterado nesta execução.
3. Atualize o `.state/hot.md` refletindo a nova adição ao foco da pesquisa.
