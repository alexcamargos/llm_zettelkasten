# /ingest-paper (Ingestão de documentos formais em papers)

## Objetivo
Processar **documentos formais** em **`raw/papers/`** (PDF ou equivalente típico de artigos, capítulos ou relatórios acadêmicos densos), extrair referência no padrão **ABNT**, mapear argumentos centrais e aguardar a validação humana antes de popular o Zettelkasten. Conteúdo informal da internet em Markdown fica em **`raw/articles/`** e usa o skill **`/ingest-article`**; transcrições do YouTube geradas pelo ETL usam **`/ingest-youtube`**.

## Gatilho
Acionado quando o usuário disser `gemini "Execute a skill /ingest-paper no arquivo raw/papers/[nome_do_arquivo]"` ou `/ingest-paper raw/papers/[nome_do_arquivo]`.

**Flags Opcionais:**
*   `--analyze-only` ou `-a`: Ativa o modo de apenas análise. O fluxo é concluído após a Etapa 2 com a gravação de um relatório estruturado em `zettelkasten/drafts/analise-[document_id].md`, sem poluir o cofre definitivo ou o índice geral.

**Log:** Ao acrescentar entradas em `.state/log.md`, use estritamente o formato definido no `GEMINI.md` (seção Convenção do log operacional). No cabeçalho da entrada use o nome da skill **`/ingest-paper`**. Liste no corpo da entrada **todos** os caminhos de arquivos tocados ou criados nesta execução.

---

## Fluxo de Execução (Workflow)

### PageIndex (MCP local) e cache em `.pageindex/`
Use este ramo conforme os seguintes critérios de tamanho e complexidade do PDF. Para documentos com **até 10 páginas**, adote leitura linear como padrão, salvo quando o PDF tiver OCR ruim, navegação difícil ou quando o usuário pedir explicitamente o uso de PageIndex. Para documentos entre **11 e 20 páginas**, trate o caso como zona cinzenta e use PageIndex quando houver densidade metodológica elevada, muitas tabelas, apêndices relevantes, OCR fraco ou necessidade provável de múltiplos retornos ao texto para confirmar método, variáveis ou resultados. Para documentos com **mais de 20 páginas**, use PageIndex por padrão. Em qualquer faixa, prefira este ramo quando a leitura integral do PDF na Etapa 1 for impraticável no ambiente.

**Pré-requisito humano:** o cliente (Gemini CLI, Cursor ou outro compatível com MCP) deve ter o servidor PageIndex em modo **local** conforme o fornecedor: comando `npx`, argumentos `-y` e `@pageindex/mcp` (Node.js ≥ 18). Referência: repositório [VectifyAI/pageindex-mcp](https://github.com/VectifyAI/pageindex-mcp).

**Identificador único (`document_id`):** calcule a impressão digital **SHA-256** do arquivo binário completo em `raw/papers/`, representada como **64 caracteres hexadecimais em minúsculas**. Siga **somente** a secção **Instrumentação obrigatória: `document_id` (SHA-256)** no topo do `GEMINI.md`.

**Persistência no repositório:** grave manualmente ou via `ZettelkastenBrain.persist_pdf_cache` o cache e o manifesto em `.pageindex/<document_id>/tree.json` e `manifest.json` respectivamente.

---

### Etapa 1: Estimativa Pré-Voo e Leitura Estrutural
1. Antes de realizar qualquer processamento conceitual profundo, **chame a ferramenta MCP `estimate_pdf_processing`** passando o caminho relativo do arquivo.
2. Apresente ao usuário as métricas calculadas: páginas detectadas, tamanho em bytes, contagem estimada de tokens de entrada e saída, tempo de processamento aproximado e os custos projetados em USD (Flash vs. Pro).
3. Se o PDF for altamente técnico (código, tabelas financeiras complexas, estatísticas), tente rodar a indexação passando a opção `engine="docling"` no MCP se o pacote estiver instalado, para extrair tabelas no formato Markdown perfeito. Se falhar ou não estiver disponível, utilize o PageIndex padrão.
4. Identifique os metadados acadêmicos e construa a referência bibliográfica rigorosa no padrão **ABNT**.
5. Formule um resumo geral do documento capturando o problema de pesquisa, a metodologia aplicada e os resultados.
6. Mapeie os conceitos-chave estruturando-os e categorizando-os implicitamente nos seguintes eixos:
   *   **Modelos e Frameworks:** Construtos ou diagramas conceituais propostos (ex: PEARLS, redes GAN).
   *   **Princípios Acionáveis:** Regras ou diretrizes práticas derivadas para orientar tomadas de decisão.
   *   **Técnicas Metodológicas:** Métodos práticos ou algoritmos estatísticos detalhados.
   *   **Anti-padrões:** Erros, falhas clássicas ou riscos a serem evitados de acordo com a obra.

### Etapa 2: Interação e Validação (Pausa Obrigatória)
1. Interrompa o processamento e apresente ao usuário na tela:
   a) A estimativa de tokens e custo obtida na Etapa 1.
   b) A referência ABNT gerada.
   c) O resumo geral da obra.
   d) A taxonomia estruturada de conceitos (Frameworks, Princípios, Técnicas e Anti-padrões).
