# /ingest-paper (Ingestão de documentos formais em papers)

## Objetivo
Processar **documentos formais** em **`raw/papers/`** (PDF ou equivalente típico de artigos, capítulos ou relatórios acadêmicos densos), extrair referência no padrão **ABNT**, mapear argumentos centrais e aguardar a validação humana antes de popular o Zettelkasten. Conteúdo informal da internet em Markdown fica em **`raw/articles/`** e usa o skill **`/ingest-article`**.

## Gatilho
Acionado quando o usuário disser `gemini "Execute a skill /ingest-paper no arquivo raw/papers/[nome_do_arquivo]"` ou `/ingest-paper raw/papers/[nome_do_arquivo]`.

**Log:** Ao acrescentar entradas em `.state/log.md`, use estritamente o formato definido no `GEMINI.md` (seção Convenção do log operacional). No cabeçalho da entrada use o nome da skill **`/ingest-paper`**. Liste no corpo da entrada **todos** os caminhos de arquivos tocados ou criados nesta execução.

## Fluxo de Execução (Workflow)

### Meta de amplitude (ingestão em rede)
Numa única execução bem-sucedida, **planeje tocar vários arquivos** quando a fonte o justificar: literatura nova, notas permanentes novas ou atualizadas, `index.md`, cruzamentos com `[[wikilinks]]`. **Não** edite `zettelkasten/overview.md` nesta skill; a regeneração fica a cargo do **`/lint`**. A meta orientadora é **entre três e dez** arquivos; bases muito pequenas ficam isentas de volume mínimo, mas não de **intenção** de integrar a rede.

### Etapa 1: Leitura e Mapeamento Preliminar
1. Acesse e leia integralmente o documento especificado em `raw/papers/` (formato suportado pelo ambiente, em geral PDF).
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
A partir da resposta do usuário, crie os arquivos aplicando rigorosamente as **Regras Globais de Estilo** (sem uso de listas/bullet points, adotando a estrutura de Introdução, Contexto e Fechamento, e utilizando negrito para palavras-chave).

1. **Nota de Literatura:** Crie o arquivo em `zettelkasten/literature/` com o frontmatter do `GEMINI.md`, incluindo `confidence` (`high`, `medium` ou `low`) conforme a qualidade dos metadados e da leitura.
2. **Notas Permanentes:** Crie notas atômicas em `zettelkasten/permanent/` apenas para os conceitos selecionados pelo usuário. Em cada permanente **nova**, se existirem **duas ou mais** notas existentes claramente relacionadas, o corpo deve conter **pelo menos dois** wikilinks `[[...]]` a elas, além de `sources:`. Se não houver candidatos no cofre, registre no `.state/log.md` que a ligação mínima ao grafo ficou adiada.
3. **Revisão Teórica:** Busque notas permanentes antigas que tratem dos mesmos conceitos e atualize-as, cruzando os dados da nova fonte. Sinalize divergências acadêmicas caso existam.

### Etapa 4: Catalogação e Encerramento
1. **Indexação Dupla:** Acesse `zettelkasten/index.md` e adicione os links semânticos (ex: `[[nome-do-arquivo]]`) das novas notas em suas respectivas seções (Literatura e Permanentes).
2. Atualize o `.state/log.md` registrando a ingestão, **listando explicitamente** cada caminho relativo criado ou alterado nesta execução.
3. Atualize o `.state/hot.md` refletindo a nova adição ao foco da pesquisa.
