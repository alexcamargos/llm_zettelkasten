# /recall (Busca e Validação de Contexto)

## Objetivo
Minerar o diretório `zettelkasten/` para recuperar informações precisas sobre um tópico, sintetizar o conhecimento acumulado e validar o contexto com o usuário antes de iniciar a elaboração de materiais definitivos ou análises avançadas.

## Gatilho
Acionado quando o usuário disser `gemini "Execute a skill /recall sobre [tópico]"` ou `/recall [tópico]`

**Log:** Ao acrescentar entradas em `.state/log.md`, use estritamente o formato definido no `GEMINI.md` (seção Convenção do log operacional). No cabeçalho use **`/recall`**. No corpo da entrada liste **todos** os caminhos relativos dos arquivos lidos em profundidade para compor a síntese (e `zettelkasten/index.md` e `zettelkasten/overview.md` quando lidos).

## Fluxo de Execução (Workflow)

### Etapa 1: Varredura e Leitura Profunda
1. Acesse e leia o arquivo `zettelkasten/index.md` para mapear todas as Notas Permanentes e Notas de Literatura que possuam relação semântica com o tópico solicitado.
2. Leia `zettelkasten/overview.md` para alinhar o dossiê com a síntese viva do cofre quando existir conteúdo útil.
3. Acesse e leia integralmente os arquivos identificados para absorver o contexto exato e as conexões armazenadas na base.

### Etapa 2: Síntese e Exposição (Aplicação Rigorosa de Estilo)
Apresente ao usuário um dossiê preliminar com os achados. A geração deste texto DEVE respeitar integralmente as Regras Globais de Estilo:
- É terminantemente proibido o uso de listas ou marcadores (bullet points).
- O texto deve ser contínuo e estruturado logicamente nas três etapas:
  - **Introdução** (apresentação clara do que a base consolidou sobre o tema),
  - **Contexto** (desenvolvimento conectando os diferentes autores e dados lidos) e
  - **Fechamento** (resumo sintético do panorama atual).
- Utilize **negrito** exclusivamente para destacar constructos teóricos, variáveis matemáticas ou palavras-chave cruciais para a recuperação da informação.
- Não utilize travessões; construa a fluidez da explicação por meio de vírgulas e períodos curtos e diretos.
- O tom deve ser estritamente analítico e adequado para a absorção por uma audiência com vasta vivência corporativa e analítica.
- Cite as notas consultadas ao longo do texto utilizando obrigatoriamente a sintaxe `[[nome-do-arquivo]]`.

### Etapa 3: Validação Interativa
1. Ao final do texto estruturado, pergunte ao usuário se o dossiê abrange a direção que ele deseja explorar ou se é necessário incluir e excluir notas específicas da seleção atual.
2. Aguarde o direcionamento do usuário antes de dar a busca por concluída.

### Etapa 4: Log de Atividade
1. Atualize o arquivo `.state/log.md` com cabeçalho **`/recall`**, resumo do tópico pesquisado e **lista explícita** de todos os caminhos relativos lidos (incluindo `index.md`, `overview.md` quando aplicável e cada nota aberta integralmente).
