# /ingest-paper-intro (Triagem da introdução de papers)

## Objetivo
Processar exclusivamente a seção introdutória (incluindo o resumo ou abstract) de documentos formais em **`raw/papers/`**. O foco é mapear a viabilidade teórica do documento e extrair os **conceitos iniciais apresentados pelo autor**, permitindo uma triagem antes da leitura integral. Recortes informais da web em **`raw/articles/`** usam **`/ingest-article`** (fluxo distinto).

## Gatilho
Acionado quando o usuário disser `gemini "Execute a skill /ingest-paper-intro no arquivo raw/papers/[nome_do_arquivo]"` ou `/ingest-paper-intro raw/papers/[nome_do_arquivo]`.

**Log:** Ao acrescentar entradas em `.state/log.md`, use estritamente o formato definido no `GEMINI.md` (seção Convenção do log operacional). No cabeçalho da entrada use o nome da skill **`/ingest-paper-intro`**. Liste todos os arquivos tocados ou criados.

## Fluxo de Execução (Workflow)

### Meta de amplitude
Quando criar literatura e permanentes, **integre em rede**: além do índice, atualize ou crie tantas ligações quanto fizer sentido: meta orientadora **três a dez** arquivos tocados quando a base já tiver notas suficientes; caso contrário, documente a rede mínima possível no log.

### Etapa 1: Leitura Delimitada e Extração
1. Acesse o documento especificado em `raw/papers/` e limite sua leitura estritamente ao **Resumo (Abstract)** e à **Introdução**. Ignore o restante do texto.
2. Identifique os metadados acadêmicos e construa a referência bibliográfica no padrão ABNT.
3. Formule um resumo focado em responder qual é o problema de pesquisa proposto e quais os principais conceitos ou variáveis apresentados inicialmente pelo autor.

### Etapa 2: Interação e Validação de Relevância
1. Apresente ao usuário na tela:
   a) A referência ABNT.
   b) O resumo do problema de pesquisa.
   c) Os conceitos-chave ou constructos teóricos introduzidos.
2. Pergunte explicitamente: "Com base nesta introdução, este artigo justifica uma leitura completa ou devemos apenas criar as notas dos conceitos preliminares mapeados?"
3. Aguarde o direcionamento do usuário.

### Etapa 3: Geração de Notas (Aplicação Rigorosa de Estilo)
Se o usuário aprovar a criação das notas preliminares, gere os arquivos aplicando todas as Regras de Estilo e Qualidade de Escrita estipuladas no arquivo principal.

**Regras estritas para a geração do texto das notas:**
- É terminantemente proibido o uso de listas ou marcadores (bullet points).
- O texto de cada nota deve ser contínuo e estruturado logicamente em três etapas: **Introdução** (apresentação clara da ideia), **Contexto** (provas ou desenvolvimento do autor) e **Fechamento** (resumo sintético da aplicação).
- Utilize **negrito** exclusivamente para destacar as palavras-chave e conceitos centrais, facilitando a recuperação da informação.
- Não utilize travessões. Empregue vírgulas ou construa períodos curtos e diretos para explicações.
- Não utilize emojis.

1. **Nota de Literatura:** Crie o arquivo em `zettelkasten/literature/` com frontmatter do `GEMINI.md`, `confidence` adequado, `source_file` sob `raw/papers/`, referência ABNT e resumo da introdução.
2. **Notas Permanentes:** Crie notas atômicas em `zettelkasten/permanent/` apenas para os conceitos validados. Para cada permanente **nova**, aplique a **ligação mínima ao grafo** do `GEMINI.md` (dois wikilinks no corpo quando existirem candidatos); caso impossível, registre no log.

### Etapa 4: Catalogação
1. Acesse `zettelkasten/index.md` e adicione os links semânticos (textuais) das novas notas em suas respectivas seções.
2. Atualize o `.state/log.md` com cabeçalho **`/ingest-paper-intro`** e **lista explícita** de todos os caminhos relativos criados ou alterados (literatura, permanentes, `index.md`, `hot.md` se tocado).
3. Atualize o `.state/hot.md` refletindo a nova adição ao foco da pesquisa.
