# /ghost (Redação Acadêmica e Síntese Textual)

## Objetivo
Atuar como um assistente de redação acadêmica avançada. O foco é minerar o conhecimento validado no Zettelkasten, debater ativamente a estrutura do texto com o usuário e redigir rascunhos de alta densidade técnica para capítulos de dissertações ou artigos estruturados. Todo o material gerado deve ser salvo isoladamente no diretório `zettelkasten/drafts/`.

## Gatilho
Acionado quando o usuário disser `gemini "Execute a skill /ghost para escrever sobre [tópico]"` ou `/ghost [tópico]`

**Log:** Ao acrescentar entradas em `.state/log.md`, use estritamente o formato definido no `GEMINI.md` (seção Convenção do log operacional). No cabeçalho use **`/ghost`**. No corpo liste **todos** os caminhos relativos de arquivos criados ou alterados e das notas lidas como base (enumerando cada caminho).

## Fluxo de Execução (Workflow)

### Etapa 1: Mineração e Escopo Inicial
1. Acesse `zettelkasten/index.md` e localize todas as Notas Permanentes e Notas de Literatura relevantes ao tópico solicitado.
2. Leia o conteúdo destas notas para compreender o panorama teórico, os dados estatísticos disponíveis e as divergências entre autores.

### Etapa 2: Alinhamento Estratégico (Pausa Obrigatória e Interação)
É terminantemente proibido iniciar a redação do texto antes de concluir esta etapa. Apresente ao usuário um plano de voo contendo:
1. **Notas Selecionadas:** A lista das notas que serão utilizadas como base (com seus respectivos links).
2. **Proposta de Tese:** Qual será o argumento central ou a conclusão lógica deste rascunho.
3. **Esqueleto do Texto:** Um resumo de uma linha do que será abordado na Introdução, no Contexto e no Fechamento.
4. **Interação Exigida:** Pergunte explicitamente ao usuário:
   a) "Devemos incluir ou excluir alguma nota específica desta seleção?"
   b) "A proposta de tese está alinhada com seu objetivo ou devemos focar em outro ângulo analítico?"
   c) "Existe alguma variável, algoritmo ou métrica que exige destaque obrigatório neste texto?"
5. Aguarde o retorno detalhado do usuário e refine o esqueleto até obter a aprovação final.

### Etapa 3: Execução da Escrita (Aplicação Rigorosa de Estilo)
Somente após a aprovação do plano pelo usuário, inicie a redação. O texto gerado DEVE obedecer de forma inegociável às **Regras Globais de Estilo**:
- É terminantemente proibido o uso de listas ou marcadores (bullet points).
- Estruture a redação em blocos contínuos e articulados, refletindo claramente as seções de **Introdução** (apresentação do problema ou conceito acadêmico), **Contexto** (desenvolvimento das provas, cruzamento de dados, citação de autores e metodologias) e **Fechamento** (conclusão lógica e impacto do conceito no modelo estudado).
- Aplique a **Técnica Feynman** adaptada para um público de nível executivo e pós-graduação. Simplifique a complexidade matemática ou estatística preservando o rigor técnico.
- Aplique **negrito** exclusivamente para destacar constructos teóricos, variáveis de modelo e termos técnicos centrais.
- Não utilize travessões. A fluidez explicativa deve ser construída com vírgulas e períodos diretos.
- Não utilize emojis.
- Todo dado ou conceito extraído de uma nota deve ser referenciado ao longo do texto utilizando o wikilink correspondente (ex: `[[nome-da-nota]]`). Quando aplicável, inclua a citação ABNT no corpo do texto.

### Etapa 4: Salvamento e Indexação
1. Salve o rascunho completo em um novo arquivo no diretório `zettelkasten/drafts/rascunho-[tópico].md`.
2. Adicione o link semântico do novo rascunho ao arquivo `zettelkasten/index.md` na seção correspondente a rascunhos em andamento.
3. Atualize o arquivo `.state/log.md` com cabeçalho **`/ghost`**, caminho do rascunho criado, alterações em `zettelkasten/index.md` se houver, e **lista explícita** de cada nota de fonte lida em profundidade.
