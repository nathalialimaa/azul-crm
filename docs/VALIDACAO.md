# Matriz final de requisitos — revisão dos originais em 26/10/2026

Fontes efetivamente lidas: **IntrucoesHackathonAzul.pdf (4 páginas)** e **Plataforma de Inteligência de CRM para Clientes de Alto Valor (25 seções)**, ambos enviados pela usuária via Drive. Hashes em `evidencias/integracao/fontes-requisitos.json`. Os documentos originais permanecem fora do repositório.

A matriz anterior citava páginas 5–9 inexistentes no PDF recebido. Esta revisão substitui aquelas referências. As exigências de entrega do enunciado estão na página 4; o núcleo obrigatório definido pela equipe está na seção 19.1 da proposta. “Caminhos possíveis” do enunciado e diferenciais da seção 19.2 não são confundidos com entregáveis obrigatórios.

| Requisito e fonte | Implementação e evidência | Avaliação |
|---|---|---|
| Carteira sintética calibrada por tarifa, rota e demanda (PDF p. 2–3; proposta 6–8 e 19.1) | Ingestão ANAC, demanda pública e VRA, geração com seed, validação SQL; preparo real com 400 clientes e 6.046 viagens | Implementado e testado; dados individuais são simulação |
| Arquitetura reaproveitável em camadas, esquemas e dicionário (PDF p. 3; proposta 5 e 7) | Store canônico, Parquet, lake com 17 tabelas, contratos e testes test_lake.py | Implementado e exportado; Snowflake tem adaptador, sem homologação real |
| Valor atual/futuro e CLV (PDF p. 2–3; proposta 10.1 e 19.1) | Score parametrizado, CLV baseline de margem descontada, sensibilidade e definição top 20%; test_clv.py | Núcleo obrigatório atendido por baseline; não é modelo preditivo de CLV treinado |
| Risco de evasão e avaliação (PDF p. 2; proposta 10.2) | Regressão logística comparada à heurística com validação temporal dos rótulos, AUC/PR-AUC/Brier e teste estatístico; test_model_selection.py e test_integrated.py | Treino e comparação implementados. Heurística mantida nesta base; não é probabilidade real calibrada |
| 3–5 segmentos acionáveis (proposta 19.1; PDF p. 3 sugere 3–4) | K-means, 4 personas, estabilidade/bootstrap e playbook | Implementado e testado |
| Priorização separando valor e risco (proposta 11 e 15) | Matriz, fila, valores em risco e filtros no painel/API | Implementado e testado |
| Próxima ação elegível e revisão humana (proposta 12–13 e 19.1) | Motor de regras por persona, NO_ACTION quando falta evidência, consentimento/checklist e decisões registradas sem envio | Implementado; ofertas comerciais permanecem hipóteses, sem concessão automática |
| RAG sobre regras públicas de fidelidade (proposta 13 e 19.1) | Regulamento público versionado no corpus, recuperação com citações, abstenção; agora inclui contexto público de comunicação nas recomendações | Implementado em recuperação lexical; contexto não certifica benefício/vigência |
| Agente baseado em LLM (PDF p. 2, caminhos possíveis; proposta 13) | Adaptador Ollama para perguntas com fontes e composição limitada de abertura/encerramento das mensagens, saída validada e fallback | Parcial: não escolhe livremente a ação nem redige benefícios; inferência real/avaliação humana de groundedness pendentes |
| Sentimento, assunto, intensidade, causa de atrito e etapa da jornada (proposta 10.4; diferencial em 19.2) | Serviço/API/CLI/painel com 7 temas, etapas, intensidade lexical e hipóteses de atrito; test_sentiment.py | Baseline implementado e testado; sem coleta automática/corpus real rotulado. Não associa opiniões a clientes |
| Explicabilidade (PDF p. 2 e 4; proposta 10.5 e 19.1) | Drivers e decomposição exata de Shapley, API/visão 360, referência explícita, versão/data; test_explanations.py | Implementado: 16 coalizões por saída e referência única. Não é SHAP condicional ou evidência causal |
| Cenários de custo/retorno sem alegação causal (proposta 14 e 19.2) | Simulador, retenção assumida, equilíbrio e comparação por persona | Implementado e testado; não estima uplift real |
| Dashboard e APIs (PDF p. 3–4; proposta 15–16) | FastAPI, oito páginas Streamlit, visão 360 e downloads | Verificado em servidores reais localhost, AppTest e HTTP |
| Premissas, substituição e IA responsável (PDF p. 2–4; proposta 18–19) | Dados sintéticos, contratos, auditoria, fontes, revisão humana e documentação | Implementado no MVP; avaliação produtiva continua necessária |
| Vídeo até 5 min, acesso funcional, repositório privado e submissão (PDF p. 4) | Roteiro organizado e projeto testado; privacidade e permissão de push verificadas via GitHub API | Repositório privado comprovado. Vídeo, hospedagem/acesso dos avaliadores e submissão não executados |

## O que não era obrigatório

A proposta 10.1 e 19.1 aceita **Customer Value Score ou CLV baseline**. Gradient boosting é condicional ao tempo; modelos causais, campanhas reais e sistemas internos estão fora do escopo inicial (19.3). Snowflake é uma tecnologia usada pela empresa, sem imposição de stack no enunciado. Nenhuma dessas observações comprova integrações que não foram executadas.

## Lacunas remanescentes, sem falsas promessas

1. Executar Ollama/modelos reais e avaliar geração/groundedness com revisores. A ação é selecionada pelo motor de regras; o adaptador acrescentado é limitado e não equivale a um agente autônomo completo.
2. Revisar vigência, autorização e condições específicas de benefícios antes de tornar uma oferta elegível. Consulta textual ao regulamento não é certificação automática.
3. Avaliar sentimento em avaliações públicas autorizadas e rotuladas; calibrar intensidade e temas. As “causas de atrito” são hipóteses de associação temática.
4. Avaliar a sensibilidade das atribuições de Shapley a outras referências representativas. O explicador entregue é exato com referência única; não modela dependência/correlação das variáveis.
5. Homologar Snowflake/MLflow se a demonstração escolher essas integrações; elas não são dependências do modo local.
6. Disponibilizar o protótipo em ambiente privado para avaliadores, gravar vídeo e realizar a submissão externa.

## Testes e evidências

A consolidação anterior passou em 213 testes completos. As mudanças desta leitura são verificadas em `evidencias/integracao/requisitos-testes.log` e no smoke atualizado. O pipeline ANAC já concluído não foi repetido porque entradas e ingestores não mudaram. Ver [CONSOLIDACAO.md](CONSOLIDACAO.md) para ambiente, comandos e resultados.


## Extensões do desenho completo da proposta

A proposta detalha um desenho maior do que o núcleo de 19.1. Campos como data de reserva, classe tarifária, tempo de conta, ruptura de conexão, experiência/reclamação por viagem e aceitação/conversão/valor incremental de campanhas ainda não fazem parte dos contratos canônicos atuais. Também não há calibração pública por opinião atribuída a cada cliente, feature de resposta a campanha ou otimização de orçamento. O sistema registra revisão de decisões, sem simular sucesso de campanha como resultado medido. Essas extensões não são apresentadas como funcionalidades prontas.