2. Pergunte explicitamente: "Quais destes conceitos devemos aprofundar e transformar em Notas Permanentes?"
3. Se o modo `--analyze-only` estiver ativo, informe: *"A flag de apenas análise está ativa. O processamento será concluído com a geração do relatório de análise na pasta de rascunhos."*
4. Aguarde a resposta e a aprovação do usuário antes de prosseguir para a Etapa 3.

### Etapa 3: Geração das Notas e Evolução da Base

**Se o modo `--analyze-only` estiver ativo:**
1. Crie um arquivo contendo a análise estrutural da obra em `zettelkasten/drafts/analise-[document_id].md`.
2. O corpo do arquivo deve conter a referência ABNT, o resumo detalhado da obra, tabelas extraídas se aplicável, e a taxonomia conceitual nos quatro eixos. Prossiga diretamente para a Etapa 4.

**Caso contrário (Ingestão Completa):**
A partir da resposta do usuário, crie os arquivos aplicando rigorosamente as **Regras Globais de Estilo** (sem bullet points no corpo, prosa Feynman contínua, título `# Título da nota` após o frontmatter):

1. **Notas de Literatura Modulares por Capítulo/Seção:**
   *   Se o documento for extenso (mais de 30 páginas), **não crie uma nota de literatura gigante**.
   *   Crie um arquivo de literatura mestre (ex: `zettelkasten/literature/autor-ano-mestre.md`) contendo os metadados do YAML, resumo geral e a ABNT, e ligue-o a subnotas específicas por capítulo ou seção.
   *   Gere arquivos específicos para cada seção ou capítulo sob demanda (ex: `literature/autor-ano-ch01.md`), contendo a síntese de ideias daquela parte em prosa contínua.
   *   Se o documento for curto (<=30 páginas), crie uma única nota de literatura convencional em `zettelkasten/literature/`.
2. **Notas Permanentes Operacionalizáveis:**
   *   Crie notas atômicas em `zettelkasten/permanent/` para os conceitos selecionados.
   *   Estruture a narrativa da prosa Feynman destacando com clareza o papel prático dos conceitos: os **Frameworks**, as diretrizes de **Princípios de Decisão**, o passo a passo das **Técnicas** e as lições aprendidas de **Anti-padrões**.
   *   Antes de finalizar, execute a busca semântica na base e conecte a nova nota a pelo menos duas Notas Permanentes existentes com `[[wikilinks]]`. Se não houver candidatas, registre a limitação no `.state/log.md`.

### Etapa 4: Catalogação e Encerramento
1. **Indexação Dupla:** Acesse `zettelkasten/index.md` e adicione os links semânticos (ex: `[[nome-do-arquivo]]`) das novas notas (incluindo o relatório de análise em drafts se for analyze-only) em suas respectivas seções.
2. Atualize o `.state/log.md` registrando a ingestão, **listando explicitamente** cada caminho relativo criado ou alterado nesta execução (incluindo manifests e caches do PageIndex se gerados).
3. Atualize o `.state/hot.md` refletindo a nova adição ao foco da pesquisa.
